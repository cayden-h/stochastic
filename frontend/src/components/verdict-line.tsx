"use client";

import { fmtK, fmtM, fmtX } from "@/lib/format";
import type { Verdict as VerdictShape } from "@/lib/types";
import { Button, Mono, Shape, Verdict } from "./ui";

/**
 * Leverage against the limit, OK or Over the limit, the room left, the Reviewer badge, and Approve.
 * Approve is live only while the approval item is PROPOSED. Every figure names its tool run.
 */
export function VerdictLine({
  verdict, runIds, busy, onApprove, onReject,
}: {
  verdict: VerdictShape; runIds: Record<string, string>; busy: boolean; onApprove: () => void; onReject: () => void;
}) {
  const over = verdict.verdict === "over_limit";
  const review = verdict.review?.verdict ?? null;
  const canApprove = verdict.approval_state === "PROPOSED" && review === "pass" && !over;
  return (
    <section className={`flex flex-col gap-4 rounded-card border bg-card p-6 ${over ? "border-denied" : "border-rule"}`}>
      <div className="flex flex-wrap items-center gap-4">
        <h2 className="font-serif text-[40px] leading-[48px] font-medium tabular-nums">
          {fmtX(verdict.leverage)} <span className="text-muted">against {fmtX(verdict.limit)}</span>
        </h2>
        <Verdict kind={over ? "over_limit" : "ok"} />
        {review ? <Verdict kind={review} /> : <Verdict kind="waiting" word="Reviewer pending" />}
        <span className="flex-1" />
        {verdict.posted ? (
          <span className="flex items-center gap-2 font-semibold text-clear"><Shape kind="check" />Approved and posted to the record.</span>
        ) : verdict.approval_state === "PROPOSED" ? (
          <div className="flex items-center gap-2">
            <Button kind="link" disabled={busy} onClick={onReject}>Reject</Button>
            <Button kind="primary" disabled={busy || !canApprove} onClick={onApprove}>Approve</Button>
          </div>
        ) : verdict.approval_state === "REJECTED" ? (
          <span className="flex items-center gap-2 font-semibold text-denied"><Shape kind="cross" />Rejected.</span>
        ) : null}
      </div>

      <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Figure label={verdict.debt_term} value={fmtK(verdict.debt)} run={runIds.covenant_debt} />
        <Figure label="Covenant EBITDA" value={fmtK(verdict.ebitda)} run={runIds.ebitda} />
        <Figure
          label="Room under the limit"
          value={over ? `Over by ${fmtX(-verdict.headroom_turns)}` : fmtX(verdict.headroom_turns)}
          run={runIds.leverage}
          tone={over ? "text-denied" : undefined}
        />
        <Figure
          label="Debt capacity for the next deal"
          value={verdict.debt_capacity == null ? "Not run" : over ? "None" : `about ${fmtM(verdict.debt_capacity)}`}
          run={verdict.debt_capacity_run_id ?? undefined}
          sub={verdict.debt_capacity == null || over ? undefined : fmtK(verdict.debt_capacity)}
        />
      </dl>

      {review === "needs_attention" && verdict.review?.reasons.length ? (
        <ul className="flex flex-col gap-1 rounded-chip bg-escalation-tint px-4 py-3 text-escalation">
          {verdict.review.reasons.map((r, i) => <li key={i}>{r}</li>)}
        </ul>
      ) : null}
      {over ? (
        <p className="text-denied">Over the limit returns the result to you as needs attention. The gateway refuses approval.</p>
      ) : null}
    </section>
  );
}

function Figure({ label, value, run, sub, tone }: { label: string; value: string; run?: string; sub?: string; tone?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] text-muted">{label}</dt>
      <dd className={`font-semibold tabular-nums ${tone ?? ""}`}>{value}</dd>
      <dd><Mono>{[sub, run].filter(Boolean).join(" ")}</Mono></dd>
    </div>
  );
}
