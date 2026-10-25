"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AgentHouse, usePrefersReducedMotion, type AgentHouseHandle } from "@/components/agent-house/agent-house";
import { CONTROLLER, fromAudit, mergeConversation, verbOfEvent, type ConversationEvent } from "@/components/agent-house/conversation";
import { useConversationPlayer, useLiveConversation } from "@/components/agent-house/use-conversation";
import { LockIcon, SilhouetteIcon } from "@/components/icons";
import { ActorChip, Avatar, Label, Mono, PageHeader, ROLES, actorOf } from "@/components/ui";
import { useDeal } from "@/lib/deal-context";
import { clock } from "@/lib/format";

/** The name's color on the timeline: the agent's own, the controller in ink, the gateway in agent blue. */
function nameTone(actor: string): string {
  const a = actorOf(actor);
  return a.role ? ROLES[a.role].name : a.kind === "Human" ? "text-ink" : "text-agent";
}

/** The verb's color, as in the frame: what waits on you in amber, policy in agent blue, a refusal in red, else teal. */
function verbTone(verb: string): string {
  if (verb === "DENIED" || verb === "REJECTED") return "text-denied";
  if (verb === "ASKED") return "text-escalation";
  if (verb === "POLICY") return "text-agent";
  return "text-forest";
}

/** The 22 px tile on the timeline: the agent's character, the controller in ink, the gateway with a lock. */
function Tile({ actor }: { actor: string }) {
  const a = actorOf(actor);
  if (a.kind === "Human") return <span className="flex size-[22px] shrink-0 items-center justify-center rounded-[6px] border-2 border-ink bg-ink"><SilhouetteIcon size={16} /></span>;
  if (a.kind === "Gateway") return <span className="flex size-[22px] shrink-0 items-center justify-center rounded-[6px] border-2 border-ink bg-white"><LockIcon size={16} /></span>;
  if (a.role) return <Avatar role={a.role} size={22} className="rounded-[6px]" />;
  return <span className="size-[22px] shrink-0 rounded-[6px] bg-agent-tint" />;
}

/** Who a line is for, in the timeline's words: "to Preparer", "to you". */
function toWords(e: ConversationEvent): string | null {
  if (e.to === CONTROLLER) return e.from === CONTROLLER ? null : "to you";
  if (!e.to.startsWith("agent:") || e.to === e.from) return null;
  return `to ${actorOf(e.to).label}`;
}

/**
 * V3-6: the agents at work, live. The Agent House (three.js, the agents modelled and animated in Blender) plays the
 * deal's conversation as it happens: who is working, who hands off to whom, and who is asking you. Below it, each
 * actor's latest line; on the right, the whole conversation, newest last, with your answers in it. Every line comes
 * from the gateway: its `conversation` events when it sends them, else the audit log. `?demo=1` runs the prototype's
 * canned loop instead, for the pitch preview.
 */
export default function Agents() {
  const { audit, kase } = useDeal();
  const house = useRef<AgentHouseHandle>(null);
  const reduced = usePrefersReducedMotion();
  const [demo, setDemo] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setDemo(new URLSearchParams(window.location.search).get("demo") === "1"), 0);
    return () => clearTimeout(t);
  }, []);

  const dealId = kase?.deal.id;
  const items = useMemo(() => kase?.work_items ?? [], [kase]);
  const derived = useMemo(() => fromAudit(audit.rows, items), [audit.rows, items]);
  const live = useLiveConversation(dealId);
  const events = useMemo(() => mergeConversation(derived, live.events, live.supported), [derived, live.events, live.supported]);
  const player = useConversationPlayer({ events, stage: kase?.stage, loaded: Boolean(kase) && live.ready, dealId, house, reducedMotion: reduced || demo, drive: !demo });
  const shown = player.shown;

  // The room: each actor's latest line, in time order, as in the frame.
  const latest = new Map<string, ConversationEvent>();
  for (const e of shown) latest.set(e.from, e);
  const chat = [...latest.values()].sort((a, b) => shown.indexOf(a) - shown.indexOf(b)).slice(-5);

  const feed = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = feed.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: reduced ? "auto" : "smooth" });
  }, [shown.length, reduced]);

  if (!kase) return null;
  const pending = kase.verdict?.approval_state === "PROPOSED";
  const briefPending = kase.stage === "awaiting_brief" || kase.stage === "brief_ready";
  const mapperRan = items.some((w) => w.type === "map_lines" && w.state !== "NEW");
  const mapperTurns = mapperRan ? (kase.sessions as { role?: string; turns?: number }[]).find((x) => x.role === "mapper")?.turns ?? 0 : 0;

  return (
    <div className="flex h-full min-h-[640px] w-full flex-col gap-[16px] px-[28px] py-[24px]">
      <PageHeader title="Agents" />

      <div className="relative flex min-h-0 w-full flex-1 gap-[16px] overflow-hidden rounded-card">
        <div className="relative flex min-w-0 flex-1 flex-col gap-[16px]">
          <AgentHouse ref={house} demo={demo} onReplay={demo || !events.length ? undefined : player.replay} onReady={player.resync}
            className="min-h-[300px] w-full flex-1 rounded-[12px]" />

          <div className="flex h-[230px] w-full shrink-0 flex-col gap-[8px] overflow-hidden p-[16px]" aria-live="polite">
            {chat.map((e) => {
              const verb = verbOfEvent(e);
              return (
                <div key={e.id} className="flex w-full items-center gap-[10px]">
                  <span className={`flex w-[120px] shrink-0 items-start ${e.from.startsWith("system") ? "" : "h-[30px]"}`}><ActorChip actor={e.from} /></span>
                  <span className="min-w-0 flex-1 truncate text-[14px] text-body" title={e.text}>{e.text}</span>
                  <span className={`shrink-0 text-[12px] font-semibold ${verbTone(verb)}`}>{verb}</span>
                </div>
              );
            })}
            {!chat.length ? <p className="text-[14px] text-slate">The agents have not started. Run the deal from the Case.</p> : null}
          </div>
        </div>

        <div className="relative flex h-full w-[300px] shrink-0 flex-col p-[18px] pr-0">
          <div className="flex w-full shrink-0 items-center pr-[18px] text-slate">
            <Label className="flex-1">Agent timeline</Label>
            {mapperTurns ? <Mono>Mapper turn {mapperTurns}</Mono> : null}
          </div>
          <span className="h-[14px] shrink-0" />
          {/* The title stays put; the conversation scrolls under it, newest last. */}
          <div ref={feed} className="flex min-h-0 flex-1 flex-col overflow-y-auto pr-[18px]">
            {shown.map((e, i) => {
              const a = actorOf(e.from);
              const last = i === shown.length - 1 && !pending && !briefPending;
              const to = toWords(e);
              return (
                <div key={e.id} className="flex w-full gap-[12px]">
                  <div className="flex w-[22px] shrink-0 flex-col items-center self-stretch">
                    <Tile actor={e.from} />
                    {last ? null : <span className="w-[2px] flex-1 bg-line" />}
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col gap-[2px] pb-[14px]">
                    <div className="flex w-full gap-[8px]">
                      <span className={`truncate text-[13px] font-semibold ${nameTone(e.from)}`}>
                        {a.label}{to ? <span className="font-normal text-faint"> {to}</span> : null}
                      </span>
                      <span className="flex-1" />
                      <span className="shrink-0 font-mono text-[11px] text-slate">{clock(e.at)}</span>
                    </div>
                    <p className={`line-clamp-2 text-[13px] ${e.kind === "refusal" ? "text-denied" : e.kind === "question" ? "text-escalation" : "text-body"}`} title={e.text}>{e.text}</p>
                  </div>
                </div>
              );
            })}
            {pending || briefPending ? (
              <div className="flex w-full gap-[12px]">
                <div className="flex w-[22px] shrink-0 flex-col items-center"><Tile actor={CONTROLLER} /></div>
                <div className="flex min-w-0 flex-1 flex-col gap-[2px] pb-[14px]">
                  <div className="flex w-full gap-[8px]">
                    <span className="text-[13px] font-semibold text-slate">Controller</span>
                    <span className="flex-1" />
                    <span className="font-mono text-[11px] text-slate">-</span>
                  </div>
                  <p className="text-[13px] text-body">{briefPending ? "Check and approve the Brief" : "Approve and post"}</p>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
