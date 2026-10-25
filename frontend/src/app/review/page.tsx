"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Companion } from "@/components/companion";
import { MathPanel } from "@/components/math-panel";
import { MAPPING_COLS, MappingSheet, mappingLayout } from "@/components/review-mapping";
import { Shape } from "@/components/ui";
import {
  type Active, type SheetHandlers, ColumnLetters, ConfidenceMark, CovenantSheetRow, DetailSheetRow, HeaderRow, LineSheetRow,
  SectionTitleRow, SubSheetRow,
} from "@/components/workbook";
import { EditsStrip, change, useDownloadFinal } from "@/components/your-edits";
import { api } from "@/lib/api";
import { useDeal } from "@/lib/deal-context";
import { useEdits } from "@/lib/edit-context";
import { canEdit, editAnchor, num } from "@/lib/edits";
import { fmtX, mappingCounts, openQuestionLines, plural } from "@/lib/format";
import type { Case, Edit, GlResponse, ToolRun } from "@/lib/types";
import {
  type AmountCell, type CovenantRow, type LineRow, type SheetRow, SECTION_TITLES, SHEET_ORDER, agentsLeverageRun,
  amountAnchor, amountNote, cellRef, detailRows, lineNote, rawAmount, remapAnchor, remapOptions, sectionRows, was,
} from "@/lib/workbook";

/** What the formula bar shows for a cell, and where the cell is. */
interface CellMeta { ref: string; row: number; col: string; value: string; note: string }

type Laid = { n: number; row: SheetRow | { kind: "head" } };

/** The rows in sheet order with their row numbers, and each editable cell's reference and formula-bar text. An opened
 * row shows its detail block (detailRows) in place of its target lines; the block's target lines stay editable there. */
function layout(kase: Case, edits: Edit[], open: Set<string>, covenant: CovenantRow[], gl: GlResponse | null) {
  const rows: Laid[] = [{ n: 1, row: { kind: "head" } }];
  const meta = new Map<string, CellMeta>();
  const result = kase.result;
  if (!result) return { rows, meta };
  const platform = kase.deal.platform;
  const amount = (cell: AmountCell, n: number, col: string) => {
    if (!cell.source) return;
    meta.set(amountAnchor(cell.source), { ref: cellRef(col, n), row: n, col, value: rawAmount(cell.value), note: amountNote(cell, cell.source.company) });
  };
  for (const part of SHEET_ORDER) {
    if (part === "covenant") {
      if (!covenant.length) continue;
      rows.push({ n: rows.length + 1, row: { kind: "section", key: "covenant", title: "Covenant test" } });
      for (const c of covenant) rows.push({ n: rows.length + 1, row: c });
      continue;
    }
    const lines = sectionRows(result, kase, edits, part);
    if (!lines.length) continue;
    rows.push({ n: rows.length + 1, row: { kind: "section", key: part, title: SECTION_TITLES[part] } });
    for (const r of lines) {
      const n = rows.length + 1;
      rows.push({ n, row: r });
      amount(r.platform, n, "B");
      amount(r.target, n, "C");
      if (r.remapLine) meta.set(remapAnchor(r.remapLine), { ref: cellRef("A", n), row: n, col: "A", value: r.remapLine.line, note: lineNote(r.remapLine, r.remap, platform) });
      if (open.has(r.key)) {
        for (const d of detailRows(r, kase, gl, edits)) {
          const m = rows.length + 1;
          rows.push({ n: m, row: d });
          if (d.kind === "dline" && d.sub) {
            amount(d.sub.target, m, "C");
            meta.set(remapAnchor(d.sub.line), { ref: cellRef("A", m), row: m, col: "A", value: d.sub.line.line, note: lineNote(d.sub.line, d.sub.remap, platform) });
          }
        }
        continue;
      }
      for (const s of r.subs) {
        const m = rows.length + 1;
        rows.push({ n: m, row: s });
        amount(s.target, m, "C");
        meta.set(remapAnchor(s.line), { ref: cellRef("A", m), row: m, col: "A", value: s.line.line, note: lineNote(s.line, s.remap, platform) });
      }
    }
  }
  return { rows, meta };
}

function Chip({ tone, children }: { tone: "mint" | "amber"; children: React.ReactNode }) {
  return (
    <span className={`inline-flex shrink-0 items-center gap-[6px] rounded-full py-[4px] pr-[12px] pl-[10px] text-[13px] font-semibold whitespace-nowrap ${
      tone === "mint" ? "bg-mint text-forest" : "bg-escalation-tint text-escalation"
    }`}>
      {children}
    </span>
  );
}

const BTN = "inline-flex shrink-0 items-center justify-center rounded-chip px-[14px] py-[6px] font-ui text-[13px] leading-[18px] font-semibold whitespace-nowrap transition-colors duration-150 disabled:cursor-not-allowed";
const PRIMARY = `${BTN} bg-forest text-white hover:bg-forest-deep disabled:opacity-40 disabled:hover:bg-forest`;
const SECONDARY = `${BTN} border border-rule bg-white text-ink hover:bg-sheet-band disabled:opacity-45 disabled:hover:bg-white`;

type Tab = "review" | "mapping";

const TABS: { key: Tab; label: string }[] = [
  { key: "review", label: "Review" },
  { key: "mapping", label: "Mapping" },
];

/**
 * V3-7, Review (D19, Figma 670:44): the combined books as a workbook the controller edits, with the Reviewer asking
 * why. It sits in the sidebar shell like every page, with "Back to case" in its header. Two tabs: Review, the
 * workbook, where an amount is changed; and Mapping, the target lines with the platform line each goes to, where a
 * line is remapped. Then the formula bar, the sheet, the verdict and Your edits, and the sheet tabs. Approve and
 * Download final files live here, and gate on every edit of either tab.
 */
export default function ReviewPage() {
  return (
    <Suspense fallback={null}>
      <ReviewScreen />
    </Suspense>
  );
}

function ReviewScreen() {
  const { kase, refresh, mappings } = useDeal();
  const router = useRouter();
  const tab: Tab = useSearchParams().get("tab") === "mapping" ? "mapping" : "review";
  const ctx = useEdits();
  const [selected, setSelected] = useState<Active | null>(null);
  const [typed, setTyped] = useState("");
  const [menu, setMenu] = useState<string | null>(null);
  // The combined rows whose detail block is open. All start closed, so the covenant block stays pinned under the income
  // statement; Expand all opens every row.
  const [open, setOpen] = useState<Set<string>>(new Set());
  const [gl, setGl] = useState<GlResponse | null>(null);
  const [sheet, setSheet] = useState<"combined" | "edits">("combined");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [runs, setRuns] = useState<ToolRun[]>([]);
  const [math, setMath] = useState(false);
  const download = useDownloadFinal(kase?.deal ?? null);

  const edits = ctx.edits;
  const dealId = kase?.deal.id;
  const editStamp = edits.map((e) => `${e.id}:${e.status}`).join(",");
  // The agents' own leverage run, for the "was" figures on the covenant rows. Read again when the edits change.
  useEffect(() => {
    if (!dealId || !editStamp) return;
    let gone = false;
    api.runs(dealId).then((r) => { if (!gone) setRuns(r); }).catch(() => {});
    return () => { gone = true; };
  }, [dealId, editStamp]);

  // The simulated GL accounts under each source line. Read once per deal; without the route the GL rows stay hidden.
  useEffect(() => {
    if (!dealId) return;
    let gone = false;
    void api.gl(dealId).then((g) => { if (!gone) setGl(g); });
    return () => { gone = true; };
  }, [dealId]);

  const verdict = kase?.verdict ?? null;
  const covenant = useMemo<CovenantRow[]>(() => {
    if (!verdict) return [];
    const o = (edits.length ? agentsLeverageRun(runs, edits)?.outputs : undefined) as { leverage?: number; ebitda?: number; debt?: number } | undefined;
    return [
      { kind: "covenant", key: "ebitda", label: "Covenant EBITDA", value: num(verdict.ebitda), was: was(num(verdict.ebitda), o?.ebitda != null ? num(o.ebitda) : null), bold: false },
      { kind: "covenant", key: "debt", label: verdict.debt_term || "Debt", value: num(verdict.debt), was: was(num(verdict.debt), o?.debt != null ? num(o.debt) : null), bold: false },
      { kind: "covenant", key: "leverage", label: `Leverage, limit ${fmtX(verdict.limit)}`, value: fmtX(verdict.leverage), was: was(fmtX(verdict.leverage), o?.leverage != null ? fmtX(o.leverage) : null), bold: true },
    ];
  }, [verdict, edits, runs]);

  const laid = useMemo(() => (kase ? layout(kase, edits, open, covenant, gl) : { rows: [] as Laid[], meta: new Map<string, CellMeta>() }), [kase, edits, open, covenant, gl]);
  const lineKeys = useMemo(() => laid.rows.flatMap((r) => (r.row.kind === "line" ? [r.row.key] : [])), [laid]);
  const asking = useMemo(() => openQuestionLines(kase?.flags ?? [], kase?.open_flags ?? []), [kase]);
  const mapped = useMemo(() => (kase ? mappingLayout(kase, mappings, edits, asking) : null), [kase, mappings, edits, asking]);

  if (!kase) return null;
  const { deal, result } = kase;
  const editable = canEdit(kase);
  const posted = Boolean(verdict?.posted);
  const review = verdict?.review?.verdict ?? null;
  const over = verdict?.verdict === "over_limit";
  const unreasoned = edits.filter((e) => e.status === "needs_reason").length;
  const reasoned = edits.filter((e) => e.status === "reasoned").length;
  const proposed = verdict?.approval_state === "PROPOSED";
  const canApprove = Boolean(verdict) && proposed && review === "pass" && !over && !unreasoned && !kase.open_flags.length;

  // The cell being worked in: typing, the large-change question, the reason bubble, or the line menu.
  const meta: Map<string, CellMeta> = tab === "mapping" && mapped ? mapped.meta : laid.meta;
  const workingKey = ctx.editing ?? ctx.confirm?.anchor ?? (ctx.asking ? editAnchor(ctx.asking) : null) ?? menu;
  const workingMeta = workingKey ? meta.get(workingKey) : undefined;
  const active: Active | null = workingKey && workingMeta ? { key: workingKey, row: workingMeta.row, col: workingMeta.col } : null;
  const focusKey = workingKey ?? selected?.key ?? null;
  const focus = focusKey ? meta.get(focusKey) : undefined;
  const formulaValue = focus ? (ctx.editing === focusKey ? typed.replace(/,/g, "") : focus.value) : "";
  const formulaNote = focus ? focus.note
    : editable && tab === "mapping" ? `Click a platform line to map the ${deal.target} line to another ${deal.platform} line. Code recomputes every total.`
    : editable ? "Click a platform or target amount to change it. Code recomputes every total."
    : posted ? "Approved and posted. The books are read-only."
    : result ? "The books open for edits once the Reviewer passes them." : "Code combines the books after the agents run.";

  const h: SheetHandlers = { active, menu, setMenu, onSelect: setSelected, onTyped: setTyped };
  const options = (s: LineRow["section"]) => remapOptions(kase, s);
  const allOpen = lineKeys.length > 0 && lineKeys.every((k) => open.has(k));

  async function act(fn: () => Promise<unknown>) {
    setBusy(true); setNote(null);
    try { await fn(); await refresh(); } catch (e) { setNote(e instanceof Error ? e.message : "Action failed"); await refresh(); }
    finally { setBusy(false); }
  }

  const editWord = plural(edits.length, "edit");
  const headline = verdict
    ? `${over ? "Over" : "Under"} the limit at ${fmtX(verdict.leverage)}.${edits.length ? ` ${editWord.charAt(0).toUpperCase()}${editWord.slice(1)}.` : ""}`
    : null;
  const sub = !verdict ? null
    : verdict.approval_state === "REJECTED" ? "Rejected. Run the deal again from the Case."
    : posted && edits.length ? "Approved with your edits. The reasons are now policies for the next add-on."
    : posted ? "Approved and posted. No edits."
    : over ? "Over the limit. The gateway refuses approval."
    : review === "needs_attention" ? `Reviewer needs attention: ${verdict.review?.reasons[0] ?? "read the log"}`
    : unreasoned ? `${plural(unreasoned, "edit")} ${unreasoned === 1 ? "needs" : "need"} a reason before you can approve.`
    : edits.length ? "Reason saved. Ready to approve."
    : review === "pass" ? "Reviewer pass. No edits."
    : "The Reviewer is checking the books.";

  return (
    <>
      {/* The page header: the way back to the case, the page, and the workbook it holds. It drags the Mac window. */}
      <header className="drag flex h-[56px] w-full shrink-0 items-center gap-[16px] border-b border-sheet-line bg-white px-[20px]">
        <Link
          href="/case"
          className="inline-flex shrink-0 items-center gap-[6px] rounded-chip py-[6px] pr-[8px] text-[14px] font-semibold text-forest underline-offset-4 hover:underline"
        >
          <span aria-hidden="true" className="font-sans">&larr;</span>
          Back to case
        </Link>
        <span className="h-[22px] w-px shrink-0 bg-sheet-line" aria-hidden="true" />
        <h1 className="shrink-0 font-serif text-[26px] leading-none text-forest">Review</h1>
        <span className="min-w-0 truncate text-[13px] text-sheet-muted" title={`${deal.platform} + ${deal.target} combined books`}>
          {deal.platform} + {deal.target} combined books
        </span>
      </header>

      {/* Ribbon */}
      <nav className="flex h-[44px] w-full shrink-0 items-center border-b border-sheet-line bg-white px-[16px]" aria-label="Review ribbon">
        <div className="flex h-full items-start gap-[4px]" role="tablist" aria-label="Review tabs">
          {TABS.map((t) => {
            const on = t.key === tab;
            return (
              <button
                key={t.key}
                type="button"
                role="tab"
                aria-selected={on}
                onClick={() => { setMenu(null); setSelected(null); router.replace(t.key === "review" ? "/review" : `/review?tab=${t.key}`, { scroll: false }); }}
                className={`relative flex h-full items-center px-[12px] text-[13px] transition-colors duration-150 ${on ? "font-semibold text-forest" : "font-medium text-sheet-muted hover:text-forest"}`}
              >
                {t.label}
                {on ? <span className="absolute bottom-0 left-[8px] h-[2px] w-[calc(100%-16px)] bg-forest" aria-hidden="true" /> : null}
              </button>
            );
          })}
        </div>
        {tab === "review" && sheet === "combined" && result ? (
          <>
            <span className="mx-[10px] h-[18px] w-px shrink-0 bg-sheet-line" aria-hidden="true" />
            <button
              type="button"
              onClick={() => setOpen(allOpen ? new Set() : new Set(lineKeys))}
              className="inline-flex shrink-0 items-center gap-[6px] rounded-chip px-[8px] py-[4px] text-[13px] font-medium text-sheet-muted hover:bg-sheet-band hover:text-forest"
              title={allOpen ? "Close every row's detail" : "Open every row's source lines and GL accounts"}
            >
              <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
                <rect x="0.5" y="0.5" width="11" height="11" rx="2" fill="none" stroke="currentColor" />
                <path d={allOpen ? "M3.5 6h5" : "M3.5 6h5M6 3.5v5"} stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
              </svg>
              {allOpen ? "Collapse all" : "Expand all"}
            </button>
          </>
        ) : null}
        <span className="flex-1" />
        <div className="flex items-center gap-[8px]">
          {note ? <span role="alert" className="max-w-[360px] truncate text-[12px] font-semibold text-denied" title={note}>{note}</span> : null}
          {download.text ? <span role="status" className={`text-[12px] ${download.bad ? "text-escalation" : "text-sheet-muted"}`}>{download.text}</span> : null}
          {result ? (
            <button type="button" className={SECONDARY} onClick={() => setMath(true)} data-testid="check-math" title="How code made each figure, re-checked in your browser">
              Check the math
            </button>
          ) : null}
          {result ? (
            <Chip tone="mint">
              <span className={result.tie_out_ok ? "" : "text-denied"}><Shape kind={result.tie_out_ok ? "check" : "cross"} size={10} /></span>
              <span className={result.tie_out_ok ? "" : "text-denied"}>{result.tie_out_ok ? "Ties out" : "Does not tie out"}</span>
            </Chip>
          ) : null}
          {edits.length ? (
            unreasoned ? (
              <Chip tone="amber"><span className="size-[8px] rounded-full bg-edit-bar" aria-hidden="true" />{plural(unreasoned, "edit")} {unreasoned === 1 ? "needs" : "need"} a reason</Chip>
            ) : (
              <Chip tone="mint"><Shape kind="check" size={10} />{plural(edits.length, "edit")}, {edits.length === 1 ? "reason" : "reasons"} given</Chip>
            )
          ) : null}
          {posted ? (
            <>
              <button type="button" className={PRIMARY} disabled={download.busy} onClick={() => void download.go()}>
                {download.busy ? "Saving files" : "Download final files"}
              </button>
              <Chip tone="mint"><Shape kind="check" size={10} />Approved and posted</Chip>
            </>
          ) : verdict ? (
            <>
              {edits.length ? (
                <>
                  <span className="text-[12px] whitespace-nowrap text-sheet-muted">after approval</span>
                  <button type="button" className={SECONDARY} disabled title="The final files come after approval">Download final files</button>
                </>
              ) : null}
              {proposed ? (
                <button
                  type="button"
                  className="shrink-0 px-[6px] text-[13px] font-medium text-sheet-muted underline-offset-4 hover:text-denied hover:underline disabled:opacity-40"
                  disabled={busy}
                  onClick={() => void act(() => api.reject(verdict.approval_item!, "Rejected by the controller on Review."))}
                >
                  Reject
                </button>
              ) : null}
              <button
                type="button"
                className={PRIMARY}
                disabled={busy || !canApprove}
                title={unreasoned ? "Give each edit a reason first" : !canApprove ? "Approval waits for the Reviewer's pass" : undefined}
                onClick={() => void act(() => api.approve(verdict.approval_item!))}
              >
                Approve
              </button>
            </>
          ) : null}
        </div>
      </nav>

      {ctx.error ? (
        <p role="alert" className="flex shrink-0 items-center gap-[12px] bg-denied-tint px-[16px] py-[6px] text-[13px] font-semibold text-denied">
          <span className="flex-1">The edit was not saved: {ctx.error}</span>
          <button type="button" className="underline-offset-4 hover:underline" onClick={ctx.clearError}>Dismiss</button>
        </p>
      ) : null}

      {/* Formula bar */}
      <div className="flex h-[36px] w-full shrink-0 items-center gap-[10px] border-b border-sheet-line bg-white pr-[16px] pl-[12px]">
        <span className="flex h-[24px] w-[52px] shrink-0 items-center justify-center rounded-[4px] border border-sheet-line font-mono text-[12px] text-ink" aria-label="Cell">
          {focus?.ref ?? ""}
        </span>
        <span className="w-[12px] shrink-0 font-serif text-[17px] text-sheet-muted italic" aria-hidden="true">fx</span>
        <span className="h-[18px] w-px shrink-0 bg-sheet-line" aria-hidden="true" />
        {formulaValue ? <span className="shrink-0 text-[13px] font-medium whitespace-nowrap text-ink">{formulaValue}</span> : null}
        <span className="truncate text-[12px] text-sheet-muted">{formulaNote}</span>
      </div>

      {tab === "mapping"
        ? <ColumnLetters active={active} cols={MAPPING_COLS} rest="E" />
        : <ColumnLetters active={sheet === "combined" ? active : null} />}

      {/* The sheet. It scrolls; the title bar, ribbon, formula bar, and the strips below stay put. */}
      <div className="relative min-h-0 w-full flex-1 overflow-x-hidden overflow-y-auto" data-sheet="">
        {tab === "mapping" && mapped ? (
          <MappingSheet kase={kase} rows={mapped.rows} editable={editable} active={active} menu={menu} setMenu={setMenu} onSelect={setSelected} />
        ) : sheet === "edits" ? (
          <EditsSheet />
        ) : (
          <div className="flex w-full flex-col">
            {laid.rows.map(({ n, row }) => {
              if (row.kind === "head") return <HeaderRow key="head" n={n} platform={deal.platform} target={deal.target} />;
              if (row.kind === "section" && row.key === "covenant") {
                // The covenant test (Covenant EBITDA, Senior Funded Bank Debt, Leverage) is pinned to the bottom of the
                // sheet, over the verdict strip, as in frame V3-7.3: the leverage an edit moves is always on screen at
                // 1440x900. It keeps its place and row numbers under the income statement, and scrolls on from there.
                const block = laid.rows.filter((r) => r.row.kind === "covenant");
                return (
                  <div key="covenant" className="sticky bottom-0 z-[5] bg-white shadow-[0_-1px_0_var(--color-sheet-line)]" data-covenant-block="">
                    <SectionTitleRow n={n} title={row.title} />
                    {block.map((r) => r.row.kind === "covenant" ? <CovenantSheetRow key={r.row.key} n={r.n} row={r.row} /> : null)}
                  </div>
                );
              }
              if (row.kind === "section") return <SectionTitleRow key={row.key} n={n} title={row.title} />;
              if (row.kind === "covenant") return null; // drawn in the pinned block above
              if (row.kind === "sub") return <SubSheetRow key={row.key} n={n} row={row} editable={editable} platform={deal.platform} options={options(row.line.section)} h={h} />;
              if (row.kind === "dline" && row.sub) {
                return (
                  <SubSheetRow
                    key={row.key} n={n} row={row.sub} editable={editable} platform={deal.platform} options={options(row.line.section)} h={h}
                    badge={row.mapping ? <ConfidenceMark mapping={row.mapping} asking={asking} /> : null}
                  />
                );
              }
              if (row.kind !== "line") {
                return <DetailSheetRow key={row.key} n={n} row={row} platform={deal.platform} target={deal.target} asking={asking} note={gl?.note ?? ""} />;
              }
              return (
                <LineSheetRow
                  key={row.key} n={n} row={row} editable={editable} platform={deal.platform} target={deal.target} options={options(row.section)}
                  open={open.has(row.key)}
                  onToggle={() => setOpen((s) => { const x = new Set(s); if (x.has(row.key)) x.delete(row.key); else x.add(row.key); return x; })}
                  h={h}
                />
              );
            })}
            {!result ? (
              <p className="px-[56px] py-[16px] text-[14px] text-sheet-muted">
                The books are not combined yet. The agents run on the{" "}
                <Link href="/case" className="font-semibold text-forest underline-offset-4 hover:underline">Case</Link>; the Reviewer hands off here.
              </p>
            ) : null}
          </div>
        )}
      </div>

      {/* Verdict */}
      <div className="flex h-[36px] w-full shrink-0 items-center gap-[12px] border-t border-sheet-line bg-white px-[16px]">
        {headline ? <strong className="shrink-0 text-[14px] font-semibold whitespace-nowrap text-forest">{headline}</strong> : null}
        {sub ? <span className="min-w-0 truncate text-[14px] text-ink" title={sub}>{sub}</span> : null}
        <span className="min-w-0 flex-1" />
        {verdict ? (
          <strong className={`shrink-0 text-[14px] font-semibold whitespace-nowrap ${over ? "text-denied" : "text-forest"}`}>
            {fmtX(verdict.leverage)} of {fmtX(verdict.limit)}
          </strong>
        ) : null}
      </div>

      <EditsStrip locked={!editable} editable={editable} />

      {/* Sheet tabs and status */}
      <footer className="flex h-[40px] w-full shrink-0 items-stretch border-t border-titlebar-line bg-sheet-head">
        <div className="-mt-px ml-[44px] flex items-stretch" role="tablist" aria-label="Sheets">
          {tab === "mapping" ? (
            <span role="tab" aria-selected="true" className="relative flex items-center bg-white px-[16px] text-[12px] font-semibold text-forest">
              <span className="absolute top-0 right-0 left-0 h-[2px] bg-forest" aria-hidden="true" />
              Mapping
            </span>
          ) : null}
          {tab === "mapping" ? null : <>
          <button
            type="button" role="tab" aria-selected={sheet === "combined"} onClick={() => setSheet("combined")}
            className={`relative flex items-center px-[16px] text-[12px] ${sheet === "combined" ? "bg-white font-semibold text-forest" : "font-medium text-sheet-muted hover:text-forest"}`}
          >
            {sheet === "combined" ? <span className="absolute top-0 right-0 left-0 h-[2px] bg-forest" aria-hidden="true" /> : null}
            Combined
          </button>
          <button
            type="button" role="tab" aria-selected={sheet === "edits"} onClick={() => setSheet("edits")}
            className={`relative flex items-center gap-[6px] px-[16px] text-[12px] ${sheet === "edits" ? "bg-white font-semibold text-forest" : "font-medium text-sheet-muted hover:text-forest"}`}
            title="Edits saved with a reason"
          >
            {sheet === "edits" ? <span className="absolute top-0 right-0 left-0 h-[2px] bg-forest" aria-hidden="true" /> : null}
            Edits <span className="font-mono text-[11px] font-normal">{reasoned}</span>
          </button>
          </>}
          <Link href="/log" className="flex items-center px-[16px] text-[12px] font-medium text-sheet-muted hover:text-forest">Audit</Link>
        </div>
        <span className="flex-1" />
        {tab === "mapping" && mapped ? (
          <span className="self-center truncate pr-[16px] pl-[12px] text-[12px] text-sheet-muted">
            {mappingStatus(kase, mappings, asking, edits)}
          </span>
        ) : verdict ? (
          <span className="self-center truncate pr-[16px] pl-[12px] text-[12px] text-sheet-muted">
            Covenant leverage {fmtX(verdict.leverage)} against {fmtX(verdict.limit)} &middot;{" "}
            <button type="button" onClick={() => setMath(true)} className="underline-offset-4 hover:text-forest hover:underline">every figure is a tool run</button>
            {" "}&middot; USD thousands
          </span>
        ) : null}
      </footer>

      <Companion />
      {math ? <MathPanel kase={kase} onClose={() => setMath(false)} /> : null}
    </>
  );
}

/** The Mapping sheet's status: how many target lines are placed, sure, and remapped. */
function mappingStatus(kase: Case, mappings: Case["mappings"], asking: Set<string>, edits: Edit[]): string {
  const { placed, sure, unsure } = mappingCounts(mappings, kase.source_lines, asking);
  const remaps = edits.filter((e) => e.kind === "remap").length;
  return `${plural(placed, `${kase.deal.target} line`)} placed · ${sure} sure · ${unsure} unsure${remaps ? ` · ${plural(remaps, "remap")}` : ""} · totals are not mapped`;
}

/** The Edits sheet: every live edit as a row of the workbook, with its reason and what it taught. */
function EditsSheet() {
  const ctx = useEdits();
  const head = "text-[12px] font-semibold whitespace-nowrap text-ink";
  const cell = "flex h-[32px] shrink-0 items-center border-r border-sheet-line px-[10px]";
  const gutter = "flex h-[32px] w-[44px] shrink-0 items-center justify-center border-r border-sheet-line bg-sheet-head text-[11px] text-sheet-muted";
  return (
    <div className="flex w-full flex-col">
      <div className="flex w-full border-b border-sheet-line">
        <div className={gutter}>1</div>
        <div className={`${cell} w-[380px] ${head}`}>Line</div>
        <div className={`${cell} w-[150px] justify-end ${head}`}>Was</div>
        <div className={`${cell} w-[150px] justify-end ${head}`}>Now</div>
        <div className={`${cell} w-[300px] ${head}`}>Reason</div>
        <div className={`${cell} min-w-0 flex-1 border-r-0 ${head}`}>Learned</div>
      </div>
      {ctx.edits.map((e, i) => (
        <div key={e.id} className="flex w-full border-b border-sheet-line text-[14px] text-ink">
          <div className={gutter}>{i + 2}</div>
          <button type="button" onClick={() => ctx.show(e.id)} className={`${cell} w-[380px] truncate text-left hover:underline`}>{e.line} &middot; {e.company}</button>
          <div className={`${cell} w-[150px] justify-end font-mono text-[13px]`}>{e.kind === "amount" ? num(e.old_value ?? 0) : e.old_platform_line ?? "Unmapped"}</div>
          <div className={`${cell} w-[150px] justify-end font-mono text-[13px]`}>{e.kind === "amount" ? num(e.new_value ?? 0) : e.new_platform_line}</div>
          <div className={`${cell} w-[300px] ${e.status === "needs_reason" ? "font-medium text-escalation" : "text-sheet-muted"}`}>
            <span className="truncate" title={e.reason_text ?? change(e)}>{e.reason_text ?? "Needs a reason"}</span>
          </div>
          <div className={`${cell} min-w-0 flex-1 border-r-0 font-mono text-[12px] text-sheet-muted`}>{e.policy_id ?? e.adjustment_id ?? ""}</div>
        </div>
      ))}
      {!ctx.edits.length ? <p className="px-[56px] py-[16px] text-[14px] text-sheet-muted">No edits yet.</p> : null}
    </div>
  );
}
