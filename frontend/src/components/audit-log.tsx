"use client";

import { clock, describe, verbOf } from "@/lib/format";
import type { AuditRow, WorkItem } from "@/lib/types";
import { ActorChip, Mono } from "./ui";

export function AuditRowView({ row, items }: { row: AuditRow; items: WorkItem[] }) {
  const denied = row.result === "DENIED";
  return (
    <div
      className={`grid grid-cols-[88px_148px_104px_1fr_200px] items-center gap-4 px-4 py-2 ${
        denied ? "border-l-4 border-denied bg-denied-tint pl-3" : "bg-card"
      }`}
    >
      <Mono>{clock(row.at)}</Mono>
      <span><ActorChip actor={row.actor} /></span>
      <span className={`text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] ${denied ? "text-denied" : ""}`}>
        {verbOf(row)}
      </span>
      <span className="truncate" title={describe(row, items)}>{describe(row, items)}</span>
      <Mono className="text-right">{row.target ?? ""} {row.hash.slice(0, 6)}</Mono>
    </div>
  );
}
