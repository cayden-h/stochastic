"use client";

import type { WorkItem } from "@/lib/types";
import { SourceChip } from "./source";
import { ActorChip, Button, Shape, Tag } from "./ui";

const POINTS: Record<string, string> = {
  E1: "Missing document", E2: "Confirm facts", E3: "Unclear clause", E4: "Plan blocked", E5: "Plan flipped", E6: "Final call",
};

function Quote({ text }: { text: string }) {
  const hi = "redeemable at the option of the holder";
  const at = text.indexOf(hi);
  if (at < 0) return <>{`"${text}"`}</>;
  return (
    <>
      {`"${text.slice(0, at)}`}
      <span className="text-escalation underline underline-offset-4">{hi}</span>
      {`${text.slice(at + hi.length)}"`}
    </>
  );
}

export function EscalationCard({
  item, busy, onAnswer, onHold,
}: {
  item: WorkItem; busy: boolean; onAnswer: (optionId: string) => void; onHold: () => void;
}) {
  const e = item.escalation ?? "";
  const context = typeof item.payload.context === "string" ? item.payload.context : null;
  return (
    <section className="flex flex-col gap-4 rounded-card border border-escalation-bar border-l-[6px] bg-card p-6">
      <div className="flex items-center gap-3">
        <ActorChip actor={item.proposed_by} />
        <span className="inline-flex items-center gap-2 text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] text-escalation">
          <Shape kind="triangle" />
          {e} {POINTS[e] ?? ""}
        </span>
        <span className="flex-1" />
        <Button kind="link" onClick={onHold} disabled={busy}>Not sure. Hold this item.</Button>
      </div>

      <h2 className="font-serif text-[26px] leading-8 font-medium">{item.question}</h2>

      {item.evidence[0] ? (
        <blockquote className="flex flex-col gap-2 border-l-2 border-rule py-1 pl-4">
          <p className="font-serif text-[20px] leading-[30px]"><Quote text={item.evidence[0].quote} /></p>
          <div><SourceChip evidence={item.evidence[0]} /></div>
        </blockquote>
      ) : null}

      {context ? <p className="text-muted">{context}</p> : null}

      <div className="grid grid-cols-2 gap-4">
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
              {suggested ? <Tag>Agent suggests</Tag> : null}
              <span className="font-semibold">{o.label}</span>
              <span className="text-muted">{o.effect}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
