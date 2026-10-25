"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";
import { type AgentInfo, type AgentKey, type ConversationMessage, CONTROLLER, agentKey } from "@/lib/conversation";
import { clock } from "@/lib/format";
import { SilhouetteIcon } from "./icons";
import { ActorChip, Avatar, Label, Mono, type Role, ROLES, Shape } from "./ui";

/** The agents in pipeline order, with the role key the v3 art uses. */
const PIPELINE: { key: AgentKey; role: Role; name: string; party: string }[] = [
  { key: "brief-reader", role: "brief_reader", name: "Brief Reader", party: "agent:brief_reader" },
  { key: "mapper", role: "mapper", name: "Mapper", party: "agent:mapper" },
  { key: "preparer", role: "preparer", name: "Preparer", party: "agent:preparer" },
  { key: "reviewer", role: "reviewer", name: "Reviewer", party: "agent:reviewer" },
];

export function agentName(party: string): string {
  return PIPELINE.find((p) => p.party === party)?.name ?? (party === CONTROLLER ? "You" : "The gateway");
}

/** A one-second clock while something on screen counts seconds. */
function useSeconds(on: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!on) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [on]);
  return now;
}

/** A small live dot: steady with reduced motion (globals.css turns animations off). */
function LiveDot({ tone }: { tone: string }) {
  return (
    <span className="relative inline-flex size-[8px] shrink-0" aria-hidden="true">
      <span className={`absolute inset-0 animate-ping rounded-full opacity-60 ${tone}`} />
      <span className={`relative inline-flex size-[8px] rounded-full ${tone}`} />
    </span>
  );
}

function StateWord({ info, elapsed, unused }: { info: AgentInfo; elapsed: number | null; unused: boolean }) {
  if (unused) return <span className="text-[12px] text-faint">Not needed</span>;
  switch (info.state) {
    case "working":
      return <span className="flex items-center gap-[6px] text-[12px] font-semibold text-forest"><LiveDot tone="bg-forest" />Working{elapsed !== null ? <span className="font-mono font-normal">{elapsed} s</span> : null}</span>;
    case "talking":
      return <span className="flex items-center gap-[6px] text-[12px] font-semibold text-forest"><LiveDot tone="bg-forest" />Talking</span>;
    case "asking":
      return <span className="flex items-center gap-[6px] text-[12px] font-semibold text-escalation"><Shape kind="triangle" size={10} />Asking you</span>;
    case "done":
      return <span className="flex items-center gap-[6px] text-[12px] font-semibold text-clear"><Shape kind="check" size={10} />Done</span>;
    default:
      return <span className="flex items-center gap-[6px] text-[12px] text-faint"><Shape kind="circle" size={10} />Waiting</span>;
  }
}

/**
 * The process at a glance: Brief Reader, Mapper, Preparer, Reviewer, You. Each agent shows its live state from the
 * conversation; an agent that asked shows the questions it waits on, and You shows whose turn it is.
 */
export function Pipeline({ agents, readerUsed, posted, approvalWaiting }: {
  agents: Record<AgentKey, AgentInfo>; readerUsed: boolean; posted: boolean; approvalWaiting: boolean;
}) {
  const anyWorking = PIPELINE.some((p) => agents[p.key].state === "working");
  const now = useSeconds(anyWorking);
  const askers = PIPELINE.filter((p) => agents[p.key].state === "asking");
  const questions = askers.reduce((n, p) => n + agents[p.key].waitingOn.length, 0);
  const yourTurn = askers.length > 0 || approvalWaiting;
  return (
    <ol className="flex w-full items-stretch" aria-label="The agents' progress" aria-live="polite">
      {PIPELINE.map((p) => {
        const info = agents[p.key];
        const unused = p.key === "brief-reader" && !readerUsed && info.state === "idle";
        const elapsed = info.state === "working" && info.since ? Math.max(0, Math.round((now - Date.parse(info.since)) / 1000)) : null;
        const look = ROLES[p.role];
        const active = info.state === "working" || info.state === "talking";
        const flowed = info.state === "done";
        return (
          <li key={p.key} className="flex min-w-0 flex-1 items-center">
            <div
              className={`flex min-w-0 flex-1 items-center gap-[8px] rounded-[12px] border px-[8px] py-[8px] transition-colors duration-300 ${
                info.state === "asking" ? "border-amber-line bg-amber-tint"
                : active ? `border-mint-edge ${look.tint}`
                : "border-transparent"
              } ${unused ? "opacity-50" : ""}`}
            >
              <Avatar role={p.role} size={26} className={info.state === "idle" && !unused ? "opacity-60" : ""} />
              <span className="flex min-w-0 flex-col gap-[2px]">
                <span className={`truncate text-[14px] font-semibold ${look.name}`}>{p.name}</span>
                <StateWord info={info} elapsed={elapsed} unused={unused} />
                {info.state === "asking" ? (
                  <span className="truncate text-[12px] text-escalation">{info.waitingOn.length === 1 ? "1 question" : `${info.waitingOn.length} questions`}</span>
                ) : null}
              </span>
            </div>
            <span aria-hidden="true" className={`mx-[2px] h-[2px] w-[10px] shrink-0 rounded-full ${flowed ? "bg-forest" : "bg-line"}`} />
          </li>
        );
      })}
      <li className="flex min-w-0 flex-1 items-center">
        <div className={`flex min-w-0 flex-1 items-center gap-[8px] rounded-[12px] border px-[8px] py-[8px] transition-colors duration-300 ${yourTurn ? "border-amber-line bg-amber-tint" : "border-transparent"}`}>
          <span className="flex size-[26px] shrink-0 items-center justify-center rounded-[7px] bg-ink text-paper" aria-hidden="true"><SilhouetteIcon /></span>
          <span className="flex min-w-0 flex-col gap-[2px]">
            <span className="truncate text-[14px] font-semibold text-ink">You</span>
            {posted ? (
              <span className="flex items-center gap-[6px] text-[12px] font-semibold text-clear"><Shape kind="check" size={10} />Approved</span>
            ) : askers.length ? (
              <span className="flex items-center gap-[6px] text-[12px] font-semibold text-escalation"><LiveDot tone="bg-escalation-bar" />Your turn</span>
            ) : approvalWaiting ? (
              <span className="flex items-center gap-[6px] text-[12px] font-semibold text-escalation"><LiveDot tone="bg-escalation-bar" />Approve</span>
            ) : (
              <span className="flex items-center gap-[6px] text-[12px] text-faint"><Shape kind="circle" size={10} />Waiting</span>
            )}
            {askers.length ? (
              <span className="truncate text-[12px] text-escalation">
                {questions} from the {askers.map((a) => a.name).join(" and ")}
              </span>
            ) : null}
          </span>
        </div>
      </li>
    </ol>
  );
}

/** The kind of message as a word on the right, as the Agents timeline frame does it. */
const KIND: Record<string, { word: string; tone: string }> = {
  question: { word: "Asked", tone: "text-escalation" },
  answer: { word: "Answered", tone: "text-ink" },
  handoff: { word: "Handoff", tone: "text-preparer" },
  check: { word: "Check", tone: "text-clear" },
  refusal: { word: "Refused", tone: "text-denied" },
  message: { word: "", tone: "text-slate" },
};

function rowTone(m: ConversationMessage): string {
  if (m.kind === "question") return "bg-amber-tint";
  if (m.kind === "refusal") return "bg-denied-tint";
  if (m.kind === "answer") return "shadow-[inset_3px_0_0_var(--color-ink)]";
  return "";
}

function Arrow() {
  return (
    <svg width="12" height="10" viewBox="0 0 12 10" aria-hidden="true" className="shrink-0 text-slate">
      <path d="M1 5H10M7 2L10 5L7 8" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** A run id as a link to the tool run's record. */
export function RunLink({ id }: { id: string }) {
  return (
    <a
      href={`${API_URL}/runs/${id}`}
      target="_blank"
      rel="noreferrer"
      className="font-mono text-[12px] text-slate underline-offset-2 hover:text-forest hover:underline"
      title="Open the tool run's record"
    >
      {id}
    </a>
  );
}

function MessageRow({ m, fresh }: { m: ConversationMessage; fresh: boolean }) {
  const kind = KIND[m.kind] ?? KIND.message;
  return (
    <li
      className={`flex w-full items-start gap-[12px] border-b border-line px-[16px] py-[10px] last:border-b-0 ${rowTone(m)} ${fresh ? "convo-in" : ""}`}
      data-kind={m.kind}
    >
      <Mono className="w-[62px] shrink-0 pt-[5px]">{clock(m.at)}</Mono>
      <span className="flex w-[232px] shrink-0 items-center gap-[6px]">
        <ActorChip actor={m.from} />
        <Arrow />
        <ActorChip actor={m.to} />
      </span>
      <span className={`min-w-0 flex-1 pt-[4px] text-[14px] leading-[20px] ${m.kind === "question" ? "font-semibold text-escalation" : m.kind === "refusal" ? "text-denied" : m.from === CONTROLLER ? "font-semibold text-ink" : "text-body"}`}>
        {m.text}
      </span>
      <span className="flex w-[84px] shrink-0 flex-col items-end gap-[2px] pt-[5px]">
        {kind.word ? <span className={`text-[11px] font-semibold uppercase tracking-[0.88px] ${kind.tone}`}>{kind.word}</span> : null}
        {m.run_id ? <RunLink id={m.run_id} /> : null}
        {!m.run_id && m.item_id && (m.kind === "question" || m.kind === "answer") ? <Mono>{m.item_id}</Mono> : null}
      </span>
    </li>
  );
}

/**
 * What the agents and the controller told each other, oldest first, on the Log page (its Conversation view). The
 * Case shows only the pipeline.
 */
export function Conversation({ messages, received, live, className = "" }: {
  messages: ConversationMessage[]; received: Record<string, number>; live: boolean; className?: string;
}) {
  const [mounted] = useState(() => Date.now());
  return (
    <section aria-label="Conversation" className={`flex w-full flex-col overflow-hidden rounded-card border border-line bg-white ${className}`}>
      <div className="flex w-full items-center gap-[10px] border-b border-line px-[16px] py-[10px]">
        <Label>Conversation</Label>
        {live ? <span className="flex items-center gap-[6px] text-[12px] font-semibold text-forest"><LiveDot tone="bg-forest" />Live</span> : null}
        <span className="flex-1" />
        <Mono>{messages.length === 1 ? "1 message" : `${messages.length} messages`}</Mono>
      </div>
      <ol className="flex flex-col" aria-live="polite" aria-relevant="additions">
        {messages.map((m) => <MessageRow key={`${m.id}-${m.at}`} m={m} fresh={(received[m.id] ?? 0) > mounted} />)}
        {!messages.length ? <li className="px-[16px] py-[14px] text-[14px] text-slate">The agents start talking when the run begins.</li> : null}
      </ol>
    </section>
  );
}

/** The question that holds the agents, at the top of the flag card: who asks, and how many questions wait. */
export function AskingBanner({ party, count }: { party: string; count: number }) {
  const key = agentKey(party);
  const role = PIPELINE.find((p) => p.key === key)?.role;
  return (
    <div className="flex w-full items-center gap-[10px] rounded-[10px] bg-escalation-tint px-[12px] py-[8px] text-escalation">
      {role ? <Avatar role={role} size={24} /> : <Shape kind="triangle" size={12} />}
      <strong className="text-[15px] font-semibold">The {agentName(party)} is asking you</strong>
      <span className="text-[13px]">{count > 1 ? `${count} questions hold the agents. Answer them and the run goes on.` : "Answer it and the run goes on."}</span>
      <span className="flex-1" />
      <LiveDot tone="bg-escalation-bar" />
    </div>
  );
}
