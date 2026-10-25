"use client";

import { clock, describe, verbOf } from "@/lib/format";
import type { AuditRow, WorkItem } from "@/lib/types";
import { ActorChip } from "./ui";

/** The verb's color: what waits on you in amber, policy in agent blue, a pass in green, a refusal in red. */
export function verbTone(verb: string): string {
  if (verb === "DENIED" || verb === "REJECTED") return "text-denied";
  if (verb === "ASKED" || verb === "HELD") return "text-escalation";
  if (verb === "POLICY") return "text-agent";
  if (verb === "PASS" || verb === "POSTED") return "text-clear";
  return "text-code";
}

/** The run column, as in the frame: the tool run id when the row is one, the record's hash on the POSTED row,
 * else "-". Every row's own hash is in the tooltip. */
function runOf(row: AuditRow, verb: string): string {
  if (row.target?.startsWith("run_")) return row.target;
  return verb === "POSTED" ? row.hash.slice(0, 6) : "-";
}

export const LOG_COLS = { time: "w-[80px]", actor: "w-[130px]", verb: "w-[100px]", run: "w-[150px]" };

export function AuditRowView({ row, items, fresh = false }: { row: AuditRow; items: WorkItem[]; fresh?: boolean }) {
  const denied = row.result === "DENIED";
  const verb = verbOf(row, items);
  const text = describe(row, items);
  return (
    <div className={`flex w-full items-center gap-[12px] border-b border-line px-[20px] py-[12px] last:border-b-0 ${denied ? "bg-denied-tint" : ""} ${fresh ? "row-new" : ""}`}>
      <span className={`${LOG_COLS.time} shrink-0 font-mono text-[12px] text-code`}>{clock(row.at)}</span>
      {/* As in the frame: chips sit at the top of a 30 px slot; the bordered gateway chip sets its own height. */}
      <span className={`${LOG_COLS.actor} flex shrink-0 items-start ${row.actor.startsWith("system") ? "" : "h-[30px]"}`}><ActorChip actor={row.actor} /></span>
      <span className={`${LOG_COLS.verb} shrink-0 text-[13px] font-semibold ${verbTone(verb)}`}>{verb}</span>
      <span className={`min-w-0 flex-1 truncate text-[14px] ${denied ? "text-denied" : "text-body"}`} title={text}>{text}</span>
      <span className={`${LOG_COLS.run} shrink-0 truncate font-mono text-[12px] text-slate`} title={`${row.target ?? ""} ${row.hash}`}>{runOf(row, verb)}</span>
    </div>
  );
}
