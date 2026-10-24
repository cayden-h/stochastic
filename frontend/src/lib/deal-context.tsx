"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { API_URL, api } from "./api";
import type { AuditResponse, Case, Deal, Health } from "./types";

interface DealData {
  deals: Deal[];
  kase: Case | null;
  health: Health | null;
  audit: AuditResponse;
  error: LoadError | null;
  loading: boolean;
  /** When this session saw the current stage begin, in ms; 0 when it was already the stage on first load. */
  stageSince: number;
  /** Reads the case again. True when this read, or a later one, committed fresh data. */
  refresh: () => Promise<boolean>;
  /** Make another deal the current one (the Dashboard rows and a new upload). */
  select: (id: string) => Promise<boolean>;
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
  const [deals, setDeals] = useState<Deal[]>([]);
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

  const refresh = useCallback(async (): Promise<boolean> => {
    const mine = ++seq.current;
    try {
      // The list is read every time: a reset drops uploaded deals, and the current one must fall back to the demo deal.
      const list = await api.deals();
      if (!list.some((d) => d.id === dealId.current)) dealId.current = list[0]?.id ?? null;
      const id = dealId.current;
      if (!id) throw new NoDeal();
      const [c, h, a] = await Promise.all([api.case(id), api.health(), api.audit(id)]);
      if (mine < committed.current) return true;  // a later read already put newer data on screen
      if (id !== dealId.current) return false;    // the controller switched deals meanwhile; that read will commit
      committed.current = mine;
      setDeals(list); setCase(c); setHealth(h); setAudit(a);
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

  const select = useCallback(async (id: string) => {
    dealId.current = id;
    return refresh();
  }, [refresh]);

  // The first read, from a timer callback so the effect body itself sets no state (react-hooks/set-state-in-effect).
  useEffect(() => {
    const t = setTimeout(refresh, 0);
    return () => clearTimeout(t);
  }, [refresh]);

  // Live updates: a `stage` event on every stage change and an `audit` event on every new log row.
  // Events are coalesced so a burst of rows refreshes once.
  const id = kase?.deal.id;
  useEffect(() => {
    if (!id) return;
    const es = new EventSource(`${API_URL}/deals/${id}/stream`);
    let timer: ReturnType<typeof setTimeout> | null = null;
    const bump = () => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => { timer = null; refresh(); }, 150);
    };
    es.addEventListener("stage", bump);
    es.addEventListener("audit", bump);
    return () => { es.close(); if (timer) clearTimeout(timer); };
  }, [id, refresh]);

  return <Ctx.Provider value={{ deals, kase, health, audit, error, loading, refresh, select, stageSince: stageSeen?.at ?? 0 }}>{children}</Ctx.Provider>;
}

export function useDeal(): DealData {
  const v = useContext(Ctx);
  if (!v) throw new Error("useDeal must be used inside DealProvider");
  return v;
}
