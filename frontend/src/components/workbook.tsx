"use client";

import { useEffect, useRef, useState } from "react";
import { useEdits } from "@/lib/edit-context";
import { num, parseAmount, signed } from "@/lib/edits";
import type { Edit, Section, SourceLine } from "@/lib/types";
import { type AmountCell, type CovenantRow, type LineRow, type SubRow, amountAnchor, remapAnchor } from "@/lib/workbook";
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
  name, line, current, remap, editable, indent, bold, row, options, platform, active, menu, setMenu, onSelect, menuLabel, collapse,
}: {
  name: string; line: SourceLine | null;
  /** The platform line the Mapper put the target line on: the row it sits under. */
  current: string; remap?: Edit; editable: boolean; indent: boolean; bold: boolean; row: number;
  options: string[]; platform: string; active: Active | null; menu: string | null; setMenu: (k: string | null) => void;
  onSelect: (a: Active) => void; menuLabel?: string; collapse?: React.ReactNode;
}) {
  const ctx = useEdits();
  const pad = indent ? "pl-[42px]" : "";
  const text = `text-[14px] text-ink ${bold ? "font-semibold" : ""}`;
  if (!line) {
    return (
      <div className={`${CELL} w-[380px] gap-[6px] ${pad} ${text}`}>
        <span className="truncate" title={name}>{name}</span>
        {collapse}
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
          {collapse}
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
  n, row, editable, platform, target, options, collapsed, onToggle, h,
}: {
  n: number; row: LineRow; editable: boolean; platform: string; target: string; options: string[];
  collapsed: boolean; onToggle: () => void; h: SheetHandlers;
}) {
  const on = h.active?.row === n;
  const collapse = row.subs.length ? (
    <button
      type="button"
      onClick={(e) => { e.stopPropagation(); onToggle(); }}
      aria-expanded={!collapsed}
      aria-label={`${collapsed ? "Show" : "Hide"} ${row.subs.length} ${target} lines`}
      className={`flex size-[18px] shrink-0 items-center justify-center rounded-[3px] text-sheet-muted hover:bg-sheet-head ${collapsed ? "" : "opacity-0 hover:opacity-100 focus-visible:opacity-100"}`}
    >
      <span className={collapsed ? "-rotate-90" : ""}><Chevron /></span>
    </button>
  ) : null;
  return (
    <Row n={n} on={on}>
      <LineCell
        name={row.line} line={row.remapLine} current={row.line} remap={row.remap} editable={editable} indent={false} bold={row.bold} row={n}
        options={options} platform={platform} active={h.active} menu={h.menu} setMenu={h.setMenu} onSelect={h.onSelect}
        menuLabel={row.remapLine && row.remapLine.line !== row.line ? `${target}'s ${row.remapLine.line}` : undefined}
        collapse={collapse}
      />
      <Amount cell={row.platform} editable={editable} row={n} col="B" bold={row.bold} active={h.active} onSelect={h.onSelect} onTyped={h.onTyped} />
      <Amount cell={row.target} editable={editable} row={n} col="C" bold={row.bold} active={h.active} onSelect={h.onSelect} onTyped={h.onTyped} />
      <div className={`${NUM} text-[14px] font-semibold whitespace-nowrap text-forest`}>{num(row.combined)}</div>
      <Change value={row.change} />
    </Row>
  );
}

export function SubSheetRow({ n, row, editable, platform, options, h }: { n: number; row: SubRow; editable: boolean; platform: string; options: string[]; h: SheetHandlers }) {
  return (
    <Row n={n} on={h.active?.row === n}>
      <LineCell
        name={row.line.line} line={row.line} current={row.parentLine} remap={row.remap} editable={editable} indent bold={false} row={n}
        options={options} platform={platform} active={h.active} menu={h.menu} setMenu={h.setMenu} onSelect={h.onSelect}
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
