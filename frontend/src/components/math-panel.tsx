"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { num } from "@/lib/edits";
import { type Check, type Step, type Term, mathReport } from "@/lib/math-check";
import type { Case, ToolRun } from "@/lib/types";
import { Label, Mono, Shape, actorOf } from "./ui";

function TermRow({ t, first }: { t: Term; first: boolean }) {
  return (
    <li className="flex items-baseline gap-[10px] py-[5px]">
      <span className="w-[12px] shrink-0 text-center font-mono text-[13px] text-sheet-muted" aria-hidden="true">
        {first ? "" : t.sign < 0 ? "−" : t.note === "divided by" ? "÷" : "+"}
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="truncate text-[14px] text-ink" title={t.label}>{t.label}</span>
        {t.note && t.note !== "divided by" ? <span className="text-[12px] leading-[16px] text-sheet-muted">{t.note}</span> : null}
      </span>
      <span className="shrink-0 font-mono text-[13px] text-ink">{num(t.amount)}</span>
    </li>
  );
}

function CheckRow({ c }: { c: Check }) {
  // A pass or fail check reports 1 or 0; there is nothing to show beside it.
  const flag = c.label === "Pass or fail" || c.label.startsWith("Every combined row");
  return (
    <li className="flex items-center gap-[8px] py-[3px] text-[12px]" data-check-ok={c.ok}>
      <span className={c.ok ? "text-clear" : "text-denied"} title={c.ok ? "Matches" : "Does not match"}>
        <Shape kind={c.ok ? "check" : "cross"} size={10} />
      </span>
      <span className={`min-w-0 flex-1 truncate ${c.ok ? "text-sheet-muted" : "font-semibold text-denied"}`} title={c.label}>{c.label}</span>
      {flag ? null : (
        <span className="shrink-0 font-mono text-[11px] text-sheet-muted">
          {c.ok ? "re-added, matches" : `run says ${fmt(c.reported)}, re-added ${fmt(c.recomputed)}`}
        </span>
      )}
    </li>
  );
}

const fmt = (v: number) => (Math.abs(v) < 20 ? v.toFixed(3) : num(v));

function StepCard({ step, i }: { step: Step; i: number }) {
  const [showOut, setShowOut] = useState(false);
  const ok = step.run ? step.checks.every((c) => c.ok) : false;
  const who = step.run ? actorOf(step.run.actor) : null;
  return (
    <section className="flex flex-col rounded-[10px] border border-sheet-line bg-white" data-step={step.key}>
      <header className="flex items-center gap-[10px] border-b border-sheet-line px-[14px] py-[10px]">
        <span className="flex size-[22px] shrink-0 items-center justify-center rounded-full bg-sheet-head font-mono text-[11px] text-sheet-muted">{i + 1}</span>
        <h3 className="min-w-0 flex-1 truncate text-[15px] font-semibold text-forest">{step.title}</h3>
        <strong className="shrink-0 font-mono text-[14px] text-ink">{step.total}</strong>
        <span className={step.run && ok ? "text-clear" : "text-denied"} title={!step.run ? "No run" : ok ? "Every check matches" : "A check does not match"}>
          <Shape kind={step.run && ok ? "check" : "cross"} size={12} />
        </span>
      </header>
      <div className="flex flex-col gap-[6px] px-[14px] py-[10px]">
        <p className="text-[13px] leading-[18px] text-sheet-muted">{step.how}</p>
        {step.terms.length ? (
          <ol className="flex flex-col divide-y divide-sheet-line">
            {step.terms.map((t, j) => <TermRow key={`${t.label}-${j}`} t={t} first={j === 0} />)}
          </ol>
        ) : null}
        {step.excluded?.length ? (
          <div className="flex flex-col">
            <button type="button" onClick={() => setShowOut((s) => !s)} aria-expanded={showOut} className="self-start text-[12px] font-semibold text-forest underline-offset-4 hover:underline">
              {showOut ? "Hide" : "Show"} {step.excluded.length} {step.excluded.length === 1 ? "line" : "lines"} left out
            </button>
            {showOut ? (
              <ol className="mt-[4px] flex flex-col divide-y divide-sheet-line opacity-80">
                {step.excluded.map((t, j) => <TermRow key={`${t.label}-${j}`} t={t} first />)}
              </ol>
            ) : null}
          </div>
        ) : null}
        {step.run ? (
          <ul className="mt-[2px] flex flex-col border-t border-sheet-line pt-[6px]" aria-label={`${step.title} checks`}>
            {step.checks.map((c) => <CheckRow key={c.label} c={c} />)}
          </ul>
        ) : (
          <p className="text-[12px] font-semibold text-denied">The result names no run for this step.</p>
        )}
      </div>
      {step.run ? (
        <footer className="flex items-center gap-[8px] border-t border-sheet-line bg-sheet-band px-[14px] py-[6px]">
          <Mono className="text-sheet-muted">{step.run.tool}</Mono>
          <Mono>{step.run.run_id}</Mono>
          <span className="flex-1" />
          <span className="text-[11px] text-sheet-muted">{who?.label} called it, code computed it</span>
        </footer>
      ) : null}
    </section>
  );
}

/**
 * Check the math (Review): the chain of tool runs behind the verdict, Covenant EBITDA and debt, then leverage, the
 * limit test, and the tie-out, each with its parts and its run. The browser re-adds each run's parts and compares
 * them with the totals the run reports, so the controller sees the arithmetic hold without trusting a summary.
 */
export function MathPanel({ kase, onClose }: { kase: Case; onClose: () => void }) {
  const [runs, setRuns] = useState<ToolRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { deal, result, verdict } = kase;
  const dealId = deal.id;
  const stamp = result?.id;

  useEffect(() => {
    let gone = false;
    api.runs(dealId)
      .then((r) => { if (!gone) setRuns(r); })
      .catch((e) => { if (!gone) setError(e instanceof Error ? e.message : "Could not read the runs"); });
    return () => { gone = true; };
  }, [dealId, stamp]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const report = useMemo(
    () => (result && runs ? mathReport(result, runs, { platform: deal.platform, target: deal.target, debtTerm: verdict?.debt_term || deal.brief?.debt_term || "Debt" }) : null),
    [result, runs, deal, verdict],
  );
  const allOk = Boolean(report && report.total && report.passed === report.total && !report.missing.length);

  return (
    <div className="fixed inset-0 z-[60] flex justify-end" role="dialog" aria-label="Check the math" aria-modal="true">
      <div aria-hidden="true" className="absolute inset-0 bg-ink/30" onClick={onClose} />
      <aside className="panel-in relative flex h-full w-full max-w-[520px] flex-col border-l border-sheet-line bg-sheet-head">
        <header className="flex shrink-0 items-start gap-[12px] border-b border-sheet-line bg-white px-[20px] py-[16px]">
          <span className="flex min-w-0 flex-1 flex-col gap-[4px]">
            <Label>How the numbers were made</Label>
            <h2 className="font-serif text-[24px] leading-[28px] text-forest">Check the math</h2>
          </span>
          <button type="button" aria-label="Close the math" onClick={onClose} className="rounded-chip px-[8px] py-[4px] text-[13px] font-semibold text-sheet-muted hover:bg-sheet-band hover:text-forest">
            Close
          </button>
        </header>

        <div className="flex min-h-0 flex-1 flex-col gap-[12px] overflow-y-auto px-[20px] py-[16px]">
          {report ? (
            <div className={`flex items-center gap-[12px] rounded-[10px] px-[14px] py-[12px] ${allOk ? "bg-clear-tint" : "bg-denied-tint"}`}>
              <span className={allOk ? "text-clear" : "text-denied"}><Shape kind={allOk ? "check" : "cross"} size={16} /></span>
              <span className="flex min-w-0 flex-col gap-[2px]">
                <strong className={`text-[15px] ${allOk ? "text-forest" : "text-denied"}`} data-testid="math-summary">
                  {report.passed} of {report.total} checks pass
                </strong>
                <span className="text-[12px] leading-[17px] text-ink">
                  {report.missing.length
                    ? `No run found for ${report.missing.join(", ")}.`
                    : "Code computed every figure below. Your browser re-added each run's parts and compared them with the totals the run reports. No model produced a number."}
                </span>
              </span>
            </div>
          ) : error ? (
            <p role="alert" className="text-[13px] font-semibold text-denied">{error}</p>
          ) : !result ? (
            <p className="text-[13px] text-sheet-muted">The books are not combined yet, so there is no math to check.</p>
          ) : (
            <p className="text-[13px] text-sheet-muted">Reading the tool runs.</p>
          )}

          {report?.steps.map((s, i) => <StepCard key={s.key} step={s} i={i} />)}

          {report ? (
            <p className="pb-[8px] text-[11px] leading-[16px] text-sheet-muted">
              USD thousands. Agent output from the {verdict?.backend ?? result?.backend} backend; the gateway, the math, and the audit log are real.
              Every run is in the Audit sheet.
            </p>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
