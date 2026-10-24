"use client";

import { useState } from "react";
import { AuditRowView, LOG_COLS } from "@/components/audit-log";
import { Page } from "@/components/shell";
import { Button, Card, Label, PageHeader, Shape } from "@/components/ui";
import { useDeal } from "@/lib/deal-context";
import { clock, plural } from "@/lib/format";

/** V3-5, the log: prove what happened. Read only, one toggle, one Verify button. All times are PT. */
export default function Log() {
  const { audit, kase, refresh } = useDeal();
  const [deniedOnly, setDeniedOnly] = useState(false);
  const [verified, setVerified] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

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
        <button
          aria-pressed={deniedOnly}
          onClick={() => setDeniedOnly((v) => !v)}
          className={`rounded-full border px-[12px] py-[6px] text-[13px] font-semibold whitespace-nowrap transition-colors duration-150 ${
            deniedOnly ? "border-denied bg-denied text-white" : "border-line bg-white text-body hover:bg-denied-tint"
          }`}
        >
          Denied only ({deniedCount})
        </button>
        <Button disabled={checking} onClick={verify}>{checking ? "Verifying" : "Verify"}</Button>
      </PageHeader>

      <Card className="flex w-full flex-col">
        <div className="flex w-full gap-[12px] border-b border-line px-[20px] py-[12px]">
          <Label className={`${LOG_COLS.time} shrink-0`}>Time</Label>
          <Label className={`${LOG_COLS.actor} shrink-0`}>Agents</Label>
          <Label className={`${LOG_COLS.verb} shrink-0`}>Verb</Label>
          <Label className="min-w-0 flex-1">Detail</Label>
          <Label className={`${LOG_COLS.run} shrink-0`}>Run</Label>
        </div>
        {rows.map((r) => <AuditRowView key={r.id} row={r} items={items} />)}
        {!rows.length ? <p className="px-[20px] py-[14px] text-[14px] text-slate">{deniedOnly ? "No actions were denied." : "No rows yet."}</p> : null}
      </Card>
    </Page>
  );
}
