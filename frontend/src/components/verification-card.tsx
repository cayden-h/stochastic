"use client";

import { useState } from "react";
import type { BriefCheck, BriefVerification } from "@/lib/types";
import { Card, Label, Mono, Shape } from "./ui";

/** "4.8(a)" reads as Section 4.8(a); "Addendum I" and "preamble" read as they are; an amount's source as it is. */
function sectionName(s: string): string {
  if (!s) return "";
  return /^\d/.test(s) ? `Section ${s}` : s.charAt(0).toUpperCase() + s.slice(1);
}

/** A Brief path as words: `ebitda_addbacks[1].cap` reads "EBITDA add-back 2, cap". */
export function fieldName(path: string): string {
  const m = path.match(/^(\w+?)(?:\[(\d+)\])?(?:\.(\w+))?$/);
  if (!m) return path;
  const names: Record<string, string> = {
    lender: "Lender", limit: "Limit", limit_section: "Limit section", limit_wording: "Limit wording",
    debt_term: "Debt term", debt_definition: "Debt definition", debt_excludes: "Debt exclusion",
    ebitda_definition: "EBITDA definition", ebitda_addbacks: "EBITDA add-back", ebitda_deductions: "EBITDA deduction",
    test_period_note: "Test period",
  };
  const base = names[m[1]] ?? m[1];
  const n = m[2] != null ? ` ${Number(m[2]) + 1}` : "";
  return `${base}${n}${m[3] ? `, ${m[3]}` : ""}`;
}

function CheckRow({ c }: { c: BriefCheck }) {
  const amount = c.field.endsWith(".amount");
  return (
    <li className="flex w-full items-start gap-[12px] border-t border-line px-[16px] py-[10px]" data-check={c.field} data-ok={c.ok}>
      <span className={`pt-[3px] ${c.ok ? "text-clear" : "text-denied"}`} title={c.ok ? "Passed" : "Failed"}>
        <Shape kind={c.ok ? "check" : "cross"} size={12} />
      </span>
      <span className="flex w-[190px] shrink-0 flex-col gap-[2px]">
        <span className="text-[14px] font-semibold text-ink">{fieldName(c.field)}</span>
        <Mono className="truncate" >{c.value}{amount && c.value !== "0" ? "K" : ""}</Mono>
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-[4px]">
        {c.quote ? (
          <q className="line-clamp-2 font-serif text-[15px] leading-[20px] text-slate" title={c.quote}>{c.quote}</q>
        ) : null}
        <span className={`text-[12px] ${c.ok ? "text-slate" : "font-semibold text-denied"}`}>{c.reason}</span>
      </span>
      <Mono className="w-[150px] shrink-0 truncate text-right" >{amount ? "From the books" : sectionName(c.section)}</Mono>
    </li>
  );
}

/**
 * The verifier's report (D23), compact: N of N checks passed, and on demand every field with its quote, its section,
 * and the pass mark. The verifier is code, not a model, so it wears the gateway's lock, not an avatar.
 */
export function VerificationCard({ report }: { report: BriefVerification }) {
  const [open, setOpen] = useState(false);
  const total = report.checks.length;
  const allOk = report.failed === 0;
  return (
    <Card className="flex w-full flex-col" >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center gap-[12px] px-[16px] py-[12px] text-left"
        data-testid="verification-card"
      >
        <span className={`flex size-[28px] shrink-0 items-center justify-center rounded-[8px] ${allOk ? "bg-clear-tint text-clear" : "bg-denied-tint text-denied"}`}>
          <Shape kind={allOk ? "check" : "cross"} size={14} />
        </span>
        <span className="flex min-w-0 flex-1 flex-col gap-[2px]">
          <span className="flex items-center gap-[8px]">
            <Label>Brief verification</Label>
            <span className={`text-[15px] font-semibold ${allOk ? "text-clear" : "text-denied"}`} data-testid="verification-summary">
              {report.passed} of {total} checks passed
            </span>
          </span>
          <span className="truncate text-[13px] text-slate">
            {report.auto_approved
              ? "Every quote is word for word in its section, every number matches its quote, and the amounts come from the books. Approved by the verifier."
              : allOk ? "Every field checks out against the agreement." : `${report.failed} failed; the controller decides.`}
          </span>
        </span>
        <span className="text-[13px] font-semibold text-slate">{open ? "Hide" : "Show"} the checks</span>
        <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" className={`shrink-0 text-slate transition-transform ${open ? "rotate-180" : ""}`}>
          <path d="M2.5 4.5L6 8L9.5 4.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open ? (
        <>
          <ol className="flex flex-col" aria-label="The verifier's checks">
            {report.checks.map((c) => <CheckRow key={c.field} c={c} />)}
          </ol>
          {report.scope_notes.length ? (
            <div className="flex flex-col gap-[4px] border-t border-line bg-fog px-[16px] py-[10px]">
              <Label>Noted, not tested</Label>
              {report.scope_notes.map((n) => <span key={n} className="text-[13px] text-slate">{n}</span>)}
            </div>
          ) : null}
        </>
      ) : null}
    </Card>
  );
}
