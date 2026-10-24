"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { API_URL, api } from "./api";
import type { AuditResponse, Case, Health } from "./types";

interface DealData {
  kase: Case | null;
  health: Health | null;
  audit: AuditResponse;
  error: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
}

const emptyAudit: AuditResponse = { chain_valid: true, rows: [] };
const Ctx = createContext<DealData | null>(null);

/** Reads the case in one call and refreshes on every stream event. The console never computes a number. */
export function DealProvider({ children }: { children: React.ReactNode }) {
  const [kase, setCase] = useState<Case | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [audit, setAudit] = useState<AuditResponse>(emptyAudit);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const dealId = useRef<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      if (!dealId.current) {
        const deals = await api.deals();
        dealId.current = deals[0]?.id ?? null;
      }
      const id = dealId.current;
      if (!id) throw new Error("The gateway has no deal loaded.");
      const [c, h, a] = await Promise.all([api.case(id), api.health(), api.audit(id)]);
      setCase(c); setHealth(h); setAudit(a);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cannot reach the gateway API");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

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

  return <Ctx.Provider value={{ kase, health, audit, error, loading, refresh }}>{children}</Ctx.Provider>;
}

export function useDeal(): DealData {
  const v = useContext(Ctx);
  if (!v) throw new Error("useDeal must be used inside DealProvider");
  return v;
}
