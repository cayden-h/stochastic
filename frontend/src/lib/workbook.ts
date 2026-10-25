import { anchorKey, num, rowParts } from "./edits.ts";
import { toK } from "./format.ts";
import type { Case, Edit, GlAccount, GlResponse, Mapping, Result, ResultRow, Section, SourceLine, ToolRun } from "./types";

/** The Review workbook (V3-7): the combined books as rows of a sheet. Every figure comes from the case: the result's
 * rows, the source lines, the verdict. The only arithmetic here is the change column, from the edits' own old and new
 * values (rowParts), as on the Case. */

/** One amount cell: the figure on screen, and the source line behind it when it is one editable detail line. */
export interface AmountCell {
  value: number;
  /** The company's own detail line behind the cell. Null for a row that gathers several lines, or a total. */
  source: SourceLine | null;
  edit?: Edit;
}

export interface LineRow {
  kind: "line";
  key: string;
  section: Section;
  line: string;
  bold: boolean;
  platform: AmountCell;
  target: AmountCell;
  combined: number;
  /** The change from the agents' combined value, from the edits' own old and new values. */
  change: number;
  /** The target's one detail line, when the row holds exactly one: its line cell can be remapped. */
  remapLine: SourceLine | null;
  remap?: Edit;
  /** The target's detail lines the Mapper put on this row, when there are several. They show under the row. */
  subs: SubRow[];
}

export interface SubRow {
  kind: "sub";
  key: string;
  parent: string;
  /** The combined row it sits under: the platform line the Mapper put it on. */
  parentLine: string;
  line: SourceLine;
  target: AmountCell;
  remap?: Edit;
}

export interface SectionRow { kind: "section"; key: string; title: string }
export interface CovenantRow { kind: "covenant"; key: string; label: string; value: string; was: string | null; bold: boolean }
/** The detail block under an opened combined row: for each company (platform, then target) the statement lines that
 * feed it, each with its filing facts and its GL accounts. Statement lines are real; GL accounts are simulated. */
export type Side = "platform" | "target";
export interface DetailHead { kind: "dhead"; key: string; parent: string; gl: boolean }
export interface DetailCompany { kind: "dcompany"; key: string; parent: string; side: Side; company: string; count: number; value: number; ties: boolean | null }
export interface DetailLine {
  kind: "dline"; key: string; parent: string; side: Side; line: SourceLine;
  /** The line's figure in USD thousands: its amount edit's new value, else the filing's. */
  value: number; edit?: Edit;
  /** The target line's mapping, for its confidence, reason, and who settled it. */
  mapping: Mapping | null;
  /** The editable sub row, when the combined row gathers several target lines: the line is edited here. */
  sub: SubRow | null;
}
export interface DetailFacts { kind: "dfacts"; key: string; parent: string; side: Side; line: SourceLine; mapping: Mapping | null }
export interface DetailGl { kind: "dgl"; key: string; parent: string; side: Side; gl: GlAccount; value: number; prior: number }
export interface DetailGlTotal { kind: "dgltotal"; key: string; parent: string; side: Side; line: SourceLine; value: number; ties: boolean }
export interface DetailNote { kind: "dnote"; key: string; parent: string; text: string }
export type DetailRow = DetailHead | DetailCompany | DetailLine | DetailFacts | DetailGl | DetailGlTotal | DetailNote;

export type SheetRow = LineRow | SubRow | SectionRow | CovenantRow | DetailRow;

const lower = (s: string | null | undefined) => (s ?? "").trim().toLowerCase();

export const SECTION_TITLES: Record<Section, string> = {
  income_statement: "Income statement",
  balance_sheet: "Balance sheet",
  cash_flow: "Cash flow",
};

/** The order on the sheet. The covenant test sits under the income statement, where the frames put it, so the leverage
 * is on screen without scrolling; the balance sheet and the cash flow follow. */
export const SHEET_ORDER: (Section | "covenant")[] = ["income_statement", "covenant", "balance_sheet", "cash_flow"];

function amountEdit(edits: Edit[], l: SourceLine): Edit | undefined {
  return edits.find((e) => e.kind === "amount" && e.company === l.company && e.line === l.line && e.section === l.section);
}

function remapEdit(edits: Edit[], l: SourceLine): Edit | undefined {
  return edits.find((e) => e.kind === "remap" && e.company === l.company && e.line === l.line && e.section === l.section);
}

/** The combined rows of one section, each with the cells an edit can name. A target line stays under the row the
 * Mapper put it on, even after a remap, so the edited line does not jump away from its bubble; its line cell says
 * where it goes now, and the result's own figures already count it there. */
export function sectionRows(result: Result, kase: Case, edits: Edit[], section: Section): LineRow[] {
  const { deal, source_lines, mappings } = kase;
  const byId = new Map(source_lines.map((l) => [l.id, l]));
  return result.rows.filter((r) => r.section === section).map((r: ResultRow, i) => {
    const parts = rowParts(r, kase, edits);
    const platformLines = source_lines.filter((l) => l.company === deal.platform && l.section === section && lower(l.line) === lower(r.line));
    const total = /^total/i.test(r.line) || platformLines.some((l) => l.is_total);
    // The Mapper's own grouping: the target detail lines it mapped to this row.
    const agents: SourceLine[] = [];
    for (const m of mappings) {
      const l = byId.get(m.target_line_id);
      if (l && l.company === deal.target && l.section === section && !l.is_total && lower(m.platform_line) === lower(r.line)) agents.push(l);
    }
    const key = `${section}|${r.line}|${i}`;
    const single = !total && agents.length === 1 ? agents[0] : null;
    // The target cell is one line's own figure only while the row holds exactly the Mapper's lines. A remap into or out
    // of the row makes the result's target figure a sum of other lines, so the cell is read-only until it is undone.
    const effective = parts.targets;
    const same = effective.length === agents.length && agents.every((a) => effective.some((t) => t.id === a.id));
    const subs: SubRow[] = !total && agents.length > 1
      ? agents.map((l) => {
          const e = amountEdit(edits, l);
          return { kind: "sub", key: `${key}|${l.id}`, parent: key, parentLine: r.line, line: l, target: { value: e?.new_value ?? toK(l.amount, l.unit), source: l, edit: e }, remap: remapEdit(edits, l) };
        })
      : [];
    return {
      kind: "line", key, section, line: r.line, bold: total,
      platform: { value: r.platform, source: parts.platform, edit: parts.platform ? amountEdit(edits, parts.platform) : undefined },
      target: { value: r.target, source: same ? single : null, edit: same && single ? amountEdit(edits, single) : undefined },
      combined: r.combined, change: parts.change,
      remapLine: single, remap: single ? remapEdit(edits, single) : undefined,
      subs,
    };
  });
}

/** The platform's lines a target line can be remapped to: its detail lines in the same section, once each. */
export function remapOptions(kase: Case, section: Section): string[] {
  return [...new Set(kase.source_lines.filter((l) => l.company === kase.deal.platform && l.section === section && !l.is_total).map((l) => l.line))];
}

export function amountAnchor(l: SourceLine): string {
  return anchorKey("amount", l.company, l.section, l.line);
}

export function remapAnchor(l: SourceLine): string {
  return anchorKey("remap", l.company, l.section, l.line);
}

/** The agents' own leverage run: the last `leverage` run before the first live edit. Its figures are the "was" values
 * on the covenant rows, read from the tool run and never worked out here. */
export function agentsLeverageRun(runs: ToolRun[], edits: Edit[]): ToolRun | null {
  if (!edits.length) return null;
  const first = [...edits].sort((a, b) => a.at.localeCompare(b.at))[0].at;
  const before = runs.filter((r) => r.tool === "leverage" && r.at < first).sort((a, b) => a.at.localeCompare(b.at));
  return before[before.length - 1] ?? null;
}

/** "was 0.76x" when the agents' figure reads differently from the one on screen, else null. */
export function was(now: string, then: string | null): string | null {
  return then !== null && then !== now ? `was ${then}` : null;
}

/** A cell reference such as C8, from the column letter and the sheet row number. */
export function cellRef(col: string, row: number): string {
  return `${col}${row}`;
}

/** The formula bar's value for an amount: the plain number, as a spreadsheet shows it (5663, -5938). */
export function rawAmount(v: number): string {
  return String(Math.round(v));
}

/** The formula bar's note for an amount cell. */
export function amountNote(cell: AmountCell, company: string): string {
  const e = cell.edit;
  if (!e) return `The agents read ${num(cell.value)} from the ${company} statements.`;
  const old = num(e.old_value ?? cell.value);
  if (e.status === "needs_reason") return `Edited by controller. The agents read ${old} from the ${company} statements.`;
  const learned = e.policy_id ?? e.adjustment_id;
  return `Edited by controller. Was ${old}. Reason: ${(e.reason_text ?? "").replace(/[.\s]+$/, "")}.${learned ? ` ${learned}` : ""}`;
}

/** The formula bar's note for a target line cell. */
export function lineNote(line: SourceLine, remap: Edit | undefined, platform: string): string {
  if (!remap) return `${line.company} line. Pick the ${platform} line it maps to.`;
  const from = remap.old_platform_line ?? "no line";
  if (remap.status === "needs_reason") return `Remapped by controller. The agents mapped it to ${from}.`;
  const learned = remap.policy_id ?? remap.adjustment_id;
  return `Remapped by controller. Was ${from}. Reason: ${(remap.reason_text ?? "").replace(/[.\s]+$/, "")}.${learned ? ` ${learned}` : ""}`;
}

/** The detail block of one combined row (see DetailRow). GL rows show only when `gl` is given; a subtotal row has no GL
 * and says so. The only arithmetic is the GL tie-out check, a sum of the simulated accounts against the filed line. */
export function detailRows(row: LineRow, kase: Case, gl: GlResponse | null, edits: Edit[]): DetailRow[] {
  const { deal, source_lines, mappings } = kase;
  const parent = row.key;
  const byLine = new Map(mappings.map((m) => [m.target_line_id, m]));
  const subs = new Map(row.subs.map((s) => [s.line.id, s]));
  const platform = source_lines.filter((l) => l.company === deal.platform && l.section === row.section && lower(l.line) === lower(row.line));
  // A target subtotal the Mapper sent to a detail line (Total Operating Expense to Operating expenses) is not added
  // again in consolidation, so it is not listed as a source of a detail row either.
  const target = source_lines.filter((l) => {
    if (l.company !== deal.target || l.section !== row.section || (l.is_total && !row.bold)) return false;
    const m = byLine.get(l.id);
    return Boolean(m) && lower(m!.platform_line) === lower(row.line);
  });
  const out: DetailRow[] = [{ kind: "dhead", key: `${parent}|dhead`, parent, gl: Boolean(gl) && !row.bold }];
  const group = (side: Side, company: string, lines: SourceLine[], total: number) => {
    const accounts = lines.map((l) => gl?.lines[l.id] ?? []);
    const allTie = gl && !row.bold ? lines.every((l, i) => !accounts[i].length || glTies(accounts[i], l.amount)) : null;
    out.push({ kind: "dcompany", key: `${parent}|${side}`, parent, side, company, count: lines.length, value: total, ties: allTie });
    if (!lines.length) {
      out.push({ kind: "dnote", key: `${parent}|${side}|none`, parent, text: `No ${company} line feeds this row.` });
      return;
    }
    lines.forEach((l, i) => {
      const e = amountEdit(edits, l);
      out.push({ kind: "dline", key: `${parent}|${l.id}`, parent, side, line: l, value: e?.new_value ?? toK(l.amount, l.unit), edit: e, mapping: byLine.get(l.id) ?? null, sub: subs.get(l.id) ?? null });
      out.push({ kind: "dfacts", key: `${parent}|${l.id}|facts`, parent, side, line: l, mapping: byLine.get(l.id) ?? null });
      if (!gl || l.is_total) return;
      for (const g of accounts[i]) {
        out.push({ kind: "dgl", key: `${parent}|${l.id}|${g.account}`, parent, side, gl: g, value: toK(g.amount, l.unit), prior: toK(g.prior, l.unit) });
      }
      if (accounts[i].length) {
        const sum = accounts[i].reduce((a, g) => a + g.amount, 0);
        out.push({ kind: "dgltotal", key: `${parent}|${l.id}|total`, parent, side, line: l, value: toK(sum, l.unit), ties: glTies(accounts[i], l.amount) });
      }
    });
  };
  group("platform", deal.platform, platform, row.platform.value);
  group("target", deal.target, target, row.target.value);
  if (row.bold) out.push({ kind: "dnote", key: `${parent}|subtotal`, parent, text: "A subtotal: code adds the lines above it, so it has no GL accounts of its own." });
  return out;
}

/** The simulated GL accounts add up to the filed line, to half a unit of the filing. */
export function glTies(accounts: GlAccount[], amount: number): boolean {
  return Math.abs(accounts.reduce((a, g) => a + g.amount, 0) - amount) <= 0.5;
}
