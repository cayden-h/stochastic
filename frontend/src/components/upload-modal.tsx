"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Pace } from "@/lib/api";
import { useDeal } from "@/lib/deal-context";
import { canStart, fmtX, plural } from "@/lib/format";
import { FileIcon, UploadIcon } from "./icons";
import { Label } from "./ui";

type Slot = "platform" | "target" | "brief";

/** Begin's pace: the Factory demo, about 30 s of agent time. */
const FACTORY_PACE = "factory" satisfies Pace;
interface Picked { file: File; sub: string }

const SLOTS: { key: Slot; label: string; accept: string }[] = [
  { key: "platform", label: "Platform", accept: ".csv,text/csv" },
  { key: "target", label: "Target", accept: ".csv,text/csv" },
  // A Brief as JSON skips the reader; the credit agreement as text is read by the Brief Reader first (D20).
  { key: "brief", label: "Brief or agreement", accept: ".json,application/json,.txt,text/plain" },
];

/** A company name from a statement file name: "Kewaunee_10Q_2024-10-31.csv" gives "Kewaunee". */
function companyOf(file: File): string {
  return file.name.replace(/\.[^.]+$/, "").split(/[_.]/)[0].replace(/-/g, " ").trim() || file.name;
}

const isAgreement = (file: File) => /\.txt$/i.test(file.name) || file.type === "text/plain";

/** What the chip says under a chosen file: the CSV's row count, the brief's own limit, or the agreement's size.
 * Nothing is computed. */
async function summarize(slot: Slot, file: File): Promise<string> {
  const text = await file.text();
  if (slot === "brief" && isAgreement(file)) {
    return `Agreement text \u00b7 ${Math.max(1, Math.round(text.length / 1000))}K characters \u00b7 the Brief Reader reads it`;
  }
  if (slot === "brief") {
    try {
      const limit = JSON.parse(text)?.limit;
      return typeof limit === "number" ? `Limit ${fmtX(limit)}` : "No limit in the file";
    } catch {
      return "Not valid JSON";
    }
  }
  const rows = plural(Math.max(0, text.split(/\r?\n/).filter((l) => l.trim()).length - 1), "row");
  return `${rows} \u00b7 as ${companyOf(file)}`;
}

/**
 * V3-2: a new deal from two statement CSVs and a Brief (JSON) or the credit agreement (text), then the run.
 * Begin is the Factory demo: it resets with memory cleared, creates the deal, and runs it at pace "factory" (about 30 s of agent time, twice the
 * 15-second demo), hard-coded as Run the demo is, and opens its Case.
 * With agreement text the run starts with the Brief Reader, and the Case shows its draft to check.
 * With no files chosen, the slots show the current deal's inputs and Begin runs it at the same pace.
 */
export function UploadModal({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const { kase, select, startRun, reset } = useDeal();
  const [picked, setPicked] = useState<Partial<Record<Slot, Picked>>>({});
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  // The deal this modal created: a retry after a failed start re-runs it instead of creating a second deal.
  const created = useRef<string | null>(null);
  const many = useRef<HTMLInputElement>(null);
  const one = useRef<Record<Slot, HTMLInputElement | null>>({ platform: null, target: null, brief: null });
  const dialog = useRef<HTMLDivElement>(null);
  // The latest onClose and busy, read by the one key handler set up on mount (the parent passes an inline onClose).
  const onCloseRef = useRef(onClose);
  const busyRef = useRef(false);
  useEffect(() => { onCloseRef.current = onClose; busyRef.current = busy; });

  // Nothing closes the modal while a request is in flight.
  const close = useCallback(() => { if (!busyRef.current) onCloseRef.current(); }, []);

  // Once, on open: focus moves into the dialog, Tab stays inside it, and focus returns to the opener on close.
  // When every control is disabled (busy), the panel itself (tabIndex -1) holds focus.
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    const panel = dialog.current;
    const focusable = () => [...(panel?.querySelectorAll<HTMLElement>("button:not([disabled]), input:not([disabled]):not(.hidden)") ?? [])];
    (focusable()[0] ?? panel)?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { close(); return; }
      if (e.key !== "Tab") return;
      const items = focusable();
      const active = document.activeElement;
      if (!items.length) { e.preventDefault(); panel?.focus(); return; }
      const first = items[0], last = items[items.length - 1];
      if (!panel?.contains(active)) { e.preventDefault(); (e.shiftKey ? last : first).focus(); }
      else if (e.shiftKey && (active === first || active === panel)) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && active === last) { e.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", onKey);
    return () => { window.removeEventListener("keydown", onKey); opener?.focus(); };
  }, [close]);

  if (!kase) return null;
  const { deal, source_lines } = kase;

  async function put(slot: Slot, file: File) {
    const sub = await summarize(slot, file);
    created.current = null;  // new inputs make a new deal
    setPicked((p) => ({ ...p, [slot]: { file, sub } }));
  }

  /** Several files at once: the JSON is the brief, the CSVs fill platform then target in the order chosen.
   * The slots name the company each CSV is read as, and Swap exchanges them. */
  async function putMany(files: FileList | null) {
    if (!files) return;
    const csvs = [...files].filter((f) => f.name.toLowerCase().endsWith(".csv"));
    const brief = [...files].find((f) => /\.(json|txt)$/i.test(f.name));
    if (csvs[0]) await put("platform", csvs[0]);
    if (csvs[1]) await put("target", csvs[1]);
    if (brief) await put("brief", brief);
  }

  function swap() {
    created.current = null;
    setPicked((p) => {
      // Only defined slots are kept, so a swap with one CSV leaves no empty key behind.
      const next: Partial<Record<Slot, Picked>> = { brief: p.brief, platform: p.target, target: p.platform };
      return Object.fromEntries(Object.entries(next).filter(([, v]) => v)) as Partial<Record<Slot, Picked>>;
    });
  }

  const current: Record<Slot, { name: string; sub: string }> = {
    platform: { name: `${deal.platform} statements`, sub: plural(source_lines.filter((l) => l.company === deal.platform).length, "line") },
    target: { name: `${deal.target} statements`, sub: plural(source_lines.filter((l) => l.company === deal.target).length, "line") },
    brief: deal.brief
      ? { name: `${deal.brief.lender.split(",")[0]} agreement`, sub: `Limit ${fmtX(deal.brief.limit)}` }
      : { name: "Credit agreement (text)", sub: "The Brief Reader reads it first" },
  };

  async function begin() {
    setBusy(true); setNote(null);
    try {
      const chosen = Object.values(picked).filter(Boolean).length;
      if (chosen && chosen < 3) throw new Error("Choose the platform CSV, the target CSV, and the brief or the agreement text, or close to keep this deal.");
      if (chosen && !created.current) {
        // A fresh reset first (memory cleared, retried while a run is finishing): otherwise the policies learned on the
        // demo deal cover the uploaded Kewaunee and Nu Aire lines, and the Factory run asks nothing.
        await reset(false);
        const p = picked.platform!.file, t = picked.target!.file;
        const form = new FormData();
        form.set("platform", companyOf(p));
        form.set("target", companyOf(t));
        form.set("name", `${companyOf(p)} acquires ${companyOf(t)}`);
        const b = picked.brief!.file;
        if (isAgreement(b)) form.set("agreement_txt", b);
        else form.set("brief", await b.text());
        form.set("platform_csv", p);
        form.set("target_csv", t);
        created.current = (await api.createDeal(form)).deal_id;
        await select(created.current);  // the new deal is current even if the start below fails
      }
      if (created.current) {
        await startRun(created.current, FACTORY_PACE);
      } else if (canStart(kase!.stage)) {
        await startRun(deal.id, FACTORY_PACE);
      }
      onClose();
      router.push("/case");
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Could not start the deal");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="no-drag fixed inset-0 z-20 flex items-center justify-center bg-[rgba(15,102,116,0.45)] p-4 pt-[34px]">
      {/* The backdrop closes on click but is not a tab stop; Close and Esc do the same from the keyboard. */}
      <div aria-hidden="true" className="absolute inset-0" onClick={close} />
      <div ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="new-deal-title" className="relative flex outline-none w-full max-w-[880px] flex-col gap-[18px] rounded-[20px] bg-white p-[28px] shadow-[0px_24px_60px_0px_rgba(15,102,116,0.3)]">
        <div className="flex w-full items-center gap-[12px]">
          <h2 id="new-deal-title" className="font-serif text-[30px] text-forest">New deal</h2>
          <span className="flex-1" />
          <button className="text-[14px] font-semibold text-slate hover:text-forest disabled:opacity-40" onClick={close} disabled={busy}>Close</button>
        </div>

        <div className="flex w-full justify-center">
          <button
            className="inline-flex items-center gap-[8px] rounded-chip border border-line bg-white px-[12px] py-[8px] text-[13px] font-semibold text-forest hover:border-mint-edge hover:bg-mint-select"
            onClick={() => many.current?.click()}
            disabled={busy}
          >
            <UploadIcon />
            Upload files
          </button>
          <input ref={many} type="file" multiple accept=".csv,.json,.txt" className="hidden" onChange={(e) => { putMany(e.target.files); e.target.value = ""; }} />
        </div>

        <div className="flex w-full gap-[12px]">
          {/* 125 px slots: the frame's height, where a long file name takes two lines. */}
          {SLOTS.map((s) => {
            const chosen = picked[s.key];
            const shown = chosen ? { name: chosen.file.name, sub: chosen.sub } : current[s.key];
            return (
              <div key={s.key} className="flex min-h-[125px] min-w-0 flex-1 flex-col gap-[10px] rounded-[12px] border border-line bg-white p-[14px]">
                <Label>{s.label}</Label>
                <button
                  className="flex w-full items-center gap-[10px] rounded-[8px] bg-mint-file p-[10px] text-left hover:brightness-[0.98]"
                  title={`Choose the ${s.label.toLowerCase()} file`}
                  onClick={() => one.current[s.key]?.click()}
                  disabled={busy}
                >
                  <FileIcon />
                  <span className="flex min-w-0 flex-1 flex-col gap-[2px]">
                    <span className="text-[13px] font-semibold break-words text-forest">{shown.name}</span>
                    <span className="text-[12px] text-mint-file-ink">{shown.sub}</span>
                  </span>
                </button>
                <input
                  ref={(el) => { one.current[s.key] = el; }}
                  type="file"
                  accept={s.accept}
                  className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) put(s.key, f); e.target.value = ""; }}
                />
              </div>
            );
          })}
        </div>

        {picked.platform || picked.target ? (
          <div className="-mt-[6px] flex w-full justify-center">
            <button className="text-[13px] font-semibold text-clear hover:underline disabled:opacity-40" onClick={swap} disabled={busy}>
              Swap platform and target
            </button>
          </div>
        ) : null}

        {note ? <p role="alert" className="rounded-[8px] bg-denied-tint px-[12px] py-[8px] text-[13px] font-semibold text-denied">{note}</p> : null}

        <div className="relative flex w-full flex-col items-center gap-[10px] pt-[24px] pb-[8px]">
          <Image src="/v3/glow.svg" alt="" width={420} height={150} className="pointer-events-none absolute top-[-23px] left-1/2 h-[150px] w-[420px] max-w-none -translate-x-1/2" />
          <button
            className="relative inline-flex min-h-11 items-center justify-center rounded-full bg-forest px-[44px] py-[14px] font-ui text-[18px] leading-[28px] font-semibold text-paper drop-shadow-[0px_8px_12px_rgba(15,102,116,0.35)] transition-colors duration-150 hover:bg-forest-deep disabled:opacity-40"
            onClick={begin}
            disabled={busy}
          >
            {busy ? "Starting" : "Begin"}
          </button>
        </div>
      </div>
    </div>
  );
}
