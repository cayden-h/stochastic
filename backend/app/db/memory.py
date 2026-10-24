"""In-memory store for the prototype. Postgres replaces it later without changing the API."""
from __future__ import annotations

from app.core.models import AuditRow, Clause, Deal, Fact, Plan, WorkItem


class MemoryStore:
    def __init__(self) -> None:
        self.deals: dict[str, Deal] = {}
        self.documents: dict[str, str] = {}  # document id -> text
        self.facts: dict[str, Fact] = {}
        self.clauses: dict[str, Clause] = {}
        self.plans: dict[str, Plan] = {}
        self.items: dict[str, WorkItem] = {}
        self.audit: list[AuditRow] = []
        self._seq: dict[str, int] = {}

    def next_id(self, prefix: str) -> str:
        self._seq[prefix] = self._seq.get(prefix, 0) + 1
        return f"{prefix}_{self._seq[prefix]:03d}"
