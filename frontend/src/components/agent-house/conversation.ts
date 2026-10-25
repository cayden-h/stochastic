/**
 * The agents' conversation: who said what to whom, in time order. Pure: no React, no three.js, so any page can use it.
 *
 * The gateway may send a `conversation` event on GET /deals/{id}/stream with this shape. Until it does, the same shape
 * is derived from the audit log, so the Agent House works on today's backend and gets richer once the event lands.
 */
import type { AuditRow, WorkItem } from "@/lib/types";

export type ConversationKind = "message" | "handoff" | "question" | "answer" | "refusal" | "check";

/** One line of the conversation. `from` and `to` are actors: agent:mapper, human:controller, system:gateway. */
export interface ConversationEvent {
  id: string;
  at: string;
  from: string;
  to: string;
  kind: ConversationKind;
  text: string;
  item_id?: string | null;
  run_id?: string | null;
}

/** The scene keys of the four agents, in pipeline order. */
export const AGENT_KEYS = ["brief-reader", "mapper", "preparer", "reviewer"] as const;
export type AgentKey = (typeof AGENT_KEYS)[number];
export type AgentState = "idle" | "working" | "talking" | "asking" | "done";
export interface AgentStatus { state: AgentState; text: string }
export type HouseState = Record<AgentKey, AgentStatus>;

export const CONTROLLER = "human:controller";
export const GATEWAY = "system:gateway";

const ROLE_KEYS: Record<string, AgentKey> = {
  "agent:brief_reader": "brief-reader", "agent:mapper": "mapper", "agent:preparer": "preparer", "agent:reviewer": "reviewer",
};

/** The scene key for an actor, or null for the controller and the gateway, which have no avatar in the house. */
export function sceneKey(actor: string): AgentKey | null {
  return ROLE_KEYS[actor] ?? null;
}

const ACTOR_OF: Record<AgentKey, string> = {
  "brief-reader": "agent:brief_reader", mapper: "agent:mapper", preparer: "agent:preparer", reviewer: "agent:reviewer",
};

export function actorOfKey(key: AgentKey): string {
  return ACTOR_OF[key];
}

/** Which agent owns each work item type, and who it is handed to when the gateway opens it. */
const OWNER: Record<string, string> = {
  draft_brief: "agent:brief_reader", map_lines: "agent:mapper", prepare_result: "agent:preparer",
  review_result: "agent:reviewer", approve_result: CONTROLLER,
};
const PREVIOUS: Record<string, string> = {
  map_lines: "agent:brief_reader", prepare_result: "agent:mapper", review_result: "agent:preparer", approve_result: "agent:reviewer",
};
const HANDOFF_TEXT: Record<string, string> = {
  draft_brief: "Read the credit agreement and draft the Brief.",
  map_lines: "Map the target's lines onto the platform's chart.",
  prepare_result: "Mapping is done. Draft the combined books.",
  review_result: "Draft books are ready. Tie them out and test the limit.",
  approve_result: "Review passed. Ready for you to approve and post.",
};

function clean(s: string | null | undefined): string {
  return (s ?? "").trim().replace(/\s+/g, " ");
}

function sentence(s: string): string {
  const t = clean(s);
  if (!t) return t;
  const c = t.charAt(0).toUpperCase() + t.slice(1);
  return /[.?!]$/.test(c) ? c : `${c}.`;
}

/**
 * Derive the conversation from audit rows. Tool runs by one agent in a row become one `check` line, bookkeeping rows
 * (session turns, posts of an agent's own work, what-if runs by the gateway) are left out.
 */
export function fromAudit(rows: AuditRow[], items: WorkItem[]): ConversationEvent[] {
  const byId = new Map(items.map((i) => [i.id, i]));
  const out: ConversationEvent[] = [];
  const seen = new Set<string>();  // agents that have acted on this deal, so a handoff comes from a real sender
  for (const r of rows) {
    if (r.actor.startsWith("agent:")) seen.add(r.actor);
    const item = r.target ? byId.get(r.target) : undefined;
    const [verb, rest] = r.action.split(":");
    const base = { id: `a${r.id}`, at: r.at, item_id: item?.id ?? null };
    if (r.result === "DENIED") {
      out.push({ ...base, from: GATEWAY, to: r.actor, kind: "refusal", text: `Refused: ${clean(r.reason) || r.action}.`.replace(/\.\.$/, ".") });
      continue;
    }
    if (verb === "create" && rest && OWNER[rest]) {
      const prev = PREVIOUS[rest];
      const from = prev && seen.has(prev) ? prev : GATEWAY;
      out.push({ ...base, from, to: OWNER[rest], kind: "handoff", text: HANDOFF_TEXT[rest] });
      continue;
    }
    if (verb === "tool" && r.actor.startsWith("agent:")) {
      const last = out[out.length - 1];
      if (last && last.kind === "check" && last.from === r.actor && last.id.startsWith("a")) {
        last.text = `${last.text.replace(/ ran\.$/, "")} · ${rest} ran.`;
        last.run_id = r.target ?? last.run_id;
        continue;
      }
      out.push({ ...base, from: r.actor, to: GATEWAY, kind: "check", text: `${rest} ran.`, run_id: r.target ?? null });
      continue;
    }
    if (verb === "propose") {
      const what: Record<string, string> = {
        draft_brief: "Brief drafted", map_lines: "Mapped the lines", prepare_result: "Draft books proposed",
        review_result: "Review",
      };
      const head = what[rest ?? ""] ?? `${rest} proposed`;
      const reason = clean(r.reason);
      out.push({ ...base, from: r.actor, to: GATEWAY, kind: "message", text: sentence(reason ? `${head}: ${reason}` : head) });
      continue;
    }
    if (verb === "ask") {
      out.push({ ...base, from: r.actor, to: CONTROLLER, kind: "question", text: clean(item?.question ?? r.reason) || "Needs your answer." });
      continue;
    }
    if (verb === "answer") {
      const opt = item?.options.find((o) => o.id === item.answer);
      const to = item?.proposed_by?.startsWith("agent:") ? item.proposed_by : item?.type === "draft_brief" ? "agent:brief_reader" : GATEWAY;
      const pick = opt ? `Option ${opt.id}. ${opt.label}` : clean(r.reason) || "Answered";
      out.push({ ...base, from: r.actor, to, kind: "answer", text: sentence(pick) });
      continue;
    }
    if (verb === "hold") {
      out.push({ ...base, from: r.actor, to: item?.proposed_by ?? GATEWAY, kind: "answer", text: "Not sure yet. Holding this one." });
      continue;
    }
    if (verb === "approve_brief") {
      out.push({ ...base, from: r.actor, to: "agent:brief_reader", kind: "answer", text: "Brief approved and locked." });
      continue;
    }
    if (verb === "approve" || verb === "reject") {
      const to = item?.type === "approve_result" ? "agent:reviewer" : item?.proposed_by ?? GATEWAY;
      const text = verb === "approve" ? "Approved." : sentence(`Rejected. ${clean(r.reason)}`);
      out.push({ ...base, from: r.actor, to, kind: "answer", text });
      continue;
    }
    if (verb === "post" && item?.type === "approve_result") {
      out.push({ ...base, from: GATEWAY, to: CONTROLLER, kind: "message", text: "Approved and posted to the record." });
      continue;
    }
    if (verb === "policy" && rest === "learn") {
      out.push({ ...base, from: GATEWAY, to: GATEWAY, kind: "message", text: sentence(`Saved policy ${r.target ?? ""}. ${clean(r.reason)}`) });
      continue;
    }
    if (verb === "run" && rest === "failed") {
      out.push({ ...base, from: GATEWAY, to: CONTROLLER, kind: "refusal", text: sentence(`Run stopped. ${clean(r.reason)}`) });
      continue;
    }
    if (verb === "reverse") {
      out.push({ ...base, from: r.actor, to: GATEWAY, kind: "message", text: sentence(`Reversed. ${clean(r.reason)}`) });
    }
  }
  return out;
}

/**
 * The conversation to show: the gateway's own events when it speaks the conversation (`supported`), else the derived
 * ones. If live events turn up without that (the history read failed), derived lines from the same span are dropped
 * so nothing shows twice; older derived lines stay.
 */
export function mergeConversation(derived: ConversationEvent[], live: ConversationEvent[], supported = false): ConversationEvent[] {
  if (supported) return live;
  if (!live.length) return derived;
  const first = Math.min(...live.map((e) => Date.parse(e.at)));
  const keep = derived.filter((e) => Date.parse(e.at) < first);
  const ids = new Set<string>();
  return [...keep, ...live].filter((e) => (ids.has(e.id) ? false : (ids.add(e.id), true)))
    .sort((a, b) => Date.parse(a.at) - Date.parse(b.at));
}

/** Read one `conversation` SSE payload, or null when it is not one. */
export function parseConversation(data: string): ConversationEvent | null {
  try {
    const e = JSON.parse(data) as Partial<ConversationEvent>;
    const kinds: ConversationKind[] = ["message", "handoff", "question", "answer", "refusal", "check"];
    if (!e || typeof e.id !== "string" || typeof e.from !== "string" || typeof e.to !== "string" || typeof e.text !== "string"
      || !kinds.includes(e.kind as ConversationKind)) return null;
    return { id: e.id, at: e.at ?? new Date().toISOString(), from: e.from, to: e.to, kind: e.kind as ConversationKind,
      text: e.text, item_id: e.item_id ?? null, run_id: e.run_id ?? null };
  } catch {
    return null;
  }
}

export function idleHouse(): HouseState {
  return Object.fromEntries(AGENT_KEYS.map((k) => [k, { state: "idle", text: "" }])) as HouseState;
}

/**
 * The settled state of every agent after these events. Transient moments (talking while a message travels) are the
 * player's job; this is where each agent rests.
 * - a handoff puts the receiver to work and the sending agent at done;
 * - a question to the controller puts the asker at asking until an answer comes back to it;
 * - an answer puts the agent back to work (its open questions on that item close);
 * - checks and messages keep the speaker working; a refusal shows on the refused agent;
 * - the approval post puts every agent that worked at done.
 */
export function settle(events: ConversationEvent[], stage?: string): HouseState {
  const s = idleHouse();
  const open = new Map<AgentKey, Set<string>>();
  const touched = new Set<AgentKey>();
  for (const e of events) {
    const from = sceneKey(e.from), to = sceneKey(e.to);
    if (from) touched.add(from);
    if (to) touched.add(to);
    switch (e.kind) {
      case "handoff":
        if (from && s[from].state !== "asking") s[from] = { state: "done", text: e.text };
        if (to) s[to] = { state: "working", text: e.text };
        break;
      case "question":
        if (from) {
          const q = open.get(from) ?? new Set<string>();
          q.add(e.item_id ?? e.id);
          open.set(from, q);
          s[from] = { state: "asking", text: e.text };
        }
        break;
      case "answer":
        if (to) {
          const q = open.get(to);
          if (q) q.delete(e.item_id ?? [...q][0]);
          if (!q || q.size === 0) s[to] = { state: "working", text: `Got it: ${e.text}` };
        }
        break;
      case "refusal":
        if (to) s[to] = { state: s[to].state === "asking" ? "asking" : "working", text: e.text };
        break;
      case "check":
      case "message":
        // a backend's own note on how it worked ("scripted backend: ...") stays in the feed, not on the bubble
        if (/^\w+ backend:/i.test(e.text)) break;
        if (from && s[from].state !== "asking") s[from] = { state: "working", text: e.text };
        // the gateway's word to an agent at work (a tool result, a check) shows on that agent; it wakes no one
        if (!from && to && s[to].state === "working") s[to] = { state: "working", text: e.text };
        if (e.from === GATEWAY && e.to === CONTROLLER && /posted/i.test(e.text)) {
          for (const k of touched) s[k] = { state: "done", text: k === "reviewer" ? "Posted to the record." : s[k].text };
        }
        break;
    }
  }
  // The stage says when a run is over or waiting, which the rows alone cannot: an agent that proposed its work and
  // handed nothing on is done once the deal waits on the controller or is posted.
  if (stage === "awaiting_approval" || stage === "posted") {
    for (const k of AGENT_KEYS) if (s[k].state === "working") s[k] = { ...s[k], state: "done" };
  }
  if ((stage === "awaiting_brief" || stage === "brief_ready") && s["brief-reader"].state !== "asking") {
    s["brief-reader"] = { state: "asking", text: "Check and approve the Brief." };
  }
  if (stage === "run_failed") {
    for (const k of AGENT_KEYS) if (s[k].state === "working") s[k] = { state: "idle", text: "Run stopped." };
  }
  return s;
}

/** The word on the right of a feed line, as in the Figma frame (ASKED, ANSWERED, POLICY, PROPOSED, PASS). */
export function verbOfEvent(e: ConversationEvent): string {
  const t = e.text;
  switch (e.kind) {
    case "question": return "ASKED";
    case "answer": return /^approved/i.test(t) ? "APPROVED" : /^rejected/i.test(t) ? "REJECTED" : "ANSWERED";
    case "handoff": return "HANDOFF";
    case "refusal": return "DENIED";
    case "check": return /\bpass/i.test(t) ? "PASS" : "CHECKED";
    case "message":
      if (e.from === CONTROLLER) {
        if (/^approved/i.test(t)) return "APPROVED";
        if (/^rejected/i.test(t)) return "REJECTED";
        if (/^reversed/i.test(t)) return "REVERSED";
        if (/^holding/i.test(t)) return "HELD";
        return /edit/i.test(t) ? "EDITED" : "SAID";
      }
      if (e.from === GATEWAY) {
        if (/polic/i.test(t)) return "POLICY";
        if (/posted/i.test(t)) return "POSTED";
        if (/stopped/i.test(t)) return "STOPPED";
        return e.to.startsWith("agent:") ? "RAN" : "NOTE";
      }
      if (/^review/i.test(t)) return /pass/i.test(t) ? "PASS" : "REVIEWED";
      if (/propos|draft|mapped|brief/i.test(t)) return "PROPOSED";
      return "NOTE";
  }
}
