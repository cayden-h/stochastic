"use client";

import { useEdits } from "@/lib/edit-context";
import { effectivePlatformLine } from "@/lib/edits";
import { isLearned, isUnsure, shownConfidence } from "@/lib/format";
import type { Case, Edit, Mapping, Section, SourceLine } from "@/lib/types";
import { SECTION_TITLES, cellRef, lineNote, remapAnchor, remapOptions } from "@/lib/workbook";
import { Shape } from "./ui";
import { type Active, type SheetCol, BOX, CELL, Chevron, LineMenu, Row } from "./workbook";

/** The Mapping sheet on the Review page: A target line, B the platform line it goes to (a menu: pick another line to
 * remap it), C how sure the Mapper was, D its reason, E room to breathe. Same grid, rows, and states as the Review sheet. */
export const MAPPING_COLS: readonly SheetCol[] = [
  { letter: "A", width: "w-[300px]" },
  { letter: "B", width: "w-[400px]" },
  { letter: "C", width: "w-[110px]" },
  { letter: "D", width: "w-[300px]" },
];

const ORDER: Section[] = ["income_statement", "balance_sheet", "cash_flow"];

export interface MappingLine {
  kind: "mapping"; key: string; mapping: Mapping; line: SourceLine;
  /** The platform line the target line lands on now: the remap's new line, else the Mapper's. */
  now: string | null;
  remap?: Edit; unsure: boolean; learned: boolean;
  /** The confidence to show: 100% once the controller answered the line or a policy placed it. */
  shown: ReturnType<typeof shownConfidence>;
}
type MappingRow = { kind: "head" } | { kind: "section"; key: string; title: string } | MappingLine;
export interface MappingCellMeta { ref: string; row: number; col: string; value: string; note: string }

/** The target's detail lines in sheet order (income statement, balance sheet, cash flow), each with its row number,
 * and the formula-bar text of each line cell. Totals have no platform line by design, so they are not listed. */
export function mappingLayout(kase: Case, mappings: Mapping[], edits: Edit[], asking: Set<string>) {
  const rows: { n: number; row: MappingRow }[] = [{ n: 1, row: { kind: "head" } }];
  const meta = new Map<string, MappingCellMeta>();
  const byId = new Map(kase.source_lines.map((l) => [l.id, l]));
  for (const section of ORDER) {
    const lines: MappingLine[] = [];
    for (const m of mappings) {
      const l = byId.get(m.target_line_id);
      if (!l || l.section !== section || l.is_total || l.company !== kase.deal.target) continue;
      const remap = edits.find((e) => e.kind === "remap" && e.company === l.company && e.line === l.line && e.section === l.section);
      lines.push({ kind: "mapping", key: m.id, mapping: m, line: l, now: effectivePlatformLine(m, l, edits), remap, unsure: isUnsure(m, asking), learned: isLearned(m), shown: shownConfidence(m, asking) });
    }
    if (!lines.length) continue;
    rows.push({ n: rows.length + 1, row: { kind: "section", key: section, title: SECTION_TITLES[section] } });
    for (const r of lines) {
      const n = rows.length + 1;
      rows.push({ n, row: r });
      meta.set(remapAnchor(r.line), { ref: cellRef("B", n), row: n, col: "B", value: r.now ?? "Not mapped", note: lineNote(r.line, r.remap, kase.deal.platform) });
    }
  }
  return { rows, meta };
}

const HEAD = "text-[12px] font-semibold whitespace-nowrap text-ink";

/** The platform line cell: where the target line goes, and the menu of the platform's lines to remap it. A remapped
 * line shows the agents' line struck through and the new one, amber until it has a reason. */
function PlatformCell({
  r, n, editable, options, platform, active, menu, setMenu, onSelect,
}: {
  r: MappingLine; n: number; editable: boolean; options: string[]; platform: string; active: Active | null;
  menu: string | null; setMenu: (k: string | null) => void; onSelect: (a: Active) => void;
}) {
  const ctx = useEdits();
  const anchor = remapAnchor(r.line);
  const open = menu === anchor;
  const canOpen = editable && !r.remap;
  const needs = r.remap?.status === "needs_reason";
  const on = active?.key === anchor || open;
  return (
    <div className={`${BOX} ${MAPPING_COLS[1].width} ${open ? "z-30" : ""}`}>
      <button
        type="button"
        data-edit-anchor={anchor}
        aria-haspopup={canOpen ? "listbox" : undefined}
        aria-expanded={canOpen ? open : undefined}
        aria-label={r.remap
          ? `${r.line.line}: remapped from ${r.remap.old_platform_line ?? "no line"} to ${r.remap.new_platform_line}`
          : `${r.line.line} goes to ${r.now ?? "no line"}.${canOpen ? ` Map it to another ${platform} line` : ""}`}
        onClick={() => { onSelect({ key: anchor, row: n, col: "B" }); if (canOpen) setMenu(open ? null : anchor); }}
        className={`group relative flex h-full w-full min-w-0 items-center justify-between gap-[8px] px-[10px] text-left outline-none ${
          r.remap ? (needs ? "bg-escalation-tint" : "") : canOpen ? "hover:bg-sheet-band" : "cursor-default"
        } ${on ? "shadow-[inset_0_0_0_2px_var(--color-forest)]" : "focus-visible:shadow-[inset_0_0_0_2px_var(--color-forest)]"} ${ctx.flash?.key === anchor ? "cell-flash" : ""}`}
      >
        {r.remap ? <span className={`absolute top-0 bottom-0 left-0 w-[3px] ${needs ? "bg-edit-bar" : "bg-forest"} ${on ? "top-[2px] bottom-[2px] left-[2px]" : ""}`} aria-hidden="true" /> : null}
        <span className="flex min-w-0 items-center gap-[6px] text-[14px] text-ink">
          {r.remap ? (
            <>
              <span className="min-w-0 shrink truncate font-mono text-[11px] text-[#6b6b6b] line-through">{r.remap.old_platform_line ?? "Not mapped"}</span>
              <span className="shrink-0 font-sans" aria-hidden="true">&rarr;</span>
              <span className="min-w-0 truncate font-semibold">{r.remap.new_platform_line}</span>
              {needs ? null : <span className="shrink-0 text-forest"><Shape kind="check" size={10} /></span>}
            </>
          ) : (
            <span className={`truncate ${r.unsure ? "font-semibold text-escalation" : r.now ? "" : "text-sheet-muted"}`}>{r.now ?? "Not mapped"}</span>
          )}
        </span>
        {canOpen || r.remap ? <span className={open || r.remap ? "" : "opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100"}><Chevron up={open} /></span> : null}
      </button>
      {open ? (
        <LineMenu
          platform={platform}
          current={r.now}
          options={options}
          label={`${r.line.company}'s ${r.line.line}`}
          onClose={() => setMenu(null)}
          onPick={async (to) => {
            setMenu(null);
            await ctx.apply({ kind: "remap", company: r.line.company, line: r.line.line, section: r.line.section, platform_line: to }, anchor);
          }}
        />
      ) : null}
    </div>
  );
}

/** The Mapping sheet in review mode: the remap is made here, from the platform line cell, and the Reviewer asks why. */
export function MappingSheet({
  kase, rows, editable, active, menu, setMenu, onSelect,
}: {
  kase: Case; rows: { n: number; row: MappingRow }[]; editable: boolean; active: Active | null;
  menu: string | null; setMenu: (k: string | null) => void; onSelect: (a: Active) => void;
}) {
  const { platform, target } = kase.deal;
  return (
    <div className="flex w-full flex-col" data-mapping-sheet="">
      {rows.map(({ n, row }) => {
        if (row.kind === "head") {
          return (
            <Row key="head" n={n} on={false}>
              <div className={`${CELL} ${MAPPING_COLS[0].width} ${HEAD} overflow-hidden`} title={`Target line · ${target}`}><span className="truncate">Target line &middot; {target}</span></div>
              <div className={`${CELL} ${MAPPING_COLS[1].width} ${HEAD} overflow-hidden`} title={`Platform line · ${platform}`}><span className="truncate">Platform line &middot; {platform}</span></div>
              <div className={`${CELL} ${MAPPING_COLS[2].width} justify-end ${HEAD}`}>Confidence</div>
              <div className={`${CELL} ${MAPPING_COLS[3].width} ${HEAD}`}>Mapper&apos;s reason</div>
            </Row>
          );
        }
        if (row.kind === "section") {
          return (
            <Row key={row.key} n={n} on={false} band>
              <div className={`${CELL} ${MAPPING_COLS[0].width} text-[11px] font-semibold tracking-[0.88px] whitespace-nowrap text-sheet-muted uppercase`}>{row.title}</div>
              <div className={`${CELL} ${MAPPING_COLS[1].width}`} />
              <div className={`${CELL} ${MAPPING_COLS[2].width}`} />
              <div className={`${CELL} ${MAPPING_COLS[3].width}`} />
            </Row>
          );
        }
        const conf = row.remap ? "Your edit" : row.unsure ? "Needs you" : row.shown.text;
        const tone = row.remap ? "text-sheet-muted" : row.unsure ? "text-escalation" : row.shown.sure ? "text-forest" : "text-sheet-muted";
        const byYou = !row.remap && !row.unsure && row.shown.by === "you";
        return (
          <Row key={row.key} n={n} on={active?.row === n}>
            <div className={`${CELL} ${MAPPING_COLS[0].width} gap-[8px] text-[14px] text-ink`}>
              <span className="truncate" title={row.line.line}>{row.line.line}</span>
            </div>
            <PlatformCell
              r={row} n={n} editable={editable} options={remapOptions(kase, row.line.section)} platform={platform}
              active={active} menu={menu} setMenu={setMenu} onSelect={onSelect}
            />
            <div
              className={`${CELL} ${MAPPING_COLS[2].width} justify-end gap-[6px] text-[13px] font-semibold whitespace-nowrap ${tone}`}
              title={!row.remap && !row.unsure ? row.shown.title ?? undefined : undefined}
            >
              {byYou ? <span className="font-mono text-[11px] font-normal text-sheet-muted">by you</span> : null}
              {conf}
            </div>
            <div className={`${CELL} ${MAPPING_COLS[3].width} gap-[8px] text-[13px] text-sheet-muted`}>
              {row.learned && !row.remap ? <span className="shrink-0 rounded-chip bg-mint px-[6px] py-[1px] text-[10px] font-semibold tracking-[0.6px] text-forest uppercase">Learned</span> : null}
              <span className="truncate" title={row.mapping.reason}>{row.mapping.reason}</span>
            </div>
          </Row>
        );
      })}
      {rows.length <= 1 ? <p className="px-[56px] py-[16px] text-[14px] text-sheet-muted">The Mapper has not mapped this deal yet.</p> : null}
    </div>
  );
}
