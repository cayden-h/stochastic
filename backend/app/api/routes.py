"""HTTP routes. Thin: they validate input and call the gateway. Shapes are in docs/architecture/gateway-and-api.md.

Owner: Tri (backend/app/api/). Cayden wrote the first version so the console had something to read.
"""
from __future__ import annotations

import asyncio
import json
import math
import os

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel, ValidationError

from app.agents import demo_replay, recording
from app.agents import runner as agent_runner
from app.agents import settings as agent_settings
from app.agents.jobs import advance
from app.api import certificate as cert_doc
from app.api import export as export_doc
from app.api.events import next_events
from app.api.schemas import (BriefAmountsBody, BriefAmountsResponse, CaseResponse, DealCreated, EditBody, MemoryCounts,
                             EditReasonBody, EditResponse, HealthResponse)
from app.core.models import CONTROLLER, SYSTEM, Brief, Deal, Edit, State
from app.db.fixtures.kewaunee import DEAL_ID
from app.db.loader import MAX_BYTES, LoaderError, parse_statement_csv
from app.gateway.gateway import Denied, Gateway, GatewayError, Invalid

BRIEF_TEXT_FIELDS = ("lender", "limit_section", "limit_wording", "debt_term", "debt_definition", "ebitda_definition",
                     "test_period_note")  # the text fields gateway.amend_brief sets


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
    # The pace of this run and of the run the controller's answer continues, on the scripted and replay backends:
    # "demo" (the 15-second Hyphenate demo), "factory" (the 30-second Factory demo), "human" (the DEMO_PACE=1
    # timings), "off"; None follows DEMO_PACE. "demo" and "factory" with no backend replay the recorded Claude
    # Haiku 5.5 run when it fits the deal, else the scripted rules (app/agents/demo_replay.py).
    pace: Literal["demo", "factory", "human", "off"] | None = None


def _debt_capacity(store, result) -> tuple[float | None, str | None]:
    """Room for the next deal. The number comes from the Reviewer's limit_test tool run, never from the route."""
    ids = result.review.run_ids if result and result.review else []
    runs = [t for t in store.tool_runs.values() if t.tool == "limit_test" and t.run_id in ids]
    for t in reversed(runs):
        value = t.outputs.get("debt_capacity")
        if value is not None:
            return value, t.run_id
    return None, None


STREAM_TICK_S = 0.25  # how often the stream looks for new events
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
            if debt and debt.tool == "covenant_debt" and eb and eb.tool == "ebitda" and eb.inputs.get("as_filed"):
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
    # Uploads already in the record when this process started (a Postgres ledger keeps them) are hidden from the
    # Dashboard list, not deleted: GET /deals?include_uploads=true lists them, and their own routes still answer.
    # A deal uploaded in this process stays listed, across /dev/reset too.
    earlier_uploads = {d.id for d in store.deals.values() if d.data_source == "upload"}

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
            "demo_recording": {"name": demo_replay.DEMO_RECORDING, **recording.info(demo_replay.recording_folder())},
        }

    def memory_counts() -> dict:
        """The learning counters across all deals: the flags a human answered (and, for a live policy whose deal was
        reset with memory kept, the answer it came from), the live policies, and the reasoned edits."""
        answers = {(i.deal_id, i.id) for i in store.items.values() if i.type == "flag" and i.answer}
        live = [p for p in store.policies.values() if not p.retired_by]
        answers |= {(p.deal_id, p.learned_from) for p in live if p.learned_from.startswith("wi_")}
        edits = [e for e in store.edits.values() if e.status == "reasoned"]
        by_deal: dict[str, dict[str, int]] = {}
        for key, rows in (("human_answers", [d for d, _ in answers]), ("policies", [p.deal_id for p in live]),
                          ("edits", [e.deal_id for e in edits])):
            for d in rows:
                by_deal.setdefault(d, {"human_answers": 0, "policies": 0, "edits": 0})[key] += 1
        return {"human_answers": len(answers), "policies": len(live), "edits": len(edits), "by_deal": by_deal}

    # One job per deal at a time. Answering the last flag starts the job runner, so a Run click at the same moment
    # would start a second Preparer; the gateway would deny its result, but the click should get a clear 409 instead.
    # The set and its lock live on the gateway: /dev/reset holds the same lock across its check and the reset, and
    # /case and /health say from the set whether a job is really running (the stage alone cannot tell after a restart).
    running, running_lock = gw.running, gw.running_lock

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
        tasks.add_task(_safe_advance, deal_id, backend, gw.run_pace.get(deal_id))
        return True

    def _safe_advance(deal_id: str, backend: str | None, pace_name: str | None = None):
        try:
            advance(gw, deal_id, backend=backend, pace_name=pace_name)
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
                "store": {**store.status(), "forks": forks}, "running": bool(running), "memory_counts": memory_counts()}

    @r.get("/memory/counts", response_model=MemoryCounts)
    def counts():
        """The sidebar's counters across every deal: human answers, live policies, reasoned edits (and per deal)."""
        with gw.lock:
            return memory_counts()

    def deal_card(d: Deal) -> dict:
        """One Dashboard row: the deal, plus its verdict (from the latest result's tool runs, or null), the time of its
        latest audit row, and where its lines come from."""
        result = store.latest_result(d.id)
        last = next((a.at for a in reversed(store.audit) if a.deal_id == d.id), None)
        return {**dump(d), "deal_id": d.id,
                "verdict": ({"leverage": result.leverage, "limit": result.limit, "verdict": result.verdict}
                            if result else None),
                "updated_at": last.isoformat() if last else None}

    @r.get("/deals")
    def deals(include_uploads: bool = False):
        """The Dashboard's deals, the live demo deal first: the deal's own fields (id, name, platform, target,
        stage, brief, data_source, note, ...) plus deal_id, verdict, and updated_at. By default the demo deal, the
        seeded cases, and the deals uploaded since this process started; include_uploads=true adds the uploads from
        before it started, which are kept in the record but hidden."""
        rows = [d for d in list(store.deals.values()) if include_uploads or d.id not in earlier_uploads]
        rows.sort(key=lambda d: d.id != DEAL_ID)  # stable: the rest keep their order
        return [deal_card(d) for d in rows]

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
                       "debt_term": d.brief.debt_term if d.brief else "", "debt_capacity": capacity,
                       "debt_capacity_run_id": capacity_run, "review": dump(result.review) if result.review else None,
                       "tie_out_ok": result.tie_out_ok, "backend": result.backend,
                       "approval_item": approval.id if approval else None,
                       "approval_state": approval.state.value if approval else None,
                       "posted": d.stage == "posted"}
            verdict.update(_sensitivity(gw, d, result) or {})
        return {
            "deal": dump(d),
            "stage": d.stage,
            "running": gw.is_running(deal_id),
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
            "edits": [dump(e) for e in store.deal_edits(deal_id)],
            "adjustments": [dump(a) for a in store.adjustments.values()],
            "brief_draft": dump(draft) if (draft := gw.brief_draft(deal_id)) else None,
            "brief_verification": dump(report) if (report := gw.brief_verification(deal_id)) else None,
            "reason_chips": {kind: [dump(c) for c in gw.reason_chips(deal_id, kind)] for kind in ("amount", "remap")},
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
    async def read_upload(field: str, upload: UploadFile, ext: str = ".csv") -> str:
        """Read one upload (a CSV, or the agreement as .txt) with a hard size cap. Never trusts content-length."""
        if not (upload.filename or "").lower().endswith(ext):
            raise HTTPException(status_code=422, detail=f"{field}: file name must end in {ext}")
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
                          brief: str | None = Form(None),
                          platform_csv: UploadFile = File(...), target_csv: UploadFile = File(...),
                          agreement_txt: UploadFile | None = File(None),
                          x_actor: str = Header(default=CONTROLLER)):
        """Load an unseen deal from two statement CSVs and either a brief (JSON) or the credit agreement as text
        (agreement_txt), exactly one. Does not run the deal. With the agreement, the deal starts with no Brief
        (brief_status "none") and the run starts with the Brief Reader, unless an approved Brief for the same
        agreement text is reused by its hash.

        The console calls POST /deals/{id}/run next. /dev/reset reseeds only the demo deal; an uploaded deal keeps
        its record across a reset, like the seeded cases.
        """
        def require():  # a denial is audited, before any file is parsed; a write, so under the lock and committed
            with gw.lock:
                try:
                    gw._require(x_actor, "create_deal", deal_id="-")
                except GatewayError as error:
                    raise HTTPException(status_code=error.status, detail=error.message)
                finally:
                    store.commit()
        # Every gateway call below may wait on the gateway lock, which a paced run holds for seconds at a time. They
        # run in a worker thread, so an upload during a run never stops the event loop (and every stream with it).
        await run_in_threadpool(require)
        name, platform, target = name.strip(), platform.strip(), target.strip()
        if not name or not platform or not target or platform.lower() == target.lower():
            raise HTTPException(status_code=422, detail="name, platform and target are required, and platform and target must differ")
        has_brief, has_agreement = bool(brief and brief.strip()), agreement_txt is not None
        if has_brief == has_agreement:
            raise HTTPException(status_code=422, detail="send exactly one of brief (a JSON string) or agreement_txt "
                                                        "(the credit agreement as a .txt file)")
        platform_text = await read_upload("platform_csv", platform_csv)
        target_text = await read_upload("target_csv", target_csv)
        parsed_brief, agreement_text = None, None
        if has_agreement:
            agreement_text = await read_upload("agreement_txt", agreement_txt, ext=".txt")
            if not agreement_text.strip():
                raise HTTPException(status_code=422, detail="agreement_txt: the agreement text is empty")
        else:
            try:
                parsed_brief = Brief.model_validate_json(brief)
            except ValidationError as error:
                raise HTTPException(status_code=422,
                                    detail=f"brief: {error.errors()[0]['loc']} {error.errors()[0]['msg']}")
            bad_path = first_non_finite(parsed_brief)
            if bad_path:
                raise HTTPException(status_code=422, detail=f"brief: {bad_path} must be finite")
            if not math.isfinite(parsed_brief.limit) or parsed_brief.limit <= 0:
                raise HTTPException(status_code=422, detail="brief: limit must be a finite number greater than 0")
        return await run_in_threadpool(load_deal, name, platform, target, platform_text, target_text, parsed_brief,
                                       agreement_text, (agreement_txt.filename if agreement_txt else None), x_actor)

    def load_deal(name: str, platform: str, target: str, platform_text: str, target_text: str,
                  parsed_brief: Brief | None, agreement_text: str | None, agreement_name: str | None,
                  x_actor: str) -> dict:
        """The blocking half of POST /deals: parse the CSVs and write the deal through the gateway. Under the gateway
        lock, so the new id and the deal are one step and two uploads cannot take the same id."""
        with gw.lock:
            deal_id = store.next_id("d")
            loaded = {}
            for field, company, text in (("platform_csv", platform, platform_text),
                                         ("target_csv", target, target_text)):
                try:
                    loaded[field] = parse_statement_csv(text, company, deal_id, store.next_id)
                except (LoaderError, ValueError, ValidationError) as error:
                    raise HTTPException(status_code=422, detail=f"{field}: {error}")
            lines = loaded["platform_csv"] + loaded["target_csv"]
            if agreement_text is not None:
                deal = Deal(id=deal_id, name=name, platform=platform, target=target, brief=None, brief_status="none")
                source = (agreement_name or "agreement.txt").strip()[:200]
                created = guard(lambda: gw.create_deal_from_agreement(x_actor, deal, lines, agreement_text,
                                                                      source=source))
            else:
                deal = Deal(id=deal_id, name=name, platform=platform, target=target, brief=parsed_brief)
                guard(lambda: gw.create_deal(x_actor, deal, lines))
                created = store.deals[deal_id]
        return {"deal_id": deal_id, "stage": created.stage, "brief_status": created.brief_status,
                "lines": {"platform": len(loaded["platform_csv"]), "target": len(loaded["target_csv"])}}

    # ------------------------------------------------------------------ the Brief Reader (D20), thin over the gateway
    def controller_only(actor: str, action: str, deal_id: str) -> None:
        """Only the controller sets or approves the Brief: an agent, the system, or another human (human:intern) is
        403 with a DENIED row. Held under the gateway lock and committed, like a gateway write."""
        with gw.lock:
            try:
                gw._require(actor, action, deal_id, deal_id)  # an agent or a malformed actor, with the usual message
                if actor != CONTROLLER:
                    gw._deny(Denied(f"{actor} may not {action}: only {CONTROLLER} sets or approves the Brief"),
                             deal_id, actor, action, deal_id)
            except GatewayError as error:
                raise HTTPException(status_code=error.status, detail=error.message)
            finally:
                gw.store.commit()

    def amount_problem(a, lengths: dict[str, int]) -> str | None:
        """The gateway's path and value checks for one entry of /brief/amounts, without writing (a dry run), so a
        list with a bad entry is refused before any entry is applied. lengths counts the draft's lists and grows
        when an entry adds an item at the next index, as the gateway would."""
        m = Gateway._PATH.fullmatch(a.field)
        if not m:
            return f"unknown field '{a.field}'"
        name, i, attr, v = m.group("field"), m.group("i"), m.group("attr"), a.value
        number = isinstance(v, (int, float)) and not isinstance(v, bool)
        if name in BRIEF_TEXT_FIELDS and i is None and attr is None:
            if not isinstance(v, str) or not v.strip() or len(v) > 2000:
                return f"{a.field} must be text of 1 to 2000 characters"
        elif name == "limit" and i is None and attr is None:
            if not number or v <= 0:
                return "limit must be a number above zero"
        elif name == "debt_excludes" and i is not None and attr is None:
            k = int(i)
            if not isinstance(v, str) or not v.strip() or k > lengths[name]:
                return f"{a.field} must be text, at an index up to {lengths[name]}"
            lengths[name] = max(lengths[name], k + 1)
        elif name in ("ebitda_addbacks", "ebitda_deductions") and i is not None and attr:
            k = int(i)
            if k > lengths[name] or (k == lengths[name] and attr != "name"):
                return f"{a.field}: add a new adjustment by its name first, at index {lengths[name]}"
            lengths[name] = max(lengths[name], k + 1)
            if attr == "name" and (not isinstance(v, str) or not v.strip()):
                return f"{a.field} must be text"
            if attr == "cap" and v is not None and (not number or v < 0):
                return f"{a.field} must be a number of USD thousands, or null for no cap"
            if attr == "amount":
                if not number:
                    return f"{a.field} must be a number of USD thousands"
                if not (a.source_ref or "").strip():
                    return f"{a.field} needs its source: the filing and the line it comes from"
        else:
            return f"unknown field '{a.field}'"
        return None

    # ------------------------------------------------------------------ the Brief Reader (D20), thin over the gateway
    @r.post("/deals/{deal_id}/brief/amounts", response_model=BriefAmountsResponse)
    def brief_amounts(deal_id: str, body: BriefAmountsBody, x_actor: str = Header(default=CONTROLLER)):
        """The controller sets fields of the draft Brief, most often an add-back amount from the books with its
        source. Any draft field can be set by its path; only an amount needs a source.

        Every entry is checked first (path, index, type, source), so a bad entry refuses the whole list with 422
        naming amounts[i], and nothing is applied (the refusal is audited). The entries are then applied in order
        through gateway.amend_brief under the gateway lock, so no other request lands between them. The gateway
        cannot roll back: if it still refuses entry i, the 422 names amounts[i] and says which earlier entries
        were applied (each with its own audit row)."""
        d = need_deal(deal_id)
        controller_only(x_actor, "amend_brief", deal_id)
        with gw.lock:
            if d.brief_status == "draft" and d.brief is not None:
                lengths = {g: len(getattr(d.brief, g)) for g in ("debt_excludes", "ebitda_addbacks", "ebitda_deductions")}
                for n, a in enumerate(body.amounts):
                    problem = amount_problem(a, lengths)
                    if problem:
                        try:
                            gw._deny(Invalid(f"amounts[{n}] ({a.field}): {problem}; nothing was applied"),
                                     deal_id, x_actor, "amend_brief", a.field)
                        except GatewayError as error:
                            raise HTTPException(status_code=error.status, detail=error.message)
                        finally:
                            gw.store.commit()
            brief = None
            for n, a in enumerate(body.amounts):
                try:
                    brief = gw.amend_brief(x_actor, deal_id, a.field, a.value, source_ref=a.source_ref,
                                           inferred=a.inferred, note=a.note)
                except GatewayError as error:
                    applied = ", ".join(f"amounts[{j}] ({e.field})" for j, e in enumerate(body.amounts[:n]))
                    raise HTTPException(status_code=error.status, detail=(
                        f"amounts[{n}] ({a.field}): {error.message}; "
                        + (f"applied before it and kept (no rollback): {applied}" if applied else "nothing was applied")))
            d = store.deals[deal_id]
            draft = gw.brief_draft(deal_id)
            return {"brief": dump(brief), "brief_draft": dump(draft) if draft else None,
                    "brief_status": d.brief_status, "stage": d.stage}

    @r.post("/deals/{deal_id}/brief/approve", response_model=Deal)
    def brief_approve(deal_id: str, x_actor: str = Header(default=CONTROLLER)):
        """The controller approves the draft Brief; it is then locked and the deal is back at stage new. The run does
        not continue by itself: the console calls POST /deals/{id}/run next. No agent and no other human can."""
        need_deal(deal_id)
        controller_only(x_actor, "approve_brief", deal_id)
        return dump(guard(lambda: gw.approve_brief(x_actor, deal_id)))

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
            gw.run_pace[deal_id] = body.pace
            try:
                return {"ok": True, "log": advance(gw, deal_id, backend=body.backend, pace_name=body.pace),
                        "stage": store.deals[deal_id].stage}
            except GatewayError as error:
                raise HTTPException(status_code=error.status, detail=error.message)
            except Exception as error:
                raise HTTPException(status_code=500, detail=str(error)[:300])
            finally:
                release(deal_id)
        with running_lock:
            busy = deal_id in running
        if busy:
            raise HTTPException(status_code=409, detail="a run is already in progress for this deal")
        gw.run_pace[deal_id] = body.pace
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

    # ------------------------------------------------------------------ review edits (D19), thin over the gateway
    def edit_response(out: dict) -> dict:
        verdict = dict(out["verdict"])
        if verdict.get("review") is not None:
            verdict["review"] = dump(verdict["review"])
        return {"edit": dump(out["edit"]), "result": dump(out["result"]), "verdict": verdict,
                "approval": dump(out["approval"]), "reasons": [dump(c) for c in out["reasons"]]}

    @r.post("/deals/{deal_id}/edits", response_model=EditResponse)
    def apply_edit(deal_id: str, body: EditBody, x_actor: str = Header(default=CONTROLLER)):
        """The controller changes one amount or one target mapping after the agents and before approval. The gateway
        recomputes every figure through the tools with new run ids and writes a new result revision."""
        need_deal(deal_id)
        return edit_response(guard(lambda: gw.apply_edit(x_actor, deal_id, body.kind, body.company, body.line,
                                                         value=body.value, platform_line=body.platform_line,
                                                         section=body.section)))

    @r.post("/edits/{edit_id}/reason", response_model=Edit)
    def reason_edit(edit_id: str, body: EditReasonBody, x_actor: str = Header(default=CONTROLLER)):
        """Why the controller made the edit: a chip or a typed reason. With remember, it becomes memory."""
        return dump(guard(lambda: gw.reason_edit(x_actor, edit_id, chip=body.chip, text=body.text,
                                                 remember=body.remember)))

    @r.delete("/edits/{edit_id}", response_model=EditResponse)
    def revert_edit(edit_id: str, x_actor: str = Header(default=CONTROLLER)):
        """Undo an edit: marked reverted, never deleted, and the books are recomputed without it."""
        return edit_response(guard(lambda: gw.revert_edit(x_actor, edit_id)))

    # ------------------------------------------------------------------ writes (agents)
    @r.post("/tools/{name}")
    def tool(name: str, body: ToolBody, x_actor: str = Header(default="agent:preparer")):
        need_deal(body.deal_id)
        return dump(guard(lambda: gw.run_tool(x_actor, body.deal_id, name, body.inputs)))

    # ------------------------------------------------------------------ live updates
    @r.get("/deals/{deal_id}/conversation")
    def conversation(deal_id: str):
        """The deal's whole conversation in order: what each agent, the gateway, and the controller told each other.
        The same messages the stream sends as `conversation` events, for a page opened late or after a restart."""
        need_deal(deal_id)
        return [dump(m) for m in guard(lambda: gw.conversation(deal_id))]

    @r.get("/deals/{deal_id}/stream")
    async def stream(deal_id: str, request: Request):
        need_deal(deal_id)

        async def gen():
            seen, last, tick = 0, None, 0
            edits_seen: dict = {}  # the edit event's cursor, updated in place by next_events
            live_seen: dict = {}  # the conversation and mapping events' cursor, likewise
            was_running = None
            while not await request.is_disconnected():
                if deal_id not in store.deals:
                    return
                events, seen, last = next_events(store, deal_id, seen, last, edits_seen=edits_seen,
                                                 live_seen=live_seen)
                for e in events:
                    yield e
                # A `run` event when a job for this deal starts or stops. The stage does not always change then (the
                # runner ends about a second after the Reviewer's hand-off), and the console enables Run and Reset
                # only once no job runs.
                now_running = gw.is_running(deal_id)
                if now_running != was_running:
                    yield f"event: run\ndata: {json.dumps({'running': now_running})}\n\n"
                    was_running = now_running
                tick += 1
                if tick % 60 == 0:
                    yield ": keepalive\n\n"
                await asyncio.sleep(STREAM_TICK_S)  # a quarter second, so a paced mapping run streams line by line

        return StreamingResponse(gen(), media_type="text/event-stream")

    return r
