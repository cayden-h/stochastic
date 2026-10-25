// The Review page's "Check the math": how code got each covenant figure, from the tool runs the result names, and an
// independent re-check of that arithmetic in the browser. The gateway's tools do the math; this file only re-adds the
// parts each run reports and compares them with the totals it reports. It never makes a number of its own.
import type { Result, ToolRun } from "./types.ts";

/** One re-check: a figure the run reports against the same figure re-added here from the run's own parts. */
export interface Check { label: string; reported: number; recomputed: number; ok: boolean }

/** One term of a sum as the panel shows it: "+ Net earnings 19,057". */
export interface Term { label: string; amount: number; sign: 1 | -1; note?: string }

/** One step of the chain, in the order code ran it. */
export interface Step {
  key: "ebitda" | "debt" | "leverage" | "limit" | "tie_out";
  title: string;
  /** What the step does, in one line. */
  how: string;
  run: ToolRun | null;
  terms: Term[];
  /** The step's result, already formatted. */
  total: string;
  /** Lines the step left out on purpose, with why. */
  excluded?: Term[];
  checks: Check[];
}

export interface MathReport { steps: Step[]; passed: number; total: number; missing: string[] }

// Amounts are USD thousands to 3 decimals; a ratio is rounded to 3. Within half a thousand dollars, or 0.001x, it matches.
const AMOUNT_TOL = 0.5;
const RATIO_TOL = 0.0015;

type Num = number | null | undefined;
const n = (v: unknown): number => (typeof v === "number" && Number.isFinite(v) ? v : 0);
const check = (label: string, reported: Num, recomputed: number, tol = AMOUNT_TOL): Check => ({
  label, reported: n(reported), recomputed, ok: typeof reported === "number" && Math.abs(reported - recomputed) <= tol,
});
const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);
const k = (v: number) => {
  const r = Math.round(v);
  return r < 0 ? `(${Math.abs(r).toLocaleString("en-US")})` : r.toLocaleString("en-US");
};
const x = (v: number) => `${v.toFixed(2)}×`;

interface EbitdaPart {
  company: string; net_income: number; interest_expense: number; interest_income: number; income_taxes: number;
  depreciation_amortization: number; subtotal: number;
}
interface Addback { name: string; amount: number; cap: number | null; applied: number; inferred?: boolean }
interface Deduction { name: string; amount: number; inferred?: boolean }
interface DebtLine { line: string; company: string; amount: number; note?: string }
interface Row { line: string; section: string; platform: number; target: number; combined: number }

/** The newest run of `tool` among `ids`, or null. */
function among(runs: Map<string, ToolRun>, ids: string[], tool: string): ToolRun | null {
  const hits = ids.map((id) => runs.get(id)).filter((r): r is ToolRun => r?.tool === tool);
  return hits[hits.length - 1] ?? null;
}

function ebitdaStep(run: ToolRun | null, names: { platform: string; target: string }): Step {
  const o = (run?.outputs ?? {}) as { ebitda?: number; base?: number; parts?: EbitdaPart[]; addbacks?: Addback[]; deductions?: Deduction[] };
  const parts = o.parts ?? [];
  const addbacks = o.addbacks ?? [];
  const deductions = o.deductions ?? [];
  const terms: Term[] = [];
  const checks: Check[] = [];
  for (const p of parts) {
    const who = p.company === "target" ? names.target : p.company === "platform" ? names.platform : p.company;
    const sub = n(p.net_income) + n(p.interest_expense) - n(p.interest_income) + n(p.income_taxes) + n(p.depreciation_amortization);
    terms.push({
      label: `${who} base EBITDA`, amount: n(p.subtotal), sign: 1,
      note: `net income ${k(p.net_income)} + interest ${k(p.interest_expense)} - interest income ${k(p.interest_income)} + taxes ${k(p.income_taxes)} + D&A ${k(p.depreciation_amortization)}`,
    });
    checks.push(check(`${who} base EBITDA`, p.subtotal, sub));
  }
  for (const a of addbacks) {
    const applied = a.cap != null ? Math.min(n(a.amount), a.cap) : n(a.amount);
    if (!applied && !n(a.applied)) continue; // a capped add-back with nothing in it is not part of the sum
    terms.push({ label: a.name, amount: n(a.applied), sign: 1, note: a.cap != null ? `${k(a.amount)}, capped at ${k(a.cap)}` : "add-back" });
    checks.push(check(`${a.name}, cap applied`, a.applied, applied));
  }
  for (const d of deductions) {
    if (!n(d.amount)) continue;
    terms.push({ label: d.name, amount: n(d.amount), sign: -1, note: "deduction" });
  }
  const base = sum(parts.map((p) => n(p.subtotal)));
  const recomputed = base + sum(addbacks.map((a) => n(a.applied))) - sum(deductions.map((d) => n(d.amount)));
  if (parts.length) checks.push(check("Base EBITDA", o.base, base));
  checks.push(check("Covenant EBITDA", o.ebitda, recomputed));
  return {
    key: "ebitda", title: "Covenant EBITDA",
    how: "Each company's base, net income + interest - interest income + taxes + D&A, then the agreement's add-backs up to their caps, less its deductions.",
    run, terms, total: k(n(o.ebitda)), checks,
  };
}

function debtStep(run: ToolRun | null, term: string): Step {
  const o = (run?.outputs ?? {}) as { debt?: number; included?: DebtLine[]; excluded?: DebtLine[] };
  const included = o.included ?? [];
  const excluded = o.excluded ?? [];
  return {
    key: "debt", title: term || "Debt",
    how: "The balance sheet lines tagged as covenant debt are added. Lines the covenant leaves out are listed, not counted.",
    run,
    terms: included.map((l) => ({ label: `${l.line}`, amount: n(l.amount), sign: 1 as const, note: l.company })),
    excluded: excluded.map((l) => ({ label: l.line, amount: n(l.amount), sign: 1 as const, note: l.note || l.company })),
    total: k(n(o.debt)),
    checks: [check(term || "Debt", o.debt, sum(included.map((l) => n(l.amount))))],
  };
}

function leverageStep(run: ToolRun | null, ebitda: Step, debt: Step): Step {
  const o = (run?.outputs ?? {}) as { leverage?: number; debt?: number; ebitda?: number };
  const d = n(o.debt);
  const e = n(o.ebitda);
  const lev = e > 0 ? d / e : 0;
  // The leverage run must divide the very figures the two runs above report, not other ones.
  const ebitdaRun = ebitda.run?.outputs as { ebitda?: number } | undefined;
  const debtRun = debt.run?.outputs as { debt?: number } | undefined;
  return {
    key: "leverage", title: "Leverage",
    how: "Debt divided by covenant EBITDA.",
    run,
    terms: [
      { label: debt.title, amount: d, sign: 1 },
      { label: "Covenant EBITDA", amount: e, sign: 1, note: "divided by" },
    ],
    total: x(n(o.leverage)),
    checks: [
      check("Uses the debt above", o.debt, n(debtRun?.debt)),
      check("Uses the EBITDA above", o.ebitda, n(ebitdaRun?.ebitda)),
      check(`${k(d)} / ${k(e)}`, o.leverage, lev, RATIO_TOL),
    ],
  };
}

function limitStep(run: ToolRun | null, leverage: Step, limit: number): Step {
  const o = (run?.outputs ?? {}) as { ok?: boolean; leverage?: number; limit?: number; wording?: string; headroom_turns?: number };
  const lev = n((leverage.run?.outputs as { leverage?: number } | undefined)?.leverage);
  const lim = o.limit ?? limit;
  const wording = o.wording ?? "less than";
  const passes = wording === "less than" ? lev < lim : lev <= lim;
  return {
    key: "limit", title: "Limit test",
    how: `The covenant reads "${wording}" ${x(lim)}.`,
    run,
    terms: [],
    total: passes ? `${x(lev)} is ${wording} ${x(lim)}: under the limit` : `${x(lev)} is not ${wording} ${x(lim)}: over the limit`,
    checks: [
      check("Tests the leverage above", o.leverage, lev, RATIO_TOL),
      check("Headroom", o.headroom_turns, lim - lev, RATIO_TOL),
      { label: "Pass or fail", reported: o.ok ? 1 : 0, recomputed: passes ? 1 : 0, ok: o.ok === passes },
    ],
  };
}

function tieOutStep(run: ToolRun | null, consolidate: ToolRun | null): Step {
  const o = (run?.outputs ?? {}) as { ok?: boolean; rows_checked?: number; balance?: { total_assets: number; total_liabilities_and_equity: number } | null };
  const rows = ((consolidate?.outputs as { rows?: Row[] } | undefined)?.rows ?? []);
  const bad = rows.filter((r) => Math.abs(n(r.platform) + n(r.target) - n(r.combined)) > AMOUNT_TOL);
  const checks: Check[] = [
    { label: `Every combined row is platform + target (${rows.length} rows)`, reported: rows.length - bad.length, recomputed: rows.length, ok: rows.length > 0 && !bad.length },
  ];
  const terms: Term[] = [];
  if (o.balance) {
    terms.push({ label: "Total assets", amount: n(o.balance.total_assets), sign: 1 });
    terms.push({ label: "Total liabilities and equity", amount: n(o.balance.total_liabilities_and_equity), sign: 1 });
    checks.push(check("Assets equal liabilities and equity", o.balance.total_assets, n(o.balance.total_liabilities_and_equity)));
  }
  return {
    key: "tie_out", title: "Tie-out",
    how: "Every combined row must equal its platform part plus its target part, and the balance sheet must balance.",
    run, terms,
    total: o.ok ? "Ties out" : "Does not tie out",
    checks,
  };
}

/**
 * The chain behind the verdict, from the runs the result names: EBITDA and debt, then leverage, then the limit test,
 * then the tie-out. `missing` names a run the result points to that the runs list does not hold.
 */
export function mathReport(result: Result, runs: ToolRun[], ctx: { platform: string; target: string; debtTerm: string }): MathReport {
  const byId = new Map(runs.map((r) => [r.run_id, r]));
  const ids = result.run_ids_by_tool ?? {};
  const pick = (tool: string) => (ids[tool] ? byId.get(ids[tool]) ?? null : null);
  const reviewIds = result.review?.run_ids ?? [];
  const all = [...(result.run_ids ?? []), ...reviewIds];
  const consolidate = pick("consolidate");
  const ebitda = ebitdaStep(pick("ebitda"), ctx);
  const debt = debtStep(pick("covenant_debt"), ctx.debtTerm);
  const leverage = leverageStep(pick("leverage"), ebitda, debt);
  const limit = limitStep(pick("limit_test") ?? among(byId, all, "limit_test"), leverage, result.limit);
  const tie = tieOutStep(pick("tie_out") ?? among(byId, all, "tie_out"), consolidate);
  const steps = [ebitda, debt, leverage, limit, tie];
  const missing = steps.filter((s) => !s.run).map((s) => s.title);
  const checks = steps.flatMap((s) => (s.run ? s.checks : []));
  return { steps, passed: checks.filter((c) => c.ok).length, total: checks.length, missing };
}
