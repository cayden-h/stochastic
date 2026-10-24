"use client";

import { useState } from "react";
import type { Result } from "@/lib/types";
import { plural } from "@/lib/format";
import { Button, Card, Label, Mono, Shape } from "./ui";

const SECTIONS: { key: string; title: string }[] = [
  { key: "balance_sheet", title: "Balance sheet" },
  { key: "income_statement", title: "Income statement" },
  { key: "cash_flow", title: "Cash flow" },
];

function num(v: number): string {
  const r = Math.round(v);
  return r < 0 ? `(${Math.abs(r).toLocaleString("en-US")})` : r.toLocaleString("en-US");
}

const COL = "w-[130px] shrink-0 text-right";

/** The combined books, in platform order and USD thousands, with the tie-out state and the run id.
 * `flagged` names the lines a flag is about; they show in amber. */
export function CombinedTable({ result, flagged }: { result: Result; flagged: Set<string> }) {
  const [open, setOpen] = useState<string>("balance_sheet");
  const consolidateRun = result.run_ids_by_tool.consolidate;
  return (
    <Card className="flex w-full flex-col">
      <div className="flex w-full items-center gap-[12px] px-[20px] pt-[14px]">
        <h2 className="flex-1 text-[16px] font-semibold text-forest">Combined books</h2>
        <span className={`inline-flex items-center gap-[6px] text-[13px] font-semibold ${result.tie_out_ok ? "text-clear" : "text-denied"}`}>
          <Shape kind={result.tie_out_ok ? "check" : "cross"} size={10} />
          {result.tie_out_ok ? "Ties out" : "Does not tie out"}
        </span>
        <Mono>USD thousands &middot; {consolidateRun}</Mono>
      </div>
      <div className="flex w-full gap-[12px] border-b border-line px-[20px] py-[12px]">
        <Label className="flex-1">Line</Label>
        <Label className={COL}>Platform</Label>
        <Label className={COL}>Target</Label>
        <Label className={COL}>Combined</Label>
      </div>
      {SECTIONS.map((s) => {
        const rows = result.rows.filter((r) => r.section === s.key);
        if (!rows.length) return null;
        const shown = open === s.key;
        return (
          <div key={s.key} className="border-b border-line last:border-b-0">
            <div className="flex items-center gap-[12px] bg-fog/60 px-[20px] py-[8px]">
              <span className="text-[13px] font-semibold text-body">{s.title}</span>
              <Mono>{plural(rows.length, "line")}</Mono>
              <span className="flex-1" />
              <Button kind="link" className="text-[13px]" onClick={() => setOpen(shown ? "" : s.key)}>{shown ? "Hide" : "Show"}</Button>
            </div>
            {shown
              ? rows.map((r, i) => {
                  const total = /^total/i.test(r.line);
                  return (
                    <div
                      key={`${r.section}-${r.line}-${i}`}
                      className={`flex w-full items-center gap-[12px] border-t border-line px-[20px] py-[12px] text-[14px] ${total ? "font-semibold" : ""}`}
                    >
                      <span className={`min-w-0 flex-1 truncate ${flagged.has(r.line) ? "text-escalation" : "text-body"}`} title={r.line}>{r.line}</span>
                      <span className={`${COL} text-forest`}>{num(r.platform)}</span>
                      <span className={`${COL} text-forest`}>{num(r.target)}</span>
                      <span className={`${COL} font-semibold text-forest`}>{num(r.combined)}</span>
                    </div>
                  );
                })
              : null}
          </div>
        );
      })}
    </Card>
  );
}

/** The books card before the Preparer has combined anything: the console shows no number it did not get from a tool. */
export function CombinedPending({ text }: { text: string }) {
  return (
    <Card className="flex w-full flex-col">
      <div className="flex w-full items-center px-[20px] pt-[14px]">
        <h2 className="flex-1 text-[16px] font-semibold text-forest">Combined books</h2>
        <Mono>USD thousands &middot; not run</Mono>
      </div>
      <p className="px-[20px] pt-[12px] pb-[16px] text-[14px] text-slate">{text}</p>
    </Card>
  );
}
