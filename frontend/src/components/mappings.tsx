"use client";

import { useEffect, useRef, useState } from "react";
import { useEdits } from "@/lib/edit-context";
import { anchorKey, effectivePlatformLine } from "@/lib/edits";
import { isLearned, isLearnedTag, isUnsure, pct } from "@/lib/format";
import type { Edit, Mapping, SourceLine } from "@/lib/types";
import { Card, Label, Mono, Shape, Tag } from "./ui";

export type MappingFilter = "all" | "unsure" | "policy" | "edited";

const FIRST = 10;

/** The edit that changed this target line, if any: a remap, or an amount edit made on the Case. */
export function editOf(line: SourceLine | undefined, edits: Edit[], kind?: Edit["kind"]): Edit | undefined {
  if (!line) return undefined;
  return edits.find((e) => (!kind || e.kind === kind) && e.company === line.company && e.line === line.line && e.section === line.section);
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
 * Read-only: a remap is made on the Review page (D19, V3-7.7). It is an edit and does not change the Mapper's record,
 * so the edit's new line is shown over it.
 */
export function Mappings({
  mappings, lines, filter, asking, received = {}, live = false,
}: {
  mappings: Mapping[]; lines: SourceLine[]; filter: MappingFilter;
  /** The lines an open question is about (openQuestionLines): those rows are unsure and wait on the controller. */
  asking: Set<string>;
  /** When each mapping arrived on the stream, in ms: rows that arrive while the page is open fade in. */
  received?: Record<string, number>;
  /** The Mapper is storing mappings now: every row shows, and the page follows the newest one. */
  live?: boolean;
}) {
  const { edits } = useEdits();
  const [expanded, setAll] = useState(false);
  const all = expanded || live;
  const [mounted] = useState(() => Date.now());
  // The newest row that arrived while the page was open holds a teal wash for about a second.
  let newest: string | null = null;
  for (const m of mappings) {
    const r = received[m.id] ?? 0;
    if (r > mounted && (newest === null || r > (received[newest] ?? 0))) newest = m.id;
  }
  // Follow the newest row while the Mapper works, until the reader scrolls on their own.
  const newestRef = useRef<HTMLDivElement>(null);
  const following = useRef(true);
  useEffect(() => {
    const stop = () => { following.current = false; };
    window.addEventListener("wheel", stop, { passive: true });
    window.addEventListener("touchmove", stop, { passive: true });
    window.addEventListener("keydown", stop);
    return () => {
      window.removeEventListener("wheel", stop);
      window.removeEventListener("touchmove", stop);
      window.removeEventListener("keydown", stop);
    };
  }, []);
  useEffect(() => {
    if (live && newest && following.current) newestRef.current?.scrollIntoView({ block: "nearest" });
  }, [live, newest]);
  const byId = new Map(lines.map((l) => [l.id, l]));
  const rows = filter === "unsure" ? mappings.filter((m) => isUnsure(m, asking))
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
          const unsure = isUnsure(m, asking);
          const line = byId.get(m.target_line_id);
          const total = line?.is_total ?? false;
          const remap = editOf(line, edits, "remap");
          const amount = editOf(line, edits, "amount");
          const now = effectivePlatformLine(m, line, edits);
          return (
            <div
              key={m.id}
              ref={m.id === newest ? newestRef : undefined}
              data-mapping-id={m.id}
              className={`flex w-full items-center gap-[12px] border-b border-line px-[20px] py-[12px] text-[14px] last:border-b-0 ${unsure && !remap ? "bg-amber-tint" : ""} ${
                m.id === newest ? "row-new" : (received[m.id] ?? 0) > mounted ? "row-in" : ""
              }`}
            >
              <span className="flex min-w-0 flex-1 items-center gap-[8px] font-medium text-body" title={m.target_line}>
                <span className="truncate">{m.target_line}</span>
                {amount ? <Mono className="shrink-0">amount edited</Mono> : null}
              </span>
              <span className={`flex min-w-0 flex-1 items-center gap-[8px] ${unsure ? "font-semibold text-escalation" : now ? "text-forest" : "text-faint"}`} title={m.reason}>
                {remap ? <Remapped edit={remap} />
                  : <span className="truncate">{now ?? (unsure ? "?" : "Total, not mapped")}</span>}
                {isLearned(m) && !remap ? <Tag tone="agent">Learned</Tag> : null}
                {m.approved_by && !remap ? <Mono>by you</Mono> : null}
                {unsure && !remap ? <Tag tone="escalation">Needs you</Tag> : null}
              </span>
              <span className={`w-[130px] shrink-0 font-ui font-semibold ${remap || total ? "text-slate" : unsure ? "text-escalation" : "text-clear"}`}>
                {remap ? "Your edit" : total ? "Total" : pct(m.confidence)}
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
              : filter === "unsure" ? "No line waits on you. The Mapper placed every line or you answered its question."
              : filter === "edited" ? "No line was edited. Remap a line or change an amount on the Review page."
              : live ? "The Mapper is reading the lines. They appear here as the gateway stores them." : "The Mapper has not run."}
          </p>
        ) : null}
      </Card>
      {rows.length > FIRST && !live ? (
        <p className="font-mono text-[12px] text-slate">
          {all ? rows.length : FIRST} of {rows.length} &middot;{" "}
          <button className="hover:text-forest hover:underline" onClick={() => setAll((v) => !v)}>{all ? "Show fewer" : "Show all"}</button>
        </p>
      ) : null}
    </>
  );
}
