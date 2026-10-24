"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { API_URL, api } from "./api";
import type { AuditResponse, Clause, Deal, Fact, Plan, WorkItem } from "./types";

interface DealData {
  deal: Deal | null;
  items: WorkItem[];
  plans: Plan[];
  facts: Fact[];
  clauses: Clause[];
  audit: AuditResponse;
  error: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
}

const empty: AuditResponse = { chain_valid: true, rows: [] };
const Ctx = createContext<DealData | null>(null);

export function DealProvider({ children }: { children: React.ReactNode }) {
  const [deal, setDeal] = useState<Deal | null>(null);
  const [items, setItems] = useState<WorkItem[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [facts, setFacts] = useState<Fact[]>([]);
  const [clauses, setClauses] = useState<Clause[]>([]);
  const [audit, setAudit] = useState<AuditResponse>(empty);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const deals = await api.deals();
      const d = deals[0] ?? null;
      setDeal(d);
      if (d) {
        const [i, p, f, c, a] = await Promise.all([
          api.items(d.id), api.plans(d.id), api.facts(d.id), api.clauses(d.id), api.audit(d.id),
        ]);
        setItems(i); setPlans(p); setFacts(f); setClauses(c); setAudit(a);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cannot reach the gateway API");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // Live updates: the gateway sends one event per new audit row.
  useEffect(() => {
    if (!deal) return;
    const es = new EventSource(`${API_URL}/deals/${deal.id}/stream`);
    es.addEventListener("audit", () => { refresh(); });
    return () => es.close();
  }, [deal?.id, refresh]);

  return (
    <Ctx.Provider value={{ deal, items, plans, facts, clauses, audit, error, loading, refresh }}>
      {children}
    </Ctx.Provider>
  );
}

export function useDeal(): DealData {
  const v = useContext(Ctx);
  if (!v) throw new Error("useDeal must be used inside DealProvider");
  return v;
}
