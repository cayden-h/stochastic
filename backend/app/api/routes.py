"""HTTP routes. Thin: they validate input and call the gateway. Shapes are in docs/architecture/gateway-and-api.md.

Owner: Tri (backend/app/api/). Cayden wrote the first version so the console had something to read.
"""
from __future__ import annotations

import asyncio
import json
import os

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents import runner as agent_runner
from app.agents import settings as agent_settings
from app.agents.jobs import advance
from app.core.models import CONTROLLER, State
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
            "settings": agent_settings.summary(),
        }

    def run_in_background(deal_id: str, backend: str | None, tasks: BackgroundTasks):
        tasks.add_task(_safe_advance, deal_id, backend)

    def _safe_advance(deal_id: str, backend: str | None):
        try:
            advance(gw, deal_id, backend=backend)
        except Exception as error:  # keep the server up; the audit log and LAST_RUNS hold the trace
            agent_runner.LAST_RUNS.append({"role": "runner", "backend": backend, "error": str(error)[:300]})

    # ------------------------------------------------------------------ reads
    @r.get("/health")
    def health():
        return {"ok": True, "chain_valid": gw.verify_chain(), "backend": backend_status()}

    @r.get("/deals")
    def deals():
        return [dump(d) for d in store.deals.values()]

    @r.get("/deals/{deal_id}")
    def deal(deal_id: str):
        return dump(need_deal(deal_id))

    @r.get("/deals/{deal_id}/case")
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
            verdict = {"leverage": result.leverage, "limit": result.limit, "verdict": result.verdict,
                       "headroom_turns": result.headroom_turns, "ebitda": result.ebitda, "debt": result.debt,
                       "debt_term": d.brief.debt_term, "review": dump(result.review) if result.review else None,
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
            seen = 0
            while not await request.is_disconnected():
                rows = [a for a in store.audit if a.deal_id == deal_id]
                for row in rows[seen:]:
                    yield f"event: audit\ndata: {json.dumps(dump(row))}\n\n"
                seen = len(rows)
                await asyncio.sleep(1)

        return StreamingResponse(gen(), media_type="text/event-stream")

    return r
