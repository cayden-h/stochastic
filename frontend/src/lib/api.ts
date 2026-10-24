import type { AuditResponse, Clause, Deal, Fact, Plan, WorkItem } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const ACTOR = "human:reviewer";

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
    throw new Error(detail.detail ?? res.statusText);
  }
  return res.json();
}

export const api = {
  deals: () => get<Deal[]>("/deals"),
  items: (id: string) => get<WorkItem[]>(`/deals/${id}/work-items`),
  plans: (id: string) => get<Plan[]>(`/deals/${id}/plans`),
  facts: (id: string) => get<Fact[]>(`/deals/${id}/facts`),
  clauses: (id: string) => get<Clause[]>(`/deals/${id}/clauses`),
  audit: (id: string) => get<AuditResponse>(`/deals/${id}/audit`),
  answer: (itemId: string, optionId: string) => post<WorkItem>(`/work-items/${itemId}/answer`, { option_id: optionId }),
  hold: (itemId: string) => post<WorkItem>(`/work-items/${itemId}/hold`),
  approve: (itemId: string) => post<WorkItem>(`/work-items/${itemId}/approve`),
  reject: (itemId: string, reason: string) => post<WorkItem>(`/work-items/${itemId}/reject`, { reason }),
  reset: () => post<{ ok: boolean }>("/dev/reset"),
};
