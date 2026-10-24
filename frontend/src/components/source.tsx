"use client";

import { createContext, useContext, useState } from "react";
import { useDeal } from "@/lib/deal-context";
import type { Evidence } from "@/lib/types";
import { Button, Label, Shape } from "./ui";

const Ctx = createContext<{ open: (e: Evidence) => void; close: () => void; evidence: Evidence | null } | null>(null);

export function SourceProvider({ children }: { children: React.ReactNode }) {
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  return (
    <Ctx.Provider value={{ open: setEvidence, close: () => setEvidence(null), evidence }}>{children}</Ctx.Provider>
  );
}

export function useSource() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSource must be used inside SourceProvider");
  return v;
}

/** A source chip opens the Source slide-over. It never changes the route. */
export function SourceChip({ evidence, label }: { evidence: Evidence; label?: string }) {
  const { open } = useSource();
  return (
    <button
      onClick={() => open(evidence)}
      className="inline-flex items-center rounded-chip border border-rule bg-paper px-2 py-1 font-mono text-[14px] leading-5 hover:bg-card"
    >
      {label ?? `Credit agreement, p. ${evidence.page ?? "?"}`}
    </button>
  );
}

export function SourcePanel() {
  const { evidence, close } = useSource();
  const { facts, clauses } = useDeal();
  if (!evidence) return null;

  const match = [...facts, ...clauses].find((x) => x.evidence.quote === evidence.quote);
  const checked = match?.checked ?? false;

  return (
    <div className="fixed inset-0 z-10 flex justify-end" role="dialog" aria-label="Source">
      <button aria-label="Close source" className="absolute inset-0 bg-ink/45" onClick={close} />
      <aside className="relative flex h-full w-[560px] flex-col gap-6 overflow-y-auto border-l border-rule bg-card p-8">
        <div className="flex items-center">
          <Label>Source</Label>
          <span className="flex-1" />
          <Button kind="link" onClick={close}>Close</Button>
        </div>
        <div className="flex flex-col gap-2">
          <h2 className="font-serif text-[26px] leading-8 font-medium">Credit agreement (illustrative)</h2>
          <span className="font-mono text-[14px] leading-5 text-muted">Page {evidence.page ?? "?"}</span>
        </div>
        <div className="flex flex-col gap-3 rounded-chip border border-hairline bg-paper p-6 font-serif text-[20px] leading-[30px]">
          <p className="text-muted">...</p>
          <p className="border-l-4 border-denied bg-denied-tint px-3 py-2">{evidence.quote}</p>
          <p className="text-muted">...</p>
          {[0, 1, 2].map((i) => <div key={i} className="h-2 rounded-chip bg-hairline" />)}
        </div>
        <div className={`flex items-center gap-2 rounded-chip px-4 py-3 font-semibold ${checked ? "bg-clear-tint text-clear" : "bg-paper text-muted"}`}>
          {checked ? <Shape kind="check" size={16} /> : null}
          {checked ? `Quote found on page ${evidence.page ?? "?"}. Checked by code.` : "Not checked by code yet."}
        </div>
      </aside>
    </div>
  );
}
