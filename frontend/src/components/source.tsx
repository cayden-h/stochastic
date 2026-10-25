"use client";

import { createContext, useContext, useState } from "react";
import { useDeal } from "@/lib/deal-context";
import type { Evidence, SourceLine } from "@/lib/types";
import { Button, Label, Mono } from "./ui";

interface Source { evidence: Evidence; line?: SourceLine }

const Ctx = createContext<{ open: (s: Source) => void; close: () => void; source: Source | null } | null>(null);

export function SourceProvider({ children }: { children: React.ReactNode }) {
  const [source, setSource] = useState<Source | null>(null);
  return <Ctx.Provider value={{ open: setSource, close: () => setSource(null), source }}>{children}</Ctx.Provider>;
}

export function useSource() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSource must be used inside SourceProvider");
  return v;
}

/** A source chip opens the Source slide-over. It never changes the route. */
export function SourceChip({ evidence, line, label }: { evidence: Evidence; line?: SourceLine; label?: string }) {
  const { open } = useSource();
  return (
    <button
      onClick={() => open({ evidence, line })}
      className="inline-flex max-w-full items-center truncate rounded-chip border border-rule bg-paper px-2 py-1 text-left font-mono text-[14px] leading-5 hover:bg-card"
      title={evidence.document_id ?? undefined}
    >
      {label ?? evidence.document_id ?? "Source"}
    </button>
  );
}

/** The exact quote and the document it comes from. The filing's note on a line is shown when there is one. */
export function SourcePanel() {
  const { source, close } = useSource();
  const { kase, deals } = useDeal();
  if (!source) return null;
  const sample = deals.find((d) => d.id === kase?.deal.id)?.data_source === "sample";
  const { evidence, line } = source;
  return (
    <div className="fixed inset-0 z-10 flex justify-end" role="dialog" aria-label="Source">
      <button aria-label="Close source" className="absolute inset-0 bg-ink/45" onClick={close} />
      <aside className="relative flex h-full w-full max-w-[560px] flex-col gap-6 overflow-y-auto border-l border-rule bg-card p-8">
        <div className="flex items-center">
          <Label>Source</Label>
          <span className="flex-1" />
          <Button kind="link" onClick={close}>Close</Button>
        </div>
        <div className="flex flex-col gap-2">
          <h2 className="font-serif text-[26px] leading-8 font-medium">{evidence.document_id ?? "Document"}</h2>
          {evidence.page != null ? <Mono>Page {evidence.page}</Mono> : null}
        </div>
        <blockquote className="rounded-chip border border-hairline bg-paper p-6 font-serif text-[20px] leading-[30px]">
          <p className="border-l-4 border-escalation-bar px-3 py-1">{`"${evidence.quote}"`}</p>
        </blockquote>
        {line ? (
          <div className="flex flex-col gap-2">
            <Label>The line</Label>
            <p><span className="font-semibold">{line.line}</span> <Mono>{line.company}, {line.period}</Mono></p>
            {line.note ? <p className="text-muted">{line.note}</p> : null}
            <Mono>{line.source_ref}</Mono>
          </div>
        ) : null}
        <p className="rounded-chip bg-paper px-4 py-3 text-muted">
          {sample
            ? "A sample case: its figures are made up, not from a filing. The quote is the agreement the sample uses. The reading of the agreement is ours, and no lender has checked it."
            : "Quoted from the public filing. Figures from public SEC filings. The reading of the agreement is ours, and no lender has checked it."}
        </p>
      </aside>
    </div>
  );
}
