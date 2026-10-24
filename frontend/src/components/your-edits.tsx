"use client";

import { useState } from "react";
import { finalFiles } from "@/lib/api";
import { useEdits } from "@/lib/edit-context";
import { num } from "@/lib/edits";
import type { Deal, Edit } from "@/lib/types";
import { Button, Label, Mono, Shape } from "./ui";

/** Old and new, in the edit's own terms: amounts in USD thousands, or the platform lines of a remap. */
function change(e: Edit): string {
  return e.kind === "amount"
    ? `${num(e.old_value ?? 0)} → ${num(e.new_value ?? 0)}`
    : `${e.old_platform_line ?? "Unmapped"} → ${e.new_platform_line}`;
}

/**
 * Your edits (review-companion.md section 7), under the verdict and styled like Answered. One row per live edit:
 * a check or a waiting dot, the line, old and new, the reason, and the policy or adjustment it made.
 * Clicking a row scrolls to the cell and flashes it; Undo reverts the edit and the agents' value comes back.
 */
export function YourEdits({ locked }: { locked: boolean }) {
  const ctx = useEdits();
  const [undoing, setUndoing] = useState<string | null>(null);
  if (!ctx.edits.length) return null;
  return (
    <section className="flex flex-col gap-[8px]" aria-label="Your edits">
      <Label>Your edits ({ctx.edits.length})</Label>
      {ctx.edits.map((e) => {
        const needs = e.status === "needs_reason";
        const learned = e.policy_id ?? e.adjustment_id;
        return (
          <div
            key={e.id}
            className={`group flex items-center gap-[12px] rounded-[12px] border bg-white px-[16px] py-[10px] transition-colors duration-150 hover:bg-fog/60 ${needs ? "border-amber-line" : "border-line"}`}
          >
            <button
              type="button"
              onClick={() => ctx.show(e.id)}
              className="flex min-w-0 flex-1 items-center gap-[12px] text-left"
              aria-label={`${e.company}, ${e.line}: ${change(e)}. ${needs ? "Needs a reason." : `Reason: ${e.reason_text}.`} Show the cell.`}
            >
              {needs ? (
                <span className="flex size-[12px] shrink-0 items-center justify-center" title="Needs a reason">
                  <span className="size-[9px] rounded-full bg-escalation-bar" />
                </span>
              ) : (
                <span className="text-clear"><Shape kind="check" size={12} /></span>
              )}
              <span className="max-w-[34%] min-w-0 shrink truncate text-[14px] text-body" title={`${e.company}, ${e.line}`}>
                <span className="text-slate">{e.company} &middot; </span>{e.line}
              </span>
              <span className="shrink-0 font-mono text-[12px] whitespace-nowrap text-forest">{change(e)}</span>
              <span className={`min-w-0 flex-1 truncate text-[14px] ${needs ? "text-escalation" : "text-slate"}`} title={e.reason_text ?? "Needs a reason before you can approve"}>
                {e.reason_text ?? "Needs a reason"}
              </span>
            </button>
            {learned ? <Mono className="shrink-0">{learned}</Mono> : null}
            {needs && !locked ? (
              <Button kind="link" className="shrink-0 text-[13px] text-escalation" onClick={() => ctx.ask(e.id)}>Give a reason</Button>
            ) : null}
            {!locked ? (
              <Button
                kind="link"
                className="shrink-0 text-[13px]"
                disabled={undoing === e.id}
                onClick={async () => { setUndoing(e.id); await ctx.revert(e.id); setUndoing(null); }}
              >
                {undoing === e.id ? "Undoing" : "Undo"}
              </Button>
            ) : null}
          </div>
        );
      })}
    </section>
  );
}

declare global {
  interface Window {
    /** Eric's Electron preload (E1): writes the files through the macOS save dialog. */
    stochastic?: { saveFiles?: (files: { url: string; name: string }[]) => Promise<unknown> };
  }
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

/** After approval: the workbook and the draft certificate, with every edit and reason in them (section 8). */
export function DownloadFinal({ deal }: { deal: Deal }) {
  const [state, setState] = useState<{ busy: boolean; text: string | null; bad: boolean }>({ busy: false, text: null, bad: false });
  const go = async () => {
    const files = finalFiles(deal);
    setState({ busy: true, text: null, bad: false });
    try {
      if (window.stochastic?.saveFiles) {
        await window.stochastic.saveFiles(files);
        setState({ busy: false, text: "Saved.", bad: false });
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
  return (
    <span className="flex items-center gap-[10px]">
      {state.text ? <span role="status" className={`text-[13px] ${state.bad ? "text-escalation" : "text-slate"}`}>{state.text}</span> : null}
      <Button kind="primary" disabled={state.busy} onClick={go}>{state.busy ? "Saving files" : "Download final files"}</Button>
    </span>
  );
}
