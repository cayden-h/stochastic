"use client";

import { fmtX, lineK, plural } from "@/lib/format";
import type { SourceLine, WorkItem } from "@/lib/types";
import { SourceChip } from "./source";
import { ActorChip, Button, Mono, Shape, Tag } from "./ui";

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
    <p className="flex items-center gap-[8px] text-[13px] text-slate">
      <span className={fork.state === "ready" ? "text-clear" : "text-slate"}><Shape kind="circle" size={10} /></span>
      <span className={live ? "" : "italic"}>{text}</span>
    </p>
  );
}

/** The question in two parts: its first sentence as the heading, the rest as the detail under it. */
function splitQuestion(q: string): [string, string] {
  const m = q.match(/^([\s\S]+?[?.])\s+([\s\S]*)$/);
  return m ? [m[1], m[2]] : [q, ""];
}

/**
 * One flag: the question and the options with their readings, then the evidence, collapsed: each option's effect
 * sentence and run id, the flagged lines, and the filing quotes. The readings sit right under the question on a projector.
 * The ratio, verdict, effect text and run id come from the gateway's tool runs. Nothing here is computed.
 */
export function FlagCard({
  item, lines, busy, onAnswer, onHold, position,
}: {
  item: WorkItem; lines: SourceLine[]; busy: boolean; onAnswer: (optionId: string) => void; onHold: () => void;
  /** "1 of 2" when several flags are open. */
  position: string;
}) {
  const covenant = item.payload.kind === "covenant_tag";
  // A learned adjustment the Preparer offers on a later deal (D19): apply or skip, never applied silently.
  const adjustment = item.payload.kind === "adjustment";
  const kind = covenant ? "Lender definition question" : adjustment ? "Learned adjustment" : "Mapping question";
  const lineIds = Array.isArray(item.payload.line_ids) ? (item.payload.line_ids as string[]) : [];
  const flagged = lines.filter((l) => lineIds.includes(l.id));
  const [heading, detail] = splitQuestion(item.question ?? "");
  const letter = (i: number) => String.fromCharCode(97 + i);
  return (
    <section className="flex w-full flex-col gap-[14px] rounded-card border border-amber-line bg-white p-[20px]">
      <div className="flex w-full items-center gap-[10px] whitespace-nowrap">
        <ActorChip actor={item.proposed_by} />
        <span className="inline-flex items-center gap-[6px] text-[11px] font-semibold uppercase tracking-[0.88px] text-escalation">
          <Shape kind="triangle" size={10} />
          {kind}
        </span>
        <span className="flex-1" />
        <Button kind="link" className="text-[13px]" onClick={onHold} disabled={busy}>Not sure. Hold this item.</Button>
        <Mono>{position}</Mono>
      </div>

      <ForkLine fork={item.payload.fork as Fork | undefined} />

      <div className="flex flex-col gap-[6px]">
        <h2 className="text-[22px] font-semibold text-forest">{heading}</h2>
        {detail ? <p className="text-[14px] leading-[20px] text-slate">{detail}</p> : null}
      </div>

      <div className="flex w-full gap-[12px]">
        {item.options.map((o, i) => {
          const suggested = o.id === item.default;
          const ok = Boolean(o.ok);
          return (
            <button
              key={o.id}
              disabled={busy}
              onClick={() => onAnswer(o.id)}
              title={o.effect}
              className={`flex min-w-0 flex-1 flex-col items-start gap-[6px] self-stretch rounded-[12px] p-[16px] text-left transition-colors duration-150 disabled:opacity-50 ${
                suggested ? "border-2 border-clear bg-mint-select p-[15px] hover:bg-mint" : "border border-line bg-white hover:bg-mint-select"
              }`}
            >
              <span className="flex w-full items-start gap-[6px] text-forest">
                <span className="pt-[2px] font-mono text-[12px]">{letter(i)}.</span>
                <span className="min-w-0 flex-1 text-[14px] font-semibold">{o.label}</span>
                {suggested ? <Tag>Suggested</Tag> : null}
                {o.added_by ? <ActorChip actor={o.added_by} /> : null}
              </span>
              {adjustment ? <span className="text-[13px] leading-[18px] text-slate">{o.effect}</span> : null}
              {o.leverage != null ? (
                <>
                  <span className={`text-[30px] font-semibold ${ok ? "text-clear" : "text-denied"}`}>{fmtX(o.leverage)}</span>
                  <span className={`text-[13px] font-medium ${ok ? "text-clear" : "text-denied"}`}>{ok ? "OK" : "Over the limit"}</span>
                </>
              ) : null}
            </button>
          );
        })}
      </div>

      <details className="rounded-[12px] border border-line bg-fog px-[14px] py-[10px]">
        <summary className="cursor-pointer text-[13px] font-semibold text-forest">
          Evidence: {plural(item.options.length, "effect")}
          {flagged.length ? `, ${plural(flagged.length, "line")}` : ""}
          {item.evidence.length ? `, ${plural(item.evidence.length, "quote")} from the filings` : ""}
        </summary>
        <div className="mt-[10px] flex flex-col gap-[12px]">
          <div className="flex flex-col gap-[6px] rounded-[8px] border border-line bg-white px-[12px] py-[10px]">
            {item.options.map((o, i) => (
              <div key={o.id} className="flex items-baseline gap-[8px] text-[13px]">
                <span className="font-mono text-[12px] text-forest">{letter(i)}.</span>
                <span className="min-w-0 flex-1 text-body">{o.effect}</span>
                {o.run_id ? <Mono>{o.run_id}</Mono> : null}
              </div>
            ))}
          </div>
          {flagged.length ? (
            <div className="flex flex-col gap-[4px] rounded-[8px] border border-line bg-white px-[12px] py-[10px]">
              {flagged.map((l) => (
                <div key={l.id} className="flex items-baseline gap-x-[12px]">
                  <span className="min-w-0 flex-1 truncate text-[14px]" title={l.line}>{l.line}</span>
                  <Mono>{l.company}</Mono>
                  <span className="text-[14px] font-semibold text-forest">{lineK(l.amount, l.unit)}</span>
                </div>
              ))}
              {flagged.find((l) => l.note) ? (
                <p className="mt-[4px] text-[13px] text-slate">{flagged.find((l) => l.note)!.note}</p>
              ) : null}
            </div>
          ) : null}

          {item.evidence.length ? (
            <div className="flex flex-col gap-[10px]">
              {item.evidence.map((e, i) => (
                <figure key={i} className="flex flex-col gap-[6px] border-l-2 border-amber-line py-[2px] pl-[12px]">
                  <p className="font-serif text-[18px] text-body">{`"${e.quote}"`}</p>
                  <div><SourceChip evidence={e} line={flagged[0]} /></div>
                </figure>
              ))}
            </div>
          ) : null}
        </div>
      </details>
    </section>
  );
}

/** The fog card in the verdict's place while there is no verdict yet. */
export function WaitingVerdict({ text, limit }: { text: string; limit: number }) {
  return (
    <div className="flex w-full items-center gap-[12px] rounded-card border border-line bg-fog p-[14px] text-[16px] font-semibold text-slate">
      <span className="min-w-0 flex-1">{text}</span>
      <span className="whitespace-nowrap">- of {fmtX(limit)}</span>
    </div>
  );
}

/** The other open flags, folded to one row under the current one. Opening it makes the next flag current. */
export function MoreFlags({ items, onOpen }: { items: WorkItem[]; onOpen: (id: string) => void }) {
  if (!items.length) return null;
  const [heading] = splitQuestion(items[0].question ?? "");
  return (
    <button
      onClick={() => onOpen(items[0].id)}
      className="flex w-full items-center gap-[12px] rounded-card border border-amber-line bg-white px-[20px] py-[14px] text-left transition-colors duration-150 hover:bg-amber-tint"
    >
      <span className="inline-flex items-center gap-[6px] text-[13px] font-semibold whitespace-nowrap text-escalation">
        <Shape kind="triangle" size={10} />
        {items.length === 1 ? "1 more question" : `${items.length} more questions`}
      </span>
      <span className="min-w-0 flex-1 truncate text-[14px] text-body">{heading}</span>
      <span className="text-[13px] font-semibold whitespace-nowrap text-forest">Open</span>
    </button>
  );
}
