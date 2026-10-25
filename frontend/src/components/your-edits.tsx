"use client";

import { useState } from "react";
import { finalFiles } from "@/lib/api";
import { useEdits } from "@/lib/edit-context";
import { num } from "@/lib/edits";
import type { Deal, Edit } from "@/lib/types";
import { Shape } from "./ui";

/** Old and new, in the edit's own terms: amounts in USD thousands, or the platform lines of a remap. */
export function change(e: Edit): string {
  return e.kind === "amount"
    ? `${num(e.old_value ?? 0)} → ${num(e.new_value ?? 0)}`
    : `${e.old_platform_line ?? "Unmapped"} → ${e.new_platform_line}`;
}

/** The arrow between old and new. The mono face's arrow is a long one, so it is set in the sans, as on the frames. */
export function Arrow() {
  return <span className="font-sans">&rarr;</span>;
}

/** Old and new for the screen, with the short arrow. */
export function Change({ e }: { e: Edit }) {
  return e.kind === "amount"
    ? <>{num(e.old_value ?? 0)} <Arrow /> {num(e.new_value ?? 0)}</>
    : <>{e.old_platform_line ?? "Unmapped"} <Arrow /> {e.new_platform_line}</>;
}

const LINK = "shrink-0 text-[14px] font-semibold whitespace-nowrap text-forest underline-offset-4 hover:underline disabled:opacity-40";

/**
 * Your edits on the Review page (V3-7): a strip under the verdict, one 36 px row per live edit. A waiting dot or a
 * check, the line and company, old and new, the reason or "Needs a reason", and the policy or adjustment it made.
 * Clicking the line scrolls to the cell and flashes it; Give a reason reopens the bubble; Undo brings the agents'
 * value back. With no edits it says how to make one.
 */
export function EditsStrip({ locked, editable }: { locked: boolean; editable: boolean }) {
  const ctx = useEdits();
  const [undoing, setUndoing] = useState<string | null>(null);
  const label = "shrink-0 text-[11px] font-semibold tracking-[0.88px] whitespace-nowrap text-sheet-muted uppercase";
  if (!ctx.edits.length) {
    return (
      <div className="flex h-[36px] w-full shrink-0 items-center gap-[12px] border-t border-sheet-line bg-white px-[16px]">
        <span className={label}>Your edits</span>
        <span className="truncate text-[14px] text-sheet-muted">
          {editable ? "None yet. Click a platform or target amount to change it." : "None."}
        </span>
      </div>
    );
  }
  const asking = ctx.asking?.id;
  return (
    <section aria-label="Your edits" className="flex max-h-[108px] w-full shrink-0 flex-col overflow-y-auto border-t border-sheet-line bg-white">
      {ctx.edits.map((e, i) => {
        const needs = e.status === "needs_reason";
        const learned = e.policy_id ?? e.adjustment_id;
        return (
          <div key={e.id} className="flex h-[36px] w-full shrink-0 items-center gap-[12px] px-[16px]">
            <span className={`${label} ${i ? "invisible" : ""}`}>Your edits ({ctx.edits.length})</span>
            <button
              type="button"
              onClick={() => ctx.show(e.id)}
              className="flex min-w-0 items-center gap-[12px] text-left"
              aria-label={`${e.line}, ${e.company}: ${change(e)}. ${needs ? "Needs a reason." : `Reason: ${e.reason_text}.`} Show the cell.`}
            >
              {needs ? (
                <span className="size-[8px] shrink-0 rounded-full bg-edit-bar" title="Needs a reason" />
              ) : (
                <span className="shrink-0 text-forest"><Shape kind="check" size={12} /></span>
              )}
              <span className="truncate text-[14px] text-ink hover:underline">{e.line} &middot; {e.company}</span>
              <span className="shrink-0 font-mono text-[13px] whitespace-nowrap text-ink"><Change e={e} /></span>
              {needs ? (
                <span className="shrink-0 text-[14px] font-medium whitespace-nowrap text-escalation">Needs a reason</span>
              ) : (
                <span className="min-w-0 truncate text-[14px] text-sheet-muted" title={e.reason_text ?? ""}>{e.reason_text}</span>
              )}
              {learned ? <span className="shrink-0 font-mono text-[12px] text-sheet-muted">{learned}</span> : null}
            </button>
            <span className="min-w-0 flex-1" />
            {needs && !locked && asking !== e.id ? (
              <button type="button" className={LINK} onClick={() => ctx.ask(e.id)}>Give a reason</button>
            ) : null}
            {!locked ? (
              <button
                type="button"
                className={LINK}
                disabled={undoing === e.id}
                onClick={async () => { setUndoing(e.id); await ctx.revert(e.id); setUndoing(null); }}
              >
                {undoing === e.id ? "Undoing" : "Undo"}
              </button>
            ) : null}
          </div>
        );
      })}
    </section>
  );
}

/** Fetch each file and hand it to the browser under its own name. A cross-origin link would ignore `download`. */
async function browserDownload(files: { url: string; name: string }[]): Promise<string[]> {
  const missing: string[] = [];
  for (const f of files) {
    const res = await fetch(f.url, { cache: "no-store" }).catch(() => null);
    if (!res?.ok) { missing.push(f.name); continue; }
    const href = URL.createObjectURL(await res.blob());
    const a = document.createElement("a");
    a.href = href; a.download = f.name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(href), 10_000);
  }
  return missing;
}

/** After approval: the workbook and the draft certificate, with every edit and reason in them (section 8).
 * In the Mac app the files go through a save dialog (window.stochastic.saveFiles); in a browser they download. */
export function useDownloadFinal(deal: Deal | null) {
  const [state, setState] = useState<{ busy: boolean; text: string | null; bad: boolean }>({ busy: false, text: null, bad: false });
  const go = async () => {
    if (!deal) return;
    const files = finalFiles(deal);
    setState({ busy: true, text: null, bad: false });
    try {
      if (window.stochastic?.saveFiles) {
        const saved = await window.stochastic.saveFiles(files);
        // Closing the folder dialog saves nothing, so nothing is said.
        setState({ busy: false, text: saved?.canceled ? null : "Saved.", bad: false });
        return;
      }
      const missing = await browserDownload(files);
      setState({
        busy: false,
        bad: missing.length > 0,
        text: !missing.length ? "Downloaded 2 files." : missing.length === files.length ? "The files are not ready yet." : `Not ready yet: ${missing.join(", ")}.`,
      });
    } catch (e) {
      setState({ busy: false, text: e instanceof Error ? e.message : "The files were not saved.", bad: true });
    }
  };
  return { ...state, go };
}
