"""In-memory store. It is the working set for every read; `postgres.py` writes it through to Tiger Cloud.

Only the gateway writes here, and it calls `commit()` after each write. Collections follow
docs/architecture/data-model.md section 3.1.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.models import (AgentSession, AgreementText, ApprovedBrief, AuditRow, ConversationMessage, Deal, Edit, LearnedAdjustment, Mapping, Policy,
                             Result, SourceLine, ToolRun, WorkItem)


# TimescaleDB's default time_bucket origin for timestamptz, so both stores floor a row to the same bucket.
BUCKET_ORIGIN = datetime(2000, 1, 3, tzinfo=timezone.utc)


def bucket_start(at: datetime, bucket_seconds: int) -> datetime:
    """`at` floored to its bucket, counted in whole microseconds from BUCKET_ORIGIN."""
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    micros = (at - BUCKET_ORIGIN) // timedelta(microseconds=1)
    size = bucket_seconds * 1_000_000
    return BUCKET_ORIGIN + timedelta(microseconds=micros // size * size)


class MemoryStore:
    kind = "memory"
    fallback_reason: str | None = None  # set when STORE=postgres could not connect

    def __init__(self) -> None:
        self._clear()

    def _clear(self) -> None:
        self.deals: dict[str, Deal] = {}
        self.source_lines: dict[str, SourceLine] = {}
        self.mappings: dict[str, Mapping] = {}
        self.items: dict[str, WorkItem] = {}
        self.results: dict[str, Result] = {}
        self.tool_runs: dict[str, ToolRun] = {}
        self.edits: dict[str, Edit] = {}  # controller edits, per deal, ids "e_001"
        self.agreements: dict[str, AgreementText] = {}  # credit agreement text, per deal
        self.policies: dict[str, Policy] = {}  # agent memory: survives a deal reset
        self.adjustments: dict[str, LearnedAdjustment] = {}  # agent memory, ids "a_001": survives a deal reset
        self.sessions: dict[str, AgentSession] = {}  # keyed by role
        self.approved_briefs: dict[str, ApprovedBrief] = {}  # by agreement hash: agent memory, survives a deal reset
        self.messages: dict[str, ConversationMessage] = {}  # the deal's conversation, ids "msg_001", in order
        self.audit: list[AuditRow] = []  # append only, in order
        self._seq: dict[str, int] = {}

    # The per-deal record: every collection whose rows carry a deal_id (the deal itself is keyed by its id).
    RECORD = ("source_lines", "mappings", "items", "results", "tool_runs", "edits", "agreements", "messages")

    def reset_deals(self, keep_memory: bool = True, keep_deals: set[str] | None = None, rechain=None,
                    reason: str | None = None) -> None:
        """Clear the record. Agent memory (policies, learned adjustments, approved Briefs, sessions) is kept unless
        asked otherwise.

        Edits and agreements are per-deal record and are cleared. The counters that memory refers to keep counting,
        so a new id never repeats one a kept record names: policies (p), adjustments (a), and the edits (e) and work
        items (wi) in learned_from and edit_id.

        `keep_deals` names deals whose whole record stays: the Dashboard's seeded cases, when only the live demo deal
        is reset. Their audit rows stay too, in order, and `rechain` (the gateway's `rechain`) chains them again; with
        keep_memory=False only the memory learned on the other deals is cleared, the sessions included; and every id
        counter keeps counting, so the reset deal's new ids never repeat a kept record's. `reason` is for the Postgres
        store's new ledger."""
        keep = set(keep_deals or ())
        memory = (self.policies, self.adjustments, self.approved_briefs, self.sessions)
        kept_deals = {k: v for k, v in self.deals.items() if k in keep}
        kept = {name: {k: v for k, v in getattr(self, name).items() if v.deal_id in keep} for name in self.RECORD}
        kept_audit = [row for row in self.audit if row.deal_id in keep]
        seq = dict(self._seq)
        self._clear()
        if keep_memory:
            self.policies, self.adjustments, self.approved_briefs, self.sessions = memory
            for prefix in ("p", "a", "e", "wi"):
                self._seq[prefix] = seq.get(prefix, 0)
        elif keep:
            self.policies = {k: v for k, v in memory[0].items() if v.deal_id in keep}
            self.adjustments = {k: v for k, v in memory[1].items() if v.deal_id in keep}
            self.approved_briefs = {k: v for k, v in memory[2].items() if v.deal_id in keep}
        if keep:
            self.deals = kept_deals
            for name, rows in kept.items():
                setattr(self, name, rows)
            self.audit = kept_audit
            self._seq = seq
            if rechain is not None:
                rechain()

    def commit(self) -> None:
        """Called by the gateway after every write. Nothing to do in memory."""

    def status(self) -> dict:
        return {"kind": self.kind, "fallback_reason": self.fallback_reason}

    def next_id(self, prefix: str) -> str:
        self._seq[prefix] = self._seq.get(prefix, 0) + 1
        return f"{prefix}_{self._seq[prefix]:03d}"

    # ---- read helpers (no writes) ----
    def lines(self, deal_id: str, company: str | None = None) -> list[SourceLine]:
        out = [l for l in self.source_lines.values() if l.deal_id == deal_id]
        if company:
            out = [l for l in out if l.company == company]
        return out

    def deal_mappings(self, deal_id: str) -> list[Mapping]:
        # list() copies the values first: a paced Mapper run adds mappings while the stream and /case read them
        return [m for m in list(self.mappings.values()) if m.deal_id == deal_id]

    def deal_messages(self, deal_id: str) -> list[ConversationMessage]:
        """The deal's conversation, in the order the gateway wrote it."""
        return [m for m in list(self.messages.values()) if m.deal_id == deal_id]

    def deal_items(self, deal_id: str, type_: str | None = None) -> list[WorkItem]:
        out = [i for i in self.items.values() if i.deal_id == deal_id]
        if type_:
            out = [i for i in out if i.type == type_]
        return out

    def deal_results(self, deal_id: str) -> list[Result]:
        return [r for r in self.results.values() if r.deal_id == deal_id]

    def deal_edits(self, deal_id: str) -> list[Edit]:
        """The deal's edits in insertion order, reverted ones included."""
        return [e for e in self.edits.values() if e.deal_id == deal_id]

    def active_edits(self, deal_id: str) -> list[Edit]:
        """The deal's edits that count: not reverted, in insertion order."""
        return [e for e in self.deal_edits(deal_id) if e.status != "reverted"]

    def role_policies(self, role: str) -> list[Policy]:
        return [p for p in self.policies.values() if p.role == role and not p.retired_by]

    def latest_result(self, deal_id: str) -> Result | None:
        rs = self.deal_results(deal_id)
        return rs[-1] if rs else None

    def timeline(self, deal_id: str, bucket_seconds: int = 60) -> dict:
        """Audit rows per time bucket, actor, and action family (the action before the colon). Counts only."""
        counts: dict[tuple[datetime, str, str], list[int]] = {}
        for row in self.audit:
            if row.deal_id != deal_id:
                continue
            key = (bucket_start(row.at, bucket_seconds), row.actor, row.action.split(":", 1)[0])
            c = counts.setdefault(key, [0, 0])
            c[0] += 1
            c[1] += row.result == "DENIED"
        buckets = [{"start": start.isoformat(), "actor": actor, "kind": kind, "rows": n, "denied": d}
                   for (start, actor, kind), (n, d) in sorted(counts.items())]
        return {"deal_id": deal_id, "bucket_seconds": bucket_seconds, "source": "memory", "buckets": buckets}
