import type { AuditRow, Mapping, SourceLine, WorkItem } from "./types";

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

/** USD thousands, as the tools report them: 25,963K. Every number keeps its unit. */
export function fmtK(v: number): string {
  return `${Math.round(v).toLocaleString("en-US")}K`;
}

/** A source line's amount in USD thousands, whatever unit the filing used (Nu Aire files in dollars). */
export function lineK(amount: number, unit: string): string {
  const dollars = ["usd", "dollars", "usd dollars", "$"].includes(unit.trim().toLowerCase());
  return fmtK(dollars ? amount / 1000 : amount);
}

/** USD thousands shown in millions for one headline figure: $49M. */
export function fmtM(v: number): string {
  return `$${Math.round(v / 1000)}M`;
}

/** A leverage ratio, two places, formatted from the unrounded value like the gateway does. */
export function fmtX(v: number): string {
  return `${v.toFixed(2)}x`;
}

export function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

/** The gateway sets `policy_id` from the policy record; a model's own wording varies, so the reason is only a fallback. */
export function isLearned(m: Mapping): boolean {
  return Boolean(m.policy_id) || m.reason.startsWith("Policy");
}

export function isLearnedTag(l: SourceLine): boolean {
  return Boolean(l.covenant_policy_id) || (l.covenant_note ?? "").startsWith("Policy");
}

const VERBS: Record<string, string> = {
  create: "CREATED", create_deal: "CREATED", propose: "PROPOSED", ask: "ASKED", answer: "ANSWERED",
  approve: "APPROVED", reject: "REJECTED", post: "POSTED", hold: "HELD", reverse: "REVERSED",
  tool: "RAN", policy: "POLICY", session: "SESSION", event: "EVENT", fork: "FORK",
};

/** Fixed verb list so the log stays scannable. */
export function verbOf(row: AuditRow): string {
  if (row.result === "DENIED") return "DENIED";
  return VERBS[row.action.split(":")[0]] ?? row.action.toUpperCase();
}

/** One plain line for the log. Uses names the controller already knows. */
export function describe(row: AuditRow, items: WorkItem[]): string {
  const item = items.find((i) => i.id === row.target);
  const [verb, rest] = row.action.split(":");
  if (row.result === "DENIED") return `Gateway refused. ${cap(row.reason ?? "Action not allowed.")}`;
  if (verb === "tool") return `${rest} ran. ${row.reason ?? ""}`.trim();
  if (verb === "ask" && item?.question) return item.question;
  if (verb === "answer" && item) {
    const opt = item.options.find((o) => o.id === item.answer);
    return `Flag answered: ${opt?.label ?? row.reason ?? "answered"}.`;
  }
  if (verb === "propose") return `${titleCase(rest ?? "item")} proposed. ${row.reason ?? ""}`.trim();
  if (verb === "create") return `${titleCase(rest ?? "item")} opened.`;
  if (verb === "create_deal") return `Deal created. ${row.reason ?? ""}`.trim();
  if (verb === "policy") return `${rest === "learn" ? "Policy learned" : "Policy applied"}. ${row.reason ?? ""}`.trim();
  if (verb === "session") return `Agent session turn. ${row.reason ?? ""}`.trim();
  if (verb === "post") return `${titleCase(item?.type ?? "item")} posted to the record.`;
  if (verb === "approve") return `${titleCase(item?.type ?? "item")} approved. ${row.reason ?? ""}`.trim();
  if (verb === "reject") return `${titleCase(item?.type ?? "item")} rejected. ${row.reason ?? ""}`.trim();
  if (verb === "hold") return "Flag held. The controller is not sure.";
  if (verb === "reverse") return `Reversed. ${row.reason ?? ""}`.trim();
  return row.reason ?? row.action;
}
