"""In-memory store. It is the working set for every read; `postgres.py` writes it through to Tiger Cloud.

Only the gateway writes here, and it calls `commit()` after each write. Collections follow
docs/architecture/data-model.md section 3.1.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.models import (AgentSession, AgreementText, ApprovedBrief, AuditRow, Deal, Edit, LearnedAdjustment, Mapping, Policy,
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
        self.policies: dict[str, Policy] = {}  # agent memory: survives a deal reset
        self.sessions: dict[str, AgentSession] = {}  # keyed by role
        self.edits: dict[str, Edit] = {}  # the controller's review edits (D19), part of the deal record
        self.adjustments: dict[str, LearnedAdjustment] = {}  # agent memory from amount edits: survives a reset
        self.agreements: dict[str, AgreementText] = {}  # credit agreement texts (D20), part of the deal record
        self.approved_briefs: dict[str, ApprovedBrief] = {}  # by agreement hash: memory, survives a reset
        self.audit: list[AuditRow] = []  # append only, in order
        self._seq: dict[str, int] = {}

    def reset_deals(self, keep_memory: bool = True) -> None:
        """Clear the record. Agent memory (policies and sessions) is kept unless asked otherwise."""
        memory = (self.policies, self.sessions, self.adjustments, self.approved_briefs)
        seq = dict(self._seq)
        self._clear()
        if keep_memory:
            self.policies, self.sessions, self.adjustments, self.approved_briefs = memory
            # The counters that memory refers to keep counting, so a new id never repeats one a kept record names:
            # policies (p), adjustments (a), and the edits (e) and work items (wi) in learned_from and edit_id.
            for prefix in ("p", "a", "e", "wi"):
                self._seq[prefix] = seq.get(prefix, 0)

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
        return [m for m in self.mappings.values() if m.deal_id == deal_id]

    def deal_items(self, deal_id: str, type_: str | None = None) -> list[WorkItem]:
        out = [i for i in self.items.values() if i.deal_id == deal_id]
        if type_:
            out = [i for i in out if i.type == type_]
        return out

    def deal_results(self, deal_id: str) -> list[Result]:
        return [r for r in self.results.values() if r.deal_id == deal_id]

    def deal_edits(self, deal_id: str) -> list[Edit]:
        return [e for e in self.edits.values() if e.deal_id == deal_id]

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
