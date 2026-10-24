"use client";

import { lineK } from "@/lib/format";
import type { SourceLine, WorkItem } from "@/lib/types";
import { SourceChip } from "./source";
import { ActorChip, Button, Mono, Shape, Tag } from "./ui";

/**
 * One flag: the question, the filing evidence, and the options with their computed effects.
 * The effect text and run id come from the gateway's tool runs. Nothing here is computed.
 */
export function FlagCard({
  item, lines, busy, onAnswer, onHold,
}: {
  item: WorkItem; lines: SourceLine[]; busy: boolean; onAnswer: (optionId: string) => void; onHold: () => void;
}) {
  const kind = item.payload.kind === "covenant_tag" ? "Covenant tag" : "Mapping";
  const lineIds = Array.isArray(item.payload.line_ids) ? (item.payload.line_ids as string[]) : [];
  const flagged = lines.filter((l) => lineIds.includes(l.id));
  const wide = item.options.length > 2;
  return (
    <section className="flex flex-col gap-4 rounded-card border border-escalation-bar border-l-[6px] bg-card p-4 sm:p-6">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <ActorChip actor={item.proposed_by} />
        <span className="inline-flex items-center gap-2 text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] text-escalation">
          <Shape kind="triangle" />
          {kind} flag
        </span>
        <Mono>{item.id}</Mono>
        <span className="flex-1" />
        <Button kind="link" onClick={onHold} disabled={busy}>Not sure. Hold this item.</Button>
      </div>

      <h2 className="font-serif text-[26px] leading-8 font-medium">{item.question}</h2>

      {flagged.length ? (
        <div className="flex flex-col gap-1 rounded-chip border border-hairline bg-paper px-4 py-3">
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
              {suggested ? <Tag>Agent suggests</Tag>
                : o.added_by ? <ActorChip actor={o.added_by} />
                : <span className="h-7" />}
              <span className="font-semibold">{o.label}</span>
              <span className="text-muted">{o.effect}</span>
              {o.run_id ? <Mono>{o.run_id}</Mono> : null}
            </button>
          );
        })}
      </div>
    </section>
  );
}
