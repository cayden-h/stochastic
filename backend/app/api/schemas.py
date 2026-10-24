"""Response models for the console. /docs and /openapi.json show these shapes."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.core.models import AgentSession, Deal, Mapping, Policy, Result, Review, SourceLine, WorkItem


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
    # Sensitivity, from a limit_test run the gateway makes for a passed result: the whole-line reading of debt,
    # its ratio, and the EBITDA add-back and rent deduction at which it reaches the limit. Never computed in the route.
    naive_debt: float | None = None
    naive_leverage: float | None = None
    naive_flip_addback: float | None = None
    naive_flip_rent: float | None = None
    sensitivity_run_id: str | None = None
    review: Review | None = None
    tie_out_ok: bool | None = None
    backend: str
    approval_item: str | None = None
    approval_state: str | None = None
    posted: bool


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


class StoreStatus(BaseModel):
    """Where the record lives: memory, or Postgres on Tiger Cloud with the write-through queue."""
    model_config = ConfigDict(extra="allow")
    kind: Literal["memory", "postgres"]
    fallback_reason: str | None = None


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
