"use client";

import Image from "next/image";
import { verbTone } from "@/components/audit-log";
import { LockIcon, SilhouetteIcon } from "@/components/icons";
import { ActorChip, Avatar, Label, Mono, PageHeader, ROLES, actorOf } from "@/components/ui";
import { useDeal } from "@/lib/deal-context";
import { clock, describe, verbOf } from "@/lib/format";
import type { AuditRow } from "@/lib/types";

/** The rows that tell the agents' story: asks, answers, proposals, policies, reviews, approvals, refusals.
 * Tool runs, session turns, and item bookkeeping stay in the Log. */
function storyRows(rows: AuditRow[]): AuditRow[] {
  return rows.filter((r) => {
    if (r.result === "DENIED") return true;
    const verb = r.action.split(":")[0];
    return ["propose", "ask", "answer", "policy", "approve", "reject", "hold", "post", "reverse"].includes(verb);
  });
}

/** The name's color on the timeline: the agent's own, the controller in ink, the gateway in agent blue. */
function nameTone(actor: string): string {
  const a = actorOf(actor);
  return a.role ? ROLES[a.role].name : a.kind === "Human" ? "text-ink" : "text-agent";
}

/** The 22 px tile on the timeline: the agent's avatar, the controller in ink, the gateway with a lock. */
function Tile({ actor }: { actor: string }) {
  const a = actorOf(actor);
  if (a.kind === "Human") return <span className="flex size-[22px] items-center justify-center rounded-[6px] border-2 border-ink bg-ink"><SilhouetteIcon size={16} /></span>;
  if (a.kind === "Gateway") return <span className="flex size-[22px] items-center justify-center rounded-[6px] border-2 border-ink bg-white"><LockIcon size={16} /></span>;
  if (a.role) return <Avatar role={a.role} size={22} className="rounded-[6px]" />;
  return <span className="size-[22px] rounded-[6px] bg-agent-tint" />;
}

/**
 * V3-6: the three agents at work. The office is a still of Josie's three.js scene; the conversation and the
 * timeline over it come from the audit log, so every line is a recorded action.
 */
export default function Agents() {
  const { audit, kase } = useDeal();
  if (!kase) return null;
  const items = kase.work_items;
  const story = storyRows(audit.rows);
  // The conversation: each actor's latest line, in time order, so the room reads as one exchange.
  const latest = new Map<string, AuditRow>();
  for (const r of story) latest.set(r.actor, r);
  const chat = [...latest.values()].sort((a, b) => a.id - b.id).slice(-5);
  const timeline = story.slice(-12);
  // Runs of this deal on the record: each run opens a new mapping item.
  const runs = audit.rows.filter((r) => r.action === "create:map_lines").length;
  const pending = kase.verdict?.approval_state === "PROPOSED";

  return (
    <div className="flex h-full min-h-[640px] w-full flex-col gap-[16px] px-[28px] py-[24px]">
      <PageHeader title="Agents" />

      <div className="relative flex min-h-0 w-full flex-1 gap-[16px] overflow-hidden rounded-card bg-white">
        <Image src="/v3/agent-house.png" alt="The agents' office: the Mapper, the Preparer, and the Reviewer at their desks." fill priority sizes="1144px" className="object-cover object-left-top" />

        <div className="relative flex min-w-0 flex-1 flex-col justify-end">
          <div className="flex h-[230px] w-full flex-col gap-[8px] overflow-hidden p-[16px]">
            {chat.map((r) => {
              const verb = verbOf(r, items);
              const text = describe(r, items);
              return (
                <div key={r.id} className="flex w-full items-center gap-[10px]">
                  <span className="flex h-[30px] w-[120px] shrink-0 items-start"><ActorChip actor={r.actor} /></span>
                  <span className="min-w-0 flex-1 truncate text-[14px] text-body" title={text}>{text}</span>
                  <span className={`shrink-0 text-[12px] font-semibold ${verbTone(verb)}`}>{verb}</span>
                </div>
              );
            })}
            {!chat.length ? <p className="text-[14px] text-slate">The agents have not started. Run the deal from the Case.</p> : null}
          </div>
        </div>

        <div className="relative flex h-full w-[300px] shrink-0 flex-col overflow-y-auto p-[18px]">
          <div className="flex w-full items-center text-slate">
            <Label className="flex-1">Agent timeline</Label>
            {runs ? <Mono>run {runs}</Mono> : null}
          </div>
          <span className="h-[14px] shrink-0" />
          {timeline.map((r, i) => {
            const a = actorOf(r.actor);
            const last = i === timeline.length - 1 && !pending;
            const text = describe(r, items);
            return (
              <div key={r.id} className="flex w-full gap-[12px]">
                <div className="flex w-[22px] shrink-0 flex-col items-center self-stretch">
                  <Tile actor={r.actor} />
                  {last ? null : <span className="w-[2px] flex-1 bg-line" />}
                </div>
                <div className="flex min-w-0 flex-1 flex-col gap-[2px] pb-[14px]">
                  <div className="flex w-full gap-[8px]">
                    <span className={`text-[13px] font-semibold ${nameTone(r.actor)}`}>{a.label}</span>
                    <span className="flex-1" />
                    <span className="font-mono text-[11px] text-slate">{clock(r.at)}</span>
                  </div>
                  <p className={`line-clamp-2 text-[13px] ${r.result === "DENIED" ? "text-denied" : "text-body"}`} title={text}>{text}</p>
                </div>
              </div>
            );
          })}
          {pending ? (
            <div className="flex w-full gap-[12px]">
              <div className="flex w-[22px] shrink-0 flex-col items-center"><Tile actor="human:controller" /></div>
              <div className="flex min-w-0 flex-1 flex-col gap-[2px] pb-[14px]">
                <div className="flex w-full gap-[8px]">
                  <span className="text-[13px] font-semibold text-slate">Controller</span>
                  <span className="flex-1" />
                  <span className="font-mono text-[11px] text-slate">-</span>
                </div>
                <p className="text-[13px] text-body">Approve and post</p>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
