// The live conversation and the live mappings, as the gateway streams them (docs/architecture/gateway-and-api.md,
// "Live events"). Pure: no React, no clock reads, no network, so `npm run test:lib` runs it under plain `node --test`.
// Only type imports here: Node strips them, and any other import would need the bundler's path aliases.
import type { Mapping } from "./types";

export type Party =
  | "agent:brief_reader" | "agent:mapper" | "agent:preparer" | "agent:reviewer"
  | "system:gateway" | "human:controller";

export type MessageKind = "message" | "handoff" | "question" | "answer" | "refusal" | "check";

/** One `conversation` event, and one entry of `GET /deals/{id}/conversation`. */
export interface ConversationMessage {
  id: string; deal_id: string; at: string; from: Party | string; to: Party | string; kind: MessageKind | string;
  text: string; item_id: string | null; run_id: string | null; line_id: string | null;
}

/** One `mapping` event: one target line's mapping, sent when the gateway stores it and again when it changes. */
export interface MappingEvent {
  mapping_id: string; line_id: string; company: string | null; section: string | null; line: string;
  platform_line: string | null; platform_line_id: string | null; confidence: number; reason: string;
  flagged: boolean; approved_by: string | null; policy_id: string | null; at: string;
}

export const CONTROLLER = "human:controller";

// ------------------------------------------------------------------ the conversation

export interface ConversationState {
  /** The deal these messages belong to. A message or a load for another deal starts the list over. */
  deal: string | null;
  /** In the gateway's order (msg_001, msg_002, ...). */
  messages: ConversationMessage[];
  /** When this page received each message from the stream, in ms. Absent for messages read with a load. */
  received: Record<string, number>;
}

export type ConversationAction =
  | { type: "message"; message: ConversationMessage; receivedAt: number }
  | { type: "load"; deal: string; messages: ConversationMessage[] }
  | { type: "reset"; deal?: string | null };

export const emptyConversation: ConversationState = { deal: null, messages: [], received: {} };

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
      return { deal: action.deal ?? state.deal, messages: [], received: {} };
    case "message": {
      const m = action.message;
      if (state.deal !== null && m.deal_id !== state.deal) {
        return { deal: m.deal_id, messages: [m], received: { [m.id]: action.receivedAt } };
      }
      const held = state.messages.find((x) => x.id === m.id);
      if (held && held.at !== m.at) {
        return { deal: m.deal_id, messages: [m], received: { [m.id]: action.receivedAt } };
      }
      if (held) {
        if (held.text === m.text && held.kind === m.kind) return state;
        return { ...state, messages: state.messages.map((x) => (x.id === m.id ? m : x)) };
      }
      const messages = [...state.messages, m];
      const last = state.messages[state.messages.length - 1];
      if (last && byOrder(last, m) > 0) messages.sort(byOrder);
      return { deal: m.deal_id, messages, received: { ...state.received, [m.id]: action.receivedAt } };
    }
    case "load": {
      const loaded = [...action.messages].sort(byOrder);
      if (state.deal !== action.deal) return { deal: action.deal, messages: loaded, received: {} };
      const at = new Map(loaded.map((m) => [m.id, m.at]));
      const conflict = state.messages.some((m) => at.has(m.id) && at.get(m.id) !== m.at);
      // An empty read, or one that disagrees with what is held, is a reset: the read is the record.
      if (conflict || !loaded.length) return { deal: action.deal, messages: loaded, received: {} };
      // Messages the stream delivered after the read was sent are kept.
      const newer = state.messages.filter((m) => !at.has(m.id));
      const messages = [...loaded, ...newer].sort(byOrder);
      const received: Record<string, number> = {};
      for (const m of newer) if (state.received[m.id] !== undefined) received[m.id] = state.received[m.id];
      for (const m of loaded) if (state.received[m.id] !== undefined) received[m.id] = state.received[m.id];
      return { deal: action.deal, messages, received };
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
