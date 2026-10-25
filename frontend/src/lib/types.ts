// Shapes returned by the gateway API. See docs/architecture/gateway-and-api.md, "The case shape".
/** SUPERSEDED: an approval item a review edit replaced (D19); it stays in the log. */
export type State = "NEW" | "PROPOSED" | "NEEDS_INFO" | "APPROVED" | "REJECTED" | "POSTED" | "REVERSED" | "SUPERSEDED";
/** The deal stages the gateway and the job runner set (backend/app/gateway, backend/app/agents/jobs.py). */
export type Stage =
  | "new" | "reading_brief" | "awaiting_brief" | "brief_ready"
  | "mapping" | "awaiting_flag" | "mapped" | "flags_answered" | "preparing"
  | "awaiting_review" | "awaiting_approval" | "needs_attention" | "posted" | "run_failed";
export type Backend = "scripted" | "anthropic" | "droid" | "replay" | string;

export interface Evidence { quote: string; page: number | null; document_id: string | null }
export interface Option {
  id: string; label: string; effect: string; run_id: string | null; added_by?: string | null;
  // Covenant flags only, read by the gateway from the option's limit_test run.
  leverage?: number | null; ok?: boolean | null; basis?: "covenant" | "as_filed" | null;
}

/** One EBITDA add-back or deduction the agreement allows. Amounts and caps in USD thousands. */
export interface BriefAdjustment { name: string; amount: number; cap: number | null; source_ref: string; note: string; inferred: boolean }

export interface Brief {
  lender: string; agreement_ref: string; limit: number; limit_section: string; limit_wording: string;
  debt_term: string; debt_definition: string; debt_excludes: string[]; ebitda_definition: string;
  ebitda_addbacks?: BriefAdjustment[]; ebitda_deductions?: BriefAdjustment[]; test_period_note?: string;
}

export interface Deal {
  id: string; name: string; platform: string; target: string; stage: Stage;
  /** Null only while a deal created from agreement text has no draft yet (D20). */
  brief: Brief | null;
  /** "approved" for a Brief sent as JSON; "draft" while the controller reviews the reader's draft; "none" before it ran. */
  brief_status?: "approved" | "draft" | "none";
  ebitda_basis?: "covenant" | "as_filed";
}

/** The quote behind one Brief field. `field` is a path such as `ebitda_addbacks[1].cap`. */
export interface BriefCitation { field: string; quote: string; section: string; confidence: number; note: string }

/** The reader's draft while the controller reviews it (D20). */
export interface BriefDraft {
  item_id: string; agreement_id: string; sha256: string; brief: Brief; citations: BriefCitation[];
  /** The brief_field flag work item ids. */
  flags: string[];
  /** False: the draft reads the base agreement only. */
  amendments_supplied: boolean;
  /** List fields the controller removed, applied at approval. */
  removed: string[];
}

export interface SourceLine {
  id: string; company: string; line: string; section: "balance_sheet" | "income_statement" | "cash_flow";
  period: string; amount: number; unit: string; source_ref: string; is_total: boolean; note: string | null;
  covenant_tag: "debt" | "not_debt" | "unclear" | "na"; covenant_note: string | null;
  covenant_policy_id?: string | null;
}

export interface Mapping {
  id: string; target_line_id: string; platform_line_id: string | null; target_line: string; platform_line: string | null;
  confidence: number; reason: string; flagged: boolean; approved_by: string | null;
  policy_id?: string | null;
}

export interface WorkItem {
  id: string; deal_id: string; type: string; state: State; proposed_by: string;
  question: string | null; evidence: Evidence[]; options: Option[]; default: string | null;
  answer: string | null; reject_reason: string | null; payload: Record<string, unknown>; created_at: string;
}

export interface ResultRow { line: string; section: string; platform: number; target: number; combined: number; run_id: string }

export interface Result {
  id: string; rows: ResultRow[]; ebitda: number; debt: number; leverage: number; limit: number;
  verdict: "ok" | "over_limit"; headroom_turns: number; tie_out_ok: boolean;
  review: { verdict: "pass" | "needs_attention"; reasons: string[]; run_ids: string[] } | null;
  run_ids: string[]; run_ids_by_tool: Record<string, string>; backend: Backend;
  /** After a review edit: the result this one replaces, and the live edits it was computed with. */
  supersedes?: string | null; edit_ids?: string[];
}

export interface Verdict {
  leverage: number; limit: number; verdict: "ok" | "over_limit"; headroom_turns: number;
  ebitda: number; debt: number; debt_term: string; debt_capacity: number | null; debt_capacity_run_id: string | null;
  naive_debt?: number; naive_ebitda?: number; naive_leverage?: number; naive_flip_addback?: number; sensitivity_run_id?: string;
  review: { verdict: "pass" | "needs_attention"; reasons: string[]; run_ids: string[] } | null;
  tie_out_ok: boolean; backend: Backend; approval_item: string | null; approval_state: State | null; posted: boolean;
}

export interface Policy {
  id: string; role: string; kind: string; pattern: string; decision: string; reason: string;
  approved_by: string; learned_from: string; times_applied: number;
}

export interface Attempt { backend: Backend; ok: boolean; seconds: number; error?: string }
export interface LastRun { role: string; backend: Backend; attempts: Attempt[]; meta: Record<string, unknown>; at: string }
export interface BackendStatus { configured: Backend; fallback: string; anthropic_key: boolean; factory_key: boolean; last_runs: LastRun[] }

export interface Case {
  /** A job is running for this deal in the gateway's process now (not inferred from the stage). */
  running?: boolean;
  deal: Deal; stage: Stage; source_lines: SourceLine[]; mappings: Mapping[]; flags: WorkItem[]; open_flags: string[];
  result: Result | null; verdict: Verdict | null; work_items: WorkItem[]; policies: Policy[]; sessions: unknown[];
  audit: { rows: number; chain_valid: boolean; denied: number }; backend: BackendStatus;
  /** The controller's edits (D19), reverted ones included. Absent until Tri's T2 adds them to /case. */
  edits?: Edit[];
  /** What reasoned amount edits taught (D19). */
  adjustments?: LearnedAdjustment[];
  /** The reason chips per edit kind, `{"amount": [...], "remap": [...]}` as `gw.reason_chips` gives them, when T2 sends them on /case. */
  reason_chips?: Partial<Record<Edit["kind"], ReasonChip[]>>;
  /** The Brief Reader's draft while the controller reviews it (D20, Tri's T4). */
  brief_draft?: BriefDraft | null;
}

export type Section = SourceLine["section"];

/** One change the controller made to the combined books, recorded on top of the agents' run (D19).
 * `line` is the company's own source line name, not the combined row's platform line. Amounts in USD thousands. */
export interface Edit {
  id: string; deal_id: string; kind: "amount" | "remap"; company: string; line: string; section: Section;
  old_value: number | null; new_value: number | null; old_platform_line: string | null; new_platform_line: string | null;
  status: "needs_reason" | "reasoned" | "reverted"; reason_chip: number | null; reason_text: string | null;
  remember: boolean; policy_id: string | null; adjustment_id: string | null; from_adjustment_id?: string | null;
  actor: string; at: string; run_ids: string[];
}

export interface LearnedAdjustment {
  id: string; deal_id: string; company: string; platform?: string | null; line: string; amount: number; reason: string;
  edit_id: string; status: "applied" | "proposed" | "retired"; at: string;
}

/** A reason the bubble offers, id 0 to 2. Hardcoded per deal for the demo. */
export interface ReasonChip { id: number; label: string }

/** POST /deals/{id}/edits and DELETE /edits/{id}: the edit, the recomputed result and verdict, and the chips. */
export interface EditResponse {
  edit: Edit; result: Result; reasons: ReasonChip[]; approval?: WorkItem;
  verdict: Pick<Verdict, "leverage" | "limit" | "verdict" | "headroom_turns" | "ebitda" | "debt" | "tie_out_ok" | "review" | "approval_item" | "approval_state">;
}

export type EditBody =
  | { kind: "amount"; company: string; line: string; section: Section; value: number }
  | { kind: "remap"; company: string; line: string; section: Section; platform_line: string };

export interface StoreStatus {
  kind: "memory" | "postgres"; fallback_reason: string | null;
  host?: string; schema?: string; ledger?: number; pending?: number; last_error?: string | null; last_write_at?: string | null;
}
export interface Health { ok: boolean; chain_valid: boolean; backend: BackendStatus; store: StoreStatus; running?: boolean }

export interface AuditRow {
  id: number; at: string; deal_id: string; actor: string; action: string; target: string | null;
  result: "ALLOWED" | "DENIED"; reason: string | null; evidence: Evidence[]; prev_hash: string; hash: string;
}
export interface AuditResponse { chain_valid: boolean; rows: AuditRow[] }

export interface ToolRun { run_id: string; deal_id: string; tool: string; actor: string; inputs: Record<string, unknown>; outputs: Record<string, unknown>; at: string }

/** POST /deals: the new deal's id, its stage, and the lines loaded per company. */
export interface DealCreated { deal_id: string; stage: Stage; lines: { platform: number; target: number } }
