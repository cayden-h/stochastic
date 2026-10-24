"""Response models for the console. /docs and /openapi.json show these shapes."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer

from app.core.models import (AgentSession, BriefDraft, Deal, Edit, LearnedAdjustment, Mapping, Policy, Result, Review,
                             SourceLine, WorkItem)


class BackendStatus(BaseModel):
    """Which agent backend is configured and what ran last; the console shows it on screen."""
    configured: str
    fallback: str
    anthropic_key: bool
    factory_key: bool
    last_runs: list[dict]


class AuditSummary(BaseModel):
    """Counts for the audit badge: rows for this deal, hash chain check, denied attempts."""
    rows: int
    chain_valid: bool
    denied: int


class Verdict(BaseModel):
    """The limit check against the covenant, with the approval state and room for the next deal."""
    leverage: float
    limit: float
    verdict: Literal["ok", "over_limit"]
    headroom_turns: float
    ebitda: float
    debt: float
    debt_term: str
    debt_capacity: float | None = None  # read from the Reviewer's limit_test run, never computed in the route
    debt_capacity_run_id: str | None = None
    # Sensitivity, from a limit_test run the gateway makes for a passed result: the whole-line reading as filed
    # (balance sheet debt over reported EBITDA), its ratio, and the EBITDA increase at which it reaches the limit.
    # Never computed in the route.
    naive_debt: float | None = None
    naive_ebitda: float | None = None
    naive_leverage: float | None = None
    naive_flip_addback: float | None = None
    sensitivity_run_id: str | None = None
    review: Review | None = None
    tie_out_ok: bool | None = None
    backend: str
    approval_item: str | None = None
    approval_state: str | None = None
    posted: bool

    @model_serializer(mode="wrap")
    def _drop_unset_sensitivity(self, handler):
        """With no sensitivity run (no covenant flag to read the whole-line debt from), the five keys are absent."""
        out = handler(self)
        for key in ("naive_debt", "naive_ebitda", "naive_leverage", "naive_flip_addback", "sensitivity_run_id"):
            if key not in self.model_fields_set:
                out.pop(key, None)
        return out


class CaseResponse(BaseModel):
    """The whole screen in one read: lines, mappings, flags, result, verdict, work items, memory, log summary."""
    model_config = ConfigDict(extra="allow")

    deal: Deal
    stage: str
    source_lines: list[SourceLine]
    mappings: list[Mapping]
    flags: list[WorkItem]
    open_flags: list[str]
    result: Result | None = None
    verdict: Verdict | None = None
    work_items: list[WorkItem]
    policies: list[Policy]
    sessions: list[AgentSession]
    audit: AuditSummary
    backend: BackendStatus
    edits: list[Edit] = Field(default_factory=list)  # the deal's edits in order, reverted ones included
    adjustments: list[LearnedAdjustment] = Field(default_factory=list)  # learned memory, all deals, like policies
    brief_draft: BriefDraft | None = None  # filled by the Brief Reader routes when they land


class StoreStatus(BaseModel):
    """Where the record lives: memory, or Postgres on Tiger Cloud with the write-through queue."""
    model_config = ConfigDict(extra="allow")
    kind: Literal["memory", "postgres"]
    fallback_reason: str | None = None
    writes: int | None = None  # Postgres only: batches written, and queue-to-commit time per batch
    avg_write_ms: float | None = None
    last_write_ms: float | None = None

    @model_serializer(mode="wrap")
    def _drop_unset_timing(self, handler):
        """The memory store reports no write timing, so its status keeps only its own keys."""
        out = handler(self)
        for key in ("writes", "avg_write_ms", "last_write_ms"):
            if key not in self.model_fields_set:
                out.pop(key, None)
        return out


class HealthResponse(BaseModel):
    """Liveness plus the audit chain check, backend status, and the store."""
    ok: bool
    chain_valid: bool
    backend: BackendStatus
    store: StoreStatus


class DealCreated(BaseModel):
    """Result of POST /deals: the new deal id, its stage, and how many lines each company loaded."""
    deal_id: str
    stage: str
    lines: dict[str, int]
