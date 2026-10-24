"use client";

import Link from "next/link";
import { useState } from "react";
import { EscalationCard } from "@/components/escalation-card";
import { Button, Shape } from "@/components/ui";
import { api } from "@/lib/api";
import { useDeal } from "@/lib/deal-context";

/** Desk: the one question that needs the reviewer now. */
export default function Desk() {
  const { items, refresh } = useDeal();
  const [busy, setBusy] = useState(false);
  const [showAnswered, setShowAnswered] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const open = items.find((i) => i.state === "NEEDS_INFO" && !i.payload.held);
  const answered = items.filter((i) => i.answer);
  const pendingRecommendation = items.find((i) => i.type === "recommend" && i.state === "PROPOSED");

  async function act(fn: () => Promise<unknown>) {
    setBusy(true); setNote(null);
    try { await fn(); await refresh(); } catch (e) { setNote(e instanceof Error ? e.message : "Action failed"); }
    finally { setBusy(false); }
  }

  return (
    <div className="mx-auto flex max-w-[960px] flex-col gap-6 pt-6 pb-12">
      <header className="flex flex-col gap-2">
        <h1 className="font-serif text-[40px] leading-[48px] font-medium">
          {open ? "One question needs you." : "Nothing needs you right now."}
        </h1>
        <p className="flex items-center gap-2 text-muted">
          <span className="text-agent"><Shape kind="circle" size={10} /></span>
          {open ? "The agents wait on your answer for this branch." : "The agents have no open questions."}
        </p>
      </header>

      {note ? <p role="alert" className="rounded-chip bg-denied-tint px-4 py-3 font-semibold text-denied">{note}</p> : null}

      {open ? (
        <EscalationCard
          item={open}
          busy={busy}
          onAnswer={(id) => act(() => api.answer(open.id, id))}
          onHold={() => act(() => api.hold(open.id))}
        />
      ) : pendingRecommendation ? (
        <div>
          <Link href="/plans" className="inline-flex min-h-11 items-center rounded-chip bg-ink px-6 py-3 font-semibold text-paper hover:bg-code">
            Review the plans
          </Link>
        </div>
      ) : null}

      {answered.length > 0 ? (
        <section className="flex flex-col gap-2">
          <span className="text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] text-muted">Answered ({answered.length})</span>
          <div className="flex items-center gap-3 rounded-chip border border-hairline bg-card px-4 py-2">
            <span className="text-clear"><Shape kind="check" /></span>
            <span className="flex-1">
              {showAnswered
                ? null
                : `${answered[answered.length - 1].escalation ?? "Item"}: ${
                    answered[answered.length - 1].options.find((o) => o.id === answered[answered.length - 1].answer)?.label ?? "answered"
                  }.`}
            </span>
            <Button kind="link" onClick={() => setShowAnswered((v) => !v)}>{showAnswered ? "Hide" : "Show"}</Button>
          </div>
          {showAnswered
            ? answered.map((i) => (
                <div key={i.id} className="flex items-center gap-3 rounded-chip border border-hairline bg-card px-4 py-2">
                  <span className="text-clear"><Shape kind="check" /></span>
                  <span>{i.escalation}: {i.question} <strong>{i.options.find((o) => o.id === i.answer)?.label}</strong></span>
                </div>
              ))
            : null}
        </section>
      ) : null}
    </div>
  );
}
