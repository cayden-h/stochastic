// Shapes returned by the gateway API. See docs/architecture/gateway-and-api.md.
export type State = "NEW" | "PROPOSED" | "NEEDS_INFO" | "APPROVED" | "REJECTED" | "POSTED" | "REVERSED";

export interface Evidence { quote: string; page: number | null; document_id: string | null }
export interface Option { id: string; label: string; effect: string }

export interface Deal { id: string; name: string; situation: string; stage: string; brief: string }

export interface WorkItem {
  id: string; deal_id: string; type: string; state: State; escalation: string | null; proposed_by: string;
  question: string | null; evidence: Evidence[]; options: Option[]; default: string | null;
  answer: string | null; reject_reason: string | null; payload: Record<string, unknown>; created_at: string;
}

export interface Plan {
  id: string; deal_id: string; name: string; instruments: Record<string, number>;
  metrics: Record<string, number>; status: "ok" | "blocked" | "needs_consent";
  needs_consent: boolean; consent_note: string | null; blocked_by: Evidence | null;
  run_id: string | null; stale: boolean;
}

export interface Fact { id: string; key: string; value: string; evidence: Evidence; checked: boolean; confirmed: boolean }
export interface Clause { id: string; section: string; meaning: string; evidence: Evidence; confidence: number; checked: boolean }

export interface AuditRow {
  id: number; at: string; deal_id: string; actor: string; action: string; target: string | null;
  result: "ALLOWED" | "DENIED"; reason: string | null; evidence: Evidence[]; prev_hash: string; hash: string;
}
export interface AuditResponse { chain_valid: boolean; rows: AuditRow[] }
