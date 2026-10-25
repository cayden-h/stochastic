// The live conversation and the live mappings, as the gateway streams them (docs/architecture/gateway-and-api.md,
// "Live events"), and the Agent House's reading of them. The one module every page reads the conversation through.
// Pure: no React, no three.js, no clock reads, no network, so `npm run test:lib` runs it under plain `node --test`.
// Only type imports here: Node strips them, and any other import would need the bundler's path aliases.
import type { AuditRow, Mapping, WorkItem } from "./types";

export type Party =
  | "agent:brief_reader" | "agent:mapper" | "agent:preparer" | "agent:reviewer"
  | "system:gateway" | "human:controller";

export type MessageKind = "message" | "handoff" | "question" | "answer" | "refusal" | "check";

/** One `conversation` event, and one entry of `GET /deals/{id}/conversation`. */
export interface ConversationMessage {
  id: string; deal_id: string; at: string; from: Party | string; to: Party | string; kind: MessageKind | string;
  text: string; item_id: string | null; run_id: string | null; line_id: string | null;
  /** The policy a message announces ("Learned p_007: ..."), when an answer taught one. */
  policy_id?: string | null;
}

/** A conversation line as the Agent House plays it: a gateway message, or one derived from the audit log
 * (`fromAudit`, for a backend without conversation events). */
export interface ConversationEvent {
  id: string; at: string; from: string; to: string; kind: MessageKind; text: string;
  item_id?: string | null; run_id?: string | null;
}
export type ConversationKind = MessageKind;

/** One `mapping` event: one target line's mapping, sent when the gateway stores it and again when it changes. */
export interface MappingEvent {
  mapping_id: string; line_id: string; company: string | null; section: string | null; line: string;
  platform_line: string | null; platform_line_id: string | null; confidence: number; reason: string;
  flagged: boolean; approved_by: string | null; policy_id: string | null; at: string;
}

export const CONTROLLER = "human:controller";
export const GATEWAY = "system:gateway";

// ------------------------------------------------------------------ the conversation

export interface ConversationState {
  /** The deal these messages belong to. A message or a load for another deal starts the list over. */
  deal: string | null;
  /** The history read (GET /conversation) has answered or failed for this deal. */
  loaded: boolean;
  /** The gateway speaks the conversation: the history read answered, or a `conversation` event arrived. */
  supported: boolean;
  /** In the gateway's order (msg_001, msg_002, ...). */
  messages: ConversationMessage[];
  /** When this page received each message from the stream, in ms. Absent for messages read with a load. */
  received: Record<string, number>;
}

export type ConversationAction =
  | { type: "message"; message: ConversationMessage; receivedAt: number }
  | { type: "load"; deal: string; messages: ConversationMessage[] }
  /** The history read failed (a backend without the conversation): pages fall back to the audit log. */
  | { type: "loadFailed"; deal: string }
  | { type: "reset"; deal?: string | null };

export const emptyConversation: ConversationState = { deal: null, loaded: false, supported: false, messages: [], received: {} };

/** The number in "msg_012", for ordering; ids that do not match sort by time after the numbered ones. */
function seq(id: string): number {
  const m = /(\d+)$/.exec(id);
  return m ? Number(m[1]) : Number.MAX_SAFE_INTEGER;
}

function byOrder(a: ConversationMessage, b: ConversationMessage): number {
  return seq(a.id) - seq(b.id) || a.at.localeCompare(b.at);
}

/**
 * Keeps the deal's messages in order, without duplicates. The stream replays the whole history on every connect, so
 * a message already held is replaced in place. Ids start again at msg_001 after `/dev/reset`, so a held id that comes
 * back with another time means the record was reset: the list starts over from that message.
 */
export function conversationReducer(state: ConversationState, action: ConversationAction): ConversationState {
  switch (action.type) {
    case "reset":
      return { ...state, deal: action.deal ?? state.deal, messages: [], received: {} };
    case "loadFailed":
      if (state.deal !== action.deal) return { ...emptyConversation, deal: action.deal, loaded: true };
      return state.loaded ? state : { ...state, loaded: true };
    case "message": {
      const m = action.message;
      const fresh = { deal: m.deal_id, loaded: false, supported: true, messages: [m], received: { [m.id]: action.receivedAt } };
      if (state.deal !== null && m.deal_id !== state.deal) return fresh;
      const held = state.messages.find((x) => x.id === m.id);
      if (held && held.at !== m.at) return { ...fresh, loaded: state.loaded };
      if (held) {
        if (held.text === m.text && held.kind === m.kind) return state.supported ? state : { ...state, supported: true };
        return { ...state, supported: true, messages: state.messages.map((x) => (x.id === m.id ? m : x)) };
      }
      const messages = [...state.messages, m];
      const last = state.messages[state.messages.length - 1];
      if (last && byOrder(last, m) > 0) messages.sort(byOrder);
      return { ...state, deal: m.deal_id, supported: true, messages, received: { ...state.received, [m.id]: action.receivedAt } };
    }
    case "load": {
      const loaded = [...action.messages].sort(byOrder);
      const done = { deal: action.deal, loaded: true, supported: true };
      if (state.deal !== action.deal) return { ...done, messages: loaded, received: {} };
      const at = new Map(loaded.map((m) => [m.id, m.at]));
      const conflict = state.messages.some((m) => at.has(m.id) && at.get(m.id) !== m.at);
      // An empty read, or one that disagrees with what is held, is a reset: the read is the record.
      if (conflict || !loaded.length) return { ...done, messages: loaded, received: {} };
      // Messages the stream delivered after the read was sent are kept.
      const newer = state.messages.filter((m) => !at.has(m.id));
      const messages = [...loaded, ...newer].sort(byOrder);
      const received: Record<string, number> = {};
      for (const m of newer) if (state.received[m.id] !== undefined) received[m.id] = state.received[m.id];
      for (const m of loaded) if (state.received[m.id] !== undefined) received[m.id] = state.received[m.id];
      return { ...done, messages, received };
    }
  }
}

// ------------------------------------------------------------------ the agents' states

export type AgentKey = "brief-reader" | "mapper" | "preparer" | "reviewer";
export const AGENT_KEYS: AgentKey[] = ["brief-reader", "mapper", "preparer", "reviewer"];

export type AgentState = "idle" | "working" | "talking" | "asking" | "done";

const KEY_OF: Record<string, AgentKey> = {
  "agent:brief_reader": "brief-reader",
  "agent:mapper": "mapper",
  "agent:preparer": "preparer",
  "agent:reviewer": "reviewer",
};

/** agent:brief_reader -> brief-reader, and so on; null for the gateway and the controller. */
export function agentKey(party: string): AgentKey | null {
  return KEY_OF[party] ?? null;
}

/** The scene key for an actor in the Agent House, or null for the controller and the gateway (no avatar there). */
export const sceneKey = agentKey;

const ACTOR_OF: Record<AgentKey, string> = {
  "brief-reader": "agent:brief_reader", mapper: "agent:mapper", preparer: "agent:preparer", reviewer: "agent:reviewer",
};

export function actorOfKey(key: AgentKey): string {
  return ACTOR_OF[key];
}

export interface AgentInfo {
  state: AgentState;
  /** The items this agent asked the controller about and is still waiting on, in the order it asked. */
  waitingOn: string[];
  /** The latest message this agent sent or received. */
  last: ConversationMessage | null;
  /** When this agent's current state began (the message's own time, ISO), or null while idle. */
  since: string | null;
}

/** How long an agent shows as talking after it says something, in ms. */
export const TALK_MS = 1800;

/** Whether a message reads as the Reviewer handing the result to the controller ("Ready for your approval"). */
export function isReadyForApproval(m: ConversationMessage): boolean {
  return m.kind === "handoff" && m.from === "agent:reviewer" && m.to === CONTROLLER;
}

/**
 * Each agent's state, read from the conversation in order:
 * - a `handoff` to an agent sets it working, and the agent that hands off is done (the Reviewer's "Ready for your
 *   approval" to the controller included);
 * - a `question` from an agent to the controller sets it asking until an `answer` with the same item_id;
 * - a `message`, `check`, or `refusal` from a working agent shows it talking for TALK_MS after this page received it,
 *   then working again. Messages read with a load (history) never show as talking.
 * `now` is the caller's clock, so the function stays pure.
 */
export function agentStates(state: ConversationState, now: number): Record<AgentKey, AgentInfo> {
  type Base = { state: Exclude<AgentState, "talking">; waitingOn: string[]; last: ConversationMessage | null; since: string | null; spokeAt: number | null };
  const fresh = (): Base => ({ state: "idle", waitingOn: [], last: null, since: null, spokeAt: null });
  const out: Record<AgentKey, Base> = { "brief-reader": fresh(), mapper: fresh(), preparer: fresh(), reviewer: fresh() };
  const become = (a: Base, s: Base["state"], at: string) => {
    if (a.state !== s) { a.state = s; a.since = at; }
  };
  for (const m of state.messages) {
    const from = agentKey(m.from);
    const to = agentKey(m.to);
    if (from) out[from].last = m;
    if (to) out[to].last = m;
    switch (m.kind) {
      case "handoff":
        if (from) { out[from].waitingOn = []; become(out[from], "done", m.at); out[from].spokeAt = null; }
        if (to) { out[to].waitingOn = []; become(out[to], "working", m.at); }
        break;
      case "question":
        if (from && m.to === CONTROLLER) {
          if (m.item_id && !out[from].waitingOn.includes(m.item_id)) out[from].waitingOn.push(m.item_id);
          become(out[from], "asking", m.at);
          out[from].spokeAt = null;
        }
        break;
      case "answer":
        if (m.from === CONTROLLER) {
          for (const k of AGENT_KEYS) {
            const a = out[k];
            if (!m.item_id || !a.waitingOn.includes(m.item_id)) continue;
            a.waitingOn = a.waitingOn.filter((id) => id !== m.item_id);
            if (!a.waitingOn.length && a.state === "asking") become(a, "working", m.at);
          }
        }
        break;
      default: // message, check, refusal
        if (from) {
          if (out[from].state === "idle") become(out[from], "working", m.at);
          const r = state.received[m.id];
          if (r !== undefined) out[from].spokeAt = r;
        }
        if (to && out[to].state === "idle") become(out[to], "working", m.at);
    }
  }
  const result = {} as Record<AgentKey, AgentInfo>;
  for (const k of AGENT_KEYS) {
    const { spokeAt, ...a } = out[k];
    const talking = a.state === "working" && spokeAt !== null && now - spokeAt < TALK_MS;
    result[k] = { ...a, state: talking ? "talking" : a.state };
  }
  return result;
}

/** When the next "talking" ends, in ms, so a caller can re-render then; null when no agent is talking. */
export function nextTalkEnd(state: ConversationState, now: number): number | null {
  let soonest: number | null = null;
  for (const m of state.messages) {
    const r = state.received[m.id];
    if (r === undefined || !agentKey(m.from)) continue;
    const end = r + TALK_MS;
    if (end > now && (soonest === null || end < soonest)) soonest = end;
  }
  return soonest;
}

/** The questions to the controller that have no answer yet, oldest first. */
export function openQuestions(state: ConversationState): ConversationMessage[] {
  const answered = new Set(state.messages.filter((m) => m.kind === "answer" && m.from === CONTROLLER).map((m) => m.item_id));
  return state.messages.filter((m) => m.kind === "question" && m.to === CONTROLLER && m.item_id && !answered.has(m.item_id));
}

/** The Reviewer's hand-off to the controller, when it is the last word on the result (no later question). */
export function readyForApproval(state: ConversationState): ConversationMessage | null {
  for (let i = state.messages.length - 1; i >= 0; i--) {
    const m = state.messages[i];
    if (isReadyForApproval(m)) return m;
    if (m.kind === "question" && m.to === CONTROLLER) return null;
  }
  return null;
}

// ------------------------------------------------------------------ the live mappings

export interface MappingState {
  /** The deal these mappings belong to. */
  deal: string | null;
  /** Mapping ids in the order the gateway first stored them. */
  order: string[];
  byId: Record<string, MappingEvent>;
  /** When this page last received each mapping, in ms, so the newest can be highlighted. */
  received: Record<string, number>;
}

export type MappingAction =
  | { type: "upsert"; deal: string; mapping: MappingEvent; receivedAt: number }
  | { type: "reset"; deal?: string | null };

export const emptyMappings: MappingState = { deal: null, order: [], byId: {}, received: {} };

function sameMapping(a: MappingEvent, b: MappingEvent): boolean {
  return a.at === b.at && a.platform_line === b.platform_line && a.confidence === b.confidence && a.flagged === b.flagged
    && a.approved_by === b.approved_by && a.policy_id === b.policy_id && a.reason === b.reason && a.line_id === b.line_id;
}

/** Upserts by mapping_id and keeps the first-stored order. A mapping for another deal starts the list over. */
export function mappingReducer(state: MappingState, action: MappingAction): MappingState {
  if (action.type === "reset") return { ...emptyMappings, deal: action.deal ?? state.deal };
  const m = action.mapping;
  const base = state.deal === action.deal ? state : { ...emptyMappings, deal: action.deal };
  const held = base.byId[m.mapping_id];
  if (held && sameMapping(held, m)) return base;
  return {
    deal: action.deal,
    order: held ? base.order : [...base.order, m.mapping_id],
    byId: { ...base.byId, [m.mapping_id]: m },
    received: { ...base.received, [m.mapping_id]: action.receivedAt },
  };
}

/** The live mappings in order. */
export function liveList(state: MappingState): MappingEvent[] {
  return state.order.map((id) => state.byId[id]);
}

/** A mapping event in the shape `/case` returns, so the Mapping page reads one kind of row. */
export function toMapping(e: MappingEvent): Mapping {
  return {
    id: e.mapping_id, target_line_id: e.line_id, platform_line_id: e.platform_line_id, target_line: e.line,
    platform_line: e.platform_line, confidence: e.confidence, reason: e.reason, flagged: e.flagged,
    approved_by: e.approved_by, policy_id: e.policy_id,
  };
}

/**
 * The mappings to show: the live ones in the order they arrived (each is at least as new as the last `/case` read,
 * because the stream re-sends a mapping when it changes), then any the case holds that the stream has not sent.
 */
export function mergeMappings(caseMappings: Mapping[], live: MappingState): Mapping[] {
  if (!live.order.length) return caseMappings;
  const out = liveList(live).map(toMapping);
  const seen = new Set(live.order);
  for (const m of caseMappings) if (!seen.has(m.id)) out.push(m);
  return out;
}

// ------------------------------------------------------------------ the Agent House's reading

export interface AgentStatus { state: AgentState; text: string }
export type HouseState = Record<AgentKey, AgentStatus>;

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
    const kinds: MessageKind[] = ["message", "handoff", "question", "answer", "refusal", "check"];
    if (!e || typeof e.id !== "string" || typeof e.from !== "string" || typeof e.to !== "string" || typeof e.text !== "string"
      || !kinds.includes(e.kind as MessageKind)) return null;
    return { id: e.id, at: e.at ?? new Date().toISOString(), from: e.from, to: e.to, kind: e.kind as MessageKind,
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
