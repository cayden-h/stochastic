"use client";

import { useState } from "react";
import type { Result } from "@/lib/types";
import { plural } from "@/lib/format";
import { Button, Label, Mono, Shape } from "./ui";

const SECTIONS: { key: string; title: string }[] = [
  { key: "balance_sheet", title: "Balance sheet" },
  { key: "income_statement", title: "Income statement" },
  { key: "cash_flow", title: "Cash flow" },
];

function num(v: number): string {
  const r = Math.round(v);
  return r < 0 ? `(${Math.abs(r).toLocaleString("en-US")})` : r.toLocaleString("en-US");
}

/** The combined books, in platform order and USD thousands, with the tie-out state and the run id. */
export function CombinedTable({ result, platform, target }: { result: Result; platform: string; target: string }) {
  const [open, setOpen] = useState<string>("");  // collapsed: the verdict above carries the figures that matter
  const consolidateRun = result.run_ids_by_tool.consolidate;
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <h2 className="font-serif text-[26px] leading-8 font-medium">Combined books</h2>
        <span className={`inline-flex items-center gap-2 rounded-chip px-3 py-1 font-semibold ${result.tie_out_ok ? "bg-clear-tint text-clear" : "bg-denied-tint text-denied"}`}>
          <Shape kind={result.tie_out_ok ? "check" : "cross"} />
          {result.tie_out_ok ? "Ties out" : "Does not tie out"}
        </span>
        <Mono>USD thousands. {consolidateRun}</Mono>
      </div>

      <div className="overflow-x-auto rounded-card border border-rule bg-card">
        <div className="min-w-[680px]">
        <div className="grid grid-cols-[1fr_160px_160px_160px] gap-4 border-b border-hairline px-4 py-2">
          <span><Label>Line</Label></span>
          <span className="text-right"><Label>{platform}</Label></span>
          <span className="text-right"><Label>{target}</Label></span>
          <span className="text-right"><Label>Combined</Label></span>
        </div>
        {SECTIONS.map((s) => {
          const rows = result.rows.filter((r) => r.section === s.key);
          if (!rows.length) return null;
          const shown = open === s.key;
          return (
            <div key={s.key} className="border-b border-hairline last:border-b-0">
              <div className="flex items-center gap-3 bg-paper px-4 py-2">
                <span className="font-semibold">{s.title}</span>
                <Mono>{plural(rows.length, "line")}</Mono>
                <span className="flex-1" />
                <Button kind="link" onClick={() => setOpen(shown ? "" : s.key)}>{shown ? "Hide" : "Show"}</Button>
              </div>
              {shown
                ? rows.map((r, i) => (
                    <div
                      key={`${r.section}-${r.line}-${i}`}
                      className={`grid grid-cols-[1fr_160px_160px_160px] gap-4 px-4 py-1 tabular-nums ${/^total/i.test(r.line) ? "border-t border-hairline font-semibold" : ""}`}
                    >
                      <span className="truncate" title={r.line}>{r.line}</span>
                      <span className="text-right">{num(r.platform)}</span>
                      <span className="text-right">{num(r.target)}</span>
                      <span className="text-right">{num(r.combined)}</span>
                    </div>
                  ))
                : null}
            </div>
          );
        })}
        </div>
      </div>
    </section>
  );
}
