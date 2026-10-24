"use client";

import { useState } from "react";
import { useEdits } from "@/lib/edit-context";
import { anchorKey, effectivePlatformLine } from "@/lib/edits";
import { isLearned, isLearnedTag, pct } from "@/lib/format";
import type { Edit, Mapping, SourceLine } from "@/lib/types";
import { Card, Label, Mono, Shape, Tag } from "./ui";

export type MappingFilter = "all" | "unsure" | "policy" | "edited";

/** Unsure: in a mapping question, or below 0.80 confidence. */
export function isUnsure(m: Mapping): boolean {
  return m.flagged || m.confidence < 0.8;
}

const FIRST = 10;

/** The edit that changed this target line, if any: a remap, or an amount edit made on the Case. */
export function editOf(line: SourceLine | undefined, edits: Edit[], kind?: Edit["kind"]): Edit | undefined {
  if (!line) return undefined;
  return edits.find((e) => (!kind || e.kind === kind) && e.company === line.company && e.line === line.line && e.section === line.section);
}

function Chevron() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true" className="pointer-events-none absolute top-1/2 right-[8px] -translate-y-1/2 text-slate">
      <path d="M2 3.5L5 6.5L8 3.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** The Platform line as a dropdown of the platform's lines in the same section. Picking one remaps the target line. */
function PlatformSelect({ line, value, options, unsure }: { line: SourceLine; value: string | null; options: string[]; unsure: boolean }) {
  const ctx = useEdits();
  const [busy, setBusy] = useState(false);
  const anchor = anchorKey("remap", line.company, line.section, line.line);
  const list = value && !options.includes(value) ? [value, ...options] : options;
  return (
    <span className="relative flex min-w-0 flex-1">
      <select
        data-edit-anchor={anchor}
        aria-label={`Platform line for ${line.line}`}
        value={value ?? ""}
        disabled={busy}
        onChange={async (e) => {
          setBusy(true);
          await ctx.apply({ kind: "remap", company: line.company, line: line.line, section: line.section, platform_line: e.target.value }, anchor);
          setBusy(false);
        }}
        className={`-ml-[8px] w-full min-w-0 cursor-pointer appearance-none truncate rounded-chip bg-transparent py-[4px] pr-[24px] pl-[8px] text-[14px] transition-colors duration-150 hover:bg-paper hover:shadow-[inset_0_0_0_1px_var(--color-hairline)] focus-visible:outline-2 focus-visible:outline-agent disabled:opacity-50 ${
          unsure ? "font-semibold text-escalation" : "text-forest"
        } ${ctx.flash?.key === anchor ? "cell-flash" : ""}`}
      >
        {value ? null : <option value="" disabled>Not mapped</option>}
        {list.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
      <Chevron />
    </span>
  );
}

/** A remapped line: the agents' platform line struck through above the new one, amber until it has a reason. */
function Remapped({ edit }: { edit: Edit }) {
  const ctx = useEdits();
  const anchor = anchorKey("remap", edit.company, edit.section, edit.line);
  const needs = edit.status === "needs_reason";
  return (
    <span
      data-edit-anchor={anchor}
      tabIndex={0}
      title={`Edited by you. ${edit.reason_text ? `Reason: ${edit.reason_text}.` : "No reason yet."}${edit.policy_id ? ` Policy ${edit.policy_id}.` : ""}`}
      className={`-my-[6px] -ml-[8px] flex min-w-0 flex-1 flex-col rounded-l-none rounded-r-chip py-[6px] outline-none focus-visible:outline-1 focus-visible:-outline-offset-1 focus-visible:outline-agent/50 pr-[8px] pl-[11px] ${
        needs ? "bg-escalation-tint shadow-[inset_3px_0_0_var(--color-escalation-bar)]" : "shadow-[inset_3px_0_0_var(--color-clear)]"
      } ${ctx.flash?.key === anchor ? "cell-flash" : ""}`}
    >
      <span className="truncate font-mono text-[12px] leading-[14px] text-muted line-through">{edit.old_platform_line ?? "Not mapped"}</span>
      <span className="flex min-w-0 items-center gap-[4px] font-normal text-forest">
        <span className="truncate">{edit.new_platform_line}</span>
        {needs ? null : <span className="text-clear"><Shape kind="check" size={10} /></span>}
      </span>
    </span>
  );
}

/**
 * The Mapper's line-by-line answer: each target line, the platform line it goes to, and how sure it was.
 * A "Learned" chip marks a mapping or a tag the gateway tied to a learned policy: the controller decided it once.
 * While the result waits for approval, the Platform line is a dropdown. A remap is an edit (D19) and does not change
 * the Mapper's record, so the edit's new line is shown over it.
 */
export function Mappings({
  mappings, lines, filter, platform, editable,
}: {
  mappings: Mapping[]; lines: SourceLine[]; filter: MappingFilter; platform: string; editable: boolean;
}) {
  const { edits } = useEdits();
  const [all, setAll] = useState(false);
  const byId = new Map(lines.map((l) => [l.id, l]));
  const options = (section: string) => [...new Set(lines.filter((l) => l.company === platform && l.section === section && !l.is_total).map((l) => l.line))];
  const rows = filter === "unsure" ? mappings.filter(isUnsure)
    : filter === "policy" ? mappings.filter(isLearned)
    : filter === "edited" ? mappings.filter((m) => editOf(byId.get(m.target_line_id), edits))
    : mappings;
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
          const line = byId.get(m.target_line_id);
          const remap = editOf(line, edits, "remap");
          const amount = editOf(line, edits, "amount");
          const now = effectivePlatformLine(m, line, edits);
          const selectable = editable && line && !line.is_total && !remap;
          return (
            <div
              key={m.id}
              className={`flex w-full items-center gap-[12px] border-b border-line px-[20px] py-[12px] text-[14px] last:border-b-0 ${unsure && !remap ? "bg-amber-tint" : ""}`}
            >
              <span className="flex min-w-0 flex-1 items-center gap-[8px] font-medium text-body" title={m.target_line}>
                <span className="truncate">{m.target_line}</span>
                {amount ? <Mono className="shrink-0">amount edited</Mono> : null}
              </span>
              <span className={`flex min-w-0 flex-1 items-center gap-[8px] ${unsure ? "font-semibold text-escalation" : now ? "text-forest" : "text-faint"}`} title={m.reason}>
                {remap ? <Remapped edit={remap} />
                  : selectable ? <PlatformSelect line={line} value={now} options={options(line.section)} unsure={unsure} />
                  : <span className="truncate">{now ?? (unsure ? "?" : "Total, not mapped")}</span>}
                {isLearned(m) && !remap ? <Tag tone="agent">Learned</Tag> : null}
                {m.approved_by && !remap ? <Mono>by you</Mono> : null}
              </span>
              <span className={`w-[130px] shrink-0 font-ui font-semibold ${remap ? "text-slate" : unsure ? "text-escalation" : "text-clear"}`}>
                {remap ? "Your edit" : pct(m.confidence)}
              </span>
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
            {filter === "policy" ? "No line was settled by an earlier answer yet."
              : filter === "unsure" ? "The Mapper was sure of every line."
              : filter === "edited" ? "No line was edited. Pick a platform line to remap one."
              : "The Mapper has not run."}
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
