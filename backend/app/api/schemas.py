"""Response models for the console. /docs and /openapi.json show these shapes."""
from __future__ import annotations

from typing import Any, Literal

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_serializer, model_validator

from app.core.models import (AgentSession, Brief, BriefDraft, Deal, Edit, EditKind, LearnedAdjustment, Mapping, Policy,
                             ReasonChip, Result, Review, Section, SourceLine, WorkItem)


class BackendStatus(BaseModel):
    """Which agent backend is configured and what ran last; the console shows it on screen."""
    configured: str
    fallback: str
    anthropic_key: bool
    factory_key: bool
    last_runs: list[dict]
    # The recording the demo paces ("demo", "factory") replay: name, model, backend, recorded_at (recording.json).
    demo_recording: dict | None = None


class MemoryCounts(BaseModel):
    """The sidebar's learning counters, across every deal in the record (GET /memory/counts, and /health)."""
    human_answers: int  # flags a human answered, plus the earlier answers behind each live policy
    policies: int  # live policies (not retired)
    edits: int  # the controller's edits saved with a reason (status "reasoned")
    by_deal: dict[str, dict[str, int]] = {}  # the same three counts per deal id


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
    # A job is running for this deal in this process now. The console reads this, not the stage: after a restart a
    # deal can sit at a working stage with nothing running (it is moved to run_failed on start).
    running: bool = False
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
    # The reasons the edit bubble offers, per edit kind ("amount", "remap"). Hardcoded per deal for the demo.
    reason_chips: dict[str, list[ReasonChip]] | None = None


class EditBody(BaseModel):
    """POST /deals/{id}/edits. An amount edit gives value (USD thousands, a finite JSON number; a boolean or a string
    is refused); a remap gives platform_line. The gateway checks the rest (the company, the line, the approval
    state) and audits every refusal. A non-finite value in a 422 is written as "non-finite" (app/api/errors.py)."""
    kind: EditKind
    company: str = Field(min_length=1, max_length=200)
    line: str = Field(min_length=1, max_length=300)
    value: float | None = None
    platform_line: str | None = Field(default=None, min_length=1, max_length=300)
    section: Section | None = None

    @field_validator("value", mode="before")
    @classmethod
    def _number(cls, v):
        """Only a JSON number: lax parsing would read true as 1.0 and the string "NaN" as nan."""
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
            raise ValueError("value must be a JSON number (USD thousands), not a boolean or a string")
        return v

    @field_validator("value")
    @classmethod
    def _finite(cls, v):
        if v is not None and not math.isfinite(v):
            raise ValueError("value must be a finite number")
        return v

    @model_validator(mode="after")
    def _fields_match_kind(self) -> "EditBody":
        if self.kind == "amount":
            if self.value is None:
                raise ValueError("value is required for an amount edit (USD thousands)")
            if self.platform_line is not None:
                raise ValueError("platform_line is only for a remap edit")
        else:
            if self.platform_line is None:
                raise ValueError("platform_line is required for a remap edit")
            if self.value is not None:
                raise ValueError("value is only for an amount edit")
        return self


class EditReasonBody(BaseModel):
    """POST /edits/{id}/reason: one of chip (a ReasonChip id) or text, and whether to remember it."""
    chip: int | None = None
    text: str | None = None
    remember: bool = True

    @field_validator("chip", mode="before")
    @classmethod
    def _chip_is_an_integer(cls, v):
        """Only a JSON integer: lax parsing would read true as chip 1."""
        if v is not None and (isinstance(v, bool) or not isinstance(v, int)):
            raise ValueError("chip must be a JSON integer (a reason chip id)")
        return v

    @model_validator(mode="after")
    def _one_reason(self) -> "EditReasonBody":
        if self.chip is None and not (self.text or "").strip():
            raise ValueError("chip or text is required: give a chip id or a text reason")
        return self


class EditVerdict(BaseModel):
    """The limit check after an edit, read from the recompute's tool runs by the gateway."""
    leverage: float
    limit: float
    verdict: Literal["ok", "over_limit"]
    headroom_turns: float
    ebitda: float
    debt: float
    tie_out_ok: bool | None = None
    review: Review | None = None
    approval_item: str
    approval_state: str


class EditResponse(BaseModel):
    """What an edit or its undo returns: the edit, the new result revision, its verdict, the new approval item,
    and the reasons the bubble offers."""
    edit: Edit
    result: Result
    verdict: EditVerdict
    approval: WorkItem
    reasons: list[ReasonChip]


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
    running: bool = False  # a job is running for some deal in this process now
    memory_counts: MemoryCounts | None = None


class DealCreated(BaseModel):
    """Result of POST /deals: the new deal id, its stage, how many lines each company loaded, and the Brief's status
    ("approved" for a Brief sent as JSON or reused by the agreement's hash, "none" until the reader runs)."""
    deal_id: str
    stage: str
    lines: dict[str, int]
    brief_status: Literal["approved", "draft", "none"] = "approved"


MAX_BRIEF_FIGURE = 1e12  # USD thousands; far above any deal, and two of them cannot sum to infinity


class BriefAmount(BaseModel):
    """One field of the draft Brief to set, by path (for example "ebitda_addbacks[2].amount"). An amount is USD
    thousands from the books and needs source_ref; the gateway checks the path, the type, and the source."""
    field: str = Field(min_length=1, max_length=200, pattern=r"^[a-z_]+(\[[0-9]+\])?(\.(name|amount|cap))?$")
    value: Any = None  # a number for an amount, a cap, or the limit; text for a text field; null for no cap
    source_ref: str | None = Field(default=None, max_length=500)
    inferred: bool = False
    note: str = Field(default="", max_length=2000)

    @field_validator("value")
    @classmethod
    def _finite(cls, value: Any, info) -> Any:
        """A boolean is not a number, a figure must be finite and below 1e12 in size, and a number sent as text for
        an amount, a cap, or the limit is refused. An integer too big for a float is refused here, not in the
        gateway. The error's loc is amounts[i].value and its message names the field path."""
        path = info.data.get("field", "value")
        if isinstance(value, bool):
            raise ValueError(f"{path}: value must be a JSON number or text, not a boolean")
        if isinstance(value, (int, float)):
            try:
                f = float(value)
            except OverflowError:
                raise ValueError(f"{path}: value must be a finite number") from None
            if not math.isfinite(f):
                raise ValueError(f"{path}: value must be a finite number")
            if abs(f) >= MAX_BRIEF_FIGURE:
                raise ValueError(f"{path}: value must be below 1e12 in size")
            return f
        if isinstance(value, str):
            numeric_field = path == "limit" or path.rsplit(".", 1)[-1] in ("amount", "cap")
            if numeric_field and _looks_numeric(value):
                raise ValueError(f"{path}: value must be a JSON number, not a number in text")
            return value
        if value is not None:
            raise ValueError(f"{path}: value must be a JSON number, text, or null")
        return value


def _looks_numeric(text: str) -> bool:
    try:
        float(text.replace(",", ""))
        return True
    except ValueError:
        return False


class BriefAmountsBody(BaseModel):
    """POST /deals/{id}/brief/amounts: one or more fields of the draft Brief, applied in order."""
    amounts: list[BriefAmount] = Field(min_length=1, max_length=100)


class BriefAmountsResponse(BaseModel):
    """The amended Brief and the draft as /case shows it, with the stage after the amendments."""
    brief: Brief
    brief_draft: BriefDraft | None = None
    brief_status: Literal["approved", "draft", "none"]
    stage: str
