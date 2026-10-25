"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { type LearnedNotice, useDeal } from "@/lib/deal-context";
import type { Notice } from "@/lib/types";
import { agentName } from "./process-flow";
import { Avatar, Shape, Tag, actorOf } from "./ui";

const LEARNED_MS = 6000;

/** The agent's character, or the gateway's lock-grey square when no agent sent it. */
function Who({ party, size }: { party: string; size: number }) {
  const role = actorOf(party).role;
  return role ? <Avatar role={role} size={size} /> : <span className="text-code"><Shape kind="square" size={size * 0.6} /></span>;
}

/** The agent's message in the agent's voice: "Learned p_007: ..." becomes "The Mapper learned p_007: ...", and
 * "Learned p_013 to p_017 (...): ..." keeps its range. A message in other words is quoted after the policy id. */
export function learnedSentence(n: Pick<LearnedNotice, "from" | "policy_id" | "text">): string {
  const who = actorOf(n.from).kind === "Agent" ? `The ${agentName(n.from)}` : "The gateway";
  const text = n.text.trim();
  if (/^learned\s+/i.test(text)) return `${who} learned ${text.replace(/^learned\s+/i, "")}`;
  return `${who} learned ${n.policy_id}${text ? `: ${text}` : "."}`;
}

/** A question for the controller: who asks, what, and one button that opens the flag card. */
function DecisionToast({ notice, more, onDecide, onLater }: { notice: Notice; more: number; onDecide: () => void; onLater: () => void }) {
  return (
    <section
      role="alert"
      aria-label={notice.title}
      data-notice={notice.item_id ?? notice.id}
      className="toast-in pointer-events-auto flex w-[380px] gap-[12px] rounded-card border border-amber-line bg-white p-[16px] shadow-[0_10px_32px_rgba(27,31,36,0.18)]"
    >
      <Who party={notice.from} size={36} />
      <div className="flex min-w-0 flex-1 flex-col gap-[6px]">
        <span className="inline-flex items-center gap-[6px] text-[11px] font-semibold tracking-[0.88px] text-escalation uppercase">
          <Shape kind="triangle" size={10} />
          Needs your decision
        </span>
        <strong className="text-[16px] leading-[21px] font-semibold text-forest">{notice.title}</strong>
        {notice.body ? <p className="line-clamp-3 text-[13px] leading-[18px] text-slate" title={notice.body}>{notice.body}</p> : null}
        <div className="flex items-center gap-[14px] pt-[4px]">
          <button
            type="button"
            onClick={onDecide}
            className="inline-flex min-h-[36px] items-center justify-center rounded-chip bg-forest px-[16px] font-ui text-[14px] font-semibold text-paper transition-colors duration-150 hover:bg-forest-deep"
          >
            Decide
          </button>
          <button type="button" onClick={onLater} className="text-[13px] font-semibold text-slate underline-offset-4 hover:text-forest hover:underline">
            Later
          </button>
          {more ? <span className="ml-auto font-mono text-[12px] text-slate">{more === 1 ? "1 more question" : `${more} more questions`}</span> : null}
        </div>
      </div>
    </section>
  );
}

/** The policies an answer just taught: the newest, and how many came with it. */
function LearnedToast({ note, more, onClose }: { note: LearnedNotice; more: number; onClose: () => void }) {
  return (
    <section
      role="status"
      data-learned={note.policy_id}
      className="toast-in pointer-events-auto flex w-[380px] items-start gap-[12px] rounded-card border border-mint-edge bg-white p-[14px] shadow-[0_10px_32px_rgba(27,31,36,0.14)]"
    >
      <Who party={note.from} size={30} />
      <div className="flex min-w-0 flex-1 flex-col gap-[4px]">
        <span className="flex items-center gap-[8px]">
          <Tag tone="agent">Learned</Tag>
          {more ? <span className="font-mono text-[12px] text-slate">+{more} more {more === 1 ? "policy" : "policies"}</span> : null}
        </span>
        <p className="line-clamp-3 text-[14px] leading-[19px] text-forest" title={learnedSentence(note)}>{learnedSentence(note)}</p>
      </div>
      <button type="button" onClick={onClose} aria-label="Close" className="-mt-[2px] -mr-[2px] flex size-[24px] shrink-0 items-center justify-center rounded-[6px] text-slate hover:bg-mint-select">
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M1.5 1.5l7 7M8.5 1.5l-7 7" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
      </button>
    </section>
  );
}

/**
 * The notifications, top right on every page: a question that needs the controller (`notify`), until they decide or
 * put it off, and each policy an answer taught, for a few seconds. A question already answered drops out on its own.
 */
export function Toasts() {
  const { notices, learned, dismiss, kase, select, requestFocus, deciding } = useDeal();
  const router = useRouter();
  const path = usePathname();
  // One learned note at a time: the newest, closed a few seconds after it came, with the ones before it.
  const lastLearned = learned[learned.length - 1]?.id ?? null;
  const learnedIds = learned.map((n) => n.id).join(" ");
  useEffect(() => {
    if (!lastLearned) return;
    const t = setTimeout(() => { for (const id of learnedIds.split(" ")) dismiss(id); }, LEARNED_MS);
    return () => clearTimeout(t);
  }, [lastLearned, learnedIds, dismiss]);
  // A question is open until the case shows it answered. One the case does not hold yet (the read is a moment behind
  // the event) still shows.
  const onCase = path.startsWith("/case");
  const open = notices.filter((n) => {
    if (onCase && n.deal_id === deciding && n.deal_id === kase?.deal.id) return false;
    if (!kase || n.deal_id !== kase.deal.id || !n.item_id) return true;
    const item = kase.flags.find((f) => f.id === n.item_id) ?? kase.work_items.find((w) => w.id === n.item_id);
    return !item || item.state === "NEEDS_INFO";
  });
  if (!open.length && !learned.length) return null;

  async function decide(n: Notice) {
    // The Case shows every open question (the current card, then "1 more question"), so Decide clears the deal's toasts.
    for (const x of notices) if (x.deal_id === n.deal_id) dismiss(x.id);
    if (kase && n.deal_id !== kase.deal.id) await select(n.deal_id);
    if (n.item_id) requestFocus(n.item_id);
    if (!onCase) router.push("/case");
  }

  return (
    <div className="pointer-events-none fixed top-[16px] right-[16px] z-[70] flex flex-col items-end gap-[10px] print:hidden [html[data-electron]_&]:top-[20px]" aria-live="polite">
      {/* One question at a time, the oldest first; the toast says how many more wait. */}
      {open[0] ? <DecisionToast key={open[0].id} notice={open[0]} more={open.length - 1} onDecide={() => void decide(open[0])} onLater={() => dismiss(open[0].id)} /> : null}
      {lastLearned ? (
        <LearnedToast
          key={lastLearned}
          note={learned[learned.length - 1]}
          more={learned.length - 1}
          onClose={() => { for (const n of learned) dismiss(n.id); }}
        />
      ) : null}
    </div>
  );
}
