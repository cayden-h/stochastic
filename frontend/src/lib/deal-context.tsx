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
  /** Reads the case again. True when this read committed fresh data. */
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
  // number; only the latest one may commit, so a slow, stale response never overwrites a newer state.
  const seq = useRef(0);

  const refresh = useCallback(async (): Promise<boolean> => {
    const mine = ++seq.current;
    try {
      // The list is read every time: a reset drops uploaded deals, and the current one must fall back to the demo deal.
      const list = await api.deals();
      if (mine !== seq.current) return false;
      if (!list.some((d) => d.id === dealId.current)) dealId.current = list[0]?.id ?? null;
      const id = dealId.current;
      if (!id) throw new NoDeal();
      const [c, h, a] = await Promise.all([api.case(id), api.health(), api.audit(id)]);
      if (mine !== seq.current || id !== dealId.current) return false;
      setDeals(list); setCase(c); setHealth(h); setAudit(a);
      setError(null);
      return true;
    } catch (e) {
      if (mine !== seq.current) return false;
      setError(e instanceof NoDeal ? { kind: "no_deal", message: e.message } : { kind: "unreachable", message: e instanceof Error ? e.message : "Cannot reach the gateway API" });
      return false;
    } finally {
      if (mine === seq.current) setLoading(false);
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

  return <Ctx.Provider value={{ deals, kase, health, audit, error, loading, refresh, select }}>{children}</Ctx.Provider>;
}

export function useDeal(): DealData {
  const v = useContext(Ctx);
  if (!v) throw new Error("useDeal must be used inside DealProvider");
  return v;
}
