"use client";

import { useEffect, useRef, useState } from "react";
import { useEdits } from "@/lib/edit-context";
import { num, parseAmount, signed } from "@/lib/edits";
import { shownConfidence } from "@/lib/format";
import type { Edit, Mapping, Section, SourceLine } from "@/lib/types";
import {
  type AmountCell, type CovenantRow, type DetailRow, type LineRow, type SubRow, amountAnchor, remapAnchor,
} from "@/lib/workbook";
import { Shape } from "./ui";

/** The Review sheet (V3-7, Figma 670:44): A line, B platform, C target, D combined, E change, F room to breathe.
 * Rows are 32 px, the grid is hairline gray, and the figures are the case's. The widths fit the page beside the
 * 240 px sidebar at 1440 by 900. */

export interface SheetCol { letter: string; width: string }

export const COLS: readonly SheetCol[] = [
  { letter: "A", width: "w-[380px]" },
  { letter: "B", width: "w-[170px]" },
  { letter: "C", width: "w-[170px]" },
  { letter: "D", width: "w-[170px]" },
  { letter: "E", width: "w-[130px]" },
] as const;

const GUTTER = "w-[44px] shrink-0";
export const BOX = "relative flex h-full shrink-0 items-center border-r border-sheet-line";
export const CELL = `${BOX} px-[10px]`;
const NUM = `${CELL} w-[170px] justify-end`;

/** The cell the controller is working in: typing, asking, or picking a line. Its row number and column letter light up. */
export interface Active { key: string; row: number; col: string }

/** The column letters over a sheet. `rest` names the last column, which takes the room that is left. */
export function ColumnLetters({ active, cols = COLS, rest = "F" }: { active: Active | null; cols?: readonly SheetCol[]; rest?: string }) {
  return (
    <div className="flex h-[24px] w-full shrink-0 border-b border-sheet-line bg-sheet-head">
      <div className={`${GUTTER} border-r border-sheet-line`} />
      {cols.map((c) => {
        const on = active?.col === c.letter;
        return (
          <div key={c.letter} className={`flex h-full shrink-0 items-center justify-center border-r border-sheet-line text-[11px] ${c.width} ${on ? "bg-mint font-semibold text-forest" : "font-medium text-sheet-muted"}`}>
            {c.letter}
          </div>
        );
      })}
      <div className={`flex h-full min-w-0 flex-1 items-center justify-center text-[11px] ${active?.col === rest ? "bg-mint font-semibold text-forest" : "font-medium text-sheet-muted"}`}>{rest}</div>
    </div>
  );
}

export function RowNumber({ n, on }: { n: number; on: boolean }) {
  return (
    <div className={`${GUTTER} flex h-full items-center justify-center border-r border-sheet-line text-[11px] ${on ? "bg-mint font-semibold text-forest" : "bg-sheet-head text-sheet-muted"}`}>
      {n}
    </div>
  );
}

export function Row({ n, on, band, children }: { n: number; on: boolean; band?: boolean; children: React.ReactNode }) {
  return (
    <div className={`flex h-[32px] w-full shrink-0 border-b border-sheet-line ${band ? "bg-sheet-band" : ""}`} data-sheet-row={n}>
      <RowNumber n={n} on={on} />
      {children}
      <div className="h-full min-w-0 flex-1" />
    </div>
  );
}

export function HeaderRow({ n, platform, target }: { n: number; platform: string; target: string }) {
  const h = "text-[12px] font-semibold whitespace-nowrap text-ink";
  return (
    <Row n={n} on={false}>
      <div className={`${CELL} w-[380px] ${h}`}>Line</div>
      {/* A long company name truncates inside its column; the full name is in the tooltip. */}
      <div className={`${NUM} ${h} overflow-hidden`} title={`Platform · ${platform}`}><span className="truncate">Platform &middot; {platform}</span></div>
      <div className={`${NUM} ${h} overflow-hidden`} title={`Target · ${target}`}><span className="truncate">Target &middot; {target}</span></div>
      <div className={`${NUM} ${h}`}>Combined</div>
      <div className={`${CELL} w-[130px] justify-end ${h}`}>Change</div>
    </Row>
  );
}

export function SectionTitleRow({ n, title }: { n: number; title: string }) {
  return (
    <Row n={n} on={false} band>
      <div className={`${CELL} w-[380px] text-[11px] font-semibold tracking-[0.88px] whitespace-nowrap text-sheet-muted uppercase`}>{title}</div>
      <div className={`${CELL} w-[170px]`} />
      <div className={`${CELL} w-[170px]`} />
      <div className={`${CELL} w-[170px]`} />
      <div className={`${CELL} w-[130px]`} />
    </Row>
  );
}

/** The change column: +500 in teal, (500) in red, from the edits' own old and new values. */
function Change({ value, text }: { value?: number; text?: string | null }) {
  const moved = value !== undefined && Math.round(value) !== 0;
  return (
    <div className={`${CELL} w-[130px] justify-end font-mono text-[12px] font-semibold whitespace-nowrap ${moved && value! < 0 ? "text-denied" : "text-forest"}`}>
      {text ?? (moved ? signed(value!) : null)}
    </div>
  );
}

/** The next or previous editable cell in reading order, for Tab while typing. */
function neighbour(key: string, back: boolean): string | null {
  const cells = [...document.querySelectorAll<HTMLElement>("[data-editable]")];
  const i = cells.findIndex((c) => c.dataset.editAnchor === key);
  return cells[i + (back ? -1 : 1)]?.dataset.editAnchor ?? null;
}

/** A click on an editable amount: typing starts in place. */
interface CellProps {
  cell: AmountCell; editable: boolean; row: number; col: string; bold?: boolean;
  active: Active | null; onSelect: (a: Active) => void; onTyped: (text: string) => void;
}

/** One amount the controller can change. States from the V3-7 frames: default, hover, typing (with the key hint),
 * edited and waiting for its reason (amber with a bar), reason given (a teal bar and a check). */
function Amount({ cell, editable, row, col, bold, active, onSelect, onTyped }: CellProps) {
  const ctx = useEdits();
  const [error, setError] = useState<string | null>(null);
  const src = cell.source;
  const anchor = src ? amountAnchor(src) : null;
  const typing = anchor !== null && ctx.editing === anchor;
  const isActive = anchor !== null && active?.key === anchor;
  const weight = bold ? "font-semibold" : "";

  if (!src || !anchor) {
    return <div className={`${NUM} text-[14px] whitespace-nowrap text-ink ${weight}`}>{num(cell.value)}</div>;
  }

  if (typing) {
    const commit = async (text: string, move?: "next" | "back") => {
      const v = parseAmount(text);
      if (v === null) { setError("Numbers only, in USD thousands"); return; }
      setError(null);
      if (num(v) === num(cell.value)) {
        ctx.setEditing(move ? neighbour(anchor, move === "back") : null);
        return;
      }
      await ctx.apply({ kind: "amount", company: src.company, line: src.line, section: src.section, value: v }, anchor, cell.value);
    };
    return (
      <div className={`${BOX} z-20 w-[170px]`}>
        <input
          autoFocus
          defaultValue={num(cell.value)}
          inputMode="decimal"
          onFocus={(e) => { e.currentTarget.select(); onTyped(e.currentTarget.value); }}
          aria-label={`${src.company}, ${src.line}, USD thousands`}
          aria-invalid={Boolean(error)}
          className={`h-full w-full rounded-[3px] border bg-white px-[10px] text-right text-[14px] text-ink tabular-nums outline-none ${error ? "border-denied" : "border-ink"}`}
          onChange={(e) => { onTyped(e.target.value); if (error) setError(null); }}
          onKeyDown={(e) => {
            if (e.key === "Enter") { e.preventDefault(); void commit(e.currentTarget.value); }
            else if (e.key === "Escape") { e.preventDefault(); setError(null); ctx.setEditing(null); }
            else if (e.key === "Tab") { e.preventDefault(); void commit(e.currentTarget.value, e.shiftKey ? "back" : "next"); }
          }}
          onBlur={() => { setError(null); if (ctx.editing === anchor) ctx.setEditing(null); }}
        />
        <span
          role={error ? "alert" : undefined}
          className={`pointer-events-none absolute top-1/2 left-[calc(100%+10px)] -translate-y-1/2 rounded-[4px] border bg-white px-[8px] py-[2px] font-mono text-[11px] whitespace-nowrap ${
            error ? "border-denied text-denied" : "border-hairline text-sheet-muted"
          }`}
        >
          {error ?? "Enter saves · Esc cancels"}
        </span>
      </div>
    );
  }

  const e = cell.edit;
  const needs = e?.status === "needs_reason";
  const ring = isActive ? "shadow-[inset_0_0_0_2px_var(--color-forest)]" : "";
  const body = (
    <>
      {e ? <span className={`absolute top-0 bottom-0 left-0 w-[3px] ${needs ? "bg-edit-bar" : "bg-forest"} ${isActive ? "top-[2px] bottom-[2px] left-[2px]" : ""}`} aria-hidden="true" /> : null}
      {e && e.old_value != null ? <span className="font-mono text-[11px] text-[#6b6b6b] line-through">{num(e.old_value)}</span> : null}
      <span className={`text-[14px] text-ink ${e ? "font-semibold" : weight}`}>{num(cell.value)}</span>
      {e && !needs ? <span className="text-forest"><Shape kind="check" size={10} /></span> : null}
    </>
  );
  const select = () => onSelect({ key: anchor, row, col });
  if (editable && !e) {
    return (
      <button
        type="button"
        data-edit-anchor={anchor}
        data-editable=""
        aria-label={`${src.company}, ${src.line}: ${num(cell.value)}. Edit`}
        onClick={() => { select(); ctx.setEditing(anchor); }}
        className={`${NUM} gap-[6px] cursor-text whitespace-nowrap outline-none hover:bg-sheet-band hover:shadow-[inset_0_0_0_1px_var(--color-hairline)] focus-visible:shadow-[inset_0_0_0_2px_var(--color-forest)] ${ring} ${ctx.flash?.key === anchor ? "cell-flash" : ""}`}
      >
        {body}
      </button>
    );
  }
  return (
    <div
      data-edit-anchor={anchor}
      tabIndex={e ? 0 : undefined}
      onClick={e ? select : undefined}
      onFocus={e ? select : undefined}
      aria-label={e ? `${src.company}, ${src.line}: ${num(cell.value)}, edited from ${num(e.old_value ?? cell.value)}. ${needs ? "Needs a reason." : `Reason: ${e.reason_text}.`}` : undefined}
      className={`${NUM} gap-[6px] whitespace-nowrap outline-none ${needs ? "bg-escalation-tint" : ""} ${ring} ${ctx.flash?.key === anchor ? "cell-flash" : ""}`}
    >
      {body}
    </div>
  );
}

export function Chevron({ up }: { up?: boolean }) {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" className={`shrink-0 text-sheet-muted ${up ? "rotate-180" : ""}`}>
      <path d="M3 4.5L6 7.5L9 4.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** The menu of the platform's lines under a target line cell (V3-7.7a). The current line is first, with a check. */
export function LineMenu({
  platform, current, options, label, onPick, onClose,
}: {
  platform: string; current: string | null; options: string[]; label?: string; onPick: (line: string) => void; onClose: () => void;
}) {
  const list = current && options.includes(current) ? [current, ...options.filter((o) => o !== current)] : options;
  const [at, setAt] = useState(Math.min(1, list.length - 1));
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.focus({ preventScroll: true }); }, []);
  return (
    <>
      <div className="fixed inset-0 z-30" onMouseDown={onClose} aria-hidden="true" />
      <div
        ref={ref}
        role="listbox"
        tabIndex={-1}
        aria-label={`Map to a ${platform} line`}
        aria-activedescendant={`line-opt-${at}`}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") { e.preventDefault(); setAt((i) => Math.min(list.length - 1, i + 1)); }
          else if (e.key === "ArrowUp") { e.preventDefault(); setAt((i) => Math.max(0, i - 1)); }
          else if (e.key === "Enter") { e.preventDefault(); if (list[at] !== current) onPick(list[at]); else onClose(); }
          else if (e.key === "Escape") { e.preventDefault(); onClose(); }
        }}
        className="absolute top-[calc(100%+4px)] left-[4px] z-40 flex max-h-[320px] w-[300px] flex-col overflow-y-auto rounded-[8px] border border-hairline bg-white py-[6px] shadow-[0_8px_24px_rgba(27,31,36,0.16)] outline-none"
      >
        {label ? <span className="px-[12px] pt-[4px] text-[12px] text-sheet-muted">{label}</span> : null}
        <span className="px-[12px] py-[4px] text-[11px] font-semibold tracking-[0.88px] whitespace-nowrap text-sheet-muted uppercase">Map to a {platform} line</span>
        {list.map((o, i) => (
          <button
            key={o}
            id={`line-opt-${i}`}
            type="button"
            role="option"
            aria-selected={o === current}
            tabIndex={-1}
            onMouseEnter={() => setAt(i)}
            onClick={() => (o === current ? onClose() : onPick(o))}
            className={`flex h-[30px] w-full shrink-0 items-center justify-between gap-[8px] px-[12px] text-left text-[14px] text-ink ${i === at ? "bg-sheet-band" : ""} ${o === current ? "font-semibold" : ""}`}
          >
            <span className="truncate">{o}</span>
            {o === current ? <span className="text-forest"><Shape kind="check" size={12} /></span> : null}
          </button>
        ))}
      </div>
    </>
  );
}

/** The line cell of a target line: its name, and a menu of the platform's lines to remap it (V3-7.7a and 7.7b).
 * A remapped line keeps its place and says where it goes now, amber until it has a reason. */
function LineCell({
  name, line, current, remap, editable, indent, bold, row, options, platform, active, menu, setMenu, onSelect, menuLabel, toggle, badge,
}: {
  name: string; line: SourceLine | null;
  /** The platform line the Mapper put the target line on: the row it sits under. */
  current: string; remap?: Edit; editable: boolean; indent: boolean; bold: boolean; row: number;
  options: string[]; platform: string; active: Active | null; menu: string | null; setMenu: (k: string | null) => void;
  onSelect: (a: Active) => void; menuLabel?: string;
  /** The detail toggle at the left of a combined row; it sits outside the line's menu button. */
  toggle?: React.ReactNode;
  /** A small mark after the name, such as the Mapper's confidence. */
  badge?: React.ReactNode;
}) {
  const ctx = useEdits();
  const pad = indent ? "pl-[58px]" : toggle ? "pl-[34px]" : "";
  const toggleSlot = toggle ? <span className="absolute top-1/2 left-[10px] z-[1] flex -translate-y-1/2">{toggle}</span> : null;
  const text = `text-[14px] text-ink ${bold ? "font-semibold" : ""}`;
  if (!line) {
    return (
      <div className={`${CELL} w-[380px] gap-[6px] ${pad} ${text}`}>
        {toggleSlot}
        <span className="truncate" title={name}>{name}</span>
        {badge}
      </div>
    );
  }
  const anchor = remapAnchor(line);
  const open = menu === anchor;
  const isActive = active?.key === anchor;
  const needs = remap?.status === "needs_reason";
  const canOpen = editable && !remap;
  const select = () => onSelect({ key: anchor, row, col: "A" });
  return (
    <div className={`${BOX} w-[380px] ${open ? "z-30" : ""}`}>
      {toggleSlot}
      <button
        type="button"
        data-edit-anchor={anchor}
        aria-haspopup={canOpen ? "listbox" : undefined}
        aria-expanded={canOpen ? open : undefined}
        aria-label={remap ? `${line.company}, ${line.line}: remapped to ${remap.new_platform_line}` : `${line.company}, ${line.line}. ${canOpen ? `Map it to a ${platform} line` : ""}`}
        onClick={() => { select(); if (canOpen) setMenu(open ? null : anchor); }}
        className={`group relative flex h-full w-full min-w-0 items-center justify-between gap-[8px] px-[10px] text-left outline-none ${pad} ${
          remap ? (needs ? "bg-escalation-tint" : "") : canOpen ? "hover:bg-sheet-band" : "cursor-default"
        } ${isActive || open ? "shadow-[inset_0_0_0_2px_var(--color-forest)]" : "focus-visible:shadow-[inset_0_0_0_2px_var(--color-forest)]"} ${ctx.flash?.key === anchor ? "cell-flash" : ""}`}
      >
        {remap ? <span className={`absolute top-0 bottom-0 left-0 w-[3px] ${needs ? "bg-edit-bar" : "bg-forest"} ${isActive ? "top-[2px] bottom-[2px] left-[2px]" : ""}`} aria-hidden="true" /> : null}
        <span className="flex min-w-0 items-center gap-[8px]">
          <span className={`truncate ${text}`} title={line.line === name ? name : `${name}, from ${line.company}'s ${line.line}`}>{name}</span>
          {remap ? (
            <span className="flex shrink-0 items-center gap-[4px] text-[12px] font-medium whitespace-nowrap text-ink">
              <span className="font-sans">&rarr;</span> {remap.new_platform_line}
              {needs ? null : <span className="text-forest"><Shape kind="check" size={10} /></span>}
            </span>
          ) : null}
          {badge}
        </span>
        {canOpen || remap ? <span className={open || remap ? "" : "opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100"}><Chevron up={open} /></span> : null}
      </button>
      {open ? (
        <LineMenu
          platform={platform}
          current={remap?.new_platform_line ?? current}
          options={options}
          label={menuLabel}
          onClose={() => setMenu(null)}
          onPick={async (to) => {
            setMenu(null);
            await ctx.apply({ kind: "remap", company: line.company, line: line.line, section: line.section, platform_line: to }, anchor);
          }}
        />
      ) : null}
    </div>
  );
}

export interface SheetHandlers {
  active: Active | null;
  menu: string | null;
  setMenu: (k: string | null) => void;
  onSelect: (a: Active) => void;
  onTyped: (text: string) => void;
}

export function LineSheetRow({
  n, row, editable, platform, target, options, open, onToggle, h,
}: {
  n: number; row: LineRow; editable: boolean; platform: string; target: string; options: string[];
  open: boolean; onToggle: () => void; h: SheetHandlers;
}) {
  const on = h.active?.row === n;
  return (
    <Row n={n} on={on}>
      <LineCell
        name={row.line} line={row.remapLine} current={row.line} remap={row.remap} editable={editable} indent={false} bold={row.bold} row={n}
        options={options} platform={platform} active={h.active} menu={h.menu} setMenu={h.setMenu} onSelect={h.onSelect}
        menuLabel={row.remapLine && row.remapLine.line !== row.line ? `${target}'s ${row.remapLine.line}` : undefined}
        toggle={<OutlineToggle open={open} onToggle={onToggle} line={row.line} />}
      />
      <Amount cell={row.platform} editable={editable} row={n} col="B" bold={row.bold} active={h.active} onSelect={h.onSelect} onTyped={h.onTyped} />
      <Amount cell={row.target} editable={editable} row={n} col="C" bold={row.bold} active={h.active} onSelect={h.onSelect} onTyped={h.onTyped} />
      <div className={`${NUM} text-[14px] font-semibold whitespace-nowrap text-forest`}>{num(row.combined)}</div>
      <Change value={row.change} />
    </Row>
  );
}

export function SubSheetRow({
  n, row, editable, platform, options, h, badge,
}: { n: number; row: SubRow; editable: boolean; platform: string; options: string[]; h: SheetHandlers; badge?: React.ReactNode }) {
  return (
    <Row n={n} on={h.active?.row === n}>
      <LineCell
        name={row.line.line} line={row.line} current={row.parentLine} remap={row.remap} editable={editable} indent bold={false} row={n}
        options={options} platform={platform} active={h.active} menu={h.menu} setMenu={h.setMenu} onSelect={h.onSelect} badge={badge}
      />
      <div className={`${CELL} w-[170px]`} />
      <Amount cell={row.target} editable={editable} row={n} col="C" active={h.active} onSelect={h.onSelect} onTyped={h.onTyped} />
      <div className={`${CELL} w-[170px]`} />
      <div className={`${CELL} w-[130px]`} />
    </Row>
  );
}

export function CovenantSheetRow({ n, row }: { n: number; row: CovenantRow }) {
  return (
    <Row n={n} on={false}>
      <div className={`${CELL} w-[380px] text-[14px] whitespace-nowrap text-ink ${row.bold ? "font-semibold" : ""}`}>{row.label}</div>
      <div className={`${CELL} w-[170px]`} />
      <div className={`${CELL} w-[170px]`} />
      <div className={`${NUM} text-[14px] font-semibold whitespace-nowrap text-forest`}>{row.value}</div>
      <Change text={row.was} />
    </Row>
  );
}

export type { Section };

/** The outline box at the left of a combined row, as a spreadsheet's row group: + opens the detail block, - closes it. */
export function OutlineToggle({ open, onToggle, line }: { open: boolean; onToggle: () => void; line: string }) {
  return (
    <button
      type="button"
      onClick={(e) => { e.stopPropagation(); onToggle(); }}
      aria-expanded={open}
      aria-label={`${open ? "Hide" : "Show"} detail for ${line}`}
      title={open ? "Hide the source lines and GL accounts" : "Show the source lines and GL accounts"}
      className={`flex size-[14px] shrink-0 items-center justify-center rounded-[2px] border bg-white text-sheet-muted outline-none hover:border-forest hover:text-forest focus-visible:border-forest ${open ? "border-forest text-forest" : "border-[#C9C9C5]"}`}
    >
      <svg width="8" height="8" viewBox="0 0 8 8" aria-hidden="true">
        <path d={open ? "M1.5 4h5" : "M1.5 4h5M4 1.5v5"} stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      </svg>
    </button>
  );
}

/** The Mapper's confidence on a target line: 100% once you answered it or a policy placed it, the model's own % in the
 * tooltip; else the model's %, teal when sure. */
export function ConfidenceMark({ mapping, asking }: { mapping: Mapping; asking: Set<string> }) {
  const c = shownConfidence(mapping, asking);
  const open = asking.has(mapping.target_line_id);
  return (
    <span className="flex shrink-0 items-center gap-[5px]" title={c.title ?? `Mapper's confidence: ${c.text}`}>
      <span className={`font-mono text-[11px] font-semibold ${open ? "text-escalation" : c.sure ? "text-forest" : "text-sheet-muted"}`}>{c.text}</span>
      {c.by === "you" ? <span className="font-mono text-[11px] text-sheet-muted">by you</span> : null}
      {c.by === "policy" ? <span className="rounded-chip bg-mint px-[5px] py-[1px] text-[9px] font-semibold tracking-[0.6px] text-forest uppercase">Learned</span> : null}
    </span>
  );
}

const DROW = "flex w-full shrink-0 border-b border-sheet-line";
const DNUM = `${CELL} w-[170px] justify-end whitespace-nowrap`;

/** One row of the detail block under an opened combined row (DetailRow in lib/workbook). Columns keep the sheet's
 * meaning where they can: the platform's figures in B, the target's in C; then D prior period, E change, F entries and
 * the last posting. GL rows are 26 px and 12 px type, denser than the statement rows. */
export function DetailSheetRow({
  n, row, platform, target, asking, note,
}: { n: number; row: DetailRow; platform: string; target: string; asking: Set<string>; note: string }) {
  const amountCells = (side: "platform" | "target", content: React.ReactNode, cls = "") => (
    <>
      <div className={`${DNUM} ${cls}`}>{side === "platform" ? content : null}</div>
      <div className={`${DNUM} ${cls}`}>{side === "target" ? content : null}</div>
    </>
  );
  const ties = (ok: boolean, label: string) => (
    <span className={`flex items-center gap-[4px] text-[11px] font-medium whitespace-nowrap ${ok ? "text-forest" : "text-denied"}`} title={ok ? `${label}: the GL accounts add up to the filed line` : `${label}: the GL accounts do not add up to the filed line`}>
      <Shape kind={ok ? "check" : "cross"} size={9} />{ok ? "Ties" : "Off"}
    </span>
  );
  if (row.kind === "dhead") {
    const h = "text-[11px] font-semibold whitespace-nowrap text-sheet-muted";
    return (
      <div className={`${DROW} h-[26px] bg-sheet-head/60`} data-sheet-row={n} data-detail={row.parent}>
        <RowNumber n={n} on={false} />
        <div className={`${CELL} w-[380px] pl-[34px] ${h}`}>Source line &middot; GL account</div>
        <div className={`${DNUM} ${h} overflow-hidden`}><span className="truncate">{platform}</span></div>
        <div className={`${DNUM} ${h} overflow-hidden`}><span className="truncate">{target}</span></div>
        <div className={`${DNUM} ${h}`}>{row.gl ? "Prior period" : null}</div>
        <div className={`${CELL} w-[130px] justify-end ${h}`}>{row.gl ? "Change" : null}</div>
        <div className={`flex h-full min-w-0 flex-1 items-center justify-end px-[10px] ${h}`}>{row.gl ? "Entries · posted" : null}</div>
      </div>
    );
  }
  if (row.kind === "dcompany") {
    return (
      <div className={`${DROW} h-[26px] bg-sheet-band`} data-sheet-row={n} data-detail={row.parent}>
        <RowNumber n={n} on={false} />
        <div className={`${CELL} w-[380px] gap-[6px] pl-[34px] text-[11px] whitespace-nowrap`}>
          <span className="font-semibold tracking-[0.88px] text-ink uppercase">{row.company}</span>
          <span className="text-sheet-muted">&middot; {row.count === 1 ? "1 statement line" : `${row.count} statement lines`}</span>
        </div>
        {amountCells(row.side, num(row.value), "text-[13px] font-semibold text-ink")}
        <div className={`${CELL} w-[170px]`} />
        <div className={`${CELL} w-[130px]`} />
        <div className="flex h-full min-w-0 flex-1 items-center justify-end px-[10px]">{row.ties === null || !row.count ? null : ties(row.ties, row.company)}</div>
      </div>
    );
  }
  if (row.kind === "dline") {
    const e = row.edit;
    return (
      <div className={`${DROW} h-[32px]`} data-sheet-row={n} data-detail={row.parent}>
        <RowNumber n={n} on={false} />
        <div className={`${CELL} w-[380px] gap-[8px] pl-[58px] text-[14px] text-ink ${row.line.is_total ? "font-semibold" : ""}`}>
          <span className="truncate" title={row.line.line}>{row.line.line}</span>
          {row.mapping && !row.line.is_total ? <ConfidenceMark mapping={row.mapping} asking={asking} /> : null}
        </div>
        {amountCells(row.side, (
          <span className="flex items-center gap-[6px]">
            {e && e.old_value != null ? <span className="font-mono text-[11px] text-[#6b6b6b] line-through">{num(e.old_value)}</span> : null}
            <span className={`text-[14px] text-ink ${e || row.line.is_total ? "font-semibold" : ""}`}>{num(row.value)}</span>
          </span>
        ))}
        <div className={`${CELL} w-[170px]`} />
        <div className={`${CELL} w-[130px]`} />
        <div className="h-full min-w-0 flex-1" />
      </div>
    );
  }
  if (row.kind === "dfacts" || row.kind === "dnote") {
    const text = row.kind === "dnote" ? row.text : facts(row.line, row.mapping, asking);
    return (
      <div className={`${DROW} h-[24px]`} data-sheet-row={n} data-detail={row.parent}>
        <RowNumber n={n} on={false} />
        <div className={`flex h-full min-w-0 flex-1 items-center pr-[16px] ${row.kind === "dnote" ? "pl-[58px] italic" : "pl-[58px]"} text-[12px] text-sheet-muted`}>
          <span className="truncate" title={text}>{text}</span>
        </div>
      </div>
    );
  }
  if (row.kind === "dgl") {
    const change = row.value - row.prior;
    return (
      <div className={`${DROW} h-[26px] text-[12px]`} data-sheet-row={n} data-detail={row.parent} title={note}>
        <RowNumber n={n} on={false} />
        <div className={`${CELL} w-[380px] gap-[8px] pl-[74px] text-ink`}>
          <span className="w-[34px] shrink-0 font-mono text-[11px] text-sheet-muted">{row.gl.account}</span>
          <span className="min-w-0 truncate" title={row.gl.name}>{row.gl.name}</span>
        </div>
        {amountCells(row.side, num(row.value), "text-ink")}
        <div className={`${DNUM} text-sheet-muted`}>{num(row.prior)}</div>
        <div className={`${CELL} w-[130px] justify-end font-mono text-[11px] whitespace-nowrap ${Math.round(change) < 0 ? "text-denied" : "text-sheet-muted"}`}>{Math.round(change) ? signed(change) : "0"}</div>
        <div className="flex h-full min-w-0 flex-1 items-center justify-end gap-[6px] overflow-hidden px-[10px] font-mono text-[11px] whitespace-nowrap text-sheet-muted">
          <span>{row.gl.entries.toLocaleString("en-US")}</span><span aria-hidden="true">&middot;</span><span>{row.gl.last_posted}</span>
        </div>
      </div>
    );
  }
  // dgltotal: the GL accounts' total, which must equal the filed statement line.
  return (
    <div className={`${DROW} h-[26px] text-[12px]`} data-sheet-row={n} data-detail={row.parent}>
      <RowNumber n={n} on={false} />
      <div className={`${CELL} w-[380px] gap-[6px] pl-[74px] font-semibold text-ink`}>
        <span className="truncate" title={`GL total, ${row.line.line}`}>GL total &middot; {row.line.line}</span>
      </div>
      {amountCells(row.side, <span className="border-t border-ink pt-px">{num(row.value)}</span>, "font-semibold text-ink")}
      <div className={`${CELL} w-[170px]`} />
      <div className={`${CELL} w-[130px]`} />
      <div className="flex h-full min-w-0 flex-1 items-center justify-end px-[10px]">{ties(row.ties, row.line.line)}</div>
    </div>
  );
}

/** The facts row under a statement line: for a target line the Mapper's confidence and reason and who settled it, then
 * the filing it came from and the filing's note. */
function facts(line: SourceLine, m: Mapping | null, asking: Set<string>): string {
  const parts: string[] = [];
  if (m && !line.is_total) {
    const c = shownConfidence(m, asking);
    const who = c.by === "you" ? `Answered by you (Mapper was ${Math.round(m.confidence * 100)}%)` : c.by === "policy" ? `Learned: placed by policy ${m.policy_id}` : `Mapper ${c.text}`;
    parts.push(`${who}: ${m.reason.replace(/[.\s]+$/, "")}.`);
  } else if (m) {
    parts.push(`Mapper: ${m.reason.replace(/[.\s]+$/, "")}.`);
  }
  parts.push(`Filed in ${line.source_ref}.`);
  if (line.note) parts.push(`Note: ${line.note.replace(/[.\s]+$/, "")}.`);
  return parts.join("  ·  ");
}
