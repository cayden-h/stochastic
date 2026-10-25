// Run with `npm run test:lib` (node --test; Node strips the types).
import assert from "node:assert/strict";
import { test } from "node:test";
import type { Result, ToolRun } from "../types.ts";
import { type MathReport, mathReport } from "../math-check.ts";

// The scripted demo deal (d_kequ_nuaire), runs 097-102, with the consolidate rows trimmed to a handful.
const D = "d_kequ_nuaire";
function run(run_id: string, tool: string, actor: string, inputs: Record<string, unknown>, outputs: Record<string, unknown>): ToolRun {
  return { run_id, deal_id: D, tool, actor, inputs, outputs, at: "2026-10-25T15:33:40Z" };
}
const BS = "balance_sheet";
const RUNS: ToolRun[] = [
  run("run_097", "consolidate", "agent:preparer", {}, {
    unit: "USD thousands",
    rows: [
      { line: "Cash and cash equivalents", section: BS, platform: 25963.0, target: 14447.056, is_total: false, combined: 40410.056 },
      { line: "Restricted cash", section: BS, platform: 3701.0, target: 0.0, is_total: false, combined: 3701.0 },
      { line: "Receivables, less allowance", section: BS, platform: 41885.0, target: 10560.193, is_total: false, combined: 52445.193 },
      { line: "Inventories", section: BS, platform: 18659.0, target: 12559.018, is_total: false, combined: 31218.018 },
      { line: "Total Assets", section: BS, platform: 134478.0, target: 47978.181, is_total: true, combined: 182456.181 },
      { line: "Total Liabilities and Stockholders' Equity", section: BS, platform: 134478.0, target: 47978.181, is_total: true, combined: 182456.181 },
    ],
  }),
  run("run_098", "ebitda", "agent:preparer", { as_filed: false }, {
    ebitda: 28378.845, base: 25311.845, addbacks_total: 5037.0, deductions_total: 1970.0,
    parts: [
      { company: "platform", net_income: 19057.0, interest_expense: 1799.0, interest_income: 0.0, income_taxes: -5938.0, depreciation_amortization: 3125.0, subtotal: 18043.0 },
      { company: "target", net_income: 5438.271, interest_expense: 0.0, interest_income: 513.77, income_taxes: 513.949, depreciation_amortization: 1830.395, subtotal: 7268.845 },
    ],
    addbacks: [
      { name: "Noncash pension termination expense", amount: 4019.0, cap: null, applied: 4019.0, inferred: false },
      { name: "Stock-based compensation", amount: 1018.0, cap: null, applied: 1018.0, inferred: false },
      { name: "Transaction costs (capped)", amount: 0.0, cap: 4000.0, applied: 0.0, inferred: true },
      { name: "Integration costs (capped)", amount: 0.0, cap: 1000.0, applied: 0.0, inferred: true },
    ],
    deductions: [{ name: "Cash rent on the Statesville property", amount: 1970.0, inferred: true }],
    basis: "covenant", unit: "USD thousands",
  }),
  run("run_099", "covenant_debt", "agent:preparer", { naive: false }, {
    debt: 21633.0, term: "Senior Funded Bank Debt", unit: "USD thousands",
    included: [
      { line: "Short-term borrowings", company: "Kewaunee", amount: 805.0 },
      { line: "Current portion of financing lease liabilities", company: "Kewaunee", amount: 109.0 },
      { line: "Financing liability: PNC Revolving Credit Facility", company: "Kewaunee", amount: 5563.0 },
      { line: "Financing liability: PNC Term Loan", company: "Kewaunee", amount: 15000.0 },
      { line: "Long-term portion of financing lease liabilities", company: "Kewaunee", amount: 156.0 },
    ],
    excluded: [
      { line: "Current portion of financing liability", company: "Kewaunee", amount: 750.0, note: "decided by human:controller on flag wi_029" },
      { line: "Long-term portion of financing liability", company: "Kewaunee", amount: 27032.0, note: "decided by human:controller on flag wi_029" },
      { line: "Financing liability: 8% Seller Notes (subordinated)", company: "Kewaunee", amount: 22540.0, note: "decided by human:controller on flag wi_029" },
    ],
  }),
  run("run_100", "leverage", "agent:preparer", { debt_run_id: "run_099", ebitda_run_id: "run_098" }, { leverage: 0.762, debt: 21633.0, ebitda: 28378.845 }),
  run("run_101", "tie_out", "agent:reviewer", { run_id: "run_097" }, {
    ok: true, bad_rows: [], balance_sheet_balances: true, rows_checked: 54, missing_totals: [],
    balance: { total_assets: 182456.181, total_liabilities_and_equity: 182456.181 },
  }),
  run("run_102", "limit_test", "agent:reviewer", { leverage_run_id: "run_100" }, {
    ok: true, verdict: "ok", leverage: 0.762, limit: 2.5, headroom_turns: 1.738, wording: "less than", debt_capacity: 49314.113,
  }),
];
const RESULT = {
  id: "r", rows: [], ebitda: 28378.845, debt: 21633.0, leverage: 0.762, limit: 2.5, verdict: "ok", headroom_turns: 1.738, tie_out_ok: true,
  review: { verdict: "pass", reasons: [], run_ids: ["run_101", "run_102"] },
  run_ids: ["run_097", "run_098", "run_099", "run_100"],
  run_ids_by_tool: { consolidate: "run_097", ebitda: "run_098", covenant_debt: "run_099", leverage: "run_100" },
  backend: "scripted",
} as unknown as Result;
const CTX = { platform: "Kewaunee", target: "Nu Aire", debtTerm: "Senior Funded Bank Debt" };

/** A copy of the runs with one run's outputs changed. The outputs are plain JSON, so a test reaches into them freely. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function tamper(id: string, change: (o: Record<string, any>) => void): ToolRun[] {
  const runs = structuredClone(RUNS);
  change(runs.find((r) => r.run_id === id)!.outputs);
  return runs;
}
const step = (r: MathReport, key: string) => r.steps.find((s) => s.key === key)!;
const failed = (r: MathReport) => r.steps.flatMap((s) => (s.run ? s.checks : [])).filter((c) => !c.ok).map((c) => c.label);

test("the real chain passes every check", () => {
  const r = mathReport(RESULT, RUNS, CTX);
  assert.deepEqual(r.missing, []);
  assert.deepEqual(failed(r), []);
  assert.equal(r.passed, r.total);
  // 2 bases + 2 non-empty add-backs + base + covenant EBITDA, debt, 3 leverage, 3 limit, 2 tie-out.
  assert.equal(r.total, 15);
  assert.deepEqual(r.steps.map((s) => s.key), ["ebitda", "debt", "leverage", "limit", "tie_out"]);
  assert.equal(step(r, "leverage").total, "0.76×");
  assert.equal(step(r, "ebitda").total, "28,379");
  assert.equal(step(r, "debt").title, "Senior Funded Bank Debt");
  assert.equal(step(r, "debt").total, "21,633");
  assert.equal(step(r, "debt").excluded?.length, 3);
  assert.equal(step(r, "limit").total, "0.76× is less than 2.50×: under the limit");
  assert.equal(step(r, "tie_out").total, "Ties out");
  // The empty capped add-backs are left out of the terms; the companies are named.
  const labels = step(r, "ebitda").terms.map((t) => t.label);
  assert.ok(labels.includes("Kewaunee base EBITDA") && labels.includes("Nu Aire base EBITDA"));
  assert.ok(!labels.some((l) => l.includes("capped")));
});

test("an EBITDA total off by 1,000 fails the Covenant EBITDA check", () => {
  const r = mathReport(RESULT, tamper("run_098", (o) => { o.ebitda += 1000; }), CTX);
  assert.ok(failed(r).includes("Covenant EBITDA"));
  assert.ok(r.passed < r.total);
});

test("a leverage that is not debt / EBITDA fails", () => {
  const r = mathReport(RESULT, tamper("run_100", (o) => { o.leverage = 0.9; }), CTX);
  assert.ok(failed(r).includes("21,633 / 28,379"));
  assert.ok(r.passed < r.total);
});

test("a combined row that is not platform + target fails the tie-out", () => {
  const r = mathReport(RESULT, tamper("run_097", (o) => { o.rows[2].combined += 10; }), CTX);
  const tie = step(r, "tie_out").checks[0];
  assert.equal(tie.ok, false);
  assert.equal(tie.reported, 5);
  assert.equal(tie.recomputed, 6);
  assert.deepEqual(failed(r), [tie.label]);
});

test("a missing run shows in missing and its checks are not counted", () => {
  const r = mathReport(RESULT, RUNS.filter((x) => x.tool !== "limit_test"), CTX);
  assert.deepEqual(r.missing, ["Limit test"]);
  assert.equal(step(r, "limit").run, null);
  assert.equal(r.total, 12);
  assert.equal(r.passed, 12);
});

test("a capped add-back applied above its cap fails", () => {
  const r = mathReport(RESULT, tamper("run_098", (o) => {
    o.addbacks[2].amount = 5000; o.addbacks[2].applied = 5000; // cap is 4,000
    o.ebitda += 5000; // the total agrees with its own parts, so the EBITDA sum check passes
  }), CTX);
  const f = failed(r);
  assert.ok(f.includes("Transaction costs (capped), cap applied"));
  assert.ok(!f.includes("Covenant EBITDA"));
  const term = step(r, "ebitda").terms.find((t) => t.label === "Transaction costs (capped)");
  assert.equal(term?.note, "5,000, capped at 4,000");
});
