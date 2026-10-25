"use client";

import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import {
  AGENT_KEYS, CONTROLLER, GATEWAY, type AgentKey, type AgentState, type ConversationEvent, sceneKey, settle,
} from "@/lib/conversation";
import type { AgentHouseHandle } from "./agent-house";

// The conversation itself comes from deal-context (one stream per page, GET /conversation on load); this file only
// plays it in the house.

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Where a message goes in the house: an agent's room, out to the controller, or nowhere (the gateway's own notes). */
function place(actor: string): AgentKey | "controller" | "gateway" {
  return sceneKey(actor) ?? (actor === CONTROLLER ? "controller" : "gateway");
}

/**
 * Plays the conversation in the house as it arrives. What was already on the record when the page opened is shown at
 * once, settled; every new line is played in turn: the speaker talks (or asks), a note flies to the listener, the
 * listener takes it, and then everyone settles where the record says they are. The feed shows a line as it is
 * spoken, so the scene and the feed never disagree. Lines that arrive in a burst (the scripted backend writes a
 * whole stage in one second) are paced, a little faster when many are waiting.
 */
export function useConversationPlayer(opts: {
  events: ConversationEvent[];
  stage: string | undefined;
  /** False until the case has loaded, so the record already there is not replayed as new. */
  loaded: boolean;
  dealId: string | undefined;
  house: RefObject<AgentHouseHandle | null>;
  reducedMotion: boolean;
  /** False while something else drives the house (the `?demo=1` loop): the feed still fills, the agents are left be. */
  drive?: boolean;
}) {
  const { events, stage, loaded, dealId, house, reducedMotion, drive = true } = opts;
  const [shown, setShown] = useState<Set<string>>(() => new Set());
  const latest = useRef({ events, stage, reducedMotion, drive });
  const run = useRef({ deal: "" as string | undefined, played: new Set<string>(), busy: false, busyGen: -1, gen: 0, applied: new Map<AgentKey, string>() });

  useEffect(() => { latest.current = { events, stage, reducedMotion, drive }; });

  const put = useCallback((k: AgentKey, state: AgentState, text: string, o?: { to?: string }) => {
    if (!latest.current.drive) return;
    const sig = `${state}|${text}|${o?.to ?? ""}`;
    if (run.current.applied.get(k) === sig) return;
    run.current.applied.set(k, sig);
    house.current?.setState(k, state, text, o);
  }, [house]);

  const settleTo = useCallback((list: ConversationEvent[], withStage: boolean) => {
    const s = settle(list, withStage ? latest.current.stage : undefined);
    for (const k of AGENT_KEYS) put(k, s[k].state, s[k].text);
  }, [put]);

  const pump = useCallback(async () => {
    const r = run.current;
    if (r.busy && r.busyGen === r.gen) return;
    const gen = r.gen;
    r.busy = true; r.busyGen = gen;
    try {
      for (;;) {
        const { events: all, reducedMotion: still } = latest.current;
        const next = all.find((e) => !r.played.has(e.id));
        if (!next || gen !== r.gen) break;
        r.played.add(next.id);
        setShown(new Set(r.played));
        const playedList = all.filter((e) => r.played.has(e.id));
        if (still) { settleTo(playedList, false); continue; }
        const waiting = all.filter((e) => !r.played.has(e.id)).length;
        const fast = waiting > 8;
        const from = sceneKey(next.from), to = sceneKey(next.to);
        const target = place(next.to);
        if (from) put(from, next.kind === "question" ? "asking" : "talking", next.text, { to: target });
        const fromGateway = next.from === GATEWAY;
        if ((from || next.from === CONTROLLER) && target !== "gateway" && place(next.from) !== target) {
          await house.current?.message(place(next.from), target, fast ? 0.6 : 0.95);
        } else {
          await sleep(fromGateway ? (fast ? 150 : 350) : fast ? 500 : 900);
        }
        if (gen !== r.gen) break;
        if (to && to !== from && fromGateway) {
          // the gateway's notes (tool results, checks) show on the agent without a fuss
          if (next.kind === "handoff") house.current?.hop(to);
          put(to, "working", next.text);
        } else if (to && to !== from) {
          house.current?.hop(to);
          const takes = next.kind === "answer" ? `Got it: ${next.text}` : next.text;
          put(to, next.kind === "answer" ? "talking" : "working", takes, { to: place(next.from) });
        }
        await sleep(fromGateway ? (fast ? 100 : 350) : fast ? 250 : 700);
        if (gen !== r.gen) break;
        settleTo(playedList, false);
      }
      if (gen === r.gen) settleTo(latest.current.events.filter((e) => r.played.has(e.id)), true);
    } finally {
      if (r.busyGen === gen) r.busy = false;
    }
    // Lines that arrive while one plays are picked up by the loop, which reads the latest list on every turn.
  }, [house, put, settleTo]);

  // First load of a deal: everything already recorded is history, shown at once and settled.
  useEffect(() => {
    if (!loaded || !dealId) return;
    const r = run.current;
    if (r.deal === dealId) {
      void pump();
      // The first pass's timer below can be cleared before it fires (the events change again at once, or a dev
      // double mount), which left the record already played but never shown: an empty feed and timeline after a
      // finished run. Show whatever is played but not yet on screen.
      const t = setTimeout(() => setShown((s) => (s.size === r.played.size ? s : new Set(r.played))), 0);
      return () => clearTimeout(t);
    }
    r.deal = dealId; r.gen++; r.applied.clear();
    r.played = new Set(latest.current.events.map((e) => e.id));
    const t = setTimeout(() => {
      setShown(new Set(r.played));
      settleTo(latest.current.events, true);
    }, 0);
    return () => clearTimeout(t);
  }, [loaded, dealId, events, pump, settleTo]);

  // A stage change with no new line (a run that stopped, the approval waiting) still moves the agents.
  useEffect(() => {
    const r = run.current;
    if (!loaded || (r.busy && r.busyGen === r.gen) || r.deal !== dealId) return;
    const t = setTimeout(() => settleTo(latest.current.events.filter((e) => r.played.has(e.id)), true), 0);
    return () => clearTimeout(t);
  }, [stage, loaded, dealId, settleTo]);

  // Leaving the page stops the player: a new generation ends a playing loop at its next step, and a replay that was
  // about to start does not. (The house itself is disposed by AgentHouse.)
  const replayTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    const r = run.current;
    return () => {
      r.gen++;
      if (replayTimer.current) clearTimeout(replayTimer.current);
    };
  }, []);

  /** Play this deal's whole conversation again from the start, for the pitch. */
  const replay = useCallback(() => {
    const r = run.current;
    r.gen++; r.played = new Set(); r.applied.clear();
    setShown(new Set());
    for (const k of AGENT_KEYS) put(k, "idle", "");
    if (replayTimer.current) clearTimeout(replayTimer.current);
    replayTimer.current = setTimeout(() => { replayTimer.current = null; void pump(); }, 400);
  }, [pump, put]);

  /** The scene was made again (a new canvas): send it every agent's state afresh. */
  const resync = useCallback(() => {
    const r = run.current;
    r.applied.clear();
    if (!(r.busy && r.busyGen === r.gen)) settleTo(latest.current.events.filter((e) => r.played.has(e.id)), true);
  }, [settleTo]);

  return { shown: events.filter((e) => shown.has(e.id)), replay, resync };
}
