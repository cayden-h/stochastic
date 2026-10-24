import type { AuditRow, Plan, WorkItem } from "./types";

export function clock(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-GB", { timeZone: "America/Los_Angeles", hour12: false });
}

export function titleCase(slug: string): string {
  const s = slug.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function cap(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function planLetter(plan: Plan): string {
  return plan.name.charAt(0);
}

const VERBS: Record<string, string> = {
  propose: "PROPOSED", ask: "ASKED", answer: "ANSWERED", approve: "APPROVED", reject: "REJECTED",
  post: "POSTED", post_plan: "POSTED", hold: "HELD", event: "EVENT",
};

/** Fixed verb list so the log stays scannable. */
export function verbOf(row: AuditRow): string {
  if (row.result === "DENIED") return "DENIED";
  return VERBS[row.action.split(":")[0]] ?? row.action.toUpperCase();
}

/** One plain line for the log. Uses names the reviewer already knows. */
export function describe(row: AuditRow, items: WorkItem[], plans: Plan[]): string {
  const item = items.find((i) => i.id === row.target);
  const plan = plans.find((p) => p.id === row.target);
  if (row.action === "post_plan" && plan) {
    return row.result === "DENIED"
      ? `Gateway refused. ${plan.name} not posted. ${row.reason ?? ""}`
      : `${plan.name} posted. ${row.reason ?? ""}`;
  }
  if (row.result === "DENIED") return `Gateway refused. ${cap(row.reason ?? "Action not allowed.")}.`;
  if (row.action.startsWith("ask:") && item?.question) return `${item.escalation}: ${item.question}`;
  if (row.action === "answer" && item) {
    const opt = item.options.find((o) => o.id === item.answer);
    return `${item.escalation ?? item.type}: ${opt?.label ?? row.reason ?? "answered"}.`;
  }
  if (row.action.startsWith("propose:")) {
    const summary = typeof item?.payload?.summary === "string" ? ` ${item.payload.summary}` : "";
    return `${item?.escalation ? item.escalation + ": " : ""}${titleCase(item?.type ?? row.action.split(":")[1])}.${summary}`;
  }
  if (row.action === "post") return `${titleCase(item?.type ?? "item")} posted to the record.`;
  if (row.action === "approve") return `${titleCase(item?.type ?? "item")} approved.`;
  if (row.action === "reject") return `${titleCase(item?.type ?? "item")} rejected. ${row.reason ?? ""}`;
  if (row.action === "hold") return `${item?.escalation ?? "Item"} held. The reviewer is not sure.`;
  if (row.action.startsWith("event:")) return row.reason ?? "Event.";
  return row.reason ?? row.action;
}
