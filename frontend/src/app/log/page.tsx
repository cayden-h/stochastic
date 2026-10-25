"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { AuditRowView, LOG_COLS } from "@/components/audit-log";
import { Conversation } from "@/components/process-flow";
import { Page } from "@/components/shell";
import { Button, Card, Label, PageHeader, Shape } from "@/components/ui";
import { useDeal } from "@/lib/deal-context";
import { clock, plural } from "@/lib/format";

type View = "audit" | "conversation";

/** V3-5, the log: prove what happened. Read only. The audit rows with one toggle and one Verify button, or the
 * conversation the agents, the gateway, and the controller had. Both update live. All times are PT. */
function Log() {
  const { audit, kase, refresh, messages, received, running } = useDeal();
  const router = useRouter();
  const view: View = useSearchParams().get("view") === "conversation" ? "conversation" : "audit";
  const [deniedOnly, setDeniedOnly] = useState(false);
  const [verified, setVerified] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  // The rows on screen when the page opened; every later row is new and gets a short highlight.
  const [seen] = useState(() => new Set(audit.rows.map((r) => r.id)));

  /** Re-reads the chain. "Verified" is stamped only when the read came back; a failed read clears it. */
  async function verify() {
    setChecking(true);
    try {
      const ok = await refresh();
      setVerified(ok ? clock(new Date().toISOString()) : null);
    } finally {
      setChecking(false);
    }
  }

  const items = kase?.work_items ?? [];
  const rows = deniedOnly ? audit.rows.filter((r) => r.result === "DENIED") : audit.rows;
  const deniedCount = audit.rows.filter((r) => r.result === "DENIED").length;
  const head = audit.rows[audit.rows.length - 1]?.hash.slice(0, 6) ?? "-";
  const views: { key: View; label: string }[] = [
    { key: "audit", label: `Audit rows (${audit.rows.length})` },
    { key: "conversation", label: `Conversation (${messages.length})` },
  ];

  return (
    <Page>
      <PageHeader title="Log">
        <span
          className={`flex items-center gap-[6px] text-[13px] font-semibold whitespace-nowrap ${audit.chain_valid ? "text-clear" : "text-denied"}`}
          title="Each row carries the hash of the row before it."
        >
          <Shape kind={audit.chain_valid ? "check" : "cross"} size={12} />
          {audit.chain_valid ? `Chain intact. ${plural(audit.rows.length, "row")}, head ${head}.` : "Chain broken. A past row changed."}
          {verified ? <span className="font-mono text-[12px] font-normal text-slate">Verified {verified} PT</span> : null}
        </span>
        {view === "audit" ? (
          <button
            aria-pressed={deniedOnly}
            onClick={() => setDeniedOnly((v) => !v)}
            className={`rounded-full border px-[12px] py-[6px] text-[13px] font-semibold whitespace-nowrap transition-colors duration-150 ${
              deniedOnly ? "border-denied bg-denied text-white" : "border-line bg-white text-body hover:bg-denied-tint"
            }`}
          >
            Denied only ({deniedCount})
          </button>
        ) : null}
        <Button disabled={checking} onClick={verify}>{checking ? "Verifying" : "Verify"}</Button>
      </PageHeader>

      <div className="flex items-center gap-[8px]" role="group" aria-label="What the log shows">
        {views.map((v) => {
          const on = v.key === view;
          return (
            <button
              key={v.key}
              aria-pressed={on}
              onClick={() => router.replace(v.key === "audit" ? "/log" : "/log?view=conversation", { scroll: false })}
              className={`rounded-full border px-[12px] py-[6px] text-[13px] font-semibold transition-colors duration-150 ${
                on ? "border-forest bg-forest text-white" : "border-line bg-white text-body hover:bg-mint-select"
              }`}
            >
              {v.label}
            </button>
          );
        })}
      </div>

      {view === "conversation" ? (
        <Conversation messages={messages} received={received} live={running} />
      ) : (
        <Card className="flex w-full flex-col">
          <div className="flex w-full gap-[12px] border-b border-line px-[20px] py-[12px]">
            <Label className={`${LOG_COLS.time} shrink-0`}>Time</Label>
            <Label className={`${LOG_COLS.actor} shrink-0`}>Agents</Label>
            <Label className={`${LOG_COLS.verb} shrink-0`}>Verb</Label>
            <Label className="min-w-0 flex-1">Detail</Label>
            <Label className={`${LOG_COLS.run} shrink-0`}>Run</Label>
          </div>
          {rows.map((r) => <AuditRowView key={`${r.id}-${r.hash}`} row={r} items={items} fresh={!seen.has(r.id)} />)}
          {!rows.length ? <p className="px-[20px] py-[14px] text-[14px] text-slate">{deniedOnly ? "No actions were denied." : "No rows yet."}</p> : null}
        </Card>
      )}
    </Page>
  );
}

export default function LogPage() {
  return <Suspense><Log /></Suspense>;
}
