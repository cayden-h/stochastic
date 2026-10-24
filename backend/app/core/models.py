"""Shared types: the contract between the data, the tools, the agents, the gateway, and the console.

Shapes follow docs/TASKS.md (shared contract), docs/architecture/gateway-and-api.md, and data-model.md.
Review edits follow docs/design/review-companion.md (D19).
The Brief Reader follows docs/architecture/brief-reader.md (D20).
Cayden owns this file. Send change requests to Cayden.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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
    SUPERSEDED = "SUPERSEDED"  # an approval item replaced by a newer one after a review edit; it stays in the log


# Work-item types used by the job runner and the gateway.
ItemType = Literal["map_lines", "flag", "prepare_result", "review_result", "approve_result", "draft_brief"]

CONTROLLER = "human:controller"
MAPPER = "agent:mapper"
PREPARER = "agent:preparer"
REVIEWER = "agent:reviewer"
BRIEF_READER = "agent:brief_reader"
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
    added_by: str | None = None  # "system:gateway" for the baseline reading the gateway adds; None when the Mapper wrote it
    # For covenant flags, read from the option's limit_test run so the console can show the ratio without parsing text.
    leverage: float | None = None  # debt over EBITDA from the run chain, unrounded like the effect text
    ok: bool | None = None
    basis: Literal["covenant", "as_filed"] | None = None


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
    brief: Brief | None = None  # None only while a deal created from agreement text has no draft yet (D20)
    # "approved" for a Brief sent as JSON (the fixture deal); "draft" while the controller reviews the reader's draft;
    # "none" before the reader ran. Mapping and the covenant tools wait for "approved".
    brief_status: Literal["approved", "draft", "none"] = "approved"

    @model_validator(mode="after")
    def _approved_needs_brief(self) -> Deal:
        """An approved deal always has its Brief; a draft or none may have no Brief until the reader runs."""
        if self.brief_status == "approved" and self.brief is None:
            raise ValueError("a deal with brief_status approved needs a brief")
        return self
    # "covenant" (the agreement's EBITDA) unless the controller chose the as-filed whole-line reading on a flag.
    ebitda_basis: Literal["covenant", "as_filed"] = "covenant"
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
    covenant_policy_id: str | None = None  # set by the gateway when a learned policy decided the tag


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
    policy_id: str | None = None  # set by the gateway when a learned policy decided it; the console's Learned chip


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
    # A revision after a review edit (D19): the result it replaces, and the live edits its runs applied.
    supersedes: str | None = None
    edit_ids: list[str] = Field(default_factory=list)


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
    company: str | None = None  # the company whose line it was learned on; it applies to that company's lines only
    # "company" for flag answers (D18: a not_debt tag cites a policy learned on that company's line).
    # "platform" for remap edits (D19): it applies to every add-on of the platform named in `platform`.
    scope: Literal["company", "platform"] = "company"
    platform: str | None = None  # the platform company name, for scope "platform"
    retired_by: str | None = None  # the reversal item that withdrew it; a retired policy is never applied
    at: datetime = Field(default_factory=now)
    times_applied: int = 0

    @model_validator(mode="after")
    def _platform_matches_scope(self) -> Policy:
        """A platform policy names its platform, and a company policy does not."""
        if self.scope == "platform" and not self.platform:
            raise ValueError("a platform policy needs platform")
        if self.scope == "company" and self.platform is not None:
            raise ValueError("a company policy must not set platform")
        return self


class AgentSession(BaseModel):
    """One agent's running state: its backend session id and a short transcript of what it did.

    The Droid backend resumes the same Droid session per role (`session_id`), so the agent keeps its conversation
    across work items and deals. The Anthropic backend replays the transcript. Either way the state is in the store and survives a restart.
    """

    role: str
    backend: str
    session_id: str | None = None
    session_key: str | None = None  # fingerprint of the setup the backend session was opened with
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
# Review edits (D19): the controller changes the combined books, gives a reason, and the agents learn from it
# ---------------------------------------------------------------------------

EditKind = Literal["amount", "remap"]
EditStatus = Literal["needs_reason", "reasoned", "reverted"]


class Edit(BaseModel):
    """One change the controller made to the agents' books, recorded on top of the run, never over it."""

    id: str
    deal_id: str
    kind: EditKind
    company: str
    line: str  # the line name as the table shows it
    section: Section
    # For "amount", in USD thousands.
    old_value: float | None = None
    new_value: float | None = None
    # For "remap": the target line's platform line before and after.
    old_platform_line: str | None = None
    new_platform_line: str | None = None
    status: EditStatus = "needs_reason"
    reason_chip: int | None = Field(default=None, ge=0, le=2)  # the ReasonChip id the controller picked
    reason_text: str | None = None  # the chip's label, or what the controller typed
    remember: bool = True
    policy_id: str | None = None  # set by the gateway when a reasoned remap made a policy
    adjustment_id: str | None = None  # set by the gateway when a reasoned amount edit made an adjustment
    from_adjustment_id: str | None = None  # set when the controller applied a learned adjustment the Preparer offered
    actor: str = CONTROLLER
    at: datetime = Field(default_factory=now)
    run_ids: list[str] = Field(default_factory=list)  # the recompute runs, all new run ids

    @model_validator(mode="after")
    def _fields_match_kind(self) -> Edit:
        """An amount edit carries values only, and a remap carries platform lines only."""
        if self.kind == "amount":
            if self.new_value is None:
                raise ValueError("an amount edit needs new_value")
            if self.old_platform_line is not None or self.new_platform_line is not None:
                raise ValueError("an amount edit must not set old_platform_line or new_platform_line")
        else:
            if self.new_platform_line is None:
                raise ValueError("a remap edit needs new_platform_line")
            if self.old_value is not None or self.new_value is not None:
                raise ValueError("a remap edit must not set old_value or new_value")
        if self.status == "reasoned" and self.reason_chip is None and not self.reason_text:
            raise ValueError("a reasoned edit needs reason_chip or reason_text")
        return self


class LearnedAdjustment(BaseModel):
    """What an amount edit teaches. The Preparer proposes it as a flag on a later deal; it is never applied silently.

    `amount` is the signed change the controller made (new value minus the agents' value, USD thousands), not the
    value: an add-back is "remove 500 of cost", which carries to another deal only as a change. Applying it on a later
    deal sets that deal's line to its own agent value plus `amount`.

    Named apart from `Adjustment`, which is the Brief's EBITDA add-back or deduction.
    """

    id: str
    deal_id: str  # the deal it was learned on
    company: str
    platform: str | None = None  # the deal's platform company, so a later add-on of that platform is offered it
    line: str
    amount: float  # the signed change, new minus old, in USD thousands (-500.0 removes 500 of cost)
    reason: str
    edit_id: str
    # "applied": learned and live. "proposed": offered on a later deal's open flag. "retired": its edit was reverted.
    status: Literal["applied", "proposed", "retired"] = "applied"
    at: datetime = Field(default_factory=now)


class ReasonChip(BaseModel):
    """One reason the bubble offers. Hardcoded per deal for the demo, and the pitch says so."""

    id: int = Field(ge=0, le=2)
    label: str


# ---------------------------------------------------------------------------
# The Brief Reader (D20): the model points at quotes, code checks them, the controller approves
# ---------------------------------------------------------------------------


class AgreementText(BaseModel):
    """The credit agreement as text. Stored apart from Deal, because /case returns the whole deal."""

    id: str
    deal_id: str
    text: str
    sha256: str  # an approved Brief is keyed by it, so the next deal under the same agreement reuses it
    source: str  # the filing and exhibit, or the uploaded file name


class BriefCitation(BaseModel):
    """The quote behind one Brief field. The gateway refuses a quote that is not in the agreement."""

    field: str  # path in the Brief, such as "limit" or "ebitda_addbacks[1].cap"
    quote: str  # the model's verbatim quote; the gateway enforces that it is in the agreement and at least four words
    section: str
    confidence: float = Field(ge=0, le=1)
    note: str = ""


class BriefFieldFlag(BaseModel):
    """A Brief field the controller must settle: low confidence, no quote, not found, or an amount from the books."""

    kind: Literal["brief_field"] = "brief_field"
    field: str
    question: str
    evidence: list[Evidence] = Field(default_factory=list)
    proposed: str | None = None  # the reader's value, if it has one


class BriefDraft(BaseModel):
    """The draft Brief with its citations and flags, as /case shows it while the controller reviews it."""

    item_id: str  # the draft_brief work item
    agreement_id: str
    sha256: str
    brief: Brief
    citations: list[BriefCitation] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)  # the brief_field flag work item ids
    # False means the draft reads the base agreement only, and the approval card says so (check 9).
    amendments_supplied: bool = False
    removed: list[str] = Field(default_factory=list)  # list fields the controller removed, applied at approval


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


class AdjustmentProposal(BaseModel):
    """The Preparer offers a learned adjustment on a later deal. The gateway opens it as a flag; never applied silently."""

    adjustment_id: str
    line_id: str  # the statement line of this deal it would change
    question: str


class PreparerInput(BaseModel):
    deal_id: str
    item_id: str
    platform_lines: list[SourceLine]
    target_lines: list[SourceLine]
    mappings: list[Mapping]
    brief: Brief
    adjustments: list[LearnedAdjustment] = Field(default_factory=list)  # learned on earlier deals; offer, never apply
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
    adjustment_flags: list[AdjustmentProposal] = Field(default_factory=list)
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


class BriefReaderInput(BaseModel):
    """Never the whole agreement: the indexes and the sections that mention a leverage ratio.
    The reader asks for more through get_section(id) and get_definition(term)."""

    deal_id: str
    item_id: str
    agreement_id: str
    sha256: str
    section_index: dict[str, str] = Field(default_factory=dict)  # section id -> heading
    definition_index: dict[str, str] = Field(default_factory=dict)  # defined term -> section id
    excerpts: dict[str, str] = Field(default_factory=dict)  # section id -> text, for the leverage sections
    amendments_supplied: bool = False  # False means the draft is the base agreement only
    session: AgentSession | None = None
    previous_refusal: str | None = None  # why the gateway refused the reader's last draft, on the one retry


class BriefReaderOutput(BaseModel):
    brief: Brief  # amounts are 0 and inferred; they come from the books, not the agreement
    citations: list[BriefCitation]
    flags: list[BriefFieldFlag] = Field(default_factory=list)
    note: str = ""
