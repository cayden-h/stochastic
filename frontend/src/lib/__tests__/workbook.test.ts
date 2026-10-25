// Run with `npm run test:lib` (node --test; Node strips the types).
import assert from "node:assert/strict";
import { test } from "node:test";
import type { Case, Edit, Mapping, SourceLine, ToolRun } from "../types";
import { agentsLeverageRun, amountNote, lineNote, remapOptions, sectionRows, was } from "../workbook.ts";

const S = "income_statement" as const;
function line(id: string, company: string, name: string, amount: number, is_total = false): SourceLine {
  return { id, company, line: name, section: S, period: "FY2024", amount, unit: "USD thousands", source_ref: "", is_total, note: null, covenant_tag: "na", covenant_note: null };
}
function mapping(target: SourceLine, platform: string): Mapping {
  return { id: `m_${target.id}`, target_line_id: target.id, platform_line_id: null, target_line: target.line, platform_line: platform, confidence: 0.9, reason: "", flagged: false, approved_by: null };
}
function edit(over: Partial<Edit>): Edit {
  return {
    id: "e_001", deal_id: "d", kind: "amount", company: "Nu Aire", line: "General and Administrative", section: S,
    old_value: 6163, new_value: 5663, old_platform_line: null, new_platform_line: null, status: "needs_reason",
    reason_chip: null, reason_text: null, remember: true, policy_id: null, adjustment_id: null, actor: "human:controller",
    at: "2026-10-25T02:00:00Z", run_ids: [], ...over,
  };
}

const platform = [line("p1", "Kewaunee", "Net sales", 203755), line("p2", "Kewaunee", "Operating expenses", 33770), line("p3", "Kewaunee", "Cost of products sold", 151704), line("p4", "Kewaunee", "Gross profit", 52051, true)];
const target = [line("t1", "Nu Aire", "Net Revenues", 74850), line("t2", "Nu Aire", "Selling Expense", 11738), line("t3", "Nu Aire", "General and Administrative", 6163), line("t4", "Nu Aire", "Research and Development", 532), line("t5", "Nu Aire", "Cost of Revenues", 51169)];
const kase = {
  deal: { id: "d", name: "", platform: "Kewaunee", target: "Nu Aire", stage: "awaiting_approval", brief: null },
  source_lines: [...platform, ...target],
  mappings: [mapping(target[0], "Net sales"), mapping(target[1], "Operating expenses"), mapping(target[2], "Operating expenses"), mapping(target[3], "Operating expenses"), mapping(target[4], "Cost of products sold")],
  result: {
    id: "r", rows: [
      { line: "Net sales", section: S, platform: 203755, target: 74850, combined: 278605, run_id: "run_013" },
      { line: "Cost of products sold", section: S, platform: 151704, target: 51169, combined: 202873, run_id: "run_013" },
      { line: "Gross profit", section: S, platform: 52051, target: 23682, combined: 75733, run_id: "run_013" },
      { line: "Operating expenses", section: S, platform: 33770, target: 18433, combined: 52203, run_id: "run_013" },
    ],
  },
} as unknown as Case;

test("a row that gathers several target lines shows them under it, each with its own editable cell", () => {
  const rows = sectionRows(kase.result!, kase, [], S);
  const opex = rows.find((r) => r.line === "Operating expenses")!;
  assert.deepEqual(opex.subs.map((s) => s.line.line), ["Selling Expense", "General and Administrative", "Research and Development"]);
  assert.equal(opex.target.source, null, "the aggregate target cell is read-only");
  assert.equal(opex.platform.source?.line, "Operating expenses");
  assert.equal(opex.subs[1].target.value, 6163);
  const sales = rows.find((r) => r.line === "Net sales")!;
  assert.equal(sales.target.source?.line, "Net Revenues", "one target line: the row's target cell edits it");
  assert.equal(sales.remapLine?.line, "Net Revenues");
  assert.equal(rows.find((r) => r.line === "Gross profit")!.bold, true);
});

test("an amount edit shows on its cell and in the change column, from the edit's own values", () => {
  const e = edit({});
  const rows = sectionRows(kase.result!, kase, [e], S);
  const opex = rows.find((r) => r.line === "Operating expenses")!;
  assert.equal(opex.subs[1].target.edit?.id, "e_001");
  assert.equal(opex.subs[1].target.value, 5663);
  assert.equal(opex.change, -500);
});

test("a remapped line stays under the Mapper's row, and the rows it left and joined show the change", () => {
  const e = edit({ kind: "remap", line: "Research and Development", old_value: null, new_value: null, old_platform_line: "Operating expenses", new_platform_line: "Cost of products sold" });
  const rows = sectionRows(kase.result!, kase, [e], S);
  const opex = rows.find((r) => r.line === "Operating expenses")!;
  assert.equal(opex.subs[2].remap?.new_platform_line, "Cost of products sold");
  assert.equal(opex.change, -532);
  const cogs = rows.find((r) => r.line === "Cost of products sold")!;
  assert.equal(cogs.change, 532);
  assert.equal(cogs.target.source, null, "a line remapped into the row makes its target figure a sum: read-only");
});

test("the remap menu offers the platform's detail lines in the section, totals left out", () => {
  assert.deepEqual(remapOptions(kase, S), ["Net sales", "Operating expenses", "Cost of products sold"]);
});

test("the agents' leverage run is the last one before the first live edit", () => {
  const run = (id: string, at: string, leverage: number): ToolRun => ({ run_id: id, deal_id: "d", tool: "leverage", actor: "", inputs: {}, outputs: { leverage }, at });
  const runs = [run("run_016", "2026-10-25T01:56:14Z", 0.762), run("run_030", "2026-10-25T02:00:01Z", 0.745)];
  assert.equal(agentsLeverageRun(runs, [edit({})])?.run_id, "run_016");
  assert.equal(agentsLeverageRun(runs, []), null);
  assert.equal(was("0.75×", "0.76×"), "was 0.76×");
  assert.equal(was("21,633", "21,633"), null);
});

test("the formula bar says who changed a cell, what the agents read, and why", () => {
  const cell = { value: 5663, source: target[2], edit: edit({}) };
  assert.equal(amountNote({ value: 6163, source: target[2] }, "Nu Aire"), "The agents read 6,163 from the Nu Aire statements.");
  assert.equal(amountNote(cell, "Nu Aire"), "Edited by controller. The agents read 6,163 from the Nu Aire statements.");
  const done = { ...cell, edit: edit({ status: "reasoned", reason_text: "One-time acquisition cost, an allowed add-back", adjustment_id: "a_001" }) };
  assert.equal(amountNote(done, "Nu Aire"), "Edited by controller. Was 6,163. Reason: One-time acquisition cost, an allowed add-back. a_001");
  assert.equal(lineNote(target[3], undefined, "Kewaunee"), "Nu Aire line. Pick the Kewaunee line it maps to.");
  const remap = edit({ kind: "remap", old_platform_line: "Operating expenses", new_platform_line: "Cost of products sold" });
  assert.equal(lineNote(target[3], remap, "Kewaunee"), "Remapped by controller. The agents mapped it to Operating expenses.");
});
