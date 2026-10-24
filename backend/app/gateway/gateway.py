"""The gateway: the only writer.

It checks the actor, the permission, the state change, maker-checker, and the run ids on every number.
It runs the math tools and records a ToolRun for each call. It writes one audit row for every action and
every denied attempt, chained by hash. Rules are in docs/architecture/gateway-and-api.md.
"""
from __future__ import annotations

import functools
import hashlib
import inspect
import json
import math
import re
import threading
from typing import Any

from app.core import agreement as agr
from app.core.models import (
    BRIEF_READER,
    CONTROLLER,
    MAPPER,
    PREPARER,
    REVIEWER,
    SYSTEM,
    AgreementText,
    AuditRow,
    Brief,
    BriefDraft,
    BriefReaderInput,
    BriefReaderOutput,
    Deal,
    AgentSession,
    Edit,
    Evidence,
    FlagOption,
    FlagProposal,
    LearnedAdjustment,
    Mapping,
    MapperOutput,
    Option,
    Policy,
    PreparerOutput,
    ReasonChip,
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
from app.agents.backends.scripted import reason_chips
from app.core.policies import newest_covering, policy_applies, same_name
from app.db.memory import MemoryStore
from app.tools import finance

GENESIS = "0" * 64
BASELINE_OPTION = "count_all"  # the option id of the baseline reading the gateway adds to a covenant flag
# The tools that take the controller's review edits (Tri's T1). The gateway refuses an edit while they do not.
# tie_out takes none: its rows come from the edited consolidate run, so applying the edits again would double count.
EDIT_TOOLS = ("consolidate", "ebitda", "covenant_debt")
T1_MISSING = "edit-aware tools not installed (T1)"
# The tools that read the Brief's terms: refused until the controller approves the Brief (D20).
BRIEF_TOOLS = ("ebitda", "covenant_debt", "limit_test")

# Per-role permissions. Agents are named, so the Mapper cannot call the Preparer's tools.
PERMISSIONS: dict[str, set[str]] = {
    BRIEF_READER: {"propose:draft_brief", "tool:get_section", "tool:get_definition"},
    MAPPER: {"propose:map_lines"},
    PREPARER: {"propose:prepare_result", "tool:consolidate", "tool:ebitda", "tool:covenant_debt", "tool:leverage"},
    REVIEWER: {"propose:review_result", "tool:tie_out", "tool:limit_test", "tool:leverage"},
    "human": {"answer", "approve", "reject", "hold", "reverse", "create_deal", "run", "amend_brief", "approve_brief"},
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


class NotReady(GatewayError):
    """A feature whose code has not landed yet, such as the edit-aware tools. Nothing is written."""
    status = 503


def parse_actor(actor: str) -> tuple[str, str]:
    kind, _, name = actor.partition(":")
    if kind not in ("agent", "human", "system") or not name:
        raise Denied(f"unknown actor '{actor}'")
    return kind, name


def _hash(row: dict, prev_hash: str) -> str:
    body = json.dumps({**row, "prev_hash": prev_hash}, sort_keys=True, default=str)
    return hashlib.sha256(body.encode()).hexdigest()


def _count(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _fmt(x: float) -> str:
    return f"{x:,.0f}"


def _brief_number_problem(brief: Brief, limit_may_be_missing: bool = False) -> str | None:
    """Every figure in a Brief is finite, and the limit is above zero (moved here from routes.py, so it holds for
    every Brief). A limit the reader did not find may be 0 while its flag is open."""
    figures = [("limit", brief.limit)]
    for group in ("ebitda_addbacks", "ebitda_deductions"):
        for i, a in enumerate(getattr(brief, group)):
            figures += [(f"{group}[{i}].amount", a.amount), (f"{group}[{i}].cap", a.cap)]
    figures += [(f"closing_financing[{i}].amount", f.amount) for i, f in enumerate(brief.closing_financing)]
    for path, value in figures:
        if value is not None and not math.isfinite(value):
            return f"{path} must be a finite number"
    if brief.limit <= 0 and not (limit_may_be_missing and brief.limit == 0):
        return "limit must be above zero"
    return None


def _signed(x: float) -> str:
    """A change as accountants write it: +500, or (500) for a decrease."""
    return f"({abs(x):,.0f})" if x < 0 else f"+{x:,.0f}"


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
        self.forks = None  # WhatIfForks when STORE=postgres and FORKS=tiger (app/gateway/whatif.py)
        self.running: set[str] = set()  # deal ids with a background run in flight, shared with the API routes

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
        """The flags that block the books: covenant and mapping questions. An adjustment flag does not block the
        Preparer or the Reviewer, because it is decided on the finished books; it blocks approval instead."""
        return [i for i in self.store.deal_items(deal_id, "flag")
                if i.state == State.NEEDS_INFO and i.payload.get("kind") != "adjustment"]

    def open_adjustment_flags(self, deal_id: str) -> list[WorkItem]:
        return [i for i in self.store.deal_items(deal_id, "flag")
                if i.state == State.NEEDS_INFO and i.payload.get("kind") == "adjustment"]

    # ------------------------------------------------------------------ deals and items
    @_writes
    def create_deal(self, actor: str, deal: Deal, lines: list[SourceLine]) -> Deal:
        self._require(actor, "create_deal", deal.id)
        if deal.id in self.store.deals:
            raise Invalid(f"deal {deal.id} exists")
        if deal.brief is not None:
            bad = _brief_number_problem(deal.brief)
            if bad:
                self._deny(Invalid(bad), deal.id, actor, "create_deal", deal.id)
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
        working = {"draft_brief": "reading_brief", "map_lines": "mapping", "prepare_result": "preparing"}.get(type_)
        if working:  # the console shows which agent is working during a 30 to 60 s model run
            self._deal(deal_id).stage = working
        return item

    @_writes
    def note_run_failed(self, deal_id: str, error: str) -> None:
        """A background run stopped on an error. The stage says so, so the console offers Run again instead of
        showing an agent working forever. The next run picks up where this one stopped."""
        deal = self._deal(deal_id)
        deal.stage = "run_failed"
        last = next((r for r in reversed(self.store.audit) if r.deal_id == deal_id), None)
        if last and last.action == "run:failed" and last.reason == error[:300]:
            return  # the runner already noted this failure; the background route notes it again
        self._log(deal_id, SYSTEM, "run:failed", "ALLOWED", deal_id, reason=error[:300])

    # ------------------------------------------------------------------ tools
    @_writes
    def run_tool(self, actor: str, deal_id: str, name: str, inputs: dict[str, Any] | None = None) -> ToolRun:
        """Run one math tool for a deal and record the run. The agent passes arguments, never numbers it made."""
        inputs = dict(inputs or {})
        self._require(actor, f"tool:{name}", deal_id)
        deal = self._deal(deal_id)
        if name in BRIEF_TOOLS and deal.brief_status != "approved":
            self._deny(IllegalTransition(f"{name} waits for the approved Brief (the Brief is {deal.brief_status})"),
                       deal_id, actor, f"tool:{name}")
        fn = finance.TOOLS.get(name)
        if fn is None:
            raise NotFound(f"tool {name} not found")
        platform_lines = self._platform_lines(deal)
        target_lines = self._target_lines(deal)
        try:
            ekw = self._edits_kwarg(actor, deal_id, name, fn, inputs)  # {"edits": [...]} on a recompute, else {}
            if name == "consolidate":
                mappings = self._usable_mappings(deal_id)
                if self.open_flags(deal_id):
                    raise ValueError("flags are still open")
                outputs = fn(platform_lines, target_lines, mappings, **ekw)
                inputs["mapping_ids"] = [m.id for m in mappings]
            elif name == "tie_out":
                rows = inputs.get("rows")
                if rows is None and inputs.get("run_id"):
                    rows = self._run(deal_id, inputs["run_id"]).outputs["rows"]
                if rows is None:
                    raise ValueError("tie_out needs rows or run_id")
                outputs = fn(rows, **ekw)
            elif name == "ebitda":
                # The deal's basis decides: as filed only after the controller chose the whole-line reading.
                # The system's what-ifs may ask for the as-filed figure explicitly.
                as_filed = deal.ebitda_basis == "as_filed" or (actor == SYSTEM and bool(inputs.get("as_filed")))
                inputs["as_filed"] = as_filed
                outputs = fn(platform_lines, target_lines, deal.brief, as_filed=as_filed, **ekw)
            elif name == "covenant_debt":
                outputs = fn(platform_lines, target_lines, deal.brief, naive=bool(inputs.get("naive", False)), **ekw)
            elif name == "leverage":
                # An agent passes run ids only, so its ratio always divides two tool outputs. The system may pass
                # values (the API's /tools route for people checking a figure by hand runs as the system).
                if actor != SYSTEM and (inputs.get("debt") is not None or inputs.get("ebitda") is not None):
                    raise ValueError("leverage takes debt_run_id and ebitda_run_id, not numbers")
                debt = inputs.get("debt")
                eb = inputs.get("ebitda")
                if inputs.get("debt_run_id"):
                    drun = self._run(deal_id, inputs["debt_run_id"])
                    if drun.tool != "covenant_debt":
                        raise ValueError("debt_run_id must name a covenant_debt run")
                    debt = drun.outputs["debt"]
                if inputs.get("ebitda_run_id"):
                    erun = self._run(deal_id, inputs["ebitda_run_id"])
                    if erun.tool != "ebitda":
                        raise ValueError("ebitda_run_id must name an ebitda run")
                    eb = erun.outputs["ebitda"]
                if debt is None or eb is None:
                    raise ValueError("leverage needs debt_run_id and ebitda_run_id")
                outputs = fn(float(debt), float(eb))
            elif name == "limit_test":
                lev = inputs.get("leverage")
                eb = debt = None
                if inputs.get("leverage_run_id"):
                    lrun = self._run(deal_id, inputs["leverage_run_id"]).outputs
                    lev, eb, debt = lrun["leverage"], lrun.get("ebitda"), lrun.get("debt")
                if lev is None:
                    raise ValueError("limit_test needs leverage, by value or by run id")
                naive = rent = None  # sensitivity: the whole-line debt and the rent deduction, read from runs
                if inputs.get("naive_debt_run_id"):
                    nrun = self._run(deal_id, inputs["naive_debt_run_id"])
                    if nrun.tool != "covenant_debt":
                        raise ValueError("naive_debt_run_id must name a covenant_debt run")
                    naive = nrun.outputs["debt"]
                naive_eb = None
                if inputs.get("naive_ebitda_run_id"):
                    nerun = self._run(deal_id, inputs["naive_ebitda_run_id"])
                    if nerun.tool != "ebitda":
                        raise ValueError("naive_ebitda_run_id must name an ebitda run")
                    naive_eb = nerun.outputs["ebitda"]
                if inputs.get("ebitda_run_id"):
                    erun = self._run(deal_id, inputs["ebitda_run_id"])
                    if erun.tool != "ebitda":
                        raise ValueError("ebitda_run_id must name an ebitda run")
                    import re  # used only here: rent as a word, so "Parent" or "Current" do not match
                    rents = [d["amount"] for d in erun.outputs["deductions"]
                             if re.search(r"\brent(al)?\b", d["name"], re.I)]
                    rent = sum(rents) if rents else None
                outputs = fn(float(lev), deal.brief.limit, ebitda_value=eb, debt=debt, naive_debt=naive,
                             rent_deduction=rent, naive_ebitda=naive_eb)
            else:
                raise ValueError(f"no argument binding for {name}")
            if ekw:
                self._check_edits_applied(name, outputs, [e.id for e in ekw["edits"]])
        except ValueError as error:
            self._log(deal_id, actor, f"tool:{name}", "ALLOWED", None, reason=f"error: {error}")
            raise Invalid(str(error))
        run = ToolRun(run_id=self.store.next_id("run"), deal_id=deal_id, tool=name, actor=actor, inputs=inputs,
                      outputs=outputs)
        self.store.tool_runs[run.run_id] = run
        self._log(deal_id, actor, f"tool:{name}", "ALLOWED", run.run_id)
        return run

    def _edits_kwarg(self, actor: str, deal_id: str, name: str, fn, inputs: dict[str, Any]) -> dict[str, Any]:
        """The review edits a run applies, named by id in its inputs so the run records them.
        Only the gateway's recompute passes them, and only the live (not reverted) edits of this deal count."""
        if "edit_ids" not in inputs:
            return {}
        if actor != SYSTEM:
            raise ValueError("only the gateway recomputes with review edits")
        if name not in EDIT_TOOLS:
            raise ValueError(f"{name} takes no edits; it reads the runs it is given")
        if "edits" not in inspect.signature(fn).parameters:
            raise ValueError(T1_MISSING)
        edits = []
        for eid in inputs["edit_ids"]:
            e = self.store.edits.get(eid)
            if e is None or e.deal_id != deal_id:
                raise ValueError(f"edit {eid} not found for this deal")
            if e.status == "reverted":
                raise ValueError(f"edit {eid} is reverted")
            edits.append(e)
        return {"edits": edits}

    @staticmethod
    def _check_edits_applied(name: str, outputs: dict, live: list[str]) -> None:
        """The T1 contract: an edit-aware tool returns `edits_applied`, the ids of the edits it used. Every id must be
        a live edit it was given, and consolidate, which every edit changes, must have applied all of them."""
        applied = outputs.get("edits_applied")
        if not isinstance(applied, list) or not all(isinstance(i, str) for i in applied):
            raise ValueError(f"{name} did not return edits_applied, the list of edit ids it applied")
        unknown = [i for i in applied if i not in live]
        if unknown or len(set(applied)) != len(applied):
            raise ValueError(f"{name} reports edits it was not given: {', '.join(unknown) or 'a duplicate id'}")
        if name == "consolidate" and set(applied) != set(live):
            missing = [i for i in live if i not in applied]
            raise ValueError(f"consolidate did not apply edits {', '.join(missing)}")

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
        if deal.brief_status != "approved":
            self._deny(IllegalTransition(f"mapping waits for the approved Brief (the Brief is {deal.brief_status})"),
                       deal.id, actor, "propose:map_lines", item.id)
        out = MapperOutput.model_validate(out.model_dump())  # the gateway re-validates the typed result
        target_by_id = {l.id: l for l in self._target_lines(deal)}
        flagged_ids = {lid for f in out.flags if f.kind == "mapping" for lid in f.line_ids}
        try:  # check the whole result before writing any of it, so a refused result leaves nothing behind
            self._check_mapping(deal, out, target_by_id)
        except Invalid as error:
            self._deny(error, deal.id, actor, "propose:map_lines", item.id)
        stored: list[Mapping] = []
        for p in out.mappings:
            t = target_by_id[p.target_line_id]
            pl = self._platform_line(deal, t.section, p.platform_line)
            m = Mapping(id=self.store.next_id("m"), deal_id=deal.id, target_line_id=t.id,
                        platform_line_id=pl.id if pl else None, target_line=t.line,
                        platform_line=pl.line if pl else p.platform_line, confidence=p.confidence,
                        reason=p.reason, flagged=t.id in flagged_ids)
            m.policy_id = self._cited_policy(p.policy_id, "mapping", m.platform_line, t)
            self.store.mappings[m.id] = m
            stored.append(m)
        for tag in out.tags:
            line = self.store.source_lines[tag.line_id]
            line.covenant_tag = tag.tag
            line.covenant_note = tag.note or None
            line.covenant_policy_id = self._cited_policy(tag.policy_id, "covenant_tag", tag.tag, line)
            if line.covenant_policy_id:
                self.note_policy_applied(line.covenant_policy_id, deal.id, line.line)
        for m in stored:
            if m.policy_id:
                self.note_policy_applied(m.policy_id, deal.id, m.target_line)
        item.state = State.PROPOSED
        item.payload = {"mappings": len(out.mappings), "tags": len(out.tags), "flags": len(out.flags),
                        "note": out.note}
        self._log(deal.id, actor, "propose:map_lines", "ALLOWED", item.id,
                  reason=f"{_count(len(out.mappings), 'mapping')}, {_count(len(out.flags), 'flag')}")
        for flag in out.flags:
            self._open_flag(deal, item, flag)
        self._post(item)
        deal.stage = "awaiting_flag" if self.open_flags(deal.id) else "mapped"
        return item

    def _check_mapping(self, deal: Deal, out: MapperOutput, target_by_id: dict[str, SourceLine]) -> None:
        for p in out.mappings:
            if p.target_line_id not in target_by_id:
                raise Invalid(f"mapping names unknown target line {p.target_line_id}: target_line_id must be the id "
                              f"of a target line ({deal.target}), never a platform line")
        for tag in out.tags:
            line = self.store.source_lines.get(tag.line_id)
            if line is None or line.deal_id != deal.id:
                raise Invalid(f"tag names unknown line {tag.line_id}")
            # An exclusion lowers the debt figure, so only the controller may make one: by answering a flag now,
            # or by an earlier answer the Mapper cites as a policy for this company's line. The prompt says the
            # same, but the gateway is what enforces it, also against text injected into a line name.
            if tag.tag == "not_debt" and not self._cited_policy(tag.policy_id, "covenant_tag", "not_debt", line):
                raise Invalid(f"tag not_debt on {line.line} ({tag.line_id}) is the controller's call: tag it unclear "
                              f"and put it in the covenant flag, or cite the policy that decided it")
        for flag in out.flags:
            self._check_flag_resolves(flag)

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
        with_baseline = self._with_baseline(flag)
        baseline_added = len(with_baseline.options) > len(flag.options)
        flag = with_baseline
        options: list[Option] = []
        for opt in flag.options:
            effect, run_id = self._flag_effect(deal, flag, opt)
            figures = {}
            test = self.store.tool_runs.get(run_id) if run_id else None
            lev = self.store.tool_runs.get(test.inputs.get("leverage_run_id", "")) if test else None
            if test and lev:
                figures = dict(leverage=lev.outputs["debt"] / lev.outputs["ebitda"], ok=bool(test.outputs["ok"]),
                               basis="as_filed" if self._whole_line(flag, opt.tags) else "covenant")
            options.append(Option(id=opt.id, label=opt.label, effect=effect, run_id=run_id,
                                  added_by=SYSTEM if opt is flag.options[-1] and baseline_added else None, **figures))
        item = WorkItem(id=self.store.next_id("wi"), deal_id=deal.id, type="flag", state=State.NEEDS_INFO,
                        proposed_by=MAPPER, question=flag.question, evidence=flag.evidence, options=options,
                        default=flag.default,
                        payload={"kind": flag.kind, "line_ids": flag.line_ids, "parent": parent.id,
                                 "option_actions": {o.id: o.model_dump() for o in flag.options}})
        self.store.items[item.id] = item
        self._log(deal.id, MAPPER, "ask:flag", "ALLOWED", item.id, reason=flag.question, evidence=flag.evidence)
        if self.forks:
            self.forks.flag_opened(item)
        return item

    @_writes
    def note_fork(self, item_id: str, fork: dict, action: str, reason: str) -> None:
        """Record a step of a flag's what-if fork on the flag and in the log. Only the gateway's fork helper calls it."""
        item = self._item(item_id)
        item.payload = {**item.payload, "fork": fork}
        self._log(item.deal_id, SYSTEM, action, "ALLOWED", item.id, reason=reason)

    @staticmethod
    def _with_baseline(flag: FlagProposal) -> FlagProposal:
        """A covenant flag always shows the reading that counts every flagged line as debt, computed like the others.
        The Mapper's options vary from run to run (the 08:30 Haiku run on 2026-10-24 offered three readings, all
        under the limit), so the gateway adds the baseline when no option has it: the controller always sees what
        the exclusions are worth."""
        if flag.kind != "covenant_tag" or not flag.line_ids:
            return flag
        if any(all(o.tags.get(lid) == "debt" for lid in flag.line_ids) for o in flag.options):
            return flag
        ids = {o.id for o in flag.options}
        baseline = FlagOption(id=next(i for i in (BASELINE_OPTION, f"{BASELINE_OPTION}_gateway") if i not in ids),
                              tags={lid: "debt" for lid in flag.line_ids},
                              label="Count every flagged line as debt, with no exclusions (the gateway's baseline)")
        return flag.model_copy(update={"options": [*flag.options, baseline]})

    @staticmethod
    def _whole_line(flag: FlagProposal | WorkItem, tags: dict[str, str]) -> bool:
        """The option that counts every flagged line as debt: the reading of someone who has not read the agreement."""
        line_ids = flag.line_ids if isinstance(flag, FlagProposal) else flag.payload.get("line_ids", [])
        return bool(line_ids) and all(tags.get(lid) == "debt" for lid in line_ids)

    def _flag_effect(self, deal: Deal, flag: FlagProposal, opt) -> tuple[str, str | None]:
        """What-if for one option, run by the system through the same tools. Tags are restored afterwards.

        The whole-line option is computed as filed: balance sheet debt over reported EBITDA, with none of the
        agreement's add-backs or its rent deduction. Counting the Statesville financing as debt while still
        subtracting its rent would mix two readings, so that option is one reading from end to end."""
        lines = {lid: self.store.source_lines[lid] for lid in flag.line_ids if lid in self.store.source_lines}
        saved = {lid: (l.covenant_tag, l.covenant_note) for lid, l in lines.items()}
        try:
            if flag.kind == "covenant_tag":
                for lid, tag in opt.tags.items():
                    if lid in lines:
                        lines[lid].covenant_tag = tag
                # Any other unclear line is counted as debt for the what-if, so the figure is a ceiling.
                as_filed = self._whole_line(flag, opt.tags)
                debt = self.run_tool(SYSTEM, deal.id, "covenant_debt", {"naive": True, "what_if": opt.id})
                eb = self.run_tool(SYSTEM, deal.id, "ebitda", {"what_if": opt.id, "as_filed": as_filed})
                lev = self.run_tool(SYSTEM, deal.id, "leverage", {"debt_run_id": debt.run_id, "ebitda_run_id": eb.run_id})
                test = self.run_tool(SYSTEM, deal.id, "limit_test", {"leverage_run_id": lev.run_id})
                verdict = "OK" if test.outputs["ok"] else "Over the limit"
                # Format from the unrounded ratio: the tool rounds to 3 places, and rounding that again to 2
                # showed 2.6148 as 2.62x while the verdict line said 2.61x.
                ratio = lev.outputs["debt"] / lev.outputs["ebitda"]
                if as_filed:
                    effect = (f"As filed: debt {_fmt(debt.outputs['debt'])}K over reported EBITDA "
                              f"{_fmt(eb.outputs['ebitda'])}K. Leverage {ratio:.2f}x against {deal.brief.limit:.2f}x. "
                              f"{verdict}.")
                else:
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
        if item.type == "flag" and item.payload.get("kind") == "adjustment":
            return self._answer_adjustment(actor, item, option_id)
        if item.type == "flag" and item.payload.get("kind") == "brief_field":
            return self._answer_brief_field(actor, item, option_id)
        item.answer = option_id
        if item.type == "flag":
            self._apply_flag_answer(actor, item, option_id)
            item.state = State.APPROVED
            self._log(item.deal_id, actor, "answer", "ALLOWED", item.id, reason=f"option {option_id}")
            self._post(item)
            deal = self._deal(item.deal_id)
            deal.stage = "awaiting_flag" if self.open_flags(deal.id) else "flags_answered"
            if self.forks:
                self.forks.flag_answered(item)
        else:
            item.state = State.PROPOSED
            self._log(item.deal_id, actor, "answer", "ALLOWED", item.id, reason=f"option {option_id}")
        return item

    def _apply_flag_answer(self, actor: str, item: WorkItem, option_id: str) -> None:
        action = item.payload.get("option_actions", {}).get(option_id, {})
        kind = item.payload.get("kind")
        label = next((o.label for o in item.options if o.id == option_id), option_id)
        if kind == "covenant_tag":
            deal = self._deal(item.deal_id)
            basis = "as_filed" if self._whole_line(item, action.get("tags", {})) else "covenant"
            if basis != deal.ebitda_basis:
                deal.ebitda_basis = basis
                self._log(item.deal_id, SYSTEM, "basis", "ALLOWED", deal.id,
                          reason="EBITDA as filed: the controller chose the whole-line reading" if basis == "as_filed"
                          else "EBITDA under the agreement's definition")
            for lid, tag in action.get("tags", {}).items():
                line = self.store.source_lines.get(lid)
                if line is not None:
                    line.covenant_tag = tag
                    line.covenant_note = f"decided by {actor} on flag {item.id}"
                    self._learn(MAPPER, "covenant_tag", line.line, tag, label, actor, item, line.company)
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
                    self._learn(MAPPER, "mapping", t.line, (pl.line if pl else ref) or "", label, actor, item, t.company)

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

    def _learn(self, role: str, kind: str, pattern: str, decision: str, label: str, actor: str, item: WorkItem,
               company: str | None = None) -> Policy:
        """The controller's answer becomes a policy the agent applies next time. The gateway is the writer.
        A policy is scoped to the company whose line it was learned on, so the same line name at another company
        is asked again instead of inheriting this answer."""
        key = pattern.strip().lower()
        for p in self.store.policies.values():
            if p.role == role and p.kind == kind and p.pattern == key and p.company == company and not p.retired_by:
                p.decision, p.approved_by, p.learned_from, p.reason = decision, actor, item.id, label
                self._log(item.deal_id, SYSTEM, "policy:update", "ALLOWED", p.id, reason=f"{key} -> {decision}")
                return p
        policy = Policy(id=self.store.next_id("p"), role=role, kind=kind, pattern=key, decision=decision,
                        reason=f"{actor} chose '{label}' on flag {item.id}", approved_by=actor,
                        learned_from=item.id, deal_id=item.deal_id, company=company)
        self.store.policies[policy.id] = policy
        self._log(item.deal_id, SYSTEM, "policy:learn", "ALLOWED", policy.id, reason=f"{key} -> {decision}")
        return policy

    def _cited_policy(self, policy_id: str | None, kind: str, decision: str | None, line: SourceLine) -> str | None:
        """A policy id an agent cites counts only if that policy exists, is live, is of this kind, decided the same
        thing, was learned on this line name, and its scope covers this line: a company policy only that company's
        lines, a platform policy (kind mapping, from a remap edit) only the add-on lines of the platform it names.
        So a platform policy never settles a covenant tag, and never a not_debt (D18). It must also be the newest live
        policy covering the line, so an older answer that a later correction replaced cannot be cited. The model's
        own wording never marks a line as learned; the gateway does, from the policy record."""
        p = self.store.policies.get(policy_id) if policy_id else None
        if not p or p.retired_by or p.kind != kind or (decision or "").strip().lower() != p.decision.strip().lower():
            return None
        deal = self.store.deals.get(line.deal_id)
        if deal is None or p.pattern != line.line.strip().lower():
            return None
        newest = newest_covering((q for q in self.store.policies.values() if q.role == p.role), kind, p.pattern,
                                 line.company, deal.platform, deal.target)
        return p.id if newest is not None and newest.id == p.id else None

    def _policy_applies(self, p: Policy, deal_id: str, company: str) -> bool:
        deal = self.store.deals.get(deal_id)
        return deal is not None and policy_applies(p, company, deal.platform, deal.target)

    def policies_for(self, role: str, deal_id: str) -> list[Policy]:
        """The live policies of a role whose scope covers this deal, which is what the agent is given. Another
        company's policies are left out, so a model is never shown an answer it may not apply."""
        deal = self._deal(deal_id)
        return [p for p in self.store.role_policies(role)
                if any(self._policy_applies(p, deal.id, c) for c in (deal.platform, deal.target))]

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
            offered = self.open_adjustment_flags(item.deal_id)
            if offered:
                self._deny(Denied(f"flag {offered[0].id} offers a learned adjustment; apply it or skip it before the "
                                  f"result can be approved"), item.deal_id, actor, "approve", item.id)
            waiting = [e for e in self.store.deal_edits(item.deal_id) if e.status == "needs_reason"]
            if waiting:
                e = waiting[0]
                self._deny(Denied(f"edit {e.id} ({e.company}, {e.line}) needs a reason before the result can be "
                                  f"approved" + (f"; {len(waiting) - 1} more edit(s) also need one" if len(waiting) > 1
                                                 else "")),
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
            for p in self.store.policies.values():  # a reversed answer must not be applied to the next deal
                if p.learned_from == item.id and not p.retired_by:
                    p.retired_by = rev.id
                    self._log(item.deal_id, SYSTEM, "policy:retire", "ALLOWED", p.id, reason=f"reversed by {rev.id}")
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
                rid = next((r for r in reversed(out.run_ids) if r in runs and runs[r] and runs[r].tool == tool), None)
                if rid:
                    by_tool[tool] = rid
        try:
            self._check_provenance(deal, actor, out, by_tool)
            offers = self._check_adjustment_flags(deal, out)
        except Invalid as error:
            self._deny(error, deal.id, actor, "propose:prepare_result", item.id)
        result = Result(id=self.store.next_id("r"), deal_id=deal.id, work_item_id=item.id, rows=out.rows,
                        ebitda=out.ebitda, debt=out.debt, leverage=out.leverage, limit=out.limit,
                        verdict=test["verdict"], headroom_turns=test["headroom_turns"], run_ids=out.run_ids,
                        run_ids_by_tool=by_tool, backend=backend)
        self.store.results[result.id] = result
        item.payload = {"result_id": result.id, "note": out.note}
        item.state = State.PROPOSED
        self._log(deal.id, actor, "propose:prepare_result", "ALLOWED", item.id,
                  reason=f"result {result.id}: leverage {out.leverage:.2f}x against {out.limit:.2f}x")
        for proposal, adj, line in offers:
            self._open_adjustment_flag(deal, item, proposal, adj, line)
        deal.stage = "awaiting_review"
        return result

    def _last_answer_at(self, deal_id: str):
        return next((r.at for r in reversed(self.store.audit)
                     if r.deal_id == deal_id and r.action == "answer" and r.result == "ALLOWED"), None)

    def _check_provenance(self, deal: Deal, actor: str, out: PreparerOutput, by_tool: dict[str, str]) -> None:
        """Every figure in the result is the output of the Preparer's own runs, chained by run id.

        A run of the right tool is not enough: the gateway's what-ifs for options the controller did not pick are
        covenant_debt runs too. So the debt run must be the Preparer's, under the agreement's reading (not naive),
        made after the last flag answer; the leverage run must divide exactly that debt run by that ebitda run; and
        the rows must be the consolidate run's rows."""
        missing = [t for t in ("consolidate", "ebitda", "covenant_debt", "leverage") if t not in by_tool]
        if missing:
            raise Invalid(f"the result names no {', '.join(missing)} run; list each run id in its named field")
        named = {t: self.store.tool_runs[rid] for t, rid in by_tool.items()}
        after = self._last_answer_at(deal.id)
        for tool, run in named.items():
            if run.actor != actor:
                raise Invalid(f"{tool} run {run.run_id} was made by {run.actor}, not by {actor}")
            if run.inputs.get("what_if"):
                raise Invalid(f"{tool} run {run.run_id} is a what-if for a flag option, not the deal's figure")
            if after is not None and run.at < after:
                raise Invalid(f"{tool} run {run.run_id} was made before the last flag answer; run it again")
        debt, eb, lev, cons = named["covenant_debt"], named["ebitda"], named["leverage"], named["consolidate"]
        if debt.inputs.get("naive"):
            raise Invalid(f"covenant_debt run {debt.run_id} is the naive reading; the result needs naive=false")
        if bool(eb.inputs.get("as_filed")) != (deal.ebitda_basis == "as_filed"):
            raise Invalid(f"ebitda run {eb.run_id} is not on the deal's basis ({deal.ebitda_basis})")
        if lev.inputs.get("debt_run_id") != debt.run_id or lev.inputs.get("ebitda_run_id") != eb.run_id:
            raise Invalid(f"leverage run {lev.run_id} must divide covenant_debt run {debt.run_id} by ebitda run "
                          f"{eb.run_id}")
        for key, value, run, out_key in (("ebitda", out.ebitda, eb, "ebitda"), ("debt", out.debt, debt, "debt"),
                                         ("leverage", out.leverage, lev, "leverage")):
            if abs(float(run.outputs.get(out_key, float("nan"))) - value) >= 1e-6:
                raise Invalid(f"{key} {value} is not the output of {run.tool} run {run.run_id}")
        expected = cons.outputs.get("rows", [])
        got = {(r.section, r.line): r for r in out.rows}
        if len(got) != len(expected) or len(out.rows) != len(expected):
            raise Invalid(f"rows must be the {len(expected)} rows of consolidate run {cons.run_id}")
        for e in expected:
            r = got.get((e["section"], e["line"]))
            if (r is None or r.run_id != cons.run_id
                    or any(abs(getattr(r, k) - e[k]) >= 1e-6 for k in ("platform", "target", "combined"))):
                raise Invalid(f"row {e['line']} does not match consolidate run {cons.run_id}")

    def _check_review(self, deal: Deal, result: Result, out: ReviewerOutput) -> tuple[ToolRun | None, ToolRun | None]:
        """The gateway reads the Reviewer's checks itself. A pass needs a tie_out run on this result's consolidate run
        and a limit_test run on its leverage run, both made for this deal and both ok."""
        for rid in out.run_ids:
            run = self.store.tool_runs.get(rid)
            if run is None or run.deal_id != deal.id:
                raise Invalid(f"run id {rid} does not exist for this deal")
        cited = [self.store.tool_runs[r] for r in out.run_ids]
        cons, lev = result.run_ids_by_tool.get("consolidate"), result.run_ids_by_tool.get("leverage")
        tie = next((r for r in reversed(cited) if r.tool == "tie_out" and r.inputs.get("run_id") == cons), None)
        test = next((r for r in reversed(cited) if r.tool == "limit_test" and r.inputs.get("leverage_run_id") == lev),
                    None)
        if out.verdict == "pass":
            if tie is None or test is None:
                raise Invalid(f"a pass must cite a tie_out run on {cons} and a limit_test run on {lev}")
            failed = [f"{r.tool} {r.run_id}" for r in (tie, test) if not r.outputs.get("ok")]
            if failed:
                raise Invalid(f"a pass cannot stand on failed checks: {', '.join(failed)}")
        return tie, test

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
        try:
            tie, _ = self._check_review(deal, result, out)
        except Invalid as error:
            self._deny(error, deal.id, actor, "propose:review_result", item.id)
        result.review = Review(verdict=out.verdict, reasons=out.reasons, run_ids=out.run_ids)
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

    # ------------------------------------------------------------------ review edits (D19)
    def reason_chips(self, deal_id: str, kind: str) -> list[ReasonChip]:
        """The reasons the bubble offers for an edit of this kind. Hardcoded per deal for the demo."""
        return reason_chips(deal_id, kind)

    def _edit(self, edit_id: str) -> Edit:
        edit = self.store.edits.get(edit_id)
        if not edit:
            raise NotFound(f"edit {edit_id} not found")
        return edit

    def _live_edits(self, deal_id: str, without: str | None = None) -> list[Edit]:
        return [e for e in self.store.deal_edits(deal_id) if e.status != "reverted" and e.id != without]

    def _live_approval(self, deal_id: str) -> WorkItem | None:
        """The approval item an edit may change: PROPOSED, after the agents and before approval. A NEEDS_INFO item
        counts only when an edit made it (its recompute failed a check), so the controller can fix or undo that edit."""
        for item in reversed(self.store.deal_items(deal_id, "approve_result")):
            if item.state == State.PROPOSED or (item.state == State.NEEDS_INFO and item.payload.get("edit_id")):
                return item
            if item.state != State.SUPERSEDED:
                return None
        return None

    def _require_controller(self, actor: str, deal_id: str, action: str, target: str | None) -> None:
        """Only the controller edits the books. An agent, the system, or another human is refused and logged."""
        if actor != CONTROLLER:
            self._deny(Denied(f"{actor} may not {action}: only {CONTROLLER} edits the combined books"),
                       deal_id, actor, action, target)

    def _approval_for_edit(self, deal_id: str, actor: str, action: str, target: str | None) -> WorkItem:
        approval = self._live_approval(deal_id)
        if approval is None:
            self._deny(IllegalTransition("the books can be edited only while the result is PROPOSED, after the "
                                         "agents and before approval"), deal_id, actor, action, target)
        return approval

    def _recompute(self, deal_id: str, edit_ids: list[str]) -> dict[str, ToolRun]:
        """Recompute the books with the live edits, as the system, through the same tools: consolidate, ebitda,
        covenant_debt, leverage, tie_out, limit_test. Every run is new and names the edits it applied, and every
        figure of the new result is read from these runs. The gateway does no math of its own here.
        When a covenant flag gave the whole-line reading, its what-if pair is run again with the edits too
        (naive covenant_debt, as-filed ebitda, leverage), under the `naive_*` keys of `run_ids_by_tool`."""
        missing = [n for n in EDIT_TOOLS if "edits" not in inspect.signature(finance.TOOLS[n]).parameters]
        if missing:
            raise NotReady(f"{T1_MISSING}: {', '.join(missing)} take no edits")
        with_edits = {"edit_ids": list(edit_ids)}
        cons = self.run_tool(SYSTEM, deal_id, "consolidate", dict(with_edits))
        eb = self.run_tool(SYSTEM, deal_id, "ebitda", dict(with_edits))
        debt = self.run_tool(SYSTEM, deal_id, "covenant_debt", {"naive": False, **with_edits})
        lev = self.run_tool(SYSTEM, deal_id, "leverage", {"debt_run_id": debt.run_id, "ebitda_run_id": eb.run_id})
        tie = self.run_tool(SYSTEM, deal_id, "tie_out", {"run_id": cons.run_id})
        test = self.run_tool(SYSTEM, deal_id, "limit_test", {"leverage_run_id": lev.run_id})
        runs = {"consolidate": cons, "ebitda": eb, "covenant_debt": debt, "leverage": lev, "tie_out": tie,
                "limit_test": test}
        runs.update(self._naive_with_edits(deal_id, with_edits))
        return runs

    def _whole_line_tags(self, deal_id: str) -> dict[str, str] | None:
        """The tags of the covenant flag option that counts every flagged line as debt (the as-filed reading)."""
        for item in reversed(self.store.deal_items(deal_id, "flag")):
            if item.payload.get("kind") != "covenant_tag":
                continue
            for action in item.payload.get("option_actions", {}).values():
                tags = action.get("tags") or {}
                if tags and all(t == "debt" for t in tags.values()):
                    return tags
        return None

    def _naive_with_edits(self, deal_id: str, with_edits: dict) -> dict[str, ToolRun]:
        """The whole-line what-if again, on the edited books, so the sensitivity figures reflect the edits. The
        flagged lines are tagged debt for the runs and restored after, as in `_flag_effect`."""
        tags = self._whole_line_tags(deal_id)
        if not tags:
            return {}
        lines = {lid: self.store.source_lines[lid] for lid in tags if lid in self.store.source_lines}
        saved = {lid: (line.covenant_tag, line.covenant_note) for lid, line in lines.items()}
        try:
            for line in lines.values():
                line.covenant_tag = "debt"
            debt = self.run_tool(SYSTEM, deal_id, "covenant_debt", {"naive": True, "what_if": "whole_line", **with_edits})
            eb = self.run_tool(SYSTEM, deal_id, "ebitda", {"as_filed": True, "what_if": "whole_line", **with_edits})
            lev = self.run_tool(SYSTEM, deal_id, "leverage", {"debt_run_id": debt.run_id, "ebitda_run_id": eb.run_id,
                                                               "what_if": "whole_line"})
        finally:
            for lid, (tag, note) in saved.items():
                lines[lid].covenant_tag, lines[lid].covenant_note = tag, note
        return {"naive_covenant_debt": debt, "naive_ebitda": eb, "naive_leverage": lev}

    def _revise(self, deal: Deal, approval: WorkItem, runs: dict[str, ToolRun], edit: Edit,
                edit_ids: list[str]) -> tuple[Result, WorkItem]:
        """Write a new result revision from the recompute runs and a new approval item for it. The old approval item
        becomes SUPERSEDED and stays in the log; the old result stays too."""
        old = self.store.results[approval.payload["result_id"]]
        cons, eb, debt, lev, tie, test = (runs[t] for t in ("consolidate", "ebitda", "covenant_debt", "leverage",
                                                             "tie_out", "limit_test"))
        reasons = []
        if not tie.outputs.get("ok"):
            reasons.append(f"Tie-out failed ({tie.run_id}) after edit {edit.id}")
        if not test.outputs.get("ok"):
            reasons.append(f"Leverage {test.outputs['leverage']:.2f}x is not below the {test.outputs['limit']:.2f}x "
                           f"limit ({test.run_id}) after edit {edit.id}")
        review = Review(verdict="pass" if not reasons else "needs_attention", reasons=reasons,
                        run_ids=[tie.run_id, test.run_id])
        rows = [ResultRow(line=r["line"], section=r["section"], platform=r["platform"], target=r["target"],
                          combined=r["combined"], run_id=cons.run_id) for r in cons.outputs["rows"]]
        result = Result(id=self.store.next_id("r"), deal_id=deal.id, work_item_id=old.work_item_id, rows=rows,
                        ebitda=eb.outputs["ebitda"], debt=debt.outputs["debt"], leverage=lev.outputs["leverage"],
                        limit=deal.brief.limit, verdict=test.outputs["verdict"],
                        headroom_turns=test.outputs["headroom_turns"], tie_out_ok=bool(tie.outputs.get("ok")),
                        review=review, run_ids=[r.run_id for r in runs.values()],
                        run_ids_by_tool={t: r.run_id for t, r in runs.items()}, backend=old.backend,
                        supersedes=old.id, edit_ids=list(edit_ids))
        self.store.results[result.id] = result
        approval.state = State.SUPERSEDED
        approval.payload = {**approval.payload, "superseded_by_result": result.id}
        passed = review.verdict == "pass"
        # The revision is the gateway's recompute, so the system proposes it; the controller, who did not propose
        # it, approves it, and maker-checker holds.
        new = WorkItem(id=self.store.next_id("wi"), deal_id=deal.id, type="approve_result",
                       state=State.PROPOSED if passed else State.NEEDS_INFO, proposed_by=SYSTEM,
                       payload={"result_id": result.id, "review_item": approval.payload.get("review_item"),
                                "edit_id": edit.id, "supersedes": approval.id},
                       question=None if passed else "The checks found a problem after the edit: " + "; ".join(reasons))
        self.store.items[new.id] = new
        approval.payload["superseded_by"] = new.id
        self._log(deal.id, SYSTEM, "supersede", "ALLOWED", approval.id, reason=f"replaced by {new.id} after edit {edit.id}")
        self._log(deal.id, SYSTEM, "create:approve_result", "ALLOWED", new.id,
                  reason=f"result {result.id} after edit {edit.id}: leverage {result.leverage:.2f}x"
                         + ("" if passed else "; needs attention"))
        deal.stage = "awaiting_approval" if passed else "needs_attention"
        return result, new

    @staticmethod
    def _edit_response(edit: Edit, result: Result, approval: WorkItem, chips: list[ReasonChip]) -> dict[str, Any]:
        verdict = {"leverage": result.leverage, "limit": result.limit, "verdict": result.verdict,
                   "headroom_turns": result.headroom_turns, "ebitda": result.ebitda, "debt": result.debt,
                   "tie_out_ok": result.tie_out_ok, "review": result.review, "approval_item": approval.id,
                   "approval_state": approval.state.value}
        return {"edit": edit, "result": result, "verdict": verdict, "approval": approval, "reasons": chips}

    def _find_edit_line(self, deal: Deal, company: str, line: str, section: str | None) -> SourceLine:
        if company not in (deal.platform, deal.target):
            raise Invalid(f"company must be {deal.platform} or {deal.target}, not '{company}'")
        key = line.strip().lower()
        hits = [sl for sl in self.store.lines(deal.id, company)
                if sl.line.strip().lower() == key and (section is None or sl.section == section)]
        if not hits:
            raise Invalid(f"{company} has no line '{line}'" + (f" in {section}" if section else ""))
        if len(hits) > 1:
            raise Invalid(f"{company} has {len(hits)} lines named '{line}'; give the section")
        if hits[0].is_total:
            raise Invalid(f"'{hits[0].line}' is a subtotal; subtotals are always computed")
        return hits[0]

    @_writes
    def apply_edit(self, actor: str, deal_id: str, kind: str, company: str, line: str, value: float | None = None,
                   platform_line: str | None = None, section: str | None = None) -> dict[str, Any]:
        """The controller changes the combined books after the agents and before approval (D19).

        `amount` replaces one company's value on one statement line (USD thousands); `remap` moves one target line
        to another platform line. The edit is recorded on top of the agents' run, never over it: the mappings and
        the source lines stay as the agents left them, and the system recomputes every figure through the
        edit-aware tools with new run ids. The result gets a new revision and a new PROPOSED approval item; the old
        approval item is SUPERSEDED. Returns the edit, the new verdict and result, the approval item, and the chips."""
        action = "edit:apply"
        deal = self._deal(deal_id)
        self._require_controller(actor, deal_id, action, None)
        approval = self._approval_for_edit(deal_id, actor, action, None)
        try:
            src = self._find_edit_line(deal, company, line, section)
            open_same = [e for e in self._live_edits(deal_id)
                         if e.kind == kind and e.company == src.company and e.line == src.line and e.section == src.section]
            if open_same:
                raise IllegalTransition(f"edit {open_same[0].id} already changes this line; undo it first")
            fields: dict[str, Any] = {}
            if kind == "amount":
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                    raise Invalid("an amount edit needs a finite value in USD thousands")
                old_value = round(finance.to_thousands(src.amount, src.unit), 3)
                if abs(float(value) - old_value) < 1e-9:
                    raise Invalid(f"the value is already {old_value}")
                fields = {"old_value": old_value, "new_value": float(value)}
                summary = f"{old_value:,.3f} -> {float(value):,.3f}"
            elif kind == "remap":
                if src.company != deal.target:
                    raise Invalid(f"only the target's lines are remapped; {src.company} is the platform")
                mapping = next((m for m in self._usable_mappings(deal_id) if m.target_line_id == src.id), None)
                if mapping is None:
                    raise Invalid(f"'{src.line}' has no approved mapping to change")
                pl = self._platform_line(deal, src.section, platform_line)
                if pl is None:
                    raise Invalid(f"'{platform_line}' is not a {deal.platform} line")
                if (mapping.platform_line or "").strip().lower() == pl.line.strip().lower():
                    raise Invalid(f"'{src.line}' is already mapped to {pl.line}")
                fields = {"old_platform_line": mapping.platform_line, "new_platform_line": pl.line}
                summary = f"{mapping.platform_line or 'unmapped'} -> {pl.line}"
            else:
                raise Invalid(f"kind must be amount or remap, not '{kind}'")
            edit = Edit(id=self.store.next_id("e"), deal_id=deal_id, kind=kind, company=src.company, line=src.line,
                        section=src.section, actor=actor, **fields)
        except GatewayError as error:
            self._deny(error, deal_id, actor, action, None)
        except (TypeError, ValueError) as error:  # a value that is not a number, or an Edit the model refuses
            self._deny(Invalid(f"invalid edit: {error}"), deal_id, actor, action, None)
        self.store.edits[edit.id] = edit
        edit_ids = [e.id for e in self._live_edits(deal_id)]
        try:
            runs = self._recompute(deal_id, edit_ids)
        except GatewayError as error:  # nothing is kept but the audit rows of the runs that were made
            del self.store.edits[edit.id]
            self._deny(type(error)(f"edit not applied: {error.message}"), deal_id, actor, action, edit.id)
        edit.run_ids = [r.run_id for r in runs.values()]
        before = self.store.results[approval.payload["result_id"]].leverage
        result, new_approval = self._revise(deal, approval, runs, edit, edit_ids)
        self._log(deal_id, actor, action, "ALLOWED", edit.id,
                  reason=f"{kind} {src.company}, {src.line}: {summary}; leverage {before:.3f}x -> {result.leverage:.3f}x "
                         f"(result {result.id})")
        return self._edit_response(edit, result, new_approval, self.reason_chips(deal_id, kind))

    @_writes
    def reason_edit(self, actor: str, edit_id: str, chip: int | None = None, text: str | None = None,
                    remember: bool = True) -> Edit:
        """The controller says why. With `remember`, a remap becomes a mapping policy for every add-on of this
        platform (the D12 path), and an amount edit becomes a LearnedAdjustment, which the Preparer may propose as a
        flag on a later deal and which is never applied silently."""
        action = "edit:reason"
        edit = self._edit(edit_id)
        deal = self._deal(edit.deal_id)
        self._require_controller(actor, deal.id, action, edit.id)
        if edit.status != "needs_reason":
            self._deny(IllegalTransition(f"edit {edit.id} is {edit.status}; only an edit that needs a reason takes one"),
                       deal.id, actor, action, edit.id)
        typed = (text or "").strip()
        if (chip is None) == (not typed):
            self._deny(Invalid("give a chip or a text reason, one of the two"), deal.id, actor, action, edit.id)
        if chip is not None:
            chips = {c.id: c for c in self.reason_chips(deal.id, edit.kind)}
            if isinstance(chip, bool) or chip not in chips:
                self._deny(Invalid(f"chip must be one of {sorted(chips)}"), deal.id, actor, action, edit.id)
            label = chips[chip].label
        else:
            if len(typed) > 500:
                self._deny(Invalid("a reason is at most 500 characters"), deal.id, actor, action, edit.id)
            label = typed
        edit.status, edit.reason_chip, edit.reason_text, edit.remember = "reasoned", chip, label, bool(remember)
        self._log(deal.id, actor, action, "ALLOWED", edit.id,
                  reason=f"{label}" + ("; remember" if remember else "; not remembered"))
        if remember and edit.kind == "remap":
            edit.policy_id = self._learn_from_edit(actor, deal, edit).id
        elif remember and edit.kind == "amount":
            adj = LearnedAdjustment(id=self.store.next_id("a"), deal_id=deal.id, company=edit.company,
                                    platform=deal.platform, line=edit.line, amount=round(edit.new_value - edit.old_value, 3), reason=label,
                                    edit_id=edit.id, status="applied")
            self.store.adjustments[adj.id] = adj
            edit.adjustment_id = adj.id
            self._log(deal.id, SYSTEM, "policy:learn", "ALLOWED", adj.id,
                      reason=f"source: edit {edit.id}; adjustment {_signed(edit.new_value - edit.old_value)} to {edit.company}, {edit.line}; "
                             f"proposed as a flag on a later deal, never applied silently")
        return edit

    def _learn_from_edit(self, actor: str, deal: Deal, edit: Edit) -> Policy:
        """A reasoned remap teaches the Mapper a platform policy: this line name, at any add-on of this platform,
        maps to this platform line. Each edit learns its own policy, never updating an older one; the newest live
        policy wins, so reverting this edit makes an older one effective again."""
        key = edit.line.strip().lower()
        policy = Policy(id=self.store.next_id("p"), role=MAPPER, kind="mapping", pattern=key,
                        decision=edit.new_platform_line, reason=edit.reason_text, approved_by=actor,
                        learned_from=edit.id, deal_id=deal.id, company=None, scope="platform", platform=deal.platform)
        self.store.policies[policy.id] = policy
        self._log(deal.id, SYSTEM, "policy:learn", "ALLOWED", policy.id,
                  reason=f"source: edit {edit.id}; {key} -> {policy.decision} for every add-on of {deal.platform}")
        return policy

    @_writes
    def revert_edit(self, actor: str, edit_id: str) -> dict[str, Any]:
        """Undo an edit: it is marked reverted (never deleted), the policy or adjustment it taught is retired the way
        a reversed flag answer retires its policies (D18), and the books are recomputed without it."""
        action = "edit:revert"
        edit = self._edit(edit_id)
        deal = self._deal(edit.deal_id)
        self._require_controller(actor, deal.id, action, edit.id)
        if edit.status == "reverted":
            self._deny(IllegalTransition(f"edit {edit.id} is already reverted"), deal.id, actor, action, edit.id)
        approval = self._approval_for_edit(deal.id, actor, action, edit.id)
        edit_ids = [e.id for e in self._live_edits(deal.id, without=edit.id)]
        try:
            runs = self._recompute(deal.id, edit_ids)
        except GatewayError as error:
            self._deny(type(error)(f"edit not reverted: {error.message}"), deal.id, actor, action, edit.id)
        edit.status = "reverted"
        self._log(deal.id, actor, action, "ALLOWED", edit.id, reason=f"{edit.kind} {edit.company}, {edit.line} undone")
        p = self.store.policies.get(edit.policy_id) if edit.policy_id else None
        if p and not p.retired_by and p.learned_from == edit.id:
            p.retired_by = edit.id
            self._log(deal.id, SYSTEM, "policy:retire", "ALLOWED", p.id, reason=f"edit {edit.id} reverted")
        adj = self.store.adjustments.get(edit.adjustment_id) if edit.adjustment_id else None
        if adj and adj.status != "retired":
            adj.status = "retired"
            self._log(deal.id, SYSTEM, "policy:retire", "ALLOWED", adj.id, reason=f"edit {edit.id} reverted")
        result, new_approval = self._revise(deal, approval, runs, edit, edit_ids)
        return self._edit_response(edit, result, new_approval, self.reason_chips(deal.id, edit.kind))

    # ------------------------------------------------------------------ learned adjustments on a later deal (D19)
    def _adjustment_matches(self, adj: LearnedAdjustment, line: SourceLine, deal: Deal) -> bool:
        """A learned adjustment covers a line of this deal with the same name, at the same company, or at the target
        of a deal on the platform it was learned under. A subtotal is never offered."""
        if line.deal_id != deal.id or line.is_total or line.line.strip().lower() != adj.line.strip().lower():
            return False
        return same_name(line.company, adj.company) or (same_name(adj.platform, deal.platform)
                                                        and same_name(line.company, deal.target))

    def adjustments_for(self, deal_id: str) -> list[LearnedAdjustment]:
        """The live learned adjustments the Preparer may offer on this deal: not retired, not learned on this deal's
        own edits, not already on an open flag, and covering one of its lines."""
        deal = self._deal(deal_id)
        offered = {i.payload.get("adjustment_id") for i in self.store.deal_items(deal_id, "flag")
                   if i.payload.get("kind") == "adjustment" and i.state in (State.NEEDS_INFO, State.POSTED)}
        lines = self.store.lines(deal_id)
        out = []
        for adj in self.store.adjustments.values():
            own = self.store.edits.get(adj.edit_id)
            if adj.status == "retired" or adj.id in offered or (own is not None and own.deal_id == deal_id):
                continue
            if any(self._adjustment_matches(adj, line, deal) for line in lines):
                out.append(adj)
        return out

    def _check_adjustment_flags(self, deal: Deal, out: PreparerOutput) -> list[tuple]:
        """Every adjustment the Preparer offers must be one the gateway would offer, on a line it covers, once."""
        allowed = {a.id: a for a in self.adjustments_for(deal.id)}
        seen: set[str] = set()
        checked = []
        for proposal in out.adjustment_flags:
            adj = allowed.get(proposal.adjustment_id)
            if adj is None:
                raise Invalid(f"adjustment {proposal.adjustment_id} is not a live learned adjustment for this deal")
            if adj.id in seen:
                raise Invalid(f"adjustment {adj.id} is offered twice")
            line = self.store.source_lines.get(proposal.line_id)
            if line is None or not self._adjustment_matches(adj, line, deal):
                raise Invalid(f"adjustment {adj.id} ({adj.line}) does not cover line {proposal.line_id}")
            seen.add(adj.id)
            checked.append((proposal, adj, line))
        return checked

    def _open_adjustment_flag(self, deal: Deal, parent: WorkItem, proposal, adj: LearnedAdjustment,
                              line: SourceLine) -> WorkItem:
        current = finance.to_thousands(line.amount, line.unit)
        options = [
            Option(id="apply", label=f"Apply it: {_signed(adj.amount)} to {line.company}, {line.line}",
                   effect=f"{line.line} goes from {_fmt(current)}K to {_fmt(current + adj.amount)}K as your edit, "
                          f"with the reason "
                          f"'{adj.reason}'. Every figure is recomputed by the tools with new run ids."),
            Option(id="skip", label="Skip it on this deal",
                   effect="The books stay as the agents made them. The adjustment is kept for later deals."),
        ]
        item = WorkItem(id=self.store.next_id("wi"), deal_id=deal.id, type="flag", state=State.NEEDS_INFO,
                        proposed_by=PREPARER, question=proposal.question, options=options, default="skip",
                        evidence=[Evidence(quote=adj.reason, document_id=f"edit {adj.edit_id} on {adj.deal_id}")],
                        payload={"kind": "adjustment", "adjustment_id": adj.id, "line_ids": [line.id],
                                 "parent": parent.id})
        self.store.items[item.id] = item
        adj.status = "proposed"
        self._log(deal.id, PREPARER, "ask:flag", "ALLOWED", item.id, reason=proposal.question, evidence=item.evidence)
        self._log(deal.id, SYSTEM, "adjustment:propose", "ALLOWED", adj.id, reason=f"offered on flag {item.id}")
        return item

    def _answer_adjustment(self, actor: str, item: WorkItem, option_id: str) -> WorkItem:
        """Apply: the adjustment becomes the controller's amount edit, through apply_edit and its recompute, reasoned
        with the adjustment's reason, so it shows in Your edits. Skip: the books stay as the agents made them."""
        adj = self.store.adjustments[item.payload["adjustment_id"]]
        line = self.store.source_lines[item.payload["line_ids"][0]]
        detail = "books left as the agents made them"
        if option_id == "apply" and adj.status == "retired":
            self._deny(IllegalTransition(f"adjustment {adj.id} was retired; skip it"), item.deal_id, actor, "answer",
                       item.id)
        if option_id == "apply":
            # The change, on this deal's own agent value: the source line, which an edit never overwrites.
            value = round(finance.to_thousands(line.amount, line.unit) + adj.amount, 3)
            edit = self.apply_edit(actor, item.deal_id, "amount", line.company, line.line, value=value,
                                   section=line.section)["edit"]
            edit.from_adjustment_id = adj.id
            self.reason_edit(actor, edit.id, text=adj.reason, remember=False)
            item.payload = {**item.payload, "edit_id": edit.id}
            detail = f"applied as edit {edit.id}"
        item.answer = option_id
        item.state = State.APPROVED
        if adj.status == "proposed":
            adj.status = "applied"  # live again for later deals, whichever way this deal went
        self._log(item.deal_id, actor, "answer", "ALLOWED", item.id, reason=f"option {option_id}: {detail}")
        self._log(item.deal_id, SYSTEM, f"adjustment:{option_id}", "ALLOWED", adj.id,
                  reason=f"flag {item.id}: {detail}")
        self._post(item)
        return item

    # ------------------------------------------------------------------ the Brief Reader (D20)
    def agreement(self, deal_id: str) -> AgreementText | None:
        return next((a for a in self.store.agreements.values() if a.deal_id == deal_id), None)

    @_writes
    def create_deal_from_agreement(self, actor: str, deal: Deal, lines: list[SourceLine], text: str,
                                   source: str) -> Deal:
        """A deal whose Brief is read from the agreement text. If an earlier deal's approved Brief has the same
        agreement hash, it is reused and the reader is skipped; an amendment is new text, so it is read again."""
        if not text.strip():
            raise Invalid("the agreement text is empty")
        sha = agr.agreement_sha256(text)
        reuse = next((self.store.deals[a.deal_id].brief for a in self.store.agreements.values()
                      if a.sha256 == sha and a.deal_id in self.store.deals
                      and self.store.deals[a.deal_id].brief_status == "approved"), None)
        deal = deal.model_copy(update={"brief": reuse.model_copy(deep=True) if reuse else None,
                                       "brief_status": "approved" if reuse else "none"})
        self.create_deal(actor, deal, lines)
        ag = AgreementText(id=self.store.next_id("ag"), deal_id=deal.id, text=text, sha256=sha, source=source)
        self.store.agreements[ag.id] = ag
        self._log(deal.id, actor, "agreement:load", "ALLOWED", ag.id,
                  reason=f"{source}; sha256 {sha[:12]}; {len(text):,} characters")
        if reuse:
            self._log(deal.id, SYSTEM, "brief:reuse", "ALLOWED", deal.id,
                      reason=f"approved Brief for agreement {sha[:12]} reused; the reader is skipped")
        return self.store.deals[deal.id]

    def brief_reader_input(self, deal_id: str, item_id: str) -> BriefReaderInput:
        """The indexes and the leverage sections, never the whole agreement (brief-reader.md section 5)."""
        ag = self.agreement(deal_id)
        if ag is None:
            raise Invalid(f"deal {deal_id} has no agreement text")
        return BriefReaderInput(deal_id=deal_id, item_id=item_id, agreement_id=ag.id, sha256=ag.sha256,
                                section_index=agr.section_index(ag.text),
                                definition_index=agr.definition_index(ag.text),
                                excerpts=agr.leverage_excerpts(ag.text), amendments_supplied=False)

    @_writes
    def read_agreement(self, actor: str, deal_id: str, name: str, args: dict[str, Any]) -> ToolRun:
        """get_section(id) and get_definition(term): read-only, logged, and not stored as tool runs (no figures)."""
        self._require(actor, f"tool:{name}", deal_id)
        ag = self.agreement(deal_id)
        if ag is None:
            raise Invalid(f"deal {deal_id} has no agreement text")
        if name == "get_section":
            key = str(args.get("id", ""))
            body = agr.section_text(ag.text, key)
            if body is None:
                raise Invalid(f"no section '{key}'; the sections are the keys of section_index")
            outputs = {"id": key, "text": agr.normalize(body)[:20000]}
        elif name == "get_definition":
            key = str(args.get("term", ""))
            body = agr.definition_text(ag.text, key)
            if body is None:
                raise Invalid(f"no definition of '{key}'; the terms are the keys of definition_index")
            outputs = {"term": key, "text": body}
        else:
            raise NotFound(f"tool {name} not found")
        self._log(deal_id, actor, f"tool:{name}", "ALLOWED", key)
        return ToolRun(run_id=f"read:{name}", deal_id=deal_id, tool=name, actor=actor, inputs=dict(args),
                       outputs=outputs)

    # -- the nine checks (brief-reader.md section 6)
    @staticmethod
    def _brief_paths(brief: Brief) -> dict[str, Any]:
        """Every required field, by path, with its value."""
        paths: dict[str, Any] = {k: getattr(brief, k) for k in ("lender", "limit", "limit_section", "limit_wording",
                                                                 "debt_term", "debt_definition", "ebitda_definition")}
        for i, x in enumerate(brief.debt_excludes):
            paths[f"debt_excludes[{i}]"] = x
        for group in ("ebitda_addbacks", "ebitda_deductions"):
            for i, a in enumerate(getattr(brief, group)):
                paths[f"{group}[{i}].name"] = a.name
                if a.cap is not None:
                    paths[f"{group}[{i}].cap"] = a.cap
        return paths

    @staticmethod
    def _section_id(ref: str) -> str:
        return re.sub(r"^(section|sec\.|§)\s*", "", ref.strip(), flags=re.I)

    def _check_brief(self, deal: Deal, ag: AgreementText, out: BriefReaderOutput) -> list[dict[str, Any]]:
        """Refuse a draft that breaks a rule; return the flags to open. The model points, code decides."""
        brief, text = out.brief, ag.text
        index = agr.section_index(text)
        required = self._brief_paths(brief)
        optional = {"test_period_note", "agreement_ref"}
        flagged = {f.field: f for f in out.flags}
        verified: dict[str, list] = {}
        for c in out.citations:
            if c.field not in required and c.field not in optional:
                raise Invalid(f"citation names unknown field '{c.field}'")
            sid = self._section_id(c.section)
            if sid not in index:
                raise Invalid(f"citation for {c.field} names section '{c.section}', which is not in the agreement")
            if not agr.quote_in(c.quote, agr.section_text(text, sid) or ""):  # check 2
                raise Invalid(f"the quote for {c.field} is not in section {sid} of the agreement, or is under "
                              f"{agr.MIN_QUOTE_WORDS} words: '{c.quote[:100]}'")
            if c.field == "limit":  # check 3, and the limit's quote names the covenant's own debt term
                if not agr.ratio_in(c.quote, brief.limit):
                    raise Invalid(f"limit {brief.limit} is not in its quote: '{c.quote[:100]}'")
                if brief.debt_term and brief.debt_term.casefold() not in agr.normalize(c.quote).casefold():
                    raise Invalid(f"the limit's quote does not name the debt term '{brief.debt_term}'")
                if sid in (agr.PREAMBLE,) or not sid[0].isdigit():
                    raise Invalid(f"the limit must be quoted from a covenant section, not '{sid}'")
            if c.field.endswith(".cap") and not agr.thousands_in(c.quote, required[c.field]):
                raise Invalid(f"{c.field} {required[c.field]} (USD thousands) is not in its quote: '{c.quote[:100]}'")
            verified.setdefault(c.field, []).append(c)
        for path, value in required.items():  # check 4, coverage, and check 8, missing is said
            if path not in verified and path not in flagged:
                raise Invalid(f"{path} has no verified quote and no flag")
            if value in ("", None) and "not found in" not in (flagged.get(path).question if path in flagged else ""):
                raise Invalid(f"{path} is empty: say where you looked, in a flag that says 'not found in sections ...'")
        bad = _brief_number_problem(brief, limit_may_be_missing="limit" in flagged)  # check 5
        if bad:
            raise Invalid(bad)
        if brief.limit_wording:
            sid = self._section_id(brief.limit_section)
            if sid not in index or not agr.quote_in(brief.limit_wording, agr.section_text(text, sid) or ""):
                raise Invalid(f"limit_wording is not a quote from the limit section '{brief.limit_section}'")
            if brief.debt_term.casefold() not in agr.normalize(brief.limit_wording).casefold():
                raise Invalid(f"debt_term '{brief.debt_term}' does not appear in limit_wording")
        for group in ("ebitda_addbacks", "ebitda_deductions"):  # check 6, amounts come from the books
            for i, a in enumerate(getattr(brief, group)):
                path = f"{group}[{i}].amount"
                if a.amount != 0 and not (a.inferred and path in flagged):
                    raise Invalid(f"{path} is {a.amount}: an amount comes from the books, so give 0 with "
                                  f"inferred=true, or flag it")
        flags = [dict(field=f.field, question=f.question, evidence=f.evidence, proposed=f.proposed,
                      proposed_by=BRIEF_READER) for f in out.flags]
        for path in required:  # check 7, confidence is a hint
            if path in flagged:
                continue
            best = max(c.confidence for c in verified[path])
            if best < 0.6:
                c = verified[path][0]
                flags.append(dict(field=path, question=f"The reader is not sure of {path} (confidence {best:.2f}). "
                                  f"Is '{required[path]}' right?", evidence=[Evidence(quote=c.quote,
                                  document_id=f"{ag.source}, {c.section}")], proposed=str(required[path]),
                                  proposed_by=SYSTEM))
        for group in ("ebitda_addbacks", "ebitda_deductions"):
            for i, a in enumerate(getattr(brief, group)):
                path = f"{group}[{i}].amount"
                if path in flagged:
                    continue
                cap = f", capped at {_fmt(a.cap)}K," if a.cap is not None else ""
                flags.append(dict(field=path, question=f"The agreement allows '{a.name}'{cap} but does not give its "
                                  f"amount. Enter the amount from the books with its source, or keep 0.",
                                  evidence=[], proposed=f"{a.amount:g}", proposed_by=SYSTEM))
        return flags

    def _open_brief_flag(self, deal: Deal, parent: WorkItem, f: dict[str, Any]) -> WorkItem:
        listed = re.fullmatch(r"(debt_excludes\[\d+\])|((ebitda_addbacks|ebitda_deductions)\[\d+\])\.name", f["field"])
        options = [Option(id="confirm", label="Keep the reader's value" if not f["field"].endswith(".amount")
                          else "Keep it as it is (0 means not applied)",
                          effect=f"{f['field']} stays {f['proposed']!s}." if f["proposed"] is not None
                          else f"{f['field']} stays as drafted.")]
        if listed:
            options.append(Option(id="remove", label="Remove it from the Brief",
                                  effect=f"{f['field']} is left out of the approved Brief."))
        item = WorkItem(id=self.store.next_id("wi"), deal_id=deal.id, type="flag", state=State.NEEDS_INFO,
                        proposed_by=f["proposed_by"], question=f["question"], evidence=f["evidence"],
                        options=options, default="confirm",
                        payload={"kind": "brief_field", "field": f["field"], "proposed": f["proposed"],
                                 "parent": parent.id})
        self.store.items[item.id] = item
        self._log(deal.id, f["proposed_by"], "ask:flag", "ALLOWED", item.id, reason=f["question"],
                  evidence=f["evidence"])
        return item

    def _draft_item(self, deal_id: str) -> WorkItem | None:
        return next((i for i in reversed(self.store.deal_items(deal_id, "draft_brief"))
                     if i.state in (State.PROPOSED, State.POSTED)), None)

    def brief_draft(self, deal_id: str) -> BriefDraft | None:
        """What /case shows as `brief_draft`: the live draft, its citations, and its flags."""
        item = self._draft_item(deal_id)
        return BriefDraft.model_validate(item.payload["draft"]) if item else None

    def _brief_flags(self, deal_id: str, open_only: bool = True) -> list[WorkItem]:
        return [i for i in self.store.deal_items(deal_id, "flag") if i.payload.get("kind") == "brief_field"
                and (i.state == State.NEEDS_INFO or not open_only)]

    @_writes
    def store_brief(self, actor: str, item_id: str, out: BriefReaderOutput) -> WorkItem:
        item = self._item(item_id)
        self._require(actor, "propose:draft_brief", item.deal_id, item.id)  # check 1
        if item.type != "draft_brief" or item.state != State.NEW:
            self._deny(IllegalTransition(f"cannot store a draft Brief on {item.type} in state {item.state.value}"),
                       item.deal_id, actor, "propose:draft_brief", item.id)
        deal = self._deal(item.deal_id)
        if deal.brief_status == "approved":
            self._deny(IllegalTransition("the Brief is approved and locked"), deal.id, actor, "propose:draft_brief",
                       item.id)
        ag = self.agreement(deal.id)
        if ag is None:
            self._deny(Invalid("the deal has no agreement text"), deal.id, actor, "propose:draft_brief", item.id)
        out = BriefReaderOutput.model_validate(out.model_dump())
        try:
            flags = self._check_brief(deal, ag, out)
        except Invalid as error:
            self._deny(error, deal.id, actor, "propose:draft_brief", item.id)
        brief = out.brief.model_copy(update={"agreement_ref": out.brief.agreement_ref or ag.source})
        deal.brief, deal.brief_status = brief, "draft"
        opened = [self._open_brief_flag(deal, item, f) for f in flags]
        draft = BriefDraft(item_id=item.id, agreement_id=ag.id, sha256=ag.sha256, brief=brief,
                           citations=out.citations, flags=[i.id for i in opened], amendments_supplied=False)
        item.state = State.PROPOSED
        item.payload = {"draft": draft.model_dump(mode="json"), "note": out.note}
        self._log(deal.id, actor, "propose:draft_brief", "ALLOWED", item.id,
                  reason=f"{_count(len(out.citations), 'citation')}, {_count(len(opened), 'flag')}; base agreement "
                         f"only (no amendment supplied)")
        deal.stage = "awaiting_brief"
        return item

    def _sync_draft(self, deal: Deal, **changes) -> None:
        item = self._draft_item(deal.id)
        if item:
            item.payload = {**item.payload, "draft": {**item.payload["draft"],
                                                      "brief": deal.brief.model_dump(mode="json"), **changes}}

    def _answer_brief_field(self, actor: str, item: WorkItem, option_id: str) -> WorkItem:
        deal = self._deal(item.deal_id)
        if deal.brief_status == "approved":
            self._deny(IllegalTransition("the Brief is approved and locked"), deal.id, actor, "answer", item.id)
        field = item.payload["field"]
        if option_id == "remove":
            draft = self.brief_draft(deal.id)
            self._sync_draft(deal, removed=sorted({*(draft.removed if draft else []), field}))
        item.answer = option_id
        item.state = State.APPROVED
        self._log(deal.id, actor, "answer", "ALLOWED", item.id, reason=f"option {option_id} on {field}")
        self._post(item)
        deal.stage = "awaiting_brief" if self._brief_flags(deal.id) else "brief_ready"
        return item

    _PATH = re.compile(r"^(?P<field>[a-z_]+)(?:\[(?P<i>\d+)\])?(?:\.(?P<attr>name|amount|cap))?$")

    @_writes
    def amend_brief(self, actor: str, deal_id: str, field: str, value: Any, source_ref: str | None = None,
                    inferred: bool = False, note: str = "") -> Brief:
        """The controller sets one field of the draft, most often an adjustment amount from the books with its
        source. A new adjustment can be added at the next index. The open flags on that field are closed."""
        action = "amend_brief"
        deal = self._deal(deal_id)
        self._require(actor, action, deal_id, deal_id)
        if deal.brief_status == "approved":
            self._deny(IllegalTransition("the Brief is approved and locked"), deal_id, actor, action, field)
        if deal.brief_status != "draft" or deal.brief is None:
            self._deny(IllegalTransition("there is no draft Brief to amend"), deal_id, actor, action, field)
        m = self._PATH.match(field or "")
        data = deal.brief.model_dump()
        try:
            if not m:
                raise Invalid(f"unknown field '{field}'")
            name, i, attr = m.group("field"), m.group("i"), m.group("attr")
            if name in ("lender", "limit_section", "limit_wording", "debt_term", "debt_definition",
                        "ebitda_definition", "test_period_note") and i is None and attr is None:
                if not isinstance(value, str) or not value.strip() or len(value) > 2000:
                    raise Invalid(f"{field} must be text of 1 to 2000 characters")
                data[name] = value.strip()
            elif name == "limit" and i is None and attr is None:
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise Invalid("limit must be a number")
                data["limit"] = float(value)
            elif name == "debt_excludes" and i is not None and attr is None:
                k = int(i)
                if not isinstance(value, str) or not value.strip() or k > len(data[name]):
                    raise Invalid(f"{field} must be text, at an index up to {len(data[name])}")
                data[name][k:k + 1] = [value.strip()]
            elif name in ("ebitda_addbacks", "ebitda_deductions") and i is not None and attr:
                k, items = int(i), data[name]
                if k > len(items) or (k == len(items) and attr != "name"):
                    raise Invalid(f"{field}: add a new adjustment by its name first, at index {len(items)}")
                if k == len(items):
                    items.append(dict(name="", amount=0.0, cap=None, source_ref=deal.brief.agreement_ref, note="",
                                      inferred=True))
                if attr == "name":
                    if not isinstance(value, str) or not value.strip():
                        raise Invalid(f"{field} must be text")
                    items[k]["name"] = value.strip()
                elif attr == "cap":
                    if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool)
                                              or value < 0):
                        raise Invalid(f"{field} must be a number of USD thousands, or null for no cap")
                    items[k]["cap"] = None if value is None else float(value)
                else:
                    if not isinstance(value, (int, float)) or isinstance(value, bool):
                        raise Invalid(f"{field} must be a number of USD thousands")
                    if not (source_ref or "").strip():
                        raise Invalid(f"{field} needs its source: the filing and the line it comes from")
                    items[k].update(amount=float(value), source_ref=source_ref.strip(), inferred=bool(inferred),
                                    note=note or items[k].get("note", ""))
            else:
                raise Invalid(f"unknown field '{field}'")
            brief = Brief.model_validate(data)
            bad = _brief_number_problem(brief)
            if bad:
                raise Invalid(bad)
        except GatewayError as error:
            self._deny(error, deal_id, actor, action, field)
        except ValueError as error:
            self._deny(Invalid(f"invalid Brief: {error}"), deal_id, actor, action, field)
        deal.brief = brief
        self._sync_draft(deal)
        shown = f"{value:,.3f}" if isinstance(value, float) else str(value)
        self._log(deal_id, actor, "brief:amend", "ALLOWED", field,
                  reason=f"{field} = {shown[:200]}" + (f"; source: {source_ref}" if source_ref else ""))
        for flag in self._brief_flags(deal_id):
            if flag.payload.get("field") == field:
                flag.answer, flag.state = "amended", State.APPROVED
                self._log(deal_id, actor, "answer", "ALLOWED", flag.id, reason=f"amended {field}")
                self._post(flag)
        deal.stage = "awaiting_brief" if self._brief_flags(deal_id) else "brief_ready"
        return brief

    @_writes
    def approve_brief(self, actor: str, deal_id: str) -> Deal:
        """The controller approves the Brief. No agent can. It is then locked on the deal, with the agreement's hash
        in the log, and mapping can start."""
        action = "approve_brief"
        deal = self._deal(deal_id)
        self._require(actor, action, deal_id, deal_id)
        item = self._draft_item(deal_id)
        if deal.brief_status != "draft" or item is None:
            self._deny(IllegalTransition(f"there is no draft Brief to approve (the Brief is {deal.brief_status})"),
                       deal_id, actor, action, deal_id)
        if actor == item.proposed_by:
            self._deny(Denied("the proposer cannot approve its own draft"), deal_id, actor, action, item.id)
        waiting = self._brief_flags(deal_id)
        if waiting:
            self._deny(Denied(f"flag {waiting[0].id} on {waiting[0].payload['field']} is open; answer every Brief "
                              f"question first"), deal_id, actor, action, item.id)
        draft = self.brief_draft(deal_id)
        data = deal.brief.model_dump()
        for path in sorted(draft.removed, key=lambda p: -int(re.search(r"\[(\d+)\]", p).group(1))):
            name, k = re.match(r"(\w+)\[(\d+)\]", path).groups()
            del data[name][int(k)]
        brief = Brief.model_validate(data)
        bad = _brief_number_problem(brief)
        empty = [k for k, v in self._brief_paths(brief).items() if v in ("", None)]
        if bad or empty:
            self._deny(Invalid(bad or f"{', '.join(empty)} still empty"), deal_id, actor, action, item.id)
        deal.brief, deal.brief_status = brief, "approved"
        ag = self.agreement(deal_id)
        self._sync_draft(deal)
        item.state = State.APPROVED
        self._log(deal_id, actor, action, "ALLOWED", item.id,
                  reason=f"Brief locked: limit {brief.limit:.2f}x, {brief.debt_term}; agreement sha256 "
                         f"{ag.sha256[:12] if ag else 'none'}; base agreement only")
        self._post(item)
        deal.stage = "new"
        return deal
