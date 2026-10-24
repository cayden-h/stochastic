"""HTTP routes. Thin: they validate input and call the gateway."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.gateway.gateway import Gateway, GatewayError


class AnswerBody(BaseModel):
    option_id: str


class RejectBody(BaseModel):
    reason: str


class EventBody(BaseModel):
    kind: str
    detail: str


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

    @r.get("/health")
    def health():
        return {"ok": True, "chain_valid": gw.verify_chain()}

    @r.get("/deals")
    def deals():
        return [dump(d) for d in store.deals.values()]

    @r.get("/deals/{deal_id}")
    def deal(deal_id: str):
        return dump(need_deal(deal_id))

    @r.get("/deals/{deal_id}/work-items")
    def work_items(deal_id: str, state: str | None = None, escalation: str | None = None):
        need_deal(deal_id)
        items = [i for i in store.items.values() if i.deal_id == deal_id]
        if state:
            items = [i for i in items if i.state.value == state]
        if escalation:
            items = [i for i in items if i.escalation == escalation]
        return [dump(i) for i in items]

    @r.get("/deals/{deal_id}/plans")
    def plans(deal_id: str):
        need_deal(deal_id)
        return [dump(p) for p in store.plans.values() if p.deal_id == deal_id]

    @r.get("/deals/{deal_id}/facts")
    def facts(deal_id: str):
        need_deal(deal_id)
        return [dump(f) for f in store.facts.values() if f.deal_id == deal_id]

    @r.get("/deals/{deal_id}/clauses")
    def clauses(deal_id: str):
        need_deal(deal_id)
        return [dump(c) for c in store.clauses.values() if c.deal_id == deal_id]

    @r.get("/deals/{deal_id}/audit")
    def audit(deal_id: str):
        need_deal(deal_id)
        return {"chain_valid": gw.verify_chain(), "rows": [dump(a) for a in store.audit if a.deal_id == deal_id]}

    @r.post("/work-items/{item_id}/answer")
    def answer(item_id: str, body: AnswerBody, x_actor: str = Header(default="human:reviewer")):
        return dump(guard(lambda: gw.answer(x_actor, item_id, body.option_id)))

    @r.post("/work-items/{item_id}/hold")
    def hold(item_id: str, x_actor: str = Header(default="human:reviewer")):
        return dump(guard(lambda: gw.hold(x_actor, item_id)))

    @r.post("/work-items/{item_id}/approve")
    def approve(item_id: str, x_actor: str = Header(default="human:reviewer")):
        return dump(guard(lambda: gw.approve(x_actor, item_id)))

    @r.post("/work-items/{item_id}/reject")
    def reject(item_id: str, body: RejectBody, x_actor: str = Header(default="human:reviewer")):
        return dump(guard(lambda: gw.reject(x_actor, item_id, body.reason)))

    @r.post("/deals/{deal_id}/events")
    def event(deal_id: str, body: EventBody, x_actor: str = Header(default="human:reviewer")):
        need_deal(deal_id)
        return dump(guard(lambda: gw.inject_event(x_actor, deal_id, body.kind, body.detail)))

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
