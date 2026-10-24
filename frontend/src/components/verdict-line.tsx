"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";
import { fmtK, fmtM, fmtX } from "@/lib/format";
import type { Verdict as VerdictShape } from "@/lib/types";
import { Label, Mono, Shape, Verdict } from "./ui";

/** A figure that ticks from its last value to the new one (about 450 ms), so an edit's recompute is seen landing.
 * With reduced motion it changes at once. The value itself always comes from the gateway. */
function useTicked(value: number): number {
  const [shown, setShown] = useState(value);
  const from = useRef(value);
  useEffect(() => {
    const start = from.current;
    from.current = value;
    if (start === value) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const t = setTimeout(() => setShown(value), 0);
      return () => clearTimeout(t);
    }
    let raf = 0;
    const t0 = performance.now();
    const step = (now: number) => {
      const k = Math.min(1, (now - t0) / 450);
      setShown(start + (value - start) * (1 - Math.pow(1 - k, 3)));
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return shown;
}

/**
 * Leverage against the limit, OK or Over the limit, the room left, and the Reviewer badge.
 * Approve and Reject sit in the page header. Every figure names its tool run.
 */
export function VerdictLine({
  verdict, runIds, asFiled, note, action,
}: {
  verdict: VerdictShape; runIds: Record<string, string>;
  /** The whole-line reading from the answered covenant flag, so the comparison stays on screen after the answer. */
  asFiled?: { leverage: number; ok: boolean; run_id: string | null } | null;
  /** One sentence on what happened, under the figure. */
  note?: ReactNode;
  /** The verdict's own action, such as Download final files after approval. */
  action?: ReactNode;
}) {
  const over = verdict.verdict === "over_limit";
  const leverage = useTicked(verdict.leverage);
  const review = verdict.review?.verdict ?? null;
  return (
    <section className={`flex w-full flex-col gap-[14px] rounded-card border bg-white p-[20px] ${over ? "border-denied" : "border-line"}`}>
      <div className="flex flex-wrap items-center gap-[12px]">
        <h2 className="text-[30px] font-semibold text-forest">
          <span aria-label={fmtX(verdict.leverage)}>{fmtX(leverage)}</span> <span className="text-[20px] font-medium text-slate">against {fmtX(verdict.limit)}</span>
        </h2>
        <Verdict kind={over ? "over_limit" : "ok"} />
        {review ? <Verdict kind={review} /> : <Verdict kind="waiting" word="Reviewer pending" />}
        <span className="flex-1" />
        {/* Approved and posted shows in the page header, where Approve was. */}
        {verdict.approval_state === "REJECTED" ? (
          <span className="flex items-center gap-[6px] text-[14px] font-semibold text-denied"><Shape kind="cross" size={12} />Rejected</span>
        ) : null}
        {action}
      </div>

      {note ? <p className="-mt-[6px] text-[14px] leading-[20px] text-slate">{note}</p> : null}

      {asFiled ? (
        <p className="-mt-[6px] text-[14px] leading-[20px] text-slate">
          Read as filed, counting the whole financing line:{" "}
          <span className={`font-semibold ${asFiled.ok ? "text-body" : "text-denied"}`}>
            {fmtX(asFiled.leverage)}, {asFiled.ok ? "under the limit" : "over the limit"}
          </span>
          . The agreement&apos;s definition gives {fmtX(verdict.leverage)}.{" "}
          {asFiled.run_id ? <Mono>{asFiled.run_id}</Mono> : null}
        </p>
      ) : null}

      <dl className="grid grid-cols-4 gap-[16px] border-t border-line pt-[14px]">
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
