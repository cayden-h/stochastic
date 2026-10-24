"use client";

import { useState } from "react";
import { AuditRowView } from "@/components/audit-log";
import { Button, Shape } from "@/components/ui";
import { useDeal } from "@/lib/deal-context";
import { clock, plural } from "@/lib/format";

/** Log: prove what happened. Read only, one toggle, one Verify button. */
export default function Log() {
  const { audit, kase, refresh } = useDeal();
  const [deniedOnly, setDeniedOnly] = useState(false);
  const [verified, setVerified] = useState<string | null>(null);

  const items = kase?.work_items ?? [];
  const rows = deniedOnly ? audit.rows.filter((r) => r.result === "DENIED") : audit.rows;
  const deniedCount = audit.rows.filter((r) => r.result === "DENIED").length;
  const head = audit.rows[audit.rows.length - 1]?.hash.slice(0, 6) ?? "-";

  return (
    <div className="mx-auto flex max-w-[1120px] flex-col gap-4 px-4 pt-6 pb-8">
      <header className="flex flex-col gap-2">
        <h1 className="font-serif text-[40px] leading-[48px] font-medium">Every action is on the record.</h1>
        <p className="text-muted">
          {deniedCount === 0 ? "No actions were denied." : `${deniedCount} ${deniedCount === 1 ? "action was" : "actions were"} denied.`} Each row carries the hash of the row before it. All times are PT.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className={`flex items-center gap-2 font-semibold ${audit.chain_valid ? "text-clear" : "text-denied"}`}>
          <Shape kind={audit.chain_valid ? "check" : "cross"} size={16} />
          {audit.chain_valid ? `Chain intact. ${plural(audit.rows.length, "row")}. Head ${head}.` : "Chain broken. A past row changed."}
          {verified ? <span className="font-mono text-[14px] leading-5 font-normal text-muted">Verified {verified}</span> : null}
        </span>
        <span className="flex-1" />
        <label className="flex items-center gap-2">
          <input type="checkbox" className="size-5 accent-ink" checked={deniedOnly} onChange={(e) => setDeniedOnly(e.target.checked)} />
          Denied only
        </label>
        <Button onClick={async () => { await refresh(); setVerified(clock(new Date().toISOString())); }}>Verify chain</Button>
      </div>

      <div className="flex flex-col gap-px overflow-hidden rounded-card border border-rule bg-hairline">
        {rows.map((r) => <AuditRowView key={r.id} row={r} items={items} />)}
      </div>
    </div>
  );
}
