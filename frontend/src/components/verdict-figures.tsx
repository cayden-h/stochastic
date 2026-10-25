"use client";

import { fmtK, fmtM, fmtX } from "@/lib/format";
import type { Verdict as VerdictShape } from "@/lib/types";
import { Label, Mono, Shape } from "./ui";

/**
 * The limit check's four figures on the Case: the covenant debt, covenant EBITDA, the room in turns of EBITDA, and the
 * covenant headroom in dollars of debt. Every figure names its tool run. Over the limit, or a Reviewer that needs
 * attention, adds its reasons under them. The leverage, the verdict words, approval, and the final files are on the
 * Review page.
 */
export function VerdictFigures({ verdict, runIds }: { verdict: VerdictShape; runIds: Record<string, string> }) {
  const over = verdict.verdict === "over_limit";
  const review = verdict.review?.verdict ?? null;
  return (
    <section aria-label="The limit check" className={`flex w-full flex-col gap-[14px] rounded-card border bg-white p-[20px] ${over ? "border-denied" : "border-line"}`}>
      <dl className="grid grid-cols-4 gap-[16px]">
        <Figure label={verdict.debt_term} value={fmtK(verdict.debt)} run={runIds.covenant_debt} />
        <Figure label="Covenant EBITDA" value={fmtK(verdict.ebitda)} run={runIds.ebitda} />
        <Figure
          label="Room (turns of EBITDA)"
          value={over ? `Over by ${fmtX(-verdict.headroom_turns)}` : fmtX(verdict.headroom_turns)}
          run={runIds.leverage}
          tone={over ? "text-denied" : undefined}
        />
        <Figure
          label="Covenant headroom"
          value={verdict.debt_capacity == null ? "Not run" : over ? "None" : `${fmtM(verdict.debt_capacity)} of debt`}
          run={verdict.debt_capacity_run_id ?? undefined}
          sub={verdict.debt_capacity == null || over ? undefined : fmtK(verdict.debt_capacity)}
        />
      </dl>

      {verdict.approval_state === "REJECTED" ? (
        <p className="flex items-center gap-[6px] text-[14px] font-semibold text-denied"><Shape kind="cross" size={12} />Rejected</p>
      ) : null}
      {review === "needs_attention" && verdict.review?.reasons.length ? (
        <ul className="flex flex-col gap-[4px] rounded-[8px] bg-escalation-tint px-[12px] py-[10px] text-[14px] text-escalation">
          {verdict.review.reasons.map((r, i) => <li key={i}>{r}</li>)}
        </ul>
      ) : null}
      {over ? (
        <p className="text-[14px] text-denied">Over the limit returns the result to you as needs attention. The gateway refuses approval.</p>
      ) : null}
    </section>
  );
}

function Figure({ label, value, run, sub, tone }: { label: string; value: string; run?: string; sub?: string; tone?: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-[4px]">
      <dt><Label>{label}</Label></dt>
      <dd className={`text-[16px] font-semibold ${tone ?? "text-forest"}`}>{value}</dd>
      <dd><Mono className="text-[11px]">{[sub, run].filter(Boolean).join(" ")}</Mono></dd>
    </div>
  );
}
