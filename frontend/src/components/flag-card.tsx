"use client";

import { fmtX, lineK } from "@/lib/format";
import type { SourceLine, WorkItem } from "@/lib/types";
import { SourceChip } from "./source";
import { ActorChip, Button, Mono, Shape, Tag, Verdict } from "./ui";

type Fork = { state: string; service_id?: string; seconds?: number; reason?: string };

/** Where this flag's what-ifs live: a Tiger fork of the ledger, made by the gateway (app/gateway/whatif.py). */
function ForkLine({ fork }: { fork?: Fork }) {
  if (!fork) return null;
  const text =
    fork.state === "creating" ? "Forking the ledger on Tiger Cloud to hold these what-ifs. About 35 s."
    : fork.state === "ready" ? `What-ifs held in Tiger fork ${fork.service_id}, outside the live ledger. Ready in ${fork.seconds} s.`
    : fork.state === "failed" || fork.state === "skipped" ? `What-ifs computed here; no fork (${fork.reason}).`
    : null;
  if (!text) return null;
  const live = fork.state === "creating" || fork.state === "ready";
  return (
    <p className="flex items-center gap-2 text-[14px] leading-5 text-muted">
      <span className={fork.state === "ready" ? "text-clear" : "text-muted"}><Shape kind="circle" size={10} /></span>
      <span className={live ? "" : "italic"}>{text}</span>
    </p>
  );
}

/**
 * One flag: the question, the options with their computed effects, then the filing evidence (collapsed for a
 * covenant flag, so the readings sit right under the question on a projector).
 * The ratio, verdict, effect text and run id come from the gateway's tool runs. Nothing here is computed.
 */
export function FlagCard({
  item, lines, busy, onAnswer, onHold,
}: {
  item: WorkItem; lines: SourceLine[]; busy: boolean; onAnswer: (optionId: string) => void; onHold: () => void;
}) {
  const covenant = item.payload.kind === "covenant_tag";
  const kind = covenant ? "Lender definition question" : "Mapping question";
  const lineIds = Array.isArray(item.payload.line_ids) ? (item.payload.line_ids as string[]) : [];
  const flagged = lines.filter((l) => lineIds.includes(l.id));
  const wide = item.options.length > 2;
  return (
    <section className="flex flex-col gap-4 rounded-card border border-escalation-bar border-l-[6px] bg-card p-4 sm:p-6">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <ActorChip actor={item.proposed_by} />
        <span className="inline-flex items-center gap-2 text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] text-escalation">
          <Shape kind="triangle" />
          {kind}
        </span>
        <Mono>{item.id}</Mono>
        <span className="flex-1" />
        <Button kind="link" onClick={onHold} disabled={busy}>Not sure. Hold this item.</Button>
      </div>

      <ForkLine fork={item.payload.fork as Fork | undefined} />

      <h2 className="font-serif text-[26px] leading-8 font-medium">{item.question}</h2>

      <div className={`grid gap-4 ${wide ? "sm:grid-cols-3" : "sm:grid-cols-2"}`}>
        {item.options.map((o) => {
          const suggested = o.id === item.default;
          return (
            <button
              key={o.id}
              disabled={busy}
              onClick={() => onAnswer(o.id)}
              className={`flex flex-col items-start gap-2 rounded-chip bg-card p-4 text-left transition-colors duration-150 hover:bg-paper disabled:opacity-50 ${
                suggested ? "border-2 border-ink" : "border border-rule"
              }`}
            >
              {o.leverage != null ? (
                <span className="flex flex-wrap items-center gap-3">
                  <span className={`font-serif text-[40px] leading-[48px] font-medium tabular-nums ${o.ok ? "" : "text-denied"}`}>
                    {fmtX(o.leverage)}
                  </span>
                  <Verdict kind={o.ok ? "ok" : "over_limit"} />
                </span>
              ) : null}
              {suggested || o.added_by ? (
                <span className="flex flex-wrap gap-2">
                  {suggested ? <Tag>Agent suggests</Tag> : null}
                  {o.added_by ? <ActorChip actor={o.added_by} /> : null}
                </span>
              ) : null}
              <span className="font-semibold">{o.label}</span>
              <span className="text-muted">{o.effect}</span>
              {o.run_id ? <Mono>{o.run_id}</Mono> : null}
            </button>
          );
        })}
      </div>

      {flagged.length || item.evidence.length ? (
        <details className="group rounded-chip border border-hairline bg-paper px-4 py-3" open={!covenant}>
          <summary className="cursor-pointer font-semibold">
            Evidence: {flagged.length ? `${flagged.length} line${flagged.length === 1 ? "" : "s"}` : ""}
            {flagged.length && item.evidence.length ? ", " : ""}
            {item.evidence.length ? `${item.evidence.length} quote${item.evidence.length === 1 ? "" : "s"} from the filings` : ""}
          </summary>
          <div className="mt-3 flex flex-col gap-4">
      {flagged.length ? (
        <div className="flex flex-col gap-1 rounded-chip border border-hairline bg-card px-4 py-3">
          {flagged.map((l) => (
            <div key={l.id} className="flex flex-wrap items-baseline gap-x-3">
              <span className="min-w-0 basis-full truncate sm:basis-0 sm:flex-1" title={l.line}>{l.line}</span>
              <Mono>{l.company}</Mono>
              <span className="font-semibold tabular-nums">{lineK(l.amount, l.unit)}</span>
            </div>
          ))}
          {flagged.find((l) => l.note) ? (
            <p className="mt-1 text-muted">{flagged.find((l) => l.note)!.note}</p>
          ) : null}
        </div>
      ) : null}

      {item.evidence.length ? (
        <div className="flex flex-col gap-3">
          {item.evidence.map((e, i) => (
            <blockquote key={i} className="flex flex-col gap-2 border-l-2 border-rule py-1 pl-4">
              <p className="font-serif text-[20px] leading-[30px]">{`"${e.quote}"`}</p>
              <div><SourceChip evidence={e} line={flagged[0]} /></div>
            </blockquote>
          ))}
        </div>
      ) : null}
          </div>
        </details>
      ) : null}
    </section>
  );
}
