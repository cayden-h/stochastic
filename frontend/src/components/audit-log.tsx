"use client";

import { clock, describe, verbOf } from "@/lib/format";
import type { AuditRow, Plan, WorkItem } from "@/lib/types";
import { ActorChip } from "./ui";

export function AuditRowView({ row, items, plans }: { row: AuditRow; items: WorkItem[]; plans: Plan[] }) {
  const denied = row.result === "DENIED";
  return (
    <div
      className={`grid grid-cols-[88px_172px_104px_1fr_160px] items-center gap-4 px-4 py-2 ${
        denied ? "border-l-4 border-denied bg-denied-tint pl-3" : "bg-card"
      }`}
    >
      <span className="font-mono text-[14px] leading-5 text-muted">{clock(row.at)}</span>
      <span><ActorChip actor={row.actor} /></span>
      <span className={`text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] ${denied ? "text-denied" : ""}`}>
        {verbOf(row)}
      </span>
      <span>{describe(row, items, plans)}</span>
      <span className="text-right font-mono text-[14px] leading-5 text-muted">
        {row.target ?? ""} {row.hash.slice(0, 6)}
      </span>
    </div>
  );
}
