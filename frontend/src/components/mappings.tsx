"use client";

import { useState } from "react";
import { isLearned, isLearnedTag, pct } from "@/lib/format";
import type { Mapping, SourceLine } from "@/lib/types";
import { Card, Label, Mono, Tag } from "./ui";

export type MappingFilter = "all" | "unsure" | "policy";

/** Unsure: in a mapping question, or below 0.80 confidence. */
export function isUnsure(m: Mapping): boolean {
  return m.flagged || m.confidence < 0.8;
}

const FIRST = 10;

/**
 * The Mapper's line-by-line answer: each target line, the platform line it goes to, and how sure it was.
 * A "Learned" chip marks a mapping or a tag the gateway tied to a learned policy: the controller decided it once.
 */
export function Mappings({ mappings, lines, filter }: { mappings: Mapping[]; lines: SourceLine[]; filter: MappingFilter }) {
  const [all, setAll] = useState(false);
  const rows = filter === "unsure" ? mappings.filter(isUnsure) : filter === "policy" ? mappings.filter(isLearned) : mappings;
  const learnedTags = filter === "policy" ? lines.filter(isLearnedTag) : [];
  const shown = all ? rows : rows.slice(0, FIRST);
  return (
    <>
      <Card className="flex w-full flex-col">
        <div className="flex w-full gap-[12px] border-b border-line px-[20px] py-[12px]">
          <Label className="min-w-0 flex-1">Target line</Label>
          <Label className="min-w-0 flex-1">Platform line</Label>
          <Label className="w-[130px] shrink-0">Confidence</Label>
        </div>
        {shown.map((m) => {
          const unsure = isUnsure(m);
          return (
            <div
              key={m.id}
              className={`flex w-full items-center gap-[12px] border-b border-line px-[20px] py-[12px] text-[14px] last:border-b-0 ${unsure ? "bg-amber-tint" : ""}`}
            >
              <span className="min-w-0 flex-1 truncate font-medium text-body" title={m.target_line}>{m.target_line}</span>
              <span
                className={`flex min-w-0 flex-1 items-center gap-[8px] ${unsure ? "font-semibold text-escalation" : m.platform_line ? "text-forest" : "text-faint"}`}
                title={m.reason}
              >
                <span className="truncate">{m.platform_line ?? (unsure ? "?" : "Total, not mapped")}</span>
                {isLearned(m) ? <Tag tone="agent">Learned</Tag> : null}
                {m.approved_by ? <Mono>by you</Mono> : null}
              </span>
              <span className={`w-[130px] shrink-0 font-ui font-semibold ${unsure ? "text-escalation" : "text-clear"}`}>{pct(m.confidence)}</span>
            </div>
          );
        })}
        {learnedTags.map((l) => (
          <div key={l.id} className="flex w-full items-center gap-[12px] border-b border-line px-[20px] py-[12px] text-[14px] last:border-b-0">
            <span className="min-w-0 flex-1 truncate font-medium text-body" title={l.line}>{l.line}</span>
            <span className="flex min-w-0 flex-1 items-center gap-[8px] text-forest" title={l.covenant_note ?? ""}>
              <span className="truncate">{l.covenant_tag === "debt" ? "Counts as debt" : l.covenant_tag === "not_debt" ? "Not debt" : l.covenant_tag}</span>
              <Tag tone="agent">Learned</Tag>
            </span>
            <Mono className="w-[130px] shrink-0">lender tag</Mono>
          </div>
        ))}
        {!shown.length && !learnedTags.length ? (
          <p className="px-[20px] py-[14px] text-[14px] text-slate">
            {filter === "policy" ? "No line was settled by an earlier answer yet." : filter === "unsure" ? "The Mapper was sure of every line." : "The Mapper has not run."}
          </p>
        ) : null}
      </Card>
      {rows.length > FIRST ? (
        <p className="font-mono text-[12px] text-slate">
          {all ? rows.length : FIRST} of {rows.length} &middot;{" "}
          <button className="hover:text-forest hover:underline" onClick={() => setAll((v) => !v)}>{all ? "Show fewer" : "Show all"}</button>
        </p>
      ) : null}
    </>
  );
}
