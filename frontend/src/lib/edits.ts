import { toK } from "./format.ts";
import type { Case, Edit, Mapping, ReasonChip, Result, ResultRow, Section, SourceLine, WorkItem } from "./types";

/** The DOM key of an editable cell, so the companion, Your edits, and the flash can find it.
 * Amount cells use the company's own source line; remap cells use the target line on the Mapping page. */
export function anchorKey(kind: Edit["kind"], company: string, section: string, line: string): string {
  return `${kind}|${company}|${section}|${line}`;
}

export function editAnchor(e: Pick<Edit, "kind" | "company" | "section" | "line">): string {
  return anchorKey(e.kind, e.company, e.section, e.line);
}

export function findAnchor(key: string): HTMLElement | null {
  if (typeof document === "undefined") return null;
  return document.querySelector<HTMLElement>(`[data-edit-anchor="${CSS.escape(key)}"]`);
}

/** The edits that still count: not reverted. */
export function liveEdits(kase: Case | null): Edit[] {
  return (kase?.edits ?? []).filter((e) => e.status !== "reverted");
}

/** The edit that is still waiting longest for its reason. */
export function oldestUnreasoned(edits: Edit[]): Edit | null {
  return edits.filter((e) => e.status === "needs_reason").sort((a, b) => a.at.localeCompare(b.at))[0] ?? null;
}

/** USD thousands as the combined table writes them: 9,812, and (500) for a negative. */
export function num(v: number): string {
  const r = Math.round(v);
  return r < 0 ? `(${Math.abs(r).toLocaleString("en-US")})` : r.toLocaleString("en-US");
}

/** A signed change: +500, or (500). */
export function signed(v: number): string {
  const r = Math.round(v);
  return r < 0 ? `(${Math.abs(r).toLocaleString("en-US")})` : `+${r.toLocaleString("en-US")}`;
}

/** Parse what the controller typed, in USD thousands. Commas and spaces are fine; parentheses or a minus make it
 * negative. Anything else is refused, so a stray letter never becomes a number. */
export function parseAmount(text: string): number | null {
  let t = text.trim().replace(/[,\s]/g, "");
  let neg = false;
  const paren = t.match(/^\((.*)\)$/);
  if (paren) { neg = true; t = paren[1]; }
  if (t.startsWith("-")) { if (neg) return null; neg = true; t = t.slice(1); }
  if (!/^\d+(\.\d+)?$|^\.\d+$/.test(t)) return null;
  const v = Number(t);
  return Number.isFinite(v) ? (neg ? -v : v) : null;
}

/** More than half the agents' value: the bubble asks before the edit is saved. */
export function isLargeChange(old: number, next: number): boolean {
  if (old === 0) return next !== 0;
  return Math.abs(next - old) > Math.abs(old) * 0.5;
}

/** The chips the gateway gave for the last edit of each kind. Before any edit this session (a reload with an edit that
 * still needs its reason), the demo deal's list from backend/app/agents/backends/scripted.py stands in. */
export const DEMO_CHIPS: Record<Edit["kind"], ReasonChip[]> = {
  amount: [
    { id: 0, label: "One-time acquisition cost, an allowed add-back" },
    { id: 1, label: "Auditor's late adjustment" },
    { id: 2, label: "Correcting a typo in the source" },
  ],
  remap: [
    { id: 0, label: "Not a cash equivalent (over 90 days)" },
    { id: 1, label: "Matches how the platform reports it" },
    { id: 2, label: "Auditor's reclassification" },
  ],
};

/** The one-line note after Save: "Learned: allowed add-back, for the next add-on." */
export function learnedNote(kind: Edit["kind"], reason: string, remember: boolean): string {
  if (!remember) return "Reason saved.";
  if (kind === "remap") return "Learned: mapping rule, for this platform.";
  let short = reason.includes(", ") ? reason.slice(reason.lastIndexOf(", ") + 2) : reason;
  short = short.replace(/^(an?|the)\s+/i, "").replace(/[.\s]+$/, "");
  if (short.length > 48) short = `${short.slice(0, 45).trimEnd()}...`;
  return `Learned: ${short.charAt(0).toLowerCase()}${short.slice(1)}, for the next add-on.`;
}

/** The approval item an edit may change: PROPOSED, or NEEDS_INFO when an edit's recompute failed a check. Mirrors the
 * gateway's `_live_approval`, so a cell is only editable when the gateway would take the edit. */
export function canEdit(kase: Case): boolean {
  const id = kase.verdict?.approval_item;
  const item = kase.work_items.find((w) => w.id === id);
  if (!item || kase.verdict?.posted) return false;
  return item.state === "PROPOSED" || (item.state === "NEEDS_INFO" && Boolean(item.payload.edit_id));
}

const lower = (s: string | null | undefined) => (s ?? "").trim().toLowerCase();

/** The platform line a target line lands on now: the live remap edit's new line, else the Mapper's. A remap does not
 * change the Mapping record; the edit carries the new platform line. */
export function effectivePlatformLine(m: Mapping, line: SourceLine | undefined, edits: Edit[]): string | null {
  const remap = line && edits.find((e) => e.kind === "remap" && e.company === line.company && e.line === line.line && e.section === line.section);
  return remap?.new_platform_line ?? m.platform_line;
}

/** A line's value as the agents used it, in USD thousands. */
function agentValue(l: SourceLine): number {
  return toK(l.amount, l.unit);
}

export interface RowParts {
  /** The platform's own line behind the row, when it is one editable detail line. */
  platform: SourceLine | null;
  /** The target's detail lines that land on this row now. Totals are never edited. */
  targets: SourceLine[];
  /** The change from the agents' combined value, from the edits' own old and new values. */
  change: number;
}

/** What feeds one combined row, so the table can edit the right source line. The combined row is a platform line that
 * can gather several target lines (Operating expenses holds Selling, G&A, R&D), and an edit names one of them. */
export function rowParts(row: ResultRow, kase: Case, edits: Edit[]): RowParts {
  const { deal, source_lines, mappings } = kase;
  const total = /^total/i.test(row.line);
  const platformLines = source_lines.filter((l) => l.company === deal.platform && l.section === row.section && lower(l.line) === lower(row.line));
  const platform = !total && platformLines.length === 1 && !platformLines[0].is_total ? platformLines[0] : null;
  const byId = new Map(source_lines.map((l) => [l.id, l]));
  const targets: SourceLine[] = [];
  let change = 0;
  for (const m of mappings) {
    const l = byId.get(m.target_line_id);
    if (!l || l.company !== deal.target || l.section !== row.section || l.is_total) continue;
    const now = effectivePlatformLine(m, l, edits);
    if (lower(now) === lower(row.line)) targets.push(l);
    // A remap moves the line's agent value from its old row to its new one; an amount edit on it counts below.
    const remap = edits.find((e) => e.kind === "remap" && e.company === l.company && e.line === l.line && e.section === l.section);
    if (remap) {
      if (lower(remap.new_platform_line) === lower(row.line)) change += agentValue(l);
      if (lower(remap.old_platform_line) === lower(row.line)) change -= agentValue(l);
    }
  }
  for (const e of edits) {
    if (e.kind !== "amount" || e.section !== row.section || e.old_value == null || e.new_value == null) continue;
    const feeds = (platform && e.company === platform.company && e.line === platform.line)
      || targets.some((t) => t.company === e.company && t.line === e.line);
    if (feeds) change += e.new_value - e.old_value;
  }
  return { platform, targets: total ? [] : targets, change };
}

/** The section the table opens on: the newest live edit's, so the edit stays in view. */
export function editedSection(result: Result, edits: Edit[]): Section | null {
  const newest = [...edits].sort((a, b) => b.at.localeCompare(a.at))[0];
  if (!newest) return null;
  return result.rows.some((r) => r.section === newest.section) ? newest.section : null;
}

export function isAdjustmentFlag(f: WorkItem): boolean {
  return f.payload.kind === "adjustment";
}
