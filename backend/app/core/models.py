"""Shared types: the contract between the data, the tools, the agents, the gateway, and the console.

Shapes follow docs/TASKS.md (shared contract), docs/architecture/gateway-and-api.md, and data-model.md.
Cayden owns this file. Send change requests to Cayden.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


def now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Work-item states and actors
# ---------------------------------------------------------------------------


class State(str, Enum):
    NEW = "NEW"
    PROPOSED = "PROPOSED"
    NEEDS_INFO = "NEEDS_INFO"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


# Work-item types used by the job runner and the gateway.
ItemType = Literal["map_lines", "flag", "prepare_result", "review_result", "approve_result"]

CONTROLLER = "human:controller"
MAPPER = "agent:mapper"
PREPARER = "agent:preparer"
REVIEWER = "agent:reviewer"
SYSTEM = "system:gateway"


# ---------------------------------------------------------------------------
# Evidence and options (shared by flags and the audit log)
# ---------------------------------------------------------------------------


class Evidence(BaseModel):
    quote: str
    page: int | None = None
    document_id: str | None = None  # the filing and exhibit, such as "8-K/A Ex 99.2 Note 4(h)"


class Option(BaseModel):
    id: str
    label: str
    effect: str  # computed by a tool run, never written by a model
    run_id: str | None = None


# ---------------------------------------------------------------------------
# The brief: the lender's limit and the covenant's own definitions
# ---------------------------------------------------------------------------


class Adjustment(BaseModel):
    """One EBITDA add-back or deduction, as the credit agreement defines it."""

    name: str
    amount: float  # in the deal's unit (USD thousands)
    cap: float | None = None
    source_ref: str
    note: str = ""
    inferred: bool = False  # True when the amount is our estimate, not a filed figure


class Financing(BaseModel):
    """One instrument of the closing financing, as filed."""

    name: str
    amount: float
    kind: Literal["senior_secured", "subordinated", "lease"]
    source_ref: str


class Brief(BaseModel):
    lender: str
    agreement_ref: str
    limit: float  # 2.50 means 2.50 to 1.00
    limit_section: str
    limit_wording: str
    debt_term: str  # "Senior Funded Bank Debt"
    debt_definition: str
    debt_excludes: list[str]
    ebitda_definition: str
    ebitda_addbacks: list[Adjustment] = Field(default_factory=list)
    ebitda_deductions: list[Adjustment] = Field(default_factory=list)
    closing_financing: list[Financing] = Field(default_factory=list)
    test_period_note: str = ""


# ---------------------------------------------------------------------------
# The record: deal, source lines, mappings, results
# ---------------------------------------------------------------------------

Section = Literal["income_statement", "balance_sheet", "cash_flow"]
CovenantTag = Literal["debt", "not_debt", "unclear", "na"]


class Deal(BaseModel):
    id: str
    name: str
    platform: str  # company name of the acquirer
    target: str  # company name of the acquired company
    stage: str = "new"
    brief: Brief
    situation: str = "PE add-on integration"


class SourceLine(BaseModel):
    """One statement line of one company. Rows are never changed after load, except the covenant tag."""

    id: str
    deal_id: str
    company: str
    line: str
    section: Section
    period: str
    amount: float
    unit: str = "USD thousands"
    source_ref: str
    is_total: bool = False  # subtotals are not added again in consolidation
    note: str | None = None  # what the filing says about the line, such as the 10-Q note on a sale-leaseback
    covenant_tag: CovenantTag = "na"
    covenant_note: str | None = None


class Mapping(BaseModel):
    id: str
    deal_id: str
    target_line_id: str
    platform_line_id: str | None = None
    target_line: str
    platform_line: str | None = None
    confidence: float = Field(ge=0, le=1)
    reason: str
    flagged: bool = False
    approved_by: str | None = None


class ResultRow(BaseModel):
    line: str
    section: Section
    platform: float
    target: float
    combined: float
    run_id: str


class Review(BaseModel):
    verdict: Literal["pass", "needs_attention"]
    reasons: list[str] = Field(default_factory=list)
    run_ids: list[str] = Field(default_factory=list)


class Result(BaseModel):
    id: str
    deal_id: str
    work_item_id: str
    rows: list[ResultRow]
    ebitda: float
    debt: float
    leverage: float
    limit: float
    verdict: Literal["ok", "over_limit"]
    headroom_turns: float
    tie_out_ok: bool | None = None
    review: Review | None = None
    run_ids: list[str]
    run_ids_by_tool: dict[str, str] = Field(default_factory=dict)
    backend: str = "scripted"  # which agent backend produced it: anthropic, droid, scripted, replay


class Policy(BaseModel):
    """What an agent learned from the controller. Written by the gateway when a flag is answered.

    Agents are stateful: the Mapper reads its policies before it maps, so a decision made once is applied
    next time with the policy as evidence instead of asking again. State lives in the store, not in a process.
    """

    id: str
    role: str  # agent:mapper, agent:preparer, agent:reviewer
    kind: Literal["covenant_tag", "mapping"]
    pattern: str  # normalized line name the policy applies to
    decision: str  # the tag, or the platform line
    reason: str
    approved_by: str
    learned_from: str  # the flag work item id
    deal_id: str
    at: datetime = Field(default_factory=now)
    times_applied: int = 0


class AgentSession(BaseModel):
    """One agent's running state: its backend session id and a short transcript of what it did.

    The Droid backend resumes the same session per role, so the agent keeps context across work items.
    The Anthropic backend replays the transcript. Either way the state is in the store and survives a restart.
    """

    role: str
    backend: str
    session_id: str | None = None
    turns: int = 0
    transcript: list[dict[str, Any]] = Field(default_factory=list)  # [{item, summary, at}]
    updated_at: datetime = Field(default_factory=now)


class ToolRun(BaseModel):
    """One call of a math tool. Every number on screen traces to one of these."""

    run_id: str
    deal_id: str
    tool: str
    actor: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    at: datetime = Field(default_factory=now)


# ---------------------------------------------------------------------------
# Work items and the audit log
# ---------------------------------------------------------------------------


class WorkItem(BaseModel):
    id: str
    deal_id: str
    type: str
    state: State = State.NEW
    escalation: str | None = None  # unused, kept so older console code does not break
    proposed_by: str
    question: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    options: list[Option] = Field(default_factory=list)
    default: str | None = None
    answer: str | None = None
    reject_reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    reverses_id: str | None = None
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


# ---------------------------------------------------------------------------
# Agent contracts: one typed input, one typed output, no memory
# ---------------------------------------------------------------------------


class LineTag(BaseModel):
    line_id: str
    tag: CovenantTag
    note: str = ""
    policy_id: str | None = None  # set when a learned policy decided it


class FlagOption(BaseModel):
    id: str
    label: str
    # For covenant_tag flags: the tag to apply to each line id if chosen.
    tags: dict[str, CovenantTag] = Field(default_factory=dict)
    # For mapping flags: the platform line (name or id) to map to if chosen (None means leave unmapped).
    platform_line: str | None = None
    # For mapping flags that cover several target lines: target line id -> platform line (name or id).
    mappings: dict[str, str | None] = Field(default_factory=dict)


class FlagProposal(BaseModel):
    """A line the Mapper could not place or tag with confidence. The gateway turns it into a flag work item
    and computes the effect of each option with the math tools."""

    kind: Literal["covenant_tag", "mapping"]
    line_ids: list[str]
    question: str
    evidence: list[Evidence] = Field(default_factory=list)
    options: list[FlagOption]
    default: str | None = None


class MappingProposal(BaseModel):
    target_line_id: str
    platform_line: str | None = None
    confidence: float = Field(ge=0, le=1)
    reason: str
    policy_id: str | None = None  # set when a learned policy decided it


class MapperInput(BaseModel):
    deal_id: str
    platform: str
    target: str
    target_lines: list[SourceLine]
    platform_lines: list[SourceLine]
    brief: Brief
    policies: list[Policy] = Field(default_factory=list)  # what the Mapper learned before
    session: AgentSession | None = None
    previous_refusal: str | None = None  # why the gateway refused the Mapper's last result, on the one retry


class MapperOutput(BaseModel):
    mappings: list[MappingProposal]
    tags: list[LineTag]
    flags: list[FlagProposal]
    note: str = ""


class PreparerInput(BaseModel):
    deal_id: str
    item_id: str
    platform_lines: list[SourceLine]
    target_lines: list[SourceLine]
    mappings: list[Mapping]
    brief: Brief
    session: AgentSession | None = None


class PreparerOutput(BaseModel):
    rows: list[ResultRow]
    ebitda: float
    debt: float
    leverage: float
    limit: float
    run_ids: list[str]
    consolidate_run_id: str | None = None
    ebitda_run_id: str | None = None
    debt_run_id: str | None = None
    leverage_run_id: str | None = None
    note: str = ""


class ReviewerInput(BaseModel):
    deal_id: str
    item_id: str
    result_id: str
    rows: list[ResultRow]
    ebitda: float
    debt: float
    leverage: float
    limit: float
    run_ids: list[str]
    consolidate_run_id: str | None = None
    leverage_run_id: str | None = None
    session: AgentSession | None = None


class ReviewerOutput(BaseModel):
    verdict: Literal["pass", "needs_attention"]
    reasons: list[str] = Field(default_factory=list)
    run_ids: list[str] = Field(default_factory=list)
