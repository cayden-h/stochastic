"""Per-tick logic for the deal event stream. Pure: no clock waits, no HTTP, so tests call it directly."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.core.models import State


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def next_events(store, deal_id: str, seen_audit: int, last_stage: str | None) -> tuple[list[str], int, str | None]:
    """Return ready-to-send SSE strings, the new audit offset, and the new last stage.

    A missing deal yields no events and leaves the cursors unchanged.
    """
    deal = store.deals.get(deal_id)
    if deal is None:
        return [], seen_audit, last_stage

    def stage_event() -> str:
        flags = [i.id for i in store.deal_items(deal_id, "flag") if i.state == State.NEEDS_INFO]
        return _sse("stage", {"deal_id": deal_id, "stage": deal.stage, "open_flags": flags,
                              "at": datetime.now(timezone.utc).isoformat()})

    out: list[str] = []
    if last_stage is None:
        out.append(stage_event())
        last_stage = deal.stage
    rows = [a for a in store.audit if a.deal_id == deal_id]
    if len(rows) < seen_audit:
        seen_audit = 0  # the audit list is replaced on /dev/reset, so replay from the start
    for row in rows[seen_audit:]:
        out.append(_sse("audit", row.model_dump(mode="json")))
    seen_audit = len(rows)
    if deal.stage != last_stage:
        out.append(stage_event())
        last_stage = deal.stage
    return out, seen_audit, last_stage
