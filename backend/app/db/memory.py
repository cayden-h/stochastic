"""In-memory store. It is the working set for every read; `postgres.py` writes it through to Tiger Cloud.

Only the gateway writes here, and it calls `commit()` after each write. Collections follow
docs/architecture/data-model.md section 3.1.
"""
from __future__ import annotations

from app.core.models import AgentSession, AuditRow, Deal, Mapping, Policy, Result, SourceLine, ToolRun, WorkItem


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
        self.audit: list[AuditRow] = []  # append only, in order
        self._seq: dict[str, int] = {}

    def reset_deals(self, keep_memory: bool = True) -> None:
        """Clear the record. Agent memory (policies and sessions) is kept unless asked otherwise."""
        policies, sessions, seq = self.policies, self.sessions, dict(self._seq)
        self._clear()
        if keep_memory:
            self.policies, self.sessions = policies, sessions
            self._seq["p"] = seq.get("p", 0)

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

    def role_policies(self, role: str) -> list[Policy]:
        return [p for p in self.policies.values() if p.role == role]

    def latest_result(self, deal_id: str) -> Result | None:
        rs = self.deal_results(deal_id)
        return rs[-1] if rs else None
