// Shapes returned by the gateway API. See docs/architecture/gateway-and-api.md, "The case shape".
export type State = "NEW" | "PROPOSED" | "NEEDS_INFO" | "APPROVED" | "REJECTED" | "POSTED" | "REVERSED";
export type Stage = "new" | "awaiting_flag" | "mapped" | "flags_answered" | "awaiting_approval" | "posted" | string;
export type Backend = "scripted" | "anthropic" | "droid" | "replay" | string;

export interface Evidence { quote: string; page: number | null; document_id: string | null }
export interface Option { id: string; label: string; effect: string; run_id: string | null; added_by?: string | null }

export interface Brief {
  lender: string; agreement_ref: string; limit: number; limit_section: string; limit_wording: string;
  debt_term: string; debt_definition: string; debt_excludes: string[]; ebitda_definition: string;
}

export interface Deal { id: string; name: string; platform: string; target: string; stage: Stage; brief: Brief }

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
}

export interface Verdict {
  leverage: number; limit: number; verdict: "ok" | "over_limit"; headroom_turns: number;
  ebitda: number; debt: number; debt_term: string; debt_capacity: number | null; debt_capacity_run_id: string | null;
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
  deal: Deal; stage: Stage; source_lines: SourceLine[]; mappings: Mapping[]; flags: WorkItem[]; open_flags: string[];
  result: Result | null; verdict: Verdict | null; work_items: WorkItem[]; policies: Policy[]; sessions: unknown[];
  audit: { rows: number; chain_valid: boolean; denied: number }; backend: BackendStatus;
}

export interface StoreStatus {
  kind: "memory" | "postgres"; fallback_reason: string | null;
  host?: string; schema?: string; ledger?: number; pending?: number; last_error?: string | null; last_write_at?: string | null;
}
export interface Health { ok: boolean; chain_valid: boolean; backend: BackendStatus; store: StoreStatus }

export interface AuditRow {
  id: number; at: string; deal_id: string; actor: string; action: string; target: string | null;
  result: "ALLOWED" | "DENIED"; reason: string | null; evidence: Evidence[]; prev_hash: string; hash: string;
}
export interface AuditResponse { chain_valid: boolean; rows: AuditRow[] }

export interface ToolRun { run_id: string; deal_id: string; tool: string; actor: string; inputs: Record<string, unknown>; outputs: Record<string, unknown>; at: string }
