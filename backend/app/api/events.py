"""Per-tick logic for the deal event stream. Pure: no clock waits, no HTTP, so tests call it directly."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.core.models import State


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def mapping_event(store, m) -> dict:
    """The `mapping` event's body for one stored mapping (gateway-and-api.md, "Live events")."""
    line = store.source_lines.get(m.target_line_id)
    return {"mapping_id": m.id, "line_id": m.target_line_id, "company": line.company if line else None,
            "section": line.section if line else None, "line": m.target_line, "platform_line": m.platform_line,
            "platform_line_id": m.platform_line_id, "confidence": m.confidence, "reason": m.reason,
            "flagged": m.flagged, "approved_by": m.approved_by, "policy_id": m.policy_id,
            "at": m.model_dump(mode="json", include={"at"})["at"]}  # the same ISO form as every other event


ROLE_NAMES = {"agent:mapper": "Mapper", "agent:preparer": "Preparer", "agent:reviewer": "Reviewer",
              "agent:brief_reader": "Brief Reader", "system:gateway": "Gateway", "system:verifier": "Verifier"}


def notify_event(store, msg) -> dict | None:
    """The `notify` event's body for a question to the controller, or None when the message is not one or its item
    is no longer waiting (answered while the page was away), so a reconnecting page never re-notifies an old
    question. `body` is the one-line question of the work item; the conversation message has the options."""
    item = store.items.get(msg.item_id) if msg.item_id else None
    if (msg.kind == "handoff" and msg.sender == "system:verifier" and msg.to == "human:controller" and item is not None
            and item.type == "draft_brief" and item.state == State.PROPOSED and item.payload.get("verification")):
        # The Brief approval (D23): the verifier checked every field; the controller approves in one click.
        report = item.payload["verification"]
        return {"id": msg.id, "deal_id": msg.deal_id, "at": msg.model_dump(mode="json", include={"at"})["at"],
                "kind": "brief_approval", "item_id": item.id, "item_ids": [item.id], "from": msg.sender,
                "title": "The Verifier checked the Brief",
                "body": f"{report['passed']} of {len(report['checks'])} checks passed. " + msg.text}
    if msg.kind != "question" or msg.to != "human:controller":
        return None
    if item is None or item.state != State.NEEDS_INFO:
        return None
    # One escalation, however many decisions (D23): the questions an agent opens together (one parent work item)
    # come as one notification, on the first of them that is still open; the Case shows them all at once.
    parent = item.payload.get("parent")
    together = [i for i in store.deal_items(item.deal_id, "flag")
                if parent and i.payload.get("parent") == parent and i.state == State.NEEDS_INFO] or [item]
    if together[0].id != item.id:
        return None
    who = ROLE_NAMES.get(msg.sender, msg.sender)
    body = " ".join((item.question or msg.text).split())
    n = len(together)
    title = f"The {who} needs your decision" if n == 1 else f"The {who} needs {n} decisions"
    if n > 1:
        body = f"{body} (and {n - 1} more question{'s' if n > 2 else ''}, answered together)"
    return {"id": msg.id, "deal_id": msg.deal_id, "at": msg.model_dump(mode="json", include={"at"})["at"],
            "kind": "decision", "item_id": item.id, "item_ids": [i.id for i in together], "from": msg.sender,
            "title": title, "body": body}


def _key(msg) -> tuple[str, str]:
    return msg.id, msg.at.isoformat()


def _live_events(store, deal_id: str, live_seen: dict) -> list[str]:
    """`conversation` events for messages not sent yet, then `mapping` events for mappings that are new or changed
    since the last tick, both in the order the gateway wrote them. The cursors live in `live_seen`."""
    out: list[str] = []
    messages = store.deal_messages(deal_id)
    sent = live_seen.get("messages", 0)
    # Ids start again at msg_001 after /dev/reset, so the last message sent is known by its id and its time.
    if len(messages) < sent or (sent and _key(messages[sent - 1]) != live_seen.get("last_message")):
        sent = 0  # the record was reset: replay the new conversation from the start
    for msg in messages[sent:]:
        out.append(_sse("conversation", msg.model_dump(mode="json")))
        note = notify_event(store, msg)
        if note:
            out.append(_sse("notify", note))
    live_seen["messages"] = len(messages)
    live_seen["last_message"] = _key(messages[-1]) if messages else None
    seen: dict = live_seen.setdefault("mappings", {})
    current = store.deal_mappings(deal_id)
    if any(mid not in {m.id for m in current} for mid in seen):
        seen.clear()  # reset: send the new deal's mappings from the start
    for m in current:
        body = mapping_event(store, m)
        sig = (body["at"], body["platform_line"], body["confidence"], body["flagged"], body["approved_by"],
               body["policy_id"])  # with `at`, a mapping that reuses an id after a reset is new
        if seen.get(m.id) != sig:
            out.append(_sse("mapping", body))
            seen[m.id] = sig
    return out


def next_events(store, deal_id: str, seen_audit: int, last_stage: str | None,
                edits_seen: dict | None = None, live_seen: dict | None = None) -> tuple[list[str], int, str | None]:
    """Return ready-to-send SSE strings, the new audit offset, and the new last stage.

    A missing deal yields no events and leaves the cursors unchanged.
    edits_seen, when given, is the edit event's cursor and is updated in place: an `edit` event is sent when the
    deal's edits (ids and statuses) differ from the last ones sent. A first call with no edits sends nothing.
    Without it, no edit event is sent, as before.
    live_seen, when given, is the cursor of the `conversation` and `mapping` events, updated in place: the first call
    sends the whole conversation and every stored mapping, later calls only what is new (or, for a mapping, changed).
    The stage event carries the deal's brief_status. Every brief_status change in the gateway comes with a stage
    change (none/new to draft/awaiting_brief, then draft/brief_ready to approved/new), so it needs no event of its own.
    """
    deal = store.deals.get(deal_id)
    if deal is None:
        return [], seen_audit, last_stage

    def stage_event() -> str:
        flags = [i.id for i in store.deal_items(deal_id, "flag") if i.state == State.NEEDS_INFO]
        return _sse("stage", {"deal_id": deal_id, "stage": deal.stage, "open_flags": flags,
                              "brief_status": deal.brief_status, "at": datetime.now(timezone.utc).isoformat()})

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
    if live_seen is not None:
        out.extend(_live_events(store, deal_id, live_seen))
    if edits_seen is not None:
        current = [{"id": e.id, "status": e.status} for e in store.deal_edits(deal_id)]
        if current != edits_seen.get("edits", []):
            out.append(_sse("edit", {"deal_id": deal_id, "edits": current,
                                     "at": datetime.now(timezone.utc).isoformat()}))
        edits_seen["edits"] = current
    if deal.stage != last_stage:
        out.append(stage_event())
        last_stage = deal.stage
    return out, seen_audit, last_stage
