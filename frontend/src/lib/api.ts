import type { ConversationMessage } from "./conversation";
import type {
  AuditResponse, Brief, Case, Deal, DealCreated, DealSummary, Edit, EditBody, EditResponse, Health, Stage, ToolRun, WorkItem,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
/** The human seat. The gateway's default controller actor; every write carries it. */
export const ACTOR = "human:controller";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

/** The error text from a FastAPI response: a string detail, a gateway {message|error} object, or a 422 list. */
async function errorText(res: Response): Promise<string> {
  const body = await res.json().catch(() => ({ detail: res.statusText }));
  const d = body.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d.length) return d[0]?.msg ?? res.statusText;
  return d?.message ?? d?.error ?? res.statusText;
}

async function post<T>(path: string, body?: unknown, method: "POST" | "DELETE" = "POST"): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json", "X-Actor": ACTOR },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

/** Load a new deal from two statement CSVs and either a Brief (JSON, field `brief`) or the credit agreement as text
 * (file field `agreement_txt`, read by the Brief Reader). POST /deals is multipart, so it skips post(). */
async function createDeal(form: FormData): Promise<DealCreated> {
  const res = await fetch(`${API_URL}/deals`, { method: "POST", headers: { "X-Actor": ACTOR }, body: form });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

/** One GET /deals row as the gateway sends it: the summary shape (`deal_id`, `verdict`, `updated_at`, `data_source`,
 * `note`), or the older full Deal (`id`, `name`). Both read as a DealSummary. */
type DealRow = Partial<Deal> & Partial<Omit<DealSummary, "verdict">> & {
  deal_id?: string; verdict?: DealSummary["verdict"]; updated_at?: string | null;
};

export function toSummary(d: DealRow): DealSummary {
  const id = d.deal_id ?? d.id ?? "";
  const platform = d.platform ?? "";
  const target = d.target ?? "";
  const v = d.verdict;
  return {
    id, platform, target, stage: (d.stage ?? "new") as Stage,
    name: d.name ?? `${platform} acquires ${target}`,
    verdict: v && typeof v.leverage === "number" ? { leverage: v.leverage, limit: v.limit, verdict: v.verdict } : null,
    updated_at: d.updated_at ?? null,
    data_source: d.data_source === "sample" || d.data_source === "filings" ? d.data_source : null,
    note: d.note ?? null,
  };
}

/** How fast a run plays. "demo" is the 15-second demo (about 6 s to the question, about 7 s after the last answer). */
export type Pace = "demo";

/** The reads for the screen and the writes. Everything else is a link to the record. */
export const api = {
  deals: async () => (await get<DealRow[]>("/deals")).map(toSummary).filter((d) => d.id),
  case: (id: string) => get<Case>(`/deals/${id}/case`),
  health: () => get<Health>("/health"),
  audit: (id: string) => get<AuditResponse>(`/deals/${id}/audit`),
  run: (runId: string) => get<ToolRun>(`/runs/${runId}`),
  /** Every tool run of the deal, oldest first. The Review page reads the agents' own leverage run from it. */
  runs: (id: string) => get<ToolRun[]>(`/deals/${id}/runs`),
  conversation: (id: string) => get<ConversationMessage[]>(`/deals/${id}/conversation`),
  // The run goes in the background ({"sync": false}): a paced run takes about 23 s, and the console follows it on the
  // stream instead of waiting on the request. `pace: "demo"` plays it in about 15 s of agent time.
  start: (id: string, pace?: Pace) =>
    post<{ ok: boolean; log: string[]; stage: string }>(`/deals/${id}/run`, pace ? { sync: false, pace } : { sync: false }),
  answer: (itemId: string, optionId: string) => post<WorkItem>(`/work-items/${itemId}/answer`, { option_id: optionId }),
  hold: (itemId: string) => post<WorkItem>(`/work-items/${itemId}/hold`),
  approve: (itemId: string) => post<WorkItem>(`/work-items/${itemId}/approve`),
  reject: (itemId: string, reason: string) => post<WorkItem>(`/work-items/${itemId}/reject`, { reason }),
  createDeal,
  /** keepMemory=false clears the learned policies and sessions, so the next judge sees the flag again. */
  // It reseeds the live demo deal only; `kept_deals` names the deals it left alone (the Dashboard's other cases).
  reset: (keepMemory = true) => post<{ ok: boolean; kept_deals?: string[] }>(`/dev/reset?keep_memory=${keepMemory}`),
  // Review edits (D19, Tri's T2): change an amount or remap a line, give the reason, undo.
  edit: (dealId: string, body: EditBody) => post<EditResponse>(`/deals/${dealId}/edits`, body),
  reason: (editId: string, reason: { chip: number } | { text: string }, remember: boolean) =>
    post<Edit>(`/edits/${editId}/reason`, { ...reason, remember }),
  revert: (editId: string) => post<EditResponse>(`/edits/${editId}`, undefined, "DELETE"),
  // The Brief Reader (D20, Tri's T4): set one field of the draft by path (an adjustment amount from the books with its
  // source, or a correction to any field the reader got wrong), then approve the Brief.
  // The route takes a list of fields ({"amounts": [...]}, applied in order); the console sends one at a time.
  amendBrief: (dealId: string, body: { field: string; value: number | string; source_ref?: string; inferred?: boolean; note?: string }) =>
    post<{ brief: Brief; brief_status: string; stage: string }>(`/deals/${dealId}/brief/amounts`, { amounts: [body] }),
  approveBrief: (dealId: string) => post<Deal>(`/deals/${dealId}/brief/approve`),
};

/** The final files after approval: the workbook (Tri's T3) and the draft certificate. Absolute URLs. */
export function finalFiles(deal: Deal): { url: string; name: string }[] {
  return [
    { url: `${API_URL}/deals/${deal.id}/export.xlsx`, name: `${deal.platform} + ${deal.target} combined books.xlsx` },
    { url: `${API_URL}/deals/${deal.id}/certificate`, name: "Compliance certificate (draft).md" },
  ];
}
