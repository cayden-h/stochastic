"""The gateway: the only writer.

It checks the actor, the permission, the state change, and the limits.
It writes one audit row for every action and every denied attempt.
Rules are in docs/architecture/gateway-and-api.md.
"""
from __future__ import annotations

import hashlib
import json

from app.core.models import AuditRow, Evidence, Option, Plan, State, WorkItem, now
from app.db.memory import MemoryStore
from app.tools.deal_math import leverage_breach

GENESIS = "0" * 64

PERMISSIONS: dict[str, set[str]] = {
    "agent": {"propose", "ask", "post_plan"},
    "human": {"answer", "approve", "reject", "hold", "inject_event", "create_deal"},
    "system": {"post", "log"},
}


class GatewayError(Exception):
    status = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class Denied(GatewayError):
    status = 403


class IllegalTransition(GatewayError):
    status = 409


class NotFound(GatewayError):
    status = 404


def parse_actor(actor: str) -> tuple[str, str]:
    kind, _, name = actor.partition(":")
    if kind not in PERMISSIONS or not name:
        raise Denied(f"unknown actor '{actor}'")
    return kind, name


def _hash(row: dict, prev_hash: str) -> str:
    body = json.dumps({**row, "prev_hash": prev_hash}, sort_keys=True, default=str)
    return hashlib.sha256(body.encode()).hexdigest()


class Gateway:
    def __init__(self, store: MemoryStore):
        self.store = store

    # ---- audit log (append only) ----
    def _log(
        self,
        deal_id: str,
        actor: str,
        action: str,
        result: str,
        target: str | None = None,
        reason: str | None = None,
        evidence: list[Evidence] | None = None,
    ) -> AuditRow:
        prev = self.store.audit[-1].hash if self.store.audit else GENESIS
        base = dict(
            id=len(self.store.audit) + 1,
            at=now(),
            deal_id=deal_id,
            actor=actor,
            action=action,
            target=target,
            result=result,
            reason=reason,
            evidence=[e.model_dump() for e in (evidence or [])],
        )
        row = AuditRow(**{**base, "evidence": evidence or []}, prev_hash=prev, hash=_hash(base, prev))
        self.store.audit.append(row)
        return row

    def verify_chain(self) -> bool:
        prev = GENESIS
        for row in self.store.audit:
            base = dict(
                id=row.id,
                at=row.at,
                deal_id=row.deal_id,
                actor=row.actor,
                action=row.action,
                target=row.target,
                result=row.result,
                reason=row.reason,
                evidence=[e.model_dump() for e in row.evidence],
            )
            if row.prev_hash != prev or row.hash != _hash(base, prev):
                return False
            prev = row.hash
        return True

    def _deny(self, error: GatewayError, deal_id: str, actor: str, action: str, target: str | None = None,
              evidence: list[Evidence] | None = None) -> None:
        self._log(deal_id, actor, action, "DENIED", target, error.message, evidence)
        raise error

    def _require(self, actor: str, action: str, deal_id: str, target: str | None = None) -> str:
        try:
            kind, _ = parse_actor(actor)
        except Denied as error:
            self._deny(error, deal_id, actor, action, target)
        if action not in PERMISSIONS[kind]:
            self._deny(Denied(f"{kind} may not {action}"), deal_id, actor, action, target)
        return kind

    def _item(self, item_id: str) -> WorkItem:
        item = self.store.items.get(item_id)
        if not item:
            raise NotFound(f"work item {item_id} not found")
        return item

    # ---- work items ----
    def propose(self, actor: str, deal_id: str, type: str, escalation: str | None = None,
                payload: dict | None = None, evidence: list[Evidence] | None = None) -> WorkItem:
        self._require(actor, "propose", deal_id)
        item = WorkItem(id=self.store.next_id("wi"), deal_id=deal_id, type=type, state=State.PROPOSED,
                        escalation=escalation, proposed_by=actor, payload=payload or {},
                        evidence=evidence or [])
        self.store.items[item.id] = item
        self._log(deal_id, actor, f"propose:{type}", "ALLOWED", item.id, evidence=item.evidence)
        return item

    def ask(self, actor: str, deal_id: str, type: str, escalation: str, question: str,
            evidence: list[Evidence], options: list[Option], default: str | None = None,
            context: str | None = None) -> WorkItem:
        self._require(actor, "ask", deal_id)
        item = WorkItem(id=self.store.next_id("wi"), deal_id=deal_id, type=type, state=State.NEEDS_INFO,
                        escalation=escalation, proposed_by=actor, question=question,
                        evidence=evidence, options=options, default=default,
                        payload={"context": context} if context else {})
        self.store.items[item.id] = item
        self._log(deal_id, actor, f"ask:{escalation}", "ALLOWED", item.id, evidence=evidence)
        return item

    def answer(self, actor: str, item_id: str, option_id: str) -> WorkItem:
        item = self._item(item_id)
        self._require(actor, "answer", item.deal_id, item.id)
        if item.state != State.NEEDS_INFO:
            self._deny(IllegalTransition(f"cannot answer an item in state {item.state.value}"),
                       item.deal_id, actor, "answer", item.id)
        if option_id not in {o.id for o in item.options}:
            self._deny(IllegalTransition(f"unknown option '{option_id}'"), item.deal_id, actor, "answer", item.id)
        item.answer = option_id
        item.state = State.PROPOSED
        self._log(item.deal_id, actor, "answer", "ALLOWED", item.id, reason=f"option {option_id}")
        return item

    def hold(self, actor: str, item_id: str) -> WorkItem:
        """Pause this branch. The item stays NEEDS_INFO and the hold is logged."""
        item = self._item(item_id)
        self._require(actor, "hold", item.deal_id, item.id)
        if item.state != State.NEEDS_INFO:
            self._deny(IllegalTransition(f"cannot hold an item in state {item.state.value}"),
                       item.deal_id, actor, "hold", item.id)
        item.payload["held"] = True
        self._log(item.deal_id, actor, "hold", "ALLOWED", item.id, reason="reviewer is not sure")
        return item

    def approve(self, actor: str, item_id: str) -> WorkItem:
        item = self._item(item_id)
        self._require(actor, "approve", item.deal_id, item.id)
        if actor == item.proposed_by:
            self._deny(Denied("the proposer cannot approve its own item"), item.deal_id, actor, "approve", item.id)
        if item.state != State.PROPOSED:
            self._deny(IllegalTransition(f"cannot approve an item in state {item.state.value}"),
                       item.deal_id, actor, "approve", item.id)
        item.state = State.APPROVED
        self._log(item.deal_id, actor, "approve", "ALLOWED", item.id)
        self._post(item)
        return item

    def reject(self, actor: str, item_id: str, reason: str) -> WorkItem:
        item = self._item(item_id)
        self._require(actor, "reject", item.deal_id, item.id)
        if item.state not in (State.PROPOSED, State.NEEDS_INFO):
            self._deny(IllegalTransition(f"cannot reject an item in state {item.state.value}"),
                       item.deal_id, actor, "reject", item.id)
        item.state = State.REJECTED
        item.reject_reason = reason
        self._log(item.deal_id, actor, "reject", "ALLOWED", item.id, reason=reason)
        return item

    def _post(self, item: WorkItem) -> None:
        """Only the gateway posts to the record."""
        item.state = State.POSTED
        self._log(item.deal_id, "system:gateway", "post", "ALLOWED", item.id)

    # ---- plans ----
    def post_plan(self, actor: str, plan: Plan, existing_senior: float, ebitda: float, limit: float,
                  preferred_counts_as_debt: bool, clause_evidence: Evidence) -> Plan:
        """Store a plan only if it respects the leverage limit. Otherwise log DENIED with the clause."""
        self._require(actor, "post_plan", plan.deal_id, plan.id)
        breach, lev = leverage_breach(existing_senior, ebitda, plan.instruments, limit, preferred_counts_as_debt)
        plan.metrics["leverage"] = lev
        plan.metrics["leverage_limit"] = limit
        if breach and plan.needs_consent:
            # The plan breaks the limit unless the lender consents. Store it as conditional, never as clear.
            plan.status = "needs_consent"
            plan.blocked_by = clause_evidence
            self.store.plans[plan.id] = plan
            self._log(plan.deal_id, actor, "post_plan", "ALLOWED", plan.id, evidence=[clause_evidence],
                      reason=f"{lev:.2f}x is more than {limit:.2f}x. Allowed only with lender consent")
            return plan
        if breach:
            plan.status = "blocked"
            plan.blocked_by = clause_evidence
            self.store.plans[plan.id] = plan
            self._deny(Denied(f"Plan breaks the leverage limit: {lev:.2f}x is more than {limit:.2f}x"),
                       plan.deal_id, actor, "post_plan", plan.id, [clause_evidence])
        plan.status = "ok"
        self.store.plans[plan.id] = plan
        self._log(plan.deal_id, actor, "post_plan", "ALLOWED", plan.id, reason=f"{lev:.2f}x within {limit:.2f}x")
        return plan

    # ---- events ----
    def inject_event(self, actor: str, deal_id: str, kind: str, detail: str) -> WorkItem:
        self._require(actor, "inject_event", deal_id)
        item = WorkItem(id=self.store.next_id("wi"), deal_id=deal_id, type="event", state=State.POSTED,
                        proposed_by=actor, payload={"kind": kind, "detail": detail})
        self.store.items[item.id] = item
        for plan in self.store.plans.values():
            if plan.deal_id == deal_id:
                plan.stale = True
        self._log(deal_id, actor, f"event:{kind}", "ALLOWED", item.id, reason=detail)
        return item
