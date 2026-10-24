"""The gateway: the only writer.

It checks the actor, the permission, the state change, maker-checker, and the run ids on every number.
It runs the math tools and records a ToolRun for each call. It writes one audit row for every action and
every denied attempt, chained by hash. Rules are in docs/architecture/gateway-and-api.md.
"""
from __future__ import annotations

import functools
import hashlib
import json
import threading
from typing import Any

from app.core.models import (
    CONTROLLER,
    MAPPER,
    PREPARER,
    REVIEWER,
    SYSTEM,
    AuditRow,
    Deal,
    AgentSession,
    Evidence,
    FlagProposal,
    Mapping,
    MapperOutput,
    Option,
    Policy,
    PreparerOutput,
    Result,
    ResultRow,
    Review,
    ReviewerOutput,
    SourceLine,
    State,
    ToolRun,
    WorkItem,
    now,
)
from app.db.memory import MemoryStore
from app.tools import finance

GENESIS = "0" * 64

# Per-role permissions. Agents are named, so the Mapper cannot call the Preparer's tools.
PERMISSIONS: dict[str, set[str]] = {
    MAPPER: {"propose:map_lines"},
    PREPARER: {"propose:prepare_result", "tool:consolidate", "tool:ebitda", "tool:covenant_debt", "tool:leverage"},
    REVIEWER: {"propose:review_result", "tool:tie_out", "tool:limit_test", "tool:leverage"},
    "human": {"answer", "approve", "reject", "hold", "reverse", "create_deal", "run"},
    "system": {"post", "log", "create_item", "tool:*"},
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


class Invalid(GatewayError):
    status = 422


def parse_actor(actor: str) -> tuple[str, str]:
    kind, _, name = actor.partition(":")
    if kind not in ("agent", "human", "system") or not name:
        raise Denied(f"unknown actor '{actor}'")
    return kind, name


def _hash(row: dict, prev_hash: str) -> str:
    body = json.dumps({**row, "prev_hash": prev_hash}, sort_keys=True, default=str)
    return hashlib.sha256(body.encode()).hexdigest()


def _fmt(x: float) -> str:
    return f"{x:,.0f}"


def _writes(method):
    """A public write holds the gateway lock, and the outermost one commits the store, also when it is denied."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self.lock:
            self._depth += 1
            try:
                return method(self, *args, **kwargs)
            finally:
                self._depth -= 1
                if self._depth == 0:
                    self.store.commit()
    return wrapper


class Gateway:
    def __init__(self, store: MemoryStore):
        self.store = store
        self.lock = threading.RLock()  # background runs and requests write through one gateway
        self._depth = 0

    # ------------------------------------------------------------------ audit log
    def _log(self, deal_id: str, actor: str, action: str, result: str, target: str | None = None,
             reason: str | None = None, evidence: list[Evidence] | None = None) -> AuditRow:
        prev = self.store.audit[-1].hash if self.store.audit else GENESIS
        base = dict(id=len(self.store.audit) + 1, at=now(), deal_id=deal_id, actor=actor, action=action,
                    target=target, result=result, reason=reason, evidence=[e.model_dump() for e in (evidence or [])])
        row = AuditRow(**{**base, "evidence": evidence or []}, prev_hash=prev, hash=_hash(base, prev))
        self.store.audit.append(row)
        return row

    def verify_chain(self) -> bool:
        prev = GENESIS
        for row in self.store.audit:
            base = dict(id=row.id, at=row.at, deal_id=row.deal_id, actor=row.actor, action=row.action,
                        target=row.target, result=row.result, reason=row.reason,
                        evidence=[e.model_dump() for e in row.evidence])
            if row.prev_hash != prev or row.hash != _hash(base, prev):
                return False
            prev = row.hash
        return True

    def _deny(self, error: GatewayError, deal_id: str, actor: str, action: str, target: str | None = None,
              evidence: list[Evidence] | None = None) -> None:
        self._log(deal_id, actor, action, "DENIED", target, error.message, evidence)
        raise error

    def _allowed(self, actor: str, action: str) -> bool:
        kind, _ = parse_actor(actor)
        perms = PERMISSIONS.get(actor) if kind == "agent" else PERMISSIONS.get(kind)
        if not perms:
            return False
        if action in perms:
            return True
        if action.startswith("tool:") and "tool:*" in perms:
            return True
        return False

    def _require(self, actor: str, action: str, deal_id: str, target: str | None = None) -> str:
        try:
            kind, _ = parse_actor(actor)
        except Denied as error:
            self._deny(error, deal_id, actor, action, target)
        if not self._allowed(actor, action):
            self._deny(Denied(f"{actor} may not {action}"), deal_id, actor, action, target)
        return kind

    # ------------------------------------------------------------------ lookups
    def _item(self, item_id: str) -> WorkItem:
        item = self.store.items.get(item_id)
        if not item:
            raise NotFound(f"work item {item_id} not found")
        return item

    def _deal(self, deal_id: str) -> Deal:
        deal = self.store.deals.get(deal_id)
        if not deal:
            raise NotFound(f"deal {deal_id} not found")
        return deal

    def _platform_lines(self, deal: Deal) -> list[SourceLine]:
        return self.store.lines(deal.id, deal.platform)

    def _target_lines(self, deal: Deal) -> list[SourceLine]:
        return self.store.lines(deal.id, deal.target)

    def _usable_mappings(self, deal_id: str) -> list[Mapping]:
        return [m for m in self.store.deal_mappings(deal_id) if not m.flagged or m.approved_by]

    def open_flags(self, deal_id: str) -> list[WorkItem]:
        return [i for i in self.store.deal_items(deal_id, "flag") if i.state == State.NEEDS_INFO]

    # ------------------------------------------------------------------ deals and items
    @_writes
    def create_deal(self, actor: str, deal: Deal, lines: list[SourceLine]) -> Deal:
        self._require(actor, "create_deal", deal.id)
        if deal.id in self.store.deals:
            raise Invalid(f"deal {deal.id} exists")
        self.store.deals[deal.id] = deal
        for line in lines:
            self.store.source_lines[line.id] = line
        self._log(deal.id, actor, "create_deal", "ALLOWED", deal.id, reason=f"{len(lines)} source lines loaded")
        return deal

    @_writes
    def create_item(self, deal_id: str, type_: str, proposed_by: str = SYSTEM, payload: dict | None = None) -> WorkItem:
        """The job runner asks the gateway to open the next work item. Only the system may do this."""
        self._deal(deal_id)
        item = WorkItem(id=self.store.next_id("wi"), deal_id=deal_id, type=type_, state=State.NEW,
                        proposed_by=proposed_by, payload=payload or {})
        self.store.items[item.id] = item
        self._log(deal_id, SYSTEM, f"create:{type_}", "ALLOWED", item.id)
        return item

    # ------------------------------------------------------------------ tools
    @_writes
    def run_tool(self, actor: str, deal_id: str, name: str, inputs: dict[str, Any] | None = None) -> ToolRun:
        """Run one math tool for a deal and record the run. The agent passes arguments, never numbers it made."""
        inputs = dict(inputs or {})
        self._require(actor, f"tool:{name}", deal_id)
        deal = self._deal(deal_id)
        fn = finance.TOOLS.get(name)
        if fn is None:
            raise NotFound(f"tool {name} not found")
        platform_lines = self._platform_lines(deal)
        target_lines = self._target_lines(deal)
        try:
            if name == "consolidate":
                mappings = self._usable_mappings(deal_id)
                if self.open_flags(deal_id):
                    raise ValueError("flags are still open")
                outputs = fn(platform_lines, target_lines, mappings)
                inputs["mapping_ids"] = [m.id for m in mappings]
            elif name == "tie_out":
                rows = inputs.get("rows")
                if rows is None and inputs.get("run_id"):
                    rows = self._run(deal_id, inputs["run_id"]).outputs["rows"]
                if rows is None:
                    raise ValueError("tie_out needs rows or run_id")
                outputs = fn(rows)
            elif name == "ebitda":
                outputs = fn(platform_lines, target_lines, deal.brief)
            elif name == "covenant_debt":
                outputs = fn(platform_lines, target_lines, deal.brief, naive=bool(inputs.get("naive", False)))
            elif name == "leverage":
                debt = inputs.get("debt")
                eb = inputs.get("ebitda")
                if inputs.get("debt_run_id"):
                    debt = self._run(deal_id, inputs["debt_run_id"]).outputs["debt"]
                if inputs.get("ebitda_run_id"):
                    eb = self._run(deal_id, inputs["ebitda_run_id"]).outputs["ebitda"]
                if debt is None or eb is None:
                    raise ValueError("leverage needs debt and ebitda, by value or by run id")
                outputs = fn(float(debt), float(eb))
            elif name == "limit_test":
                lev = inputs.get("leverage")
                eb = debt = None
                if inputs.get("leverage_run_id"):
                    lrun = self._run(deal_id, inputs["leverage_run_id"]).outputs
                    lev, eb, debt = lrun["leverage"], lrun.get("ebitda"), lrun.get("debt")
                if lev is None:
                    raise ValueError("limit_test needs leverage, by value or by run id")
                outputs = fn(float(lev), deal.brief.limit, ebitda_value=eb, debt=debt)
            else:
                raise ValueError(f"no argument binding for {name}")
        except ValueError as error:
            self._log(deal_id, actor, f"tool:{name}", "ALLOWED", None, reason=f"error: {error}")
            raise Invalid(str(error))
        run = ToolRun(run_id=self.store.next_id("run"), deal_id=deal_id, tool=name, actor=actor, inputs=inputs,
                      outputs=outputs)
        self.store.tool_runs[run.run_id] = run
        self._log(deal_id, actor, f"tool:{name}", "ALLOWED", run.run_id)
        return run

    def _run(self, deal_id: str, run_id: str) -> ToolRun:
        run = self.store.tool_runs.get(run_id)
        if not run or run.deal_id != deal_id:
            raise ValueError(f"run id {run_id} not found for this deal")
        return run

    # ------------------------------------------------------------------ mapper result
    @_writes
    def store_mapping(self, actor: str, item_id: str, out: MapperOutput) -> WorkItem:
        item = self._item(item_id)
        self._require(actor, "propose:map_lines", item.deal_id, item.id)
        if item.type != "map_lines" or item.state != State.NEW:
            self._deny(IllegalTransition(f"cannot store a mapping on {item.type} in state {item.state.value}"),
                       item.deal_id, actor, "propose:map_lines", item.id)
        deal = self._deal(item.deal_id)
        out = MapperOutput.model_validate(out.model_dump())  # the gateway re-validates the typed result
        target_by_id = {l.id: l for l in self._target_lines(deal)}
        flagged_ids = {lid for f in out.flags if f.kind == "mapping" for lid in f.line_ids}
        for p in out.mappings:
            t = target_by_id.get(p.target_line_id)
            if t is None:
                raise Invalid(f"mapping names unknown target line {p.target_line_id}")
            pl = self._platform_line(deal, t.section, p.platform_line)
            m = Mapping(id=self.store.next_id("m"), deal_id=deal.id, target_line_id=t.id,
                        platform_line_id=pl.id if pl else None, target_line=t.line,
                        platform_line=pl.line if pl else p.platform_line, confidence=p.confidence,
                        reason=p.reason, flagged=t.id in flagged_ids)
            self.store.mappings[m.id] = m
        for tag in out.tags:
            line = self.store.source_lines.get(tag.line_id)
            if line is None or line.deal_id != deal.id:
                raise Invalid(f"tag names unknown line {tag.line_id}")
            line.covenant_tag = tag.tag
            line.covenant_note = tag.note or None
            if tag.policy_id:
                self.note_policy_applied(tag.policy_id, deal.id, line.line)
        for p in out.mappings:
            if p.policy_id:
                self.note_policy_applied(p.policy_id, deal.id, target_by_id[p.target_line_id].line)
        item.state = State.PROPOSED
        item.payload = {"mappings": len(out.mappings), "tags": len(out.tags), "flags": len(out.flags),
                        "note": out.note}
        self._log(deal.id, actor, "propose:map_lines", "ALLOWED", item.id,
                  reason=f"{len(out.mappings)} mappings, {len(out.flags)} flags")
        for flag in out.flags:
            self._check_flag_resolves(flag)
        for flag in out.flags:
            self._open_flag(deal, item, flag)
        self._post(item)
        deal.stage = "awaiting_flag" if self.open_flags(deal.id) else "mapped"
        return item

    @staticmethod
    def _check_flag_resolves(flag: FlagProposal) -> None:
        """A covenant flag exists to settle its lines. Every option must give each flagged line a settled tag
        (debt or not_debt); an option that leaves a line unclear would block the Preparer after the answer.
        The Haiku 5.5 run of 2026-10-24 did this on "Short-term borrowings", and its replay stopped at the Preparer."""
        if flag.kind != "covenant_tag":
            return
        for opt in flag.options:
            unsettled = [lid for lid in flag.line_ids if opt.tags.get(lid) not in ("debt", "not_debt")]
            if unsettled:
                raise Invalid(f"flag option '{opt.id}' leaves {len(unsettled)} flagged line(s) unsettled "
                              f"({', '.join(unsettled)}): every option must tag each flagged line debt or not_debt")

    def _open_flag(self, deal: Deal, parent: WorkItem, flag: FlagProposal) -> WorkItem:
        """Turn a flag proposal into a NEEDS_INFO work item. The effect of each option is computed by tools."""
        options: list[Option] = []
        for opt in flag.options:
            effect, run_id = self._flag_effect(deal, flag, opt)
            options.append(Option(id=opt.id, label=opt.label, effect=effect, run_id=run_id))
        item = WorkItem(id=self.store.next_id("wi"), deal_id=deal.id, type="flag", state=State.NEEDS_INFO,
                        proposed_by=MAPPER, question=flag.question, evidence=flag.evidence, options=options,
                        default=flag.default,
                        payload={"kind": flag.kind, "line_ids": flag.line_ids, "parent": parent.id,
                                 "option_actions": {o.id: o.model_dump() for o in flag.options}})
        self.store.items[item.id] = item
        self._log(deal.id, MAPPER, "ask:flag", "ALLOWED", item.id, reason=flag.question, evidence=flag.evidence)
        return item

    def _flag_effect(self, deal: Deal, flag: FlagProposal, opt) -> tuple[str, str | None]:
        """What-if for one option, run by the system through the same tools. Tags are restored afterwards."""
        lines = {lid: self.store.source_lines[lid] for lid in flag.line_ids if lid in self.store.source_lines}
        saved = {lid: (l.covenant_tag, l.covenant_note) for lid, l in lines.items()}
        try:
            if flag.kind == "covenant_tag":
                for lid, tag in opt.tags.items():
                    if lid in lines:
                        lines[lid].covenant_tag = tag
                # Any other unclear line is counted as debt for the what-if, so the figure is a ceiling.
                debt = self.run_tool(SYSTEM, deal.id, "covenant_debt", {"naive": True, "what_if": opt.id})
                eb = self.run_tool(SYSTEM, deal.id, "ebitda", {"what_if": opt.id})
                lev = self.run_tool(SYSTEM, deal.id, "leverage", {"debt_run_id": debt.run_id, "ebitda_run_id": eb.run_id})
                test = self.run_tool(SYSTEM, deal.id, "limit_test", {"leverage_run_id": lev.run_id})
                verdict = "OK" if test.outputs["ok"] else "Over the limit"
                # Format from the unrounded ratio: the tool rounds to 3 places, and rounding that again to 2
                # showed 2.6148 as 2.62x while the verdict line said 2.61x.
                ratio = lev.outputs["debt"] / lev.outputs["ebitda"]
                effect = (f"{deal.brief.debt_term} {_fmt(debt.outputs['debt'])}K. Leverage {ratio:.2f}x "
                          f"against {deal.brief.limit:.2f}x. {verdict}.")
                return effect, test.run_id
            if flag.kind == "mapping":
                parts = []
                for lid, l in lines.items():
                    ref = opt.mappings.get(lid, opt.platform_line) if opt.mappings else opt.platform_line
                    pl = self._platform_line(deal, l.section, ref)
                    amt = finance.to_thousands(l.amount, l.unit)
                    if pl:
                        parts.append(f"{l.line} ({_fmt(amt)}K) to {pl.line}")
                    elif ref:
                        parts.append(f"{l.line} ({_fmt(amt)}K) to '{ref}', which is not a platform line")
                    else:
                        parts.append(f"{l.line} ({_fmt(amt)}K) left unmapped and listed")
                return "; ".join(parts) + ".", None
            return "No effect computed.", None
        except GatewayError as error:
            return f"Effect not computed: {error.message}", None
        finally:
            for lid, (tag, note) in saved.items():
                lines[lid].covenant_tag = tag
                lines[lid].covenant_note = note

    # ------------------------------------------------------------------ human moments
    @_writes
    def answer(self, actor: str, item_id: str, option_id: str) -> WorkItem:
        item = self._item(item_id)
        self._require(actor, "answer", item.deal_id, item.id)
        if item.state != State.NEEDS_INFO:
            self._deny(IllegalTransition(f"cannot answer an item in state {item.state.value}"),
                       item.deal_id, actor, "answer", item.id)
        if option_id not in {o.id for o in item.options}:
            self._deny(IllegalTransition(f"unknown option '{option_id}'"), item.deal_id, actor, "answer", item.id)
        item.answer = option_id
        if item.type == "flag":
            self._apply_flag_answer(actor, item, option_id)
            item.state = State.APPROVED
            self._log(item.deal_id, actor, "answer", "ALLOWED", item.id, reason=f"option {option_id}")
            self._post(item)
            deal = self._deal(item.deal_id)
            deal.stage = "awaiting_flag" if self.open_flags(deal.id) else "flags_answered"
        else:
            item.state = State.PROPOSED
            self._log(item.deal_id, actor, "answer", "ALLOWED", item.id, reason=f"option {option_id}")
        return item

    def _apply_flag_answer(self, actor: str, item: WorkItem, option_id: str) -> None:
        action = item.payload.get("option_actions", {}).get(option_id, {})
        kind = item.payload.get("kind")
        label = next((o.label for o in item.options if o.id == option_id), option_id)
        if kind == "covenant_tag":
            for lid, tag in action.get("tags", {}).items():
                line = self.store.source_lines.get(lid)
                if line is not None:
                    line.covenant_tag = tag
                    line.covenant_note = f"decided by {actor} on flag {item.id}"
                    self._learn(MAPPER, "covenant_tag", line.line, tag, label, actor, item)
        elif kind == "mapping":
            deal = self._deal(item.deal_id)
            per_line = action.get("mappings") or {}
            for m in self.store.deal_mappings(item.deal_id):
                if m.target_line_id in item.payload.get("line_ids", []):
                    t = self.store.source_lines[m.target_line_id]
                    ref = per_line.get(t.id, action.get("platform_line")) if per_line else action.get("platform_line")
                    pl = self._platform_line(deal, t.section, ref)
                    m.platform_line = pl.line if pl else ref
                    m.platform_line_id = pl.id if pl else None
                    m.approved_by = actor
                    m.flagged = True
                    self._learn(MAPPER, "mapping", t.line, (pl.line if pl else ref) or "", label, actor, item)

    def _platform_line(self, deal: Deal, section: str, ref: str | None) -> SourceLine | None:
        """Find a platform line by id or by name (case-insensitive) within a section."""
        if not ref:
            return None
        line = self.store.source_lines.get(ref)
        if line is not None and line.deal_id == deal.id and line.company == deal.platform:
            return line
        key = ref.strip().lower()
        for l in self._platform_lines(deal):
            if l.section == section and l.line.strip().lower() == key:
                return l
        for l in self._platform_lines(deal):  # a name that exists in another section still resolves
            if l.line.strip().lower() == key:
                return l
        return None

    def _learn(self, role: str, kind: str, pattern: str, decision: str, label: str, actor: str, item: WorkItem) -> Policy:
        """The controller's answer becomes a policy the agent applies next time. The gateway is the writer."""
        key = pattern.strip().lower()
        for p in self.store.policies.values():
            if p.role == role and p.kind == kind and p.pattern == key:
                p.decision, p.approved_by, p.learned_from, p.reason = decision, actor, item.id, label
                self._log(item.deal_id, SYSTEM, "policy:update", "ALLOWED", p.id, reason=f"{key} -> {decision}")
                return p
        policy = Policy(id=self.store.next_id("p"), role=role, kind=kind, pattern=key, decision=decision,
                        reason=f"{actor} chose '{label}' on flag {item.id}", approved_by=actor,
                        learned_from=item.id, deal_id=item.deal_id)
        self.store.policies[policy.id] = policy
        self._log(item.deal_id, SYSTEM, "policy:learn", "ALLOWED", policy.id, reason=f"{key} -> {decision}")
        return policy

    @_writes
    def note_policy_applied(self, policy_id: str, deal_id: str, line: str) -> None:
        p = self.store.policies.get(policy_id)
        if p:
            p.times_applied += 1
            self._log(deal_id, SYSTEM, "policy:apply", "ALLOWED", p.id, reason=line)

    @_writes
    def session(self, role: str, backend: str) -> AgentSession:
        """The role's one session. A change of backend keeps the turns and transcript; only the backend's own
        session id is dropped, because a Droid session id means nothing to another backend."""
        s = self.store.sessions.get(role)
        if s is None:
            s = AgentSession(role=role, backend=backend)
            self.store.sessions[role] = s
        elif s.backend != backend:
            s.backend, s.session_id, s.session_key = backend, None, None
        return s

    @_writes
    def update_session(self, role: str, backend: str, item_id: str, summary: str, session_id: str | None = None,
                       session_key: str | None = None) -> AgentSession:
        s = self.session(role, backend)
        s.turns += 1
        s.updated_at = now()
        if session_id:
            s.session_id, s.session_key = session_id, session_key
        s.transcript.append({"item": item_id, "summary": summary, "at": now().isoformat()})
        s.transcript = s.transcript[-20:]
        deal_id = self.store.items[item_id].deal_id if item_id in self.store.items else ""
        self._log(deal_id, SYSTEM, "session:turn", "ALLOWED", role, reason=f"{backend} turn {s.turns}")
        return s

    @_writes
    def hold(self, actor: str, item_id: str) -> WorkItem:
        item = self._item(item_id)
        self._require(actor, "hold", item.deal_id, item.id)
        if item.state != State.NEEDS_INFO:
            self._deny(IllegalTransition(f"cannot hold an item in state {item.state.value}"),
                       item.deal_id, actor, "hold", item.id)
        item.payload["held"] = True
        self._log(item.deal_id, actor, "hold", "ALLOWED", item.id, reason="controller is not sure")
        return item

    @_writes
    def approve(self, actor: str, item_id: str) -> WorkItem:
        item = self._item(item_id)
        self._require(actor, "approve", item.deal_id, item.id)
        if actor == item.proposed_by:
            self._deny(Denied("the proposer cannot approve its own item"), item.deal_id, actor, "approve", item.id)
        if item.state != State.PROPOSED:
            self._deny(IllegalTransition(f"cannot approve an item in state {item.state.value}"),
                       item.deal_id, actor, "approve", item.id)
        if item.type == "approve_result":
            result = self.store.results.get(item.payload.get("result_id", ""))
            if result is None or result.review is None or result.review.verdict != "pass":
                self._deny(Denied("a result cannot be approved until the Reviewer verdict is pass"),
                           item.deal_id, actor, "approve", item.id)
        item.state = State.APPROVED
        self._log(item.deal_id, actor, "approve", "ALLOWED", item.id)
        self._post(item)
        if item.type == "approve_result":
            self._deal(item.deal_id).stage = "posted"
        return item

    @_writes
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

    @_writes
    def reverse(self, actor: str, item_id: str, reason: str) -> WorkItem:
        """A reversal is a new item linked to the original. Nothing is deleted."""
        item = self._item(item_id)
        self._require(actor, "reverse", item.deal_id, item.id)
        if item.state != State.POSTED:
            self._deny(IllegalTransition(f"cannot reverse an item in state {item.state.value}"),
                       item.deal_id, actor, "reverse", item.id)
        rev = WorkItem(id=self.store.next_id("wi"), deal_id=item.deal_id, type=f"reverse:{item.type}",
                       state=State.POSTED, proposed_by=actor, reverses_id=item.id,
                       payload={"reason": reason, "original_payload": item.payload})
        self.store.items[rev.id] = rev
        item.state = State.REVERSED
        self._log(item.deal_id, actor, "reverse", "ALLOWED", item.id, reason=reason)
        self._log(item.deal_id, SYSTEM, "post", "ALLOWED", rev.id, reason=f"reverses {item.id}")
        if item.type == "flag":
            self._deal(item.deal_id).stage = "awaiting_flag"
        return rev

    def _post(self, item: WorkItem) -> None:
        """Only the gateway posts to the record."""
        item.state = State.POSTED
        self._log(item.deal_id, SYSTEM, "post", "ALLOWED", item.id)

    # ------------------------------------------------------------------ preparer and reviewer results
    @_writes
    def store_result(self, actor: str, item_id: str, out: PreparerOutput, backend: str = "scripted") -> Result:
        item = self._item(item_id)
        self._require(actor, "propose:prepare_result", item.deal_id, item.id)
        if item.type != "prepare_result" or item.state != State.NEW:
            self._deny(IllegalTransition(f"cannot store a result on {item.type} in state {item.state.value}"),
                       item.deal_id, actor, "propose:prepare_result", item.id)
        deal = self._deal(item.deal_id)
        out = PreparerOutput.model_validate(out.model_dump())
        # Check 6: every number carries a run id from the math code, and the numbers match the runs.
        runs = {rid: self.store.tool_runs.get(rid) for rid in set(out.run_ids) | {r.run_id for r in out.rows}}
        for rid, run in runs.items():
            if run is None or run.deal_id != deal.id:
                self._deny(Invalid(f"run id {rid} does not exist for this deal"), deal.id, actor,
                           "propose:prepare_result", item.id)
        def produced(tool: str, key: str, value: float) -> bool:
            return any(r.tool == tool and abs(float(r.outputs.get(key, float("nan"))) - value) < 1e-6
                       for r in runs.values() if r)
        for tool, key, value in (("ebitda", "ebitda", out.ebitda), ("covenant_debt", "debt", out.debt),
                                 ("leverage", "leverage", out.leverage)):
            if not produced(tool, key, value):
                self._deny(Invalid(f"{key} {value} was not produced by a {tool} run in run_ids"), deal.id, actor,
                           "propose:prepare_result", item.id)
        if abs(out.limit - deal.brief.limit) > 1e-9:
            self._deny(Invalid("limit must come from the brief"), deal.id, actor, "propose:prepare_result", item.id)
        test = finance.limit_test(out.leverage, deal.brief.limit)
        by_tool = {k: v for k, v in (("consolidate", out.consolidate_run_id), ("ebitda", out.ebitda_run_id),
                                      ("covenant_debt", out.debt_run_id), ("leverage", out.leverage_run_id)) if v}
        for tool, rid in list(by_tool.items()):
            run = self.store.tool_runs.get(rid)
            if run is None or run.tool != tool or run.deal_id != deal.id:
                self._deny(Invalid(f"{tool}_run_id {rid} is not a {tool} run for this deal"), deal.id, actor,
                           "propose:prepare_result", item.id)
        for tool in ("consolidate", "ebitda", "covenant_debt", "leverage"):  # fill from run_ids when not named
            if tool not in by_tool:
                rid = next((r for r in out.run_ids if r in runs and runs[r] and runs[r].tool == tool), None)
                if rid:
                    by_tool[tool] = rid
        result = Result(id=self.store.next_id("r"), deal_id=deal.id, work_item_id=item.id, rows=out.rows,
                        ebitda=out.ebitda, debt=out.debt, leverage=out.leverage, limit=out.limit,
                        verdict=test["verdict"], headroom_turns=test["headroom_turns"], run_ids=out.run_ids,
                        run_ids_by_tool=by_tool, backend=backend)
        self.store.results[result.id] = result
        item.payload = {"result_id": result.id, "note": out.note}
        item.state = State.PROPOSED
        self._log(deal.id, actor, "propose:prepare_result", "ALLOWED", item.id,
                  reason=f"result {result.id}: leverage {out.leverage:.2f}x against {out.limit:.2f}x")
        deal.stage = "awaiting_review"
        return result

    @_writes
    def store_review(self, actor: str, item_id: str, out: ReviewerOutput) -> WorkItem:
        item = self._item(item_id)
        self._require(actor, "propose:review_result", item.deal_id, item.id)
        if item.type != "review_result" or item.state != State.NEW:
            self._deny(IllegalTransition(f"cannot store a review on {item.type} in state {item.state.value}"),
                       item.deal_id, actor, "propose:review_result", item.id)
        deal = self._deal(item.deal_id)
        out = ReviewerOutput.model_validate(out.model_dump())
        result = self.store.results.get(item.payload.get("result_id", ""))
        if result is None:
            raise Invalid("review item has no result")
        for rid in out.run_ids:
            if rid not in self.store.tool_runs:
                self._deny(Invalid(f"run id {rid} does not exist"), deal.id, actor, "propose:review_result", item.id)
        result.review = Review(verdict=out.verdict, reasons=out.reasons, run_ids=out.run_ids)
        tie = next((self.store.tool_runs[r] for r in out.run_ids if self.store.tool_runs[r].tool == "tie_out"), None)
        if tie is not None:
            result.tie_out_ok = bool(tie.outputs.get("ok"))
        item.state = State.PROPOSED
        self._log(deal.id, actor, "propose:review_result", "ALLOWED", item.id,
                  reason=f"{out.verdict}: {'; '.join(out.reasons) or 'no findings'}")
        self._post(item)
        # The approval item is proposed by the Preparer (the maker), so the maker-checker rule applies to it.
        approval = WorkItem(id=self.store.next_id("wi"), deal_id=deal.id, type="approve_result",
                            state=State.PROPOSED if out.verdict == "pass" else State.NEEDS_INFO,
                            proposed_by=PREPARER, payload={"result_id": result.id, "review_item": item.id},
                            question=None if out.verdict == "pass" else "The Reviewer found a problem: "
                            + "; ".join(out.reasons))
        self.store.items[approval.id] = approval
        self._log(deal.id, SYSTEM, "create:approve_result", "ALLOWED", approval.id,
                  reason="ready for the controller" if out.verdict == "pass" else "needs attention")
        deal.stage = "awaiting_approval" if out.verdict == "pass" else "needs_attention"
        return approval
