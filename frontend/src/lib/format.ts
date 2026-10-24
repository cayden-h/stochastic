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

/** USD thousands shown in millions for a headline figure: $49.3M. */
export function fmtM(v: number): string {
  return `$${(v / 1000).toFixed(1)}M`;
}

/** A leverage ratio, two places, formatted from the unrounded value like the gateway does. v3 writes the times sign. */
export function fmtX(v: number): string {
  return `${v.toFixed(2)}\u00d7`;
}

/** A confidence as a whole percent: 0.42 is 42%. */
export function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}

/** How long ago, in words a controller reads at a glance. Past a day it falls back to the PT clock. */
export function ago(iso: string, now = Date.now()): string {
  const s = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return clock(iso);
}

/** The stage in the controller's words, and whether it waits on them. */
export function stageWords(stage: string): { text: string; tone: "you" | "work" | "done" | "bad" | "idle" } {
  switch (stage) {
    case "new": return { text: "Not started", tone: "idle" };
    case "mapping": return { text: "Mapping", tone: "work" };
    case "awaiting_flag": return { text: "Mapping \u00b7 needs you", tone: "you" };
    case "mapped": case "flags_answered": case "preparing": return { text: "Preparing", tone: "work" };
    case "awaiting_review": return { text: "Reviewing", tone: "work" };
    case "awaiting_approval": return { text: "Approval \u00b7 needs you", tone: "you" };
    case "needs_attention": return { text: "Needs attention", tone: "bad" };
    case "posted": return { text: "Posted", tone: "done" };
    case "run_failed": return { text: "Run stopped", tone: "bad" };
    default: return { text: titleCase(stage), tone: "work" };
  }
}

export function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

/** Learned only when the gateway tied the line to a live policy record. A model's wording ("Policy p_006 ...") can
 * name a policy that does not exist or no longer applies, so the reason text never counts. */
export function isLearned(m: Mapping): boolean {
  return Boolean(m.policy_id);
}

export function isLearnedTag(l: SourceLine): boolean {
  return Boolean(l.covenant_policy_id);
}

/** The distinct policies applied to this deal's lines: one controller answer can settle several lines. */
export function learnedPolicies(mappings: Mapping[], lines: SourceLine[]): Set<string> {
  const ids = [...mappings.map((m) => m.policy_id), ...lines.map((l) => l.covenant_policy_id)];
  return new Set(ids.filter((id): id is string => Boolean(id)));
}

const VERBS: Record<string, string> = {
  create: "CREATED", create_deal: "CREATED", propose: "PROPOSED", ask: "ASKED", answer: "ANSWERED",
  approve: "APPROVED", reject: "REJECTED", post: "POSTED", hold: "HELD", reverse: "REVERSED",
  tool: "RAN", policy: "POLICY", session: "SESSION", event: "EVENT", fork: "FORK",
};

/** What the gateway's `post` row recorded, in words. Only the approval post puts the books on the record. */
const POSTED: Record<string, string> = {
  map_lines: "Mapping recorded.", prepare_result: "Draft books recorded.", review_result: "Review recorded.",
  flag: "Answer recorded.", approve_result: "Approved and posted to the record.",
};

function isApprovalPost(row: AuditRow, items: WorkItem[]): boolean {
  return items.find((i) => i.id === row.target)?.type === "approve_result";
}

/** Fixed verb list so the log stays scannable. A post of anything but the approval is RECORDED, not POSTED. */
export function verbOf(row: AuditRow, items: WorkItem[] = []): string {
  if (row.result === "DENIED") return "DENIED";
  const verb = row.action.split(":")[0];
  if (verb === "post" && !isApprovalPost(row, items)) return "RECORDED";
  return VERBS[verb] ?? row.action.toUpperCase();
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
  if (verb === "post") {
    if (item?.type.startsWith("reverse:")) return `Reversal recorded. ${row.reason ?? ""}`.trim();
    return POSTED[item?.type ?? ""] ?? `${titleCase(item?.type ?? "item")} recorded.`;
  }
  if (verb === "approve") return `${titleCase(item?.type ?? "item")} approved. ${row.reason ?? ""}`.trim();
  if (verb === "reject") return `${titleCase(item?.type ?? "item")} rejected. ${row.reason ?? ""}`.trim();
  if (verb === "hold") return "Flag held. The controller is not sure.";
  if (verb === "reverse") return `Reversed. ${row.reason ?? ""}`.trim();
  return row.reason ?? row.action;
}
