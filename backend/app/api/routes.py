"""HTTP routes. Thin: they validate input and call the gateway. Shapes are in docs/architecture/gateway-and-api.md.

Owner: Tri (backend/app/api/). Cayden wrote the first version so the console had something to read.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import threading

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel, ValidationError

from app.agents import runner as agent_runner
from app.agents import settings as agent_settings
from app.agents.jobs import advance
from app.api import certificate as cert_doc
from app.api import export as export_doc
from app.api.events import next_events
from app.api.schemas import CaseResponse, DealCreated, HealthResponse
from app.core.models import CONTROLLER, SYSTEM, Brief, Deal, State
from app.db.loader import MAX_BYTES, LoaderError, parse_statement_csv
from app.gateway.gateway import Gateway, GatewayError


class AnswerBody(BaseModel):
    option_id: str


class ReasonBody(BaseModel):
    reason: str


class ToolBody(BaseModel):
    deal_id: str
    inputs: dict = {}


class RunBody(BaseModel):
    backend: str | None = None  # anthropic, droid, scripted, replay; default from AGENT_BACKEND
    sync: bool = True


def _debt_capacity(store, result) -> tuple[float | None, str | None]:
    """Room for the next deal. The number comes from the Reviewer's limit_test tool run, never from the route."""
    ids = result.review.run_ids if result and result.review else []
    runs = [t for t in store.tool_runs.values() if t.tool == "limit_test" and t.run_id in ids]
    for t in reversed(runs):
        value = t.outputs.get("debt_capacity")
        if value is not None:
            return value, t.run_id
    return None, None


SENSITIVITY_KEYS = ("naive_debt", "naive_ebitda", "naive_leverage", "naive_flip_addback")


def _whole_line_runs(store, deal_id: str) -> tuple[str, str] | None:
    """The covenant_debt and as-filed ebitda runs behind the covenant flag option that counts every flagged line as
    debt: the whole-line reading, which the gateway computes as filed (balance sheet debt over reported EBITDA).

    After the controller answers, the flagged lines carry their settled tags, so a fresh naive covenant_debt run
    no longer gives the whole-line figure. The option's what-if run, made by the gateway when the flag opened, does.
    The chain is option limit_test run -> its leverage run -> its covenant_debt and ebitda runs. Run ids only."""
    for item in reversed(store.deal_items(deal_id)):
        if item.type != "flag" or item.payload.get("kind") != "covenant_tag":
            continue
        actions = item.payload.get("option_actions", {})
        for opt in item.options:
            tags = actions.get(opt.id, {}).get("tags", {})
            if not opt.run_id or not tags or any(t != "debt" for t in tags.values()):
                continue
            test = store.tool_runs.get(opt.run_id)
            lev = store.tool_runs.get(test.inputs.get("leverage_run_id", "")) if test else None
            debt = store.tool_runs.get(lev.inputs.get("debt_run_id", "")) if lev else None
            eb = store.tool_runs.get(lev.inputs.get("ebitda_run_id", "")) if lev else None
            if debt and debt.tool == "covenant_debt" and eb and eb.tool == "ebitda":
                return debt.run_id, eb.run_id
    return None


# Leverage runs whose sensitivity run failed, keyed by (deal id, run id, run time) because /dev/reset restarts the
# run ids. Not retried on later reads, so a failure adds one audit row, not one per read.
_SENSITIVITY_FAILED: set[tuple[str, str, str]] = set()


def _sensitivity(gw: Gateway, deal: Deal, result) -> dict | None:
    """How far the whole-line reading (as filed) is from the limit, from a limit_test run made by the gateway.

    Only for a result the Reviewer passed, and only when a covenant flag option gives the whole-line covenant_debt
    run. With no such flag (for example a second run where a policy settled the lines) nothing runs and the keys
    are left out: a fresh naive run would read the settled tags, not the whole-line reading.
    A run already made for this result's leverage run is reused, so reading /case twice does not add runs.
    A gateway error returns None and is remembered per leverage run, so an optional figure never fails /case."""
    if not result or not result.review or result.review.verdict != "pass":
        return None
    lev_id = result.run_ids_by_tool.get("leverage")
    lev = gw.store.tool_runs.get(lev_id) if lev_id else None
    if lev is None:
        return None
    failed_key = (deal.id, lev.run_id, lev.at.isoformat())
    if failed_key in _SENSITIVITY_FAILED:
        return None
    with gw.lock:  # find-or-create in one step, so two reads cannot both create a run
        run = next((t for t in reversed(list(gw.store.tool_runs.values()))
                    if t.deal_id == deal.id and t.tool == "limit_test" and t.inputs.get("sensitivity") is True
                    and t.inputs.get("leverage_run_id") == lev_id), None)
        if run is None:
            naive = _whole_line_runs(gw.store, deal.id)
            if naive is None:
                return None
            try:
                run = gw.run_tool(SYSTEM, deal.id, "limit_test",
                                  {"leverage_run_id": lev_id, "naive_debt_run_id": naive[0],
                                   "naive_ebitda_run_id": naive[1], "sensitivity": True})
            except GatewayError:
                _SENSITIVITY_FAILED.add(failed_key)
                return None
    out = {k: run.outputs.get(k) for k in SENSITIVITY_KEYS}
    out["sensitivity_run_id"] = run.run_id
    return out


def first_non_finite(brief: Brief) -> str | None:
    """Path of the first NaN or infinite figure in the brief, or None. A cap may be None."""
    fields = []  # limit has its own check in the route
    for group in ("ebitda_addbacks", "ebitda_deductions"):
        for i, adj in enumerate(getattr(brief, group)):
            fields += [(f"{group}[{i}].amount", adj.amount), (f"{group}[{i}].cap", adj.cap)]
    fields += [(f"closing_financing[{i}].amount", f.amount) for i, f in enumerate(brief.closing_financing)]
    return next((path for path, v in fields if v is not None and not math.isfinite(v)), None)


def build_router(gw: Gateway) -> APIRouter:
    r = APIRouter()
    store = gw.store

    def guard(fn):
        try:
            return fn()
        except GatewayError as error:
            raise HTTPException(status_code=error.status, detail=error.message)

    def dump(model):
        return model.model_dump(mode="json")

    def need_deal(deal_id: str):
        deal = store.deals.get(deal_id)
        if not deal:
            raise HTTPException(status_code=404, detail="deal not found")
        return deal

    def backend_status() -> dict:
        return {
            "configured": os.getenv("AGENT_BACKEND", "scripted"),
            "fallback": os.getenv("AGENT_FALLBACK", "scripted"),
            "anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
            "factory_key": bool(os.getenv("FACTORY_API_KEY")),
            "last_runs": agent_runner.LAST_RUNS[-6:],
            "totals_this_process": agent_runner.TOTALS,
            "settings": agent_settings.summary(),
        }

    # One job per deal at a time. Answering the last flag starts the job runner, so a Run click at the same moment
    # would start a second Preparer; the gateway would deny its result, but the click should get a clear 409 instead.
    running: set[str] = set()
    running_lock = threading.Lock()
    gw.running = running  # /dev/reset refuses while a run is in flight

    def claim(deal_id: str) -> bool:
        with running_lock:
            if deal_id in running:
                return False
            running.add(deal_id)
            return True

    def release(deal_id: str) -> None:
        with running_lock:
            running.discard(deal_id)

    def run_in_background(deal_id: str, backend: str | None, tasks: BackgroundTasks) -> bool:
        if not claim(deal_id):
            return False
        tasks.add_task(_safe_advance, deal_id, backend)
        return True

    def _safe_advance(deal_id: str, backend: str | None):
        try:
            advance(gw, deal_id, backend=backend)
        except Exception as error:  # keep the server up; the audit log and LAST_RUNS hold the trace
            agent_runner.LAST_RUNS.append({"role": "runner", "backend": backend, "error": str(error)[:300]})
            try:
                gw.note_run_failed(deal_id, f"{type(error).__name__}: {error}")
            except Exception:  # noqa: BLE001 - the deal may have been reset meanwhile
                pass
        finally:
            release(deal_id)

    # ------------------------------------------------------------------ reads
    @r.get("/health", response_model=HealthResponse)
    def health():
        forks = gw.forks.status() if gw.forks else {"enabled": False}
        return {"ok": True, "chain_valid": gw.verify_chain(), "backend": backend_status(),
                "store": {**store.status(), "forks": forks}}

    @r.get("/deals")
    def deals():
        return [dump(d) for d in store.deals.values()]

    @r.get("/deals/{deal_id}")
    def deal(deal_id: str):
        return dump(need_deal(deal_id))

    @r.get("/deals/{deal_id}/case", response_model=CaseResponse)
    def case(deal_id: str):
        """The whole screen in one read: lines, mappings, flags, result, verdict, log summary."""
        d = need_deal(deal_id)
        items = store.deal_items(deal_id)
        flags = [i for i in items if i.type == "flag"]
        result = store.latest_result(deal_id)
        approval = next((i for i in reversed(items) if i.type == "approve_result"
                         and i.state not in (State.REJECTED, State.REVERSED)), None)
        verdict = None
        if result:
            capacity, capacity_run = _debt_capacity(store, result)
            verdict = {"leverage": result.leverage, "limit": result.limit, "verdict": result.verdict,
                       "headroom_turns": result.headroom_turns, "ebitda": result.ebitda, "debt": result.debt,
                       "debt_term": d.brief.debt_term, "debt_capacity": capacity,
                       "debt_capacity_run_id": capacity_run, "review": dump(result.review) if result.review else None,
                       "tie_out_ok": result.tie_out_ok, "backend": result.backend,
                       "approval_item": approval.id if approval else None,
                       "approval_state": approval.state.value if approval else None,
                       "posted": d.stage == "posted"}
            verdict.update(_sensitivity(gw, d, result) or {})
        return {
            "deal": dump(d),
            "stage": d.stage,
            "source_lines": [dump(l) for l in store.lines(deal_id)],
            "mappings": [dump(m) for m in store.deal_mappings(deal_id)],
            "flags": [dump(f) for f in flags],
            "open_flags": [f.id for f in flags if f.state == State.NEEDS_INFO],
            "result": dump(result) if result else None,
            "verdict": verdict,
            "work_items": [dump(i) for i in items],
            "policies": [dump(p) for p in store.policies.values()],
            "sessions": [dump(s) for s in store.sessions.values()],
            "audit": {"rows": len([a for a in store.audit if a.deal_id == deal_id]), "chain_valid": gw.verify_chain(),
                      "denied": len([a for a in store.audit if a.deal_id == deal_id and a.result == "DENIED"])},
            "backend": backend_status(),
        }

    def need_posted(deal_id: str, what: str):
        """The deal, its items, and its result, once the controller approved that result and it is posted; else 409.
        The certificate and the final workbook share this gate so the two cannot drift."""
        d = need_deal(deal_id)
        items = store.deal_items(deal_id)
        result = store.latest_result(deal_id)
        approval = cert_doc.approval_item(items, result) if result else None
        if (not result or not approval or approval.payload.get("result_id") != result.id
                or approval.state != State.POSTED or d.stage != "posted"):
            raise HTTPException(status_code=409, detail=f"{what} available after the controller approves the result")
        return d, items, result

    @r.get("/deals/{deal_id}/certificate")
    def certificate(deal_id: str, format: Literal["md", "html", "json"] = "md"):
        """Draft compliance certificate from the approved, posted result. Every figure carries its run id."""
        d, items, result = need_posted(deal_id, "certificate is")
        doc = cert_doc.build_certificate(store, d, result, items, chain_valid=gw.verify_chain())
        if format == "json":
            return doc
        if format == "html":
            return HTMLResponse(cert_doc.render_html(doc))
        return Response(cert_doc.render_markdown(doc), media_type="text/markdown; charset=utf-8")

    @r.get("/deals/{deal_id}/export.xlsx")
    def export_xlsx(deal_id: str):
        """The combined books as a workbook (Combined, Edits, Audit), from the approved, posted result."""
        d, items, result = need_posted(deal_id, "final files are")
        wb = export_doc.build_workbook(store, d, result, items, chain_valid=gw.verify_chain())
        name = export_doc.export_filename(d.platform, d.target)
        return Response(export_doc.workbook_bytes(wb), media_type=export_doc.XLSX_MEDIA_TYPE,
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @r.get("/deals/{deal_id}/source-lines")
    def source_lines(deal_id: str, company: str | None = None):
        need_deal(deal_id)
        return [dump(l) for l in store.lines(deal_id, company)]

    @r.get("/deals/{deal_id}/mappings")
    def mappings(deal_id: str):
        need_deal(deal_id)
        return [dump(m) for m in store.deal_mappings(deal_id)]

    @r.get("/deals/{deal_id}/result")
    def result(deal_id: str):
        need_deal(deal_id)
        res = store.latest_result(deal_id)
        if not res:
            raise HTTPException(status_code=404, detail="no result yet")
        return dump(res)

    @r.get("/deals/{deal_id}/work-items")
    def work_items(deal_id: str, state: str | None = None, type: str | None = None):
        need_deal(deal_id)
        items = store.deal_items(deal_id, type)
        if state:
            items = [i for i in items if i.state.value == state]
        return [dump(i) for i in items]

    @r.get("/deals/{deal_id}/audit")
    def audit(deal_id: str):
        need_deal(deal_id)
        return {"chain_valid": gw.verify_chain(), "rows": [dump(a) for a in store.audit if a.deal_id == deal_id]}

    @r.get("/deals/{deal_id}/timeline")
    def timeline(deal_id: str, bucket: int = Query(60, ge=1, le=86400)):
        """Audit rows per time bucket, actor, and action family. On Postgres it runs TimescaleDB time_bucket."""
        need_deal(deal_id)
        return store.timeline(deal_id, bucket)

    @r.get("/deals/{deal_id}/runs")
    def runs(deal_id: str):
        need_deal(deal_id)
        return [dump(t) for t in store.tool_runs.values() if t.deal_id == deal_id]

    @r.get("/runs/{run_id}")
    def run(run_id: str):
        t = store.tool_runs.get(run_id)
        if not t:
            raise HTTPException(status_code=404, detail="run not found")
        return dump(t)

    @r.get("/agents/memory")
    def memory():
        return {"policies": [dump(p) for p in store.policies.values()],
                "sessions": [dump(s) for s in store.sessions.values()], "backend": backend_status()}

    # ------------------------------------------------------------------ writes (human)
    async def read_upload(field: str, upload: UploadFile) -> str:
        """Read one CSV upload with a hard size cap. Never trusts content-length."""
        if not (upload.filename or "").lower().endswith(".csv"):
            raise HTTPException(status_code=422, detail=f"{field}: file name must end in .csv")
        raw = await upload.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise HTTPException(status_code=422, detail=f"{field}: file is larger than {MAX_BYTES // (1024 * 1024)} MB")
        try:
            return raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise HTTPException(status_code=422, detail=f"{field}: file is not valid UTF-8")

    @r.post("/deals", status_code=201, response_model=DealCreated)
    async def create_deal(name: str = Form(..., min_length=1, max_length=200),
                          platform: str = Form(..., min_length=1, max_length=100),
                          target: str = Form(..., min_length=1, max_length=100),
                          brief: str = Form(...),
                          platform_csv: UploadFile = File(...), target_csv: UploadFile = File(...),
                          x_actor: str = Header(default=CONTROLLER)):
        """Load an unseen deal from two statement CSVs and a brief (JSON). Does not run the deal.

        The console calls POST /deals/{id}/run next. /dev/reset reseeds only the demo deal, so uploaded deals
        are lost on reset, which is fine for the demo.
        """
        guard(lambda: gw._require(x_actor, "create_deal", deal_id="-"))  # a denial is audited, before any file is parsed
        name, platform, target = name.strip(), platform.strip(), target.strip()
        if not name or not platform or not target or platform.lower() == target.lower():
            raise HTTPException(status_code=422, detail="name, platform and target are required, and platform and target must differ")
        platform_text = await read_upload("platform_csv", platform_csv)
        target_text = await read_upload("target_csv", target_csv)
        try:
            parsed_brief = Brief.model_validate_json(brief)
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=f"brief: {error.errors()[0]['loc']} {error.errors()[0]['msg']}")
        bad_path = first_non_finite(parsed_brief)
        if bad_path:
            raise HTTPException(status_code=422, detail=f"brief: {bad_path} must be finite")
        if not math.isfinite(parsed_brief.limit) or parsed_brief.limit <= 0:
            raise HTTPException(status_code=422, detail="brief: limit must be a finite number greater than 0")
        deal_id = store.next_id("d")
        loaded = {}
        for field, company, text in (("platform_csv", platform, platform_text), ("target_csv", target, target_text)):
            try:
                loaded[field] = parse_statement_csv(text, company, deal_id, store.next_id)
            except (LoaderError, ValueError, ValidationError) as error:
                raise HTTPException(status_code=422, detail=f"{field}: {error}")
        deal = Deal(id=deal_id, name=name, platform=platform, target=target, brief=parsed_brief)
        guard(lambda: gw.create_deal(x_actor, deal, loaded["platform_csv"] + loaded["target_csv"]))
        return {"deal_id": deal_id, "stage": deal.stage,
                "lines": {"platform": len(loaded["platform_csv"]), "target": len(loaded["target_csv"])}}

    @r.post("/deals/{deal_id}/run")
    def run_deal(deal_id: str, body: RunBody | None = None, tasks: BackgroundTasks = None,
                 x_actor: str = Header(default=CONTROLLER)):
        need_deal(deal_id)
        body = body or RunBody()
        if not gw._allowed(x_actor, "run"):
            raise HTTPException(status_code=403, detail=f"{x_actor} may not run")
        if body.sync:
            if not claim(deal_id):
                raise HTTPException(status_code=409, detail="a run is already in progress for this deal")
            try:
                return {"ok": True, "log": advance(gw, deal_id, backend=body.backend), "stage": store.deals[deal_id].stage}
            except GatewayError as error:
                raise HTTPException(status_code=error.status, detail=error.message)
            except Exception as error:
                raise HTTPException(status_code=500, detail=str(error)[:300])
            finally:
                release(deal_id)
        if not run_in_background(deal_id, body.backend, tasks):
            raise HTTPException(status_code=409, detail="a run is already in progress for this deal")
        return {"ok": True, "log": ["started"], "stage": store.deals[deal_id].stage}

    @r.post("/work-items/{item_id}/answer")
    def answer(item_id: str, body: AnswerBody, tasks: BackgroundTasks, x_actor: str = Header(default=CONTROLLER),
               auto_advance: bool = True):
        item = guard(lambda: gw.answer(x_actor, item_id, body.option_id))
        if auto_advance and not gw.open_flags(item.deal_id):
            run_in_background(item.deal_id, None, tasks)
        return dump(item)

    @r.post("/work-items/{item_id}/hold")
    def hold(item_id: str, x_actor: str = Header(default=CONTROLLER)):
        return dump(guard(lambda: gw.hold(x_actor, item_id)))

    @r.post("/work-items/{item_id}/approve")
    def approve(item_id: str, x_actor: str = Header(default=CONTROLLER)):
        return dump(guard(lambda: gw.approve(x_actor, item_id)))

    @r.post("/work-items/{item_id}/reject")
    def reject(item_id: str, body: ReasonBody, x_actor: str = Header(default=CONTROLLER)):
        return dump(guard(lambda: gw.reject(x_actor, item_id, body.reason)))

    @r.post("/work-items/{item_id}/reverse")
    def reverse(item_id: str, body: ReasonBody, x_actor: str = Header(default=CONTROLLER)):
        return dump(guard(lambda: gw.reverse(x_actor, item_id, body.reason)))

    # ------------------------------------------------------------------ writes (agents)
    @r.post("/tools/{name}")
    def tool(name: str, body: ToolBody, x_actor: str = Header(default="agent:preparer")):
        need_deal(body.deal_id)
        return dump(guard(lambda: gw.run_tool(x_actor, body.deal_id, name, body.inputs)))

    # ------------------------------------------------------------------ live updates
    @r.get("/deals/{deal_id}/stream")
    async def stream(deal_id: str, request: Request):
        need_deal(deal_id)

        async def gen():
            seen, last, tick = 0, None, 0
            while not await request.is_disconnected():
                if deal_id not in store.deals:
                    return
                events, seen, last = next_events(store, deal_id, seen, last)
                for e in events:
                    yield e
                tick += 1
                if tick % 15 == 0:
                    yield ": keepalive\n\n"
                await asyncio.sleep(1)

        return StreamingResponse(gen(), media_type="text/event-stream")

    return r
