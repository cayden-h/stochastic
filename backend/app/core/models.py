"""Shared types. Shapes follow docs/architecture/gateway-and-api.md and data-model.md."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


def now() -> datetime:
    return datetime.now(timezone.utc)


class State(str, Enum):
    NEW = "NEW"
    PROPOSED = "PROPOSED"
    NEEDS_INFO = "NEEDS_INFO"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


class Evidence(BaseModel):
    quote: str
    page: int | None = None
    document_id: str | None = None


class Option(BaseModel):
    id: str
    label: str
    effect: str


class Deal(BaseModel):
    id: str
    name: str
    situation: str
    stage: str
    brief: str


class Fact(BaseModel):
    id: str
    deal_id: str
    key: str
    value: str
    evidence: Evidence
    checked: bool = False
    confirmed: bool = False


class Clause(BaseModel):
    id: str
    deal_id: str
    section: str
    meaning: str
    evidence: Evidence
    confidence: float
    checked: bool = False


class Plan(BaseModel):
    id: str
    deal_id: str
    name: str
    instruments: dict[str, float]  # amounts in millions
    metrics: dict[str, float]
    status: Literal["ok", "blocked", "needs_consent"] = "ok"
    needs_consent: bool = False
    consent_note: str | None = None
    blocked_by: Evidence | None = None
    run_id: str | None = None
    stale: bool = False


class WorkItem(BaseModel):
    id: str
    deal_id: str
    type: str
    state: State = State.NEW
    escalation: str | None = None
    proposed_by: str
    question: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    options: list[Option] = Field(default_factory=list)
    default: str | None = None
    answer: str | None = None
    reject_reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now)


class AuditRow(BaseModel):
    id: int
    at: datetime
    deal_id: str
    actor: str
    action: str
    target: str | None = None
    result: Literal["ALLOWED", "DENIED"]
    reason: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    prev_hash: str
    hash: str
