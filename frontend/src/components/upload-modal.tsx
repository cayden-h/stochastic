"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useDeal } from "@/lib/deal-context";
import { canStart, fmtX, plural } from "@/lib/format";
import { FileIcon, UploadIcon } from "./icons";
import { Label } from "./ui";

type Slot = "platform" | "target" | "brief";
interface Picked { file: File; sub: string }

const SLOTS: { key: Slot; label: string; accept: string }[] = [
  { key: "platform", label: "Platform", accept: ".csv,text/csv" },
  { key: "target", label: "Target", accept: ".csv,text/csv" },
  { key: "brief", label: "Brief", accept: ".json,application/json" },
];

/** A company name from a statement file name: "Kewaunee_10Q_2024-10-31.csv" gives "Kewaunee". */
function companyOf(file: File): string {
  return file.name.replace(/\.[^.]+$/, "").split(/[_.]/)[0].replace(/-/g, " ").trim() || file.name;
}

/** What the chip says under a chosen file: the CSV's row count, or the brief's own limit. Nothing is computed. */
async function summarize(slot: Slot, file: File): Promise<string> {
  const text = await file.text();
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
 * V3-2: a new deal from two statement CSVs and a brief (POST /deals), then the run.
 * With no files chosen, the slots show the current deal's inputs and Begin runs it.
 */
export function UploadModal({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const { kase, select } = useDeal();
  const [picked, setPicked] = useState<Partial<Record<Slot, Picked>>>({});
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  // The deal this modal created: a retry after a failed start re-runs it instead of creating a second deal.
  const created = useRef<string | null>(null);
  const many = useRef<HTMLInputElement>(null);
  const one = useRef<Record<Slot, HTMLInputElement | null>>({ platform: null, target: null, brief: null });
  const dialog = useRef<HTMLDivElement>(null);
  const busyRef = useRef(false);
  useEffect(() => { busyRef.current = busy; }, [busy]);

  // Nothing closes the modal while a request is in flight.
  const close = useCallback(() => { if (!busyRef.current) onClose(); }, [onClose]);

  // Focus moves into the dialog on open, Tab stays inside it, and focus returns to the opener on close.
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    const focusable = () => [...(dialog.current?.querySelectorAll<HTMLElement>("button:not([disabled]), input:not([disabled]):not(.hidden)") ?? [])];
    focusable()[0]?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { close(); return; }
      if (e.key !== "Tab") return;
      const items = focusable();
      if (!items.length) return;
      const first = items[0], last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
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
    const brief = [...files].find((f) => f.name.toLowerCase().endsWith(".json"));
    if (csvs[0]) await put("platform", csvs[0]);
    if (csvs[1]) await put("target", csvs[1]);
    if (brief) await put("brief", brief);
  }

  function swap() {
    created.current = null;
    setPicked((p) => ({ ...p, platform: p.target, target: p.platform }));
  }

  const current: Record<Slot, { name: string; sub: string }> = {
    platform: { name: `${deal.platform} statements`, sub: plural(source_lines.filter((l) => l.company === deal.platform).length, "line") },
    target: { name: `${deal.target} statements`, sub: plural(source_lines.filter((l) => l.company === deal.target).length, "line") },
    brief: { name: `${deal.brief.lender.split(",")[0]} agreement`, sub: `Limit ${fmtX(deal.brief.limit)}` },
  };

  async function begin() {
    setBusy(true); setNote(null);
    try {
      const chosen = Object.keys(picked).length;
      if (chosen && chosen < 3) throw new Error("Choose the platform CSV, the target CSV, and the brief, or close to keep this deal.");
      if (chosen && !created.current) {
        const p = picked.platform!.file, t = picked.target!.file;
        const form = new FormData();
        form.set("platform", companyOf(p));
        form.set("target", companyOf(t));
        form.set("name", `${companyOf(p)} acquires ${companyOf(t)}`);
        form.set("brief", await picked.brief!.file.text());
        form.set("platform_csv", p);
        form.set("target_csv", t);
        created.current = (await api.createDeal(form)).deal_id;
        await select(created.current);  // the new deal is current even if the start below fails
      }
      if (created.current) {
        await api.start(created.current);
      } else if (canStart(kase!.stage)) {
        await api.start(deal.id);
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
    <div className="no-drag fixed inset-0 z-20 flex items-center justify-center bg-[rgba(15,41,33,0.45)] p-4 pt-[34px]">
      {/* The backdrop closes on click but is not a tab stop; Close and Esc do the same from the keyboard. */}
      <div aria-hidden="true" className="absolute inset-0" onClick={close} />
      <div ref={dialog} role="dialog" aria-modal="true" aria-labelledby="new-deal-title" className="relative flex w-full max-w-[880px] flex-col gap-[18px] rounded-[20px] bg-white p-[28px] shadow-[0px_24px_60px_0px_rgba(15,41,33,0.3)]">
        <div className="flex w-full items-center gap-[12px]">
          <h2 id="new-deal-title" className="font-serif text-[30px] text-forest">New deal</h2>
          <span className="flex-1" />
          <button className="text-[14px] font-semibold text-slate hover:text-forest disabled:opacity-40" onClick={close} disabled={busy}>Close</button>
        </div>

        <div className="flex w-full justify-center">
          <button
            className="inline-flex items-center gap-[8px] rounded-chip border border-mint-edge bg-white px-[12px] py-[8px] text-[13px] font-semibold text-clear hover:bg-mint-select"
            onClick={() => many.current?.click()}
            disabled={busy}
          >
            <UploadIcon />
            Upload files
          </button>
          <input ref={many} type="file" multiple accept=".csv,.json" className="hidden" onChange={(e) => { putMany(e.target.files); e.target.value = ""; }} />
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
            className="relative inline-flex min-h-11 items-center justify-center rounded-full bg-forest px-[44px] py-[14px] font-ui text-[18px] leading-[28px] font-semibold text-paper drop-shadow-[0px_8px_12px_rgba(30,107,82,0.35)] transition-colors duration-150 hover:bg-clear disabled:opacity-40"
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
