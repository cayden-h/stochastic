"use client";

import { useState } from "react";
import { useEdits } from "@/lib/edit-context";
import { anchorKey, canEdit, editedSection, num, parseAmount, rowParts, signed } from "@/lib/edits";
import { clock, plural, toK } from "@/lib/format";
import type { Case, Edit, Result, Section, SourceLine } from "@/lib/types";
import { Button, Card, Label, Mono, Shape } from "./ui";

const SECTIONS: { key: Section; title: string }[] = [
  { key: "balance_sheet", title: "Balance sheet" },
  { key: "income_statement", title: "Income statement" },
  { key: "cash_flow", title: "Cash flow" },
];

const COL = "w-[130px] shrink-0 px-[8px] text-right";

/** The next or previous editable cell in reading order, for Tab while typing. */
function neighbour(key: string, back: boolean): string | null {
  const cells = [...document.querySelectorAll<HTMLElement>("[data-editable]")];
  const i = cells.findIndex((c) => c.dataset.editAnchor === key);
  return cells[i + (back ? -1 : 1)]?.dataset.editAnchor ?? null;
}

/** A source line's filed amount in USD thousands: the agents' value before any edit. */
function sourceK(l: SourceLine): number {
  return toK(l.amount, l.unit);
}

/** Who changed the cell, when, why, and what it taught. Fixed to the viewport so the card's clipping never cuts it. */
function EditTip({ edit, rect, was }: { edit: Edit; rect: DOMRect; was: string }) {
  const learned = edit.policy_id ?? edit.adjustment_id;
  return (
    <div
      role="tooltip"
      className="pointer-events-none fixed z-40 w-[280px] rounded-[10px] bg-ink px-[12px] py-[10px] text-left text-[13px] leading-[18px] font-normal text-paper shadow-lg"
      style={{ top: rect.bottom + 6, left: Math.max(12, rect.right - 280) }}
    >
      <p>Edited by you at {clock(edit.at)} PT. Was {was}.</p>
      <p className="mt-[4px]">{edit.reason_text ? `Reason: ${edit.reason_text}` : "No reason yet. Approval waits for one."}</p>
      {learned ? <p className="mt-[4px] font-mono text-[12px] text-hairline">{edit.policy_id ? "Policy" : "Adjustment"} {learned}</p> : null}
    </div>
  );
}

/**
 * One amount the controller can change: the platform's or the target's value on one source line.
 * States from review-companion.md section 4: default, hover, editing, edited and needs a reason, reason given.
 * An edited cell is not edited again; Undo in Your edits brings the agents' value back first.
 */
function AmountCell({
  anchor, value, edit, editable, line, company, section,
}: {
  anchor: string; value: number; edit?: Edit; editable: boolean; line: string; company: string; section: Section;
}) {
  const ctx = useEdits();
  const [error, setError] = useState<string | null>(null);
  const [tip, setTip] = useState<DOMRect | null>(null);
  const typing = ctx.editing === anchor;
  const flashing = ctx.flash?.key === anchor;

  if (typing) {
    const commit = async (text: string, move?: "next" | "back") => {
      const v = parseAmount(text);
      if (v === null) { setError("Numbers only, in USD thousands"); return; }
      setError(null);
      if (num(v) === num(value)) {
        ctx.setEditing(move ? neighbour(anchor, move === "back") : null);
        return;
      }
      await ctx.apply({ kind: "amount", company, line, section, value: v }, anchor, value);
    };
    return (
      <span className={`${COL} relative -my-[6px] flex flex-col items-end`}>
        <input
          autoFocus
          defaultValue={num(value)}
          inputMode="decimal"
          onFocus={(e) => e.currentTarget.select()}
          aria-label={`${company}, ${line}, USD thousands`}
          aria-invalid={Boolean(error)}
          className={`h-[32px] w-full rounded-chip border bg-white px-[8px] text-right text-[14px] text-ink tabular-nums outline-none ${error ? "border-denied" : "border-ink"}`}
          onChange={() => { if (error) setError(null); }}
          onKeyDown={(e) => {
            if (e.key === "Enter") { e.preventDefault(); commit(e.currentTarget.value); }
            else if (e.key === "Escape") { e.preventDefault(); setError(null); ctx.setEditing(null); }
            else if (e.key === "Tab") { e.preventDefault(); commit(e.currentTarget.value, e.shiftKey ? "back" : "next"); }
          }}
          onBlur={() => { setError(null); if (ctx.editing === anchor) ctx.setEditing(null); }}
        />
        {error ? <span role="alert" className="mt-[2px] text-[11px] whitespace-nowrap text-denied">{error}</span> : null}
      </span>
    );
  }

  const tone = edit
    ? edit.status === "needs_reason"
      ? "bg-escalation-tint shadow-[inset_3px_0_0_var(--color-escalation-bar)]"
      : "bg-white shadow-[inset_3px_0_0_var(--color-clear)]"
    : "";
  // The 3 px bar is straight, so the cell keeps its left edge and only the right corners round.
  const corners = edit ? "rounded-l-none rounded-r-chip" : "rounded-chip";
  const body = (
    <>
      {edit && edit.old_value != null ? (
        <span className="block font-mono text-[12px] leading-[14px] text-muted line-through">{num(edit.old_value)}</span>
      ) : null}
      <span className="inline-flex items-center justify-end gap-[4px] text-forest">
        {num(value)}
        {edit?.status === "reasoned" ? <span className="text-clear"><Shape kind="check" size={10} /></span> : null}
      </span>
    </>
  );
  const hover = edit ? {
    onMouseEnter: (e: React.MouseEvent<HTMLElement>) => setTip(e.currentTarget.getBoundingClientRect()),
    onMouseLeave: () => setTip(null),
    onFocus: (e: React.FocusEvent<HTMLElement>) => {
      // Focus handed back after the bubble closes is not the controller asking for the tooltip.
      if (e.currentTarget.dataset.returning !== undefined) { delete e.currentTarget.dataset.returning; return; }
      setTip(e.currentTarget.getBoundingClientRect());
    },
    onBlur: () => setTip(null),
  } : {};
  const shell = `${COL} -my-[6px] block py-[6px] outline-none focus-visible:outline-1 focus-visible:-outline-offset-1 focus-visible:outline-agent/50 ${corners} ${tone} ${flashing ? "cell-flash" : ""}`;
  return (
    <>
      {editable && !edit ? (
        <button
          data-edit-anchor={anchor}
          data-editable=""
          type="button"
          aria-label={`${company}, ${line}: ${num(value)}. Edit`}
          onClick={() => ctx.setEditing(anchor)}
          className={`${shell} cursor-text transition-colors duration-150 hover:bg-paper hover:shadow-[inset_0_0_0_1px_var(--color-hairline)] focus-visible:outline-2 focus-visible:outline-agent`}
        >
          {body}
        </button>
      ) : (
        <span
          data-edit-anchor={anchor}
          tabIndex={edit ? 0 : undefined}
          aria-label={edit ? `${company}, ${line}: ${num(value)}, edited from ${num(edit.old_value ?? value)}` : undefined}
          className={shell}
          {...hover}
        >
          {body}
        </span>
      )}
      {edit && tip ? <EditTip edit={edit} rect={tip} was={num(edit.old_value ?? value)} /> : null}
    </>
  );
}

/** The Combined cell: always computed. On a row an edit changed, the change from the agents' value sits under it. */
function CombinedCell({ value, change }: { value: number; change: number }) {
  const moved = Math.round(change) !== 0;
  return (
    <span className={`${COL} flex flex-col items-end font-semibold text-forest`}>
      {num(value)}
      {moved ? <span className={`font-mono text-[12px] leading-[14px] font-normal ${change > 0 ? "text-clear" : "text-denied"}`}>{signed(change)}</span> : null}
    </span>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true" className={`shrink-0 transition-transform duration-150 ${open ? "rotate-90" : ""}`}>
      <path d="M3.5 2L6.5 5L3.5 8" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** The combined books, in platform order and USD thousands, with the tie-out state and the run id.
 * `flagged` names the lines a flag is about; they show in amber. While the result waits for approval the platform
 * and target amounts are editable (D19). A row that gathers several target lines opens to edit one of them, because
 * an edit names one source line. */
export function CombinedTable({ result, flagged, kase }: { result: Result; flagged: Set<string>; kase: Case }) {
  const { edits } = useEdits();
  const editable = canEdit(kase);
  const amountEdit = (l: SourceLine) => edits.find((e) => e.kind === "amount" && e.company === l.company && e.line === l.line && e.section === l.section);

  // The table opens on the section of the newest edit, so the edit stays in view; otherwise the balance sheet.
  const newestId = edits[edits.length - 1]?.id ?? null;
  const edited = editedSection(result, edits);
  const [choice, setChoice] = useState<{ open: string; seen: string | null }>({ open: edited ?? "balance_sheet", seen: newestId });
  const open = choice.seen === newestId ? choice.open : edited ?? choice.open;
  const setOpen = (s: string) => setChoice({ open: s, seen: newestId });
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const toggle = (k: string) => setExpanded((s) => { const n = new Set(s); if (n.has(k)) n.delete(k); else n.add(k); return n; });

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
      {editable ? (
        <p className="px-[20px] pt-[4px] text-[13px] text-slate">Click a platform or target amount to change it. Code recomputes every total.</p>
      ) : null}
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
              <Button kind="link" className="text-[13px]" aria-expanded={shown} onClick={() => setOpen(shown ? "" : s.key)}>{shown ? "Hide" : "Show"}</Button>
            </div>
            {shown
              ? rows.map((r, i) => {
                  const total = /^total/i.test(r.line);
                  const section = r.section as Section;
                  const parts = rowParts(r, kase, edits);
                  const rowKey = `${r.section}|${r.line}`;
                  const many = parts.targets.length > 1;
                  const hasSubEdit = many && parts.targets.some((t) => amountEdit(t));
                  const isOpen = many && (expanded.has(rowKey) || hasSubEdit);
                  const single = parts.targets.length === 1 ? parts.targets[0] : null;
                  return (
                    <div key={`${rowKey}-${i}`} className="border-t border-line">
                      <div className={`flex w-full items-center gap-[12px] px-[20px] py-[12px] text-[14px] ${total ? "font-semibold" : ""}`}>
                        {many ? (
                          <button
                            type="button"
                            onClick={() => toggle(rowKey)}
                            disabled={hasSubEdit}
                            aria-expanded={isOpen}
                            className="group flex min-w-0 flex-1 items-center gap-[6px] text-left text-body enabled:hover:text-forest disabled:cursor-default"
                          >
                            <span className={`truncate ${flagged.has(r.line) ? "text-escalation" : ""}`}>{r.line}</span>
                            <span className="text-slate"><Chevron open={isOpen} /></span>
                            <Mono className="shrink-0">{plural(parts.targets.length, `${kase.deal.target} line`)}</Mono>
                          </button>
                        ) : (
                          <span className={`min-w-0 flex-1 truncate ${flagged.has(r.line) ? "text-escalation" : "text-body"}`} title={single ? `${r.line}, from ${kase.deal.target}'s ${single.line}` : r.line}>{r.line}</span>
                        )}
                        {parts.platform ? (
                          <AmountCell
                            anchor={anchorKey("amount", parts.platform.company, r.section, parts.platform.line)}
                            value={r.platform} edit={amountEdit(parts.platform)} editable={editable}
                            company={parts.platform.company} line={parts.platform.line} section={section}
                          />
                        ) : <span className={`${COL} text-forest`}>{num(r.platform)}</span>}
                        {single ? (
                          <AmountCell
                            anchor={anchorKey("amount", single.company, r.section, single.line)}
                            value={r.target} edit={amountEdit(single)} editable={editable}
                            company={single.company} line={single.line} section={section}
                          />
                        ) : many && editable && !isOpen ? (
                          <button
                            type="button"
                            onClick={() => toggle(rowKey)}
                            aria-label={`${r.line}: open its ${plural(parts.targets.length, `${kase.deal.target} line`)} to edit one`}
                            className={`${COL} -my-[6px] cursor-pointer rounded-chip py-[6px] text-forest transition-colors duration-150 hover:bg-paper hover:shadow-[inset_0_0_0_1px_var(--color-hairline)]`}
                          >
                            {num(r.target)}
                          </button>
                        ) : <span className={`${COL} text-forest`}>{num(r.target)}</span>}
                        <CombinedCell value={r.combined} change={parts.change} />
                      </div>
                      {isOpen ? parts.targets.map((t) => {
                        const e = amountEdit(t);
                        return (
                          <div key={t.id} className="flex w-full items-center gap-[12px] py-[8px] pr-[20px] pl-[36px] text-[13px] text-slate last:pb-[14px]">
                            <span className="min-w-0 flex-1 truncate" title={`${kase.deal.target}: ${t.line}`}>{t.line}</span>
                            <span className={COL} />
                            <AmountCell
                              anchor={anchorKey("amount", t.company, t.section, t.line)}
                              value={e?.new_value ?? sourceK(t)} edit={e} editable={editable}
                              company={t.company} line={t.line} section={t.section}
                            />
                            <span className={COL} />
                          </div>
                        );
                      }) : null}
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
