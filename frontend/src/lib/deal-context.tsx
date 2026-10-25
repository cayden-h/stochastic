"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { API_URL, api } from "./api";
import {
  type AgentInfo, type AgentKey, type ConversationMessage, type MappingEvent, type MappingState,
  agentStates as readAgentStates, conversationReducer, emptyConversation, emptyMappings, mappingReducer, mergeMappings,
  nextTalkEnd,
} from "./conversation";
import { canStart, runInFlight } from "./format";
import type { AuditResponse, Case, DealSummary, Health, Mapping, Notice, Stage } from "./types";

/** A policy an answer just taught, from a `conversation` message with `policy_id` ("Learned p_007: ..."). */
export interface LearnedNotice { id: string; deal_id: string; from: string; policy_id: string; text: string; at: string }

/** Where the controller asked to go from a notification: the flag card of this item, on the Case. */
export interface FocusRequest { item_id: string; at: number }

/** The deal the controller picked, kept for a reload of this window. Storage can be missing or refuse; then the
 * console opens on the first deal, as before. */
const PICKED = "stochastic:deal";
function readPicked(): string | null {
  try { return window.sessionStorage.getItem(PICKED); } catch { return null; }
}
function writePicked(id: string | null): void {
  try { if (id) window.sessionStorage.setItem(PICKED, id); else window.sessionStorage.removeItem(PICKED); } catch { /* no storage */ }
}

/** A message sent before this page's stream connected is history, not news: it gets no toast. A little slack covers
 * the clocks of the browser and the gateway. */
const HISTORY_SLACK_MS = 2000;

interface DealData {
  /** Every case, from GET /deals. The current deal's row reads its stage from the case, which is fresher. */
  deals: DealSummary[];
  kase: Case | null;
  health: Health | null;
  audit: AuditResponse;
  error: LoadError | null;
  loading: boolean;
  /** When this session saw the current stage begin, in ms; 0 when it was already the stage on first load. */
  stageSince: number;
  /** Reads the case again. True when this read, or a later one, committed fresh data. */
  refresh: () => Promise<boolean>;
  /** Reads GET /deals again, alone: the other cases change without an event on this page's stream. */
  reloadDeals: () => Promise<void>;
  /** Make another deal the current one (the Dashboard rows and a new upload). */
  select: (id: string) => Promise<boolean>;
  /** The live conversation of the current deal, in the gateway's order (the stream, and GET /conversation on load). */
  messages: ConversationMessage[];
  /** When this page received each message from the stream, in ms (absent for history read on load). */
  received: Record<string, number>;
  /** The history read has answered or failed; until then a page cannot tell history from new lines. */
  conversationLoaded: boolean;
  /** The gateway speaks the conversation; when false, the Agents page derives it from the audit log. */
  conversationSupported: boolean;
  /** Each agent's live state, read from the conversation. */
  agentStates: Record<AgentKey, AgentInfo>;
  /** The mappings as the `mapping` events delivered them, with when each arrived (to highlight the newest). */
  liveMappings: MappingState;
  /** The mappings to show: the live ones, then any the last /case read has that the stream has not sent. */
  mappings: Mapping[];
  /** The clock the agent states were read at, in ms. It ticks only while an agent is talking. */
  now: number;
  /** Start the deal's run in the background. True from the click until the stream shows the run started. */
  startRun: (id?: string) => Promise<void>;
  starting: boolean;
  /** POST /dev/reset, then clear the live conversation and mappings and read the case again. */
  reset: (keepMemory: boolean) => Promise<void>;
  /** A run is in flight: starting, or the gateway says a job runs for the deal (`running` on /case). Writes wait for it. */
  running: boolean;
  /** The 15-second demo: reset to a fresh deal with memory cleared, make the demo deal current, and run it at demo pace. */
  runDemo: () => Promise<void>;
  /** The questions that opened for the controller while this page was open (`notify` events), oldest first. */
  notices: Notice[];
  /** The policies answers taught while this page was open, oldest first. */
  learned: LearnedNotice[];
  /** Close a notice or a learned note by its id. */
  dismiss: (id: string) => void;
  /** When the last policy was learned, in ms, so the sidebar's Policies counter can pulse. 0 before any. */
  learnedAt: number;
  /** A notification's Decide: open the Case on this item's flag card. */
  focus: FocusRequest | null;
  requestFocus: (itemId: string) => void;
  /** The deal whose questions the controller is answering now (they pressed Decide): on its Case, a question that
   * opens next is already on screen ("1 more question"), so it gets no toast there. A reset clears it. */
  deciding: string | null;
}

/** The gateway answered but holds no deal: a different screen from the gateway being down. */
class NoDeal extends Error {
  constructor() { super("The gateway has no deal loaded."); }
}

export interface LoadError { kind: "unreachable" | "no_deal"; message: string }

const emptyAudit: AuditResponse = { chain_valid: true, rows: [] };
const Ctx = createContext<DealData | null>(null);

/** Reads the case in one call and refreshes on every stream event. The console never computes a number. */
export function DealProvider({ children }: { children: React.ReactNode }) {
  const [deals, setDeals] = useState<DealSummary[]>([]);
  const [kase, setCase] = useState<Case | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [audit, setAudit] = useState<AuditResponse>(emptyAudit);
  const [error, setError] = useState<LoadError | null>(null);
  const [loading, setLoading] = useState(true);
  const dealId = useRef<string | null>(null);

  // Reads can overlap (a stream event while a reset is in flight, or select(B) while A loads). Each read takes a
  // number, and a read commits only if no later-numbered read has committed already. A stale response never
  // overwrites newer state, and a steady stream of events cannot starve updates (each finished read still commits).
  const seq = useRef(0);
  const committed = useRef(0);
  const [stageSeen, setStageSeen] = useState<{ deal: string; stage: string; at: number } | null>(null);
  const [conversation, dispatchConversation] = useReducer(conversationReducer, emptyConversation);
  const [live, dispatchMapping] = useReducer(mappingReducer, emptyMappings);
  const [starting, setStarting] = useState(false);
  const [now, setNow] = useState(0);

  const refresh = useCallback(async (): Promise<boolean> => {
    const mine = ++seq.current;
    try {
      // The list is read every time: a reset drops uploaded deals, and the current one must fall back to the demo deal.
      const list = await api.deals();
      if (dealId.current === null) dealId.current = readPicked();
      if (!list.some((d) => d.id === dealId.current)) dealId.current = list[0]?.id ?? null;
      const id = dealId.current;
      if (!id) throw new NoDeal();
      const [c, h, a] = await Promise.all([api.case(id), api.health(), api.audit(id)]);
      if (mine < committed.current) return true;  // a later read already put newer data on screen
      if (id !== dealId.current) return false;    // the controller switched deals meanwhile; that read will commit
      committed.current = mine;
      setDeals(list); setCase(c); setHealth(h); setAudit(a);
      if (!canStart(c.stage)) setStarting(false);
      // When this session saw the stage change, so a progress clock can start there (the backend logs no row
      // when a rerun reuses an agent's work item).
      setStageSeen((prev) => (prev && prev.deal === c.deal.id && prev.stage === c.stage ? prev
        : { deal: c.deal.id, stage: c.stage, at: prev && prev.deal === c.deal.id ? Date.now() : 0 }));
      setError(null);
      return true;
    } catch (e) {
      if (mine < committed.current) return true;
      setError(e instanceof NoDeal ? { kind: "no_deal", message: e.message } : { kind: "unreachable", message: e instanceof Error ? e.message : "Cannot reach the gateway API" });
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const reloadDeals = useCallback(async () => {
    try { setDeals(await api.deals()); } catch { /* the next full read says what is wrong */ }
  }, []);

  const select = useCallback(async (id: string) => {
    dealId.current = id;
    writePicked(id);
    return refresh();
  }, [refresh]);

  const [notices, setNotices] = useState<Notice[]>([]);
  const [learned, setLearned] = useState<LearnedNotice[]>([]);
  const [focus, setFocus] = useState<FocusRequest | null>(null);
  const [deciding, setDeciding] = useState<string | null>(null);
  const dismiss = useCallback((nid: string) => {
    setNotices((n) => n.filter((x) => x.id !== nid));
    setLearned((n) => n.filter((x) => x.id !== nid));
  }, []);
  const requestFocus = useCallback((itemId: string) => {
    setFocus({ item_id: itemId, at: Date.now() });
    setDeciding(dealId.current);
  }, []);

  // The first read, from a timer callback so the effect body itself sets no state (react-hooks/set-state-in-effect).
  useEffect(() => {
    const t = setTimeout(refresh, 0);
    return () => clearTimeout(t);
  }, [refresh]);

  // Live updates: a `stage` event on every stage change, an `audit` event on every new log row, an `edit` event when the
  // controller's edits change, a `conversation` event per message, and a `mapping` event per stored or changed mapping.
  // Stage, audit, and edit events are coalesced so a burst reads the case once; conversation and mapping events go
  // straight into their reducers.
  // The stream replays the whole history on connect, and the reducers drop what they already hold.
  const id = kase?.deal.id;
  useEffect(() => {
    if (!id) return;
    let closed = false;
    // The whole conversation once, for a page opened late; the stream's replay brings the same messages.
    const load = () => api.conversation(id)
      .then((messages) => { if (!closed) dispatchConversation({ type: "load", deal: id, messages }); })
      .catch(() => { if (!closed) dispatchConversation({ type: "loadFailed", deal: id }); });
    load();
    const es = new EventSource(`${API_URL}/deals/${id}/stream`);
    const connected = Date.now();
    const live = (at: string) => new Date(at).getTime() >= connected - HISTORY_SLACK_MS;
    let firstStage = true;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const bump = () => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => { timer = null; refresh(); }, 150);
    };
    const parse = <T,>(e: Event): T | null => {
      try { return JSON.parse((e as MessageEvent<string>).data) as T; } catch { return null; }
    };
    es.addEventListener("stage", (e) => {
      const body = parse<{ stage: Stage }>(e);
      if (body && !canStart(body.stage)) setStarting(false);
      // Back at `new` (a reset, from this page or another): the deal holds no mappings, and the conversation is
      // read again, as a reset sends no event of its own.
      // The first stage event is the stream's own opening line, already covered by the read above.
      if (body?.stage === "new" && !firstStage) { dispatchMapping({ type: "reset", deal: id }); load(); }
      firstStage = false;
      bump();
    });
    es.addEventListener("audit", bump);
    // A job started or stopped: the runner ends about a second after the Reviewer's hand-off, with no stage change.
    es.addEventListener("run", bump);
    // An edit, a reason, or an undo made elsewhere (another window, the API): read the case again.
    es.addEventListener("edit", bump);
    es.addEventListener("conversation", (e) => {
      const message = parse<ConversationMessage>(e);
      if (!message) return;
      dispatchConversation({ type: "message", message, receivedAt: Date.now() });
      // A policy an answer just taught: the console says so where the controller is looking.
      if (message.policy_id && live(message.at)) {
        const note: LearnedNotice = { id: `learned_${message.id}`, deal_id: message.deal_id, from: message.from, policy_id: message.policy_id, text: message.text, at: message.at };
        setLearned((n) => (n.some((x) => x.id === note.id) ? n : [...n, note]));
      }
    });
    // A question to the controller opened: a toast on every page, and in the Mac app a native notification. The
    // stream replays the open questions when it connects; those are history (the Case badge counts them), not news.
    es.addEventListener("notify", (e) => {
      const notice = parse<Notice>(e);
      if (!notice?.id || !live(notice.at)) return;
      setNotices((n) => (n.some((x) => x.id === notice.id || (notice.item_id && x.item_id === notice.item_id)) ? n : [...n, notice]));
      try { window.stochastic?.notify?.({ title: notice.title, body: notice.body }); } catch { /* the bridge is optional */ }
    });
    es.addEventListener("mapping", (e) => {
      const mapping = parse<MappingEvent>(e);
      if (mapping) dispatchMapping({ type: "upsert", deal: id, mapping, receivedAt: Date.now() });
    });
    return () => { closed = true; es.close(); if (timer) clearTimeout(timer); };
  }, [id, refresh]);

  // The agent states read "talking" for a moment after a message; the clock ticks only to end that moment.
  useEffect(() => {
    const t0 = Date.now();
    const end = nextTalkEnd(conversation, t0);
    if (end === null) return;
    const t = setTimeout(() => setNow(Date.now()), end - t0 + 20);
    return () => clearTimeout(t);
  }, [conversation, now]);

  const startRun = useCallback(async (runId?: string) => {
    const target = runId ?? dealId.current;
    if (!target) return;
    setStarting(true);
    try {
      await api.start(target);
    } catch (e) {
      setStarting(false);
      throw e;
    }
    // The stream's stage event ends `starting`; a read now covers a stream that is reconnecting.
    void refresh();
  }, [refresh]);

  // A start whose stage event never came (the stream down) does not hold the buttons forever.
  useEffect(() => {
    if (!starting) return;
    const t = setTimeout(() => setStarting(false), 15_000);
    return () => clearTimeout(t);
  }, [starting]);

  const resetOnce = useCallback(async (keepMemory: boolean) => {
    // The job runner finishes about a second after the Reviewer's hand-off (the paced wait after a stored result), and
    // the gateway refuses a reset until then (409). A reset clicked in that second waits for it instead of failing.
    let res: Awaited<ReturnType<typeof api.reset>>;
    for (let attempt = 0; ; attempt++) {
      try {
        res = await api.reset(keepMemory);
        break;
      } catch (e) {
        if (attempt >= 8 || !(e instanceof Error) || !/run is in progress/i.test(e.message)) throw e;
        await new Promise((r) => setTimeout(r, 700));
      }
    }
    dispatchConversation({ type: "reset" });
    dispatchMapping({ type: "reset" });
    setNotices([]); setLearned([]); setDeciding(null);
    return res;
  }, []);

  const reset = useCallback(async (keepMemory: boolean) => {
    await resetOnce(keepMemory);
    await refresh();
  }, [refresh, resetOnce]);

  const runDemo = useCallback(async () => {
    setStarting(true);
    try {
      const { kept_deals: kept = [] } = await resetOnce(false);
      // The demo deal is the one the reset reseeded: every deal but the ones it kept. A gateway that does not say
      // which it kept has one deal from the filings, the demo deal.
      const list = await api.deals();
      const demo = (kept.length ? list.find((d) => !kept.includes(d.id)) : undefined)
        ?? list.find((d) => d.data_source === "filings") ?? list[0];
      if (!demo) throw new Error("The gateway has no deal to run.");
      dealId.current = demo.id;
      writePicked(demo.id);
      await api.start(demo.id, "demo");
    } catch (e) {
      setStarting(false);
      throw e;
    }
    void refresh();
  }, [refresh, resetOnce]);

  // Messages and mappings are shown only for the deal they belong to, so a deal switch never shows the last one's.
  const messages = useMemo(() => (conversation.deal === id ? conversation.messages : []), [conversation, id]);
  const liveMappings = live.deal === id ? live : emptyMappings;
  const agents = useMemo(
    () => readAgentStates(conversation.deal === id ? conversation : emptyConversation, now),
    [conversation, id, now],
  );
  const caseMappings = kase?.mappings;
  const mappings = useMemo(() => mergeMappings(caseMappings ?? [], liveMappings), [caseMappings, liveMappings]);
  const running = runInFlight(starting, kase);

  return (
    <Ctx.Provider value={{
      deals, kase, health, audit, error, loading, refresh, reloadDeals, select, stageSince: stageSeen?.at ?? 0,
      messages, received: conversation.received, agentStates: agents,
      conversationLoaded: conversation.deal === id && conversation.loaded,
      conversationSupported: conversation.deal === id && conversation.supported, liveMappings, mappings, now, startRun, starting, reset, running,
      runDemo, notices, learned, dismiss, learnedAt: learned.length ? Date.parse(learned[learned.length - 1].at) || 1 : 0, focus, requestFocus, deciding,
    }}>
      {children}
    </Ctx.Provider>
  );
}

export function useDeal(): DealData {
  const v = useContext(Ctx);
  if (!v) throw new Error("useDeal must be used inside DealProvider");
  return v;
}
