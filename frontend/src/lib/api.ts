import type { AuditResponse, Case, Deal, Health, ToolRun, WorkItem } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
/** The human seat. The gateway's default controller actor; every write carries it. */
export const ACTOR = "human:controller";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Actor": ACTOR },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    const d = detail.detail;
    throw new Error(typeof d === "string" ? d : d?.message ?? d?.error ?? res.statusText);
  }
  return res.json();
}

/** Load a new deal from two statement CSVs and a brief (JSON). POST /deals is multipart, so it skips post(). */
async function createDeal(form: FormData): Promise<{ deal_id: string; stage: string; lines: { platform: number; target: number } }> {
  const res = await fetch(`${API_URL}/deals`, { method: "POST", headers: { "X-Actor": ACTOR }, body: form });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof detail.detail === "string" ? detail.detail : res.statusText);
  }
  return res.json();
}

/** One read for the screen, three writes. Everything else is a link to the record. */
export const api = {
  deals: () => get<Deal[]>("/deals"),
  case: (id: string) => get<Case>(`/deals/${id}/case`),
  health: () => get<Health>("/health"),
  audit: (id: string) => get<AuditResponse>(`/deals/${id}/audit`),
  run: (runId: string) => get<ToolRun>(`/runs/${runId}`),
  start: (id: string) => post<{ ok: boolean; log: string[]; stage: string }>(`/deals/${id}/run`, {}),
  answer: (itemId: string, optionId: string) => post<WorkItem>(`/work-items/${itemId}/answer`, { option_id: optionId }),
  hold: (itemId: string) => post<WorkItem>(`/work-items/${itemId}/hold`),
  approve: (itemId: string) => post<WorkItem>(`/work-items/${itemId}/approve`),
  reject: (itemId: string, reason: string) => post<WorkItem>(`/work-items/${itemId}/reject`, { reason }),
  createDeal,
  /** keepMemory=false clears the learned policies and sessions, so the next judge sees the flag again. */
  reset: (keepMemory = true) => post<{ ok: boolean }>(`/dev/reset?keep_memory=${keepMemory}`),
};
