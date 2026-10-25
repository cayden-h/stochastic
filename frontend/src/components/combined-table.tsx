"use client";

import { useState } from "react";
import { useEdits } from "@/lib/edit-context";
import { editedSection, num, rowParts, signed } from "@/lib/edits";
import { clock, plural, toK } from "@/lib/format";
import type { Case, Edit, Result, Section, SourceLine } from "@/lib/types";
import { Button, Card, Label, Mono, Shape } from "./ui";

const SECTIONS: { key: Section; title: string }[] = [
  { key: "balance_sheet", title: "Balance sheet" },
  { key: "income_statement", title: "Income statement" },
  { key: "cash_flow", title: "Cash flow" },
];

const COL = "w-[130px] shrink-0 px-[8px] text-right";

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
 * One amount on the Case's read-only books. An edited cell (made on the Review page) keeps its states from
 * review-companion.md section 4: amber with a bar while it needs a reason, a teal bar and a check once it has one.
 * Hovering or focusing an edited cell says who changed it, when, and why.
 */
function AmountCell({ value, edit }: { value: number; edit?: Edit }) {
  const [tip, setTip] = useState<DOMRect | null>(null);
  const tone = edit
    ? edit.status === "needs_reason"
      ? "bg-escalation-tint shadow-[inset_3px_0_0_var(--color-edit-bar)]"
      : "bg-white shadow-[inset_3px_0_0_var(--color-forest)]"
    : "";
  // The 3 px bar is straight, so the cell keeps its left edge and only the right corners round.
  const corners = edit ? "rounded-l-none rounded-r-chip" : "rounded-chip";
  const hover = edit ? {
    tabIndex: 0,
    onMouseEnter: (e: React.MouseEvent<HTMLElement>) => setTip(e.currentTarget.getBoundingClientRect()),
    onMouseLeave: () => setTip(null),
    onFocus: (e: React.FocusEvent<HTMLElement>) => setTip(e.currentTarget.getBoundingClientRect()),
    onBlur: () => setTip(null),
  } : {};
  return (
    <>
      <span
        aria-label={edit ? `${num(value)}, edited from ${num(edit.old_value ?? value)}` : undefined}
        className={`${COL} -my-[6px] block py-[6px] outline-none focus-visible:outline-1 focus-visible:-outline-offset-1 focus-visible:outline-forest/50 ${corners} ${tone}`}
        {...hover}
      >
        {edit && edit.old_value != null ? (
          <span className="block font-mono text-[12px] leading-[14px] text-muted line-through">{num(edit.old_value)}</span>
        ) : null}
        <span className="inline-flex items-center justify-end gap-[4px] text-forest">
          {num(value)}
          {edit?.status === "reasoned" ? <span className="text-clear"><Shape kind="check" size={10} /></span> : null}
        </span>
      </span>
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
 * `flagged` names the lines a flag is about; they show in amber. Read-only: the controller edits the books on the
 * Review page (D19, V3-7), and the edits show here with their states. A row that gathers several target lines opens
 * to show them. */
export function CombinedTable({ result, flagged, kase, onHide }: {
  result: Result; flagged: Set<string>; kase: Case;
  /** On the Case the books start hidden; this hides them again. */
  onHide?: () => void;
}) {
  const { edits } = useEdits();
  const amountEdit = (l: SourceLine) => edits.find((e) => e.kind === "amount" && e.company === l.company && e.line === l.line && e.section === l.section);

  // The table opens on the section of the newest edit, so the edit stays in view; otherwise the balance sheet.
  const newestId = edits[edits.length - 1]?.id ?? null;
  const edited = editedSection(result, edits);
  const [choice, setChoice] = useState<{ open: string; seen: string | null }>({ open: edited ?? "balance_sheet", seen: newestId });
  const open = choice.seen === newestId ? choice.open : edited ?? choice.open;
  const setOpen = (s: string) => setChoice({ open: s, seen: newestId });
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const toggle = (k: string) => setExpanded((s) => { const n = new Set(s); if (n.has(k)) n.delete(k); else n.add(k); return n; });

  return (
    <Card className="flex w-full flex-col">
      <BooksHeader result={result} open={onHide ? true : undefined} onToggle={onHide} />
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
                          <AmountCell value={r.platform} edit={amountEdit(parts.platform)} />
                        ) : <span className={`${COL} text-forest`}>{num(r.platform)}</span>}
                        {single ? (
                          <AmountCell value={r.target} edit={amountEdit(single)} />
                        ) : <span className={`${COL} text-forest`}>{num(r.target)}</span>}
                        <CombinedCell value={r.combined} change={parts.change} />
                      </div>
                      {isOpen ? parts.targets.map((t) => {
                        const e = amountEdit(t);
                        return (
                          <div key={t.id} className="flex w-full items-center gap-[12px] py-[8px] pr-[20px] pl-[36px] text-[13px] text-slate last:pb-[14px]">
                            <span className="min-w-0 flex-1 truncate" title={`${kase.deal.target}: ${t.line}`}>{t.line}</span>
                            <span className={COL} />
                            <AmountCell value={e?.new_value ?? sourceK(t)} edit={e} />
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

/** The books card's title row: the tie-out state, the run, and on the Case the Show or Hide toggle. */
function BooksHeader({ result, open, onToggle }: { result: Result; open?: boolean; onToggle?: () => void }) {
  return (
    <div className={`flex w-full items-center gap-[12px] px-[20px] ${open === false ? "py-[14px]" : "pt-[14px]"}`}>
      <h2 className="flex-1 text-[16px] font-semibold text-forest">Combined books</h2>
      <span className={`inline-flex items-center gap-[6px] text-[13px] font-semibold ${result.tie_out_ok ? "text-clear" : "text-denied"}`}>
        <Shape kind={result.tie_out_ok ? "check" : "cross"} size={10} />
        {result.tie_out_ok ? "Ties out" : "Does not tie out"}
      </span>
      <Mono>USD thousands &middot; {result.run_ids_by_tool.consolidate}</Mono>
      {onToggle ? (
        <Button kind="link" className="text-[13px]" aria-expanded={open} onClick={onToggle}>
          {open ? "Hide combined books" : "Show combined books"}
        </Button>
      ) : null}
    </div>
  );
}

/** The Case's books, hidden until asked for: the title row with the tie-out state and Show combined books. */
export function CombinedCollapsed({ result, onShow }: { result: Result; onShow: () => void }) {
  return (
    <Card className="flex w-full flex-col">
      <BooksHeader result={result} open={false} onToggle={onShow} />
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
