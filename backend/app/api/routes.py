"""HTTP routes. Thin: they validate input and call the gateway. Shapes are in docs/architecture/gateway-and-api.md.

Owner: Tri (backend/app/api/). Cayden wrote the first version so the console had something to read.
"""
from __future__ import annotations

import asyncio
import json
import math
import os

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError

from app.agents import runner as agent_runner
from app.agents.jobs import advance
from app.api.events import next_events
from app.api.schemas import CaseResponse, DealCreated, HealthResponse
from app.core.models import CONTROLLER, Brief, Deal, State
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
            "fallback": os.getenv("AGENT_FALLBACK", "anthropic,scripted"),
            "anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
            "factory_key": bool(os.getenv("FACTORY_API_KEY")),
            "last_runs": agent_runner.LAST_RUNS[-6:],
        }

    def run_in_background(deal_id: str, backend: str | None, tasks: BackgroundTasks):
        tasks.add_task(_safe_advance, deal_id, backend)

    def _safe_advance(deal_id: str, backend: str | None):
        try:
            advance(gw, deal_id, backend=backend)
        except Exception as error:  # keep the server up; the audit log and LAST_RUNS hold the trace
            agent_runner.LAST_RUNS.append({"role": "runner", "backend": backend, "error": str(error)[:300]})

    # ------------------------------------------------------------------ reads
    @r.get("/health", response_model=HealthResponse)
    def health():
        return {"ok": True, "chain_valid": gw.verify_chain(), "backend": backend_status()}

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
            try:
                return {"ok": True, "log": advance(gw, deal_id, backend=body.backend), "stage": store.deals[deal_id].stage}
            except GatewayError as error:
                raise HTTPException(status_code=error.status, detail=error.message)
            except Exception as error:
                raise HTTPException(status_code=500, detail=str(error)[:300])
        run_in_background(deal_id, body.backend, tasks)
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
