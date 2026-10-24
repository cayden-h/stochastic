"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ACTOR } from "@/lib/api";
import { useDeal } from "@/lib/deal-context";
import { ActorChip, Mono, Shape } from "./ui";

const TABS = [
  { href: "/", label: "Case" },
  { href: "/log", label: "Log" },
];

/** Which backend produced the agent output. Shown on every screen, from GET /health. */
export function BackendBadge() {
  const { health, kase } = useDeal();
  const status = health?.backend ?? kase?.backend;
  if (!status) return null;
  const last = status.last_runs[status.last_runs.length - 1];
  const produced = kase?.verdict?.backend ?? last?.backend ?? null;
  const fellBack = produced !== null && produced !== status.configured;
  return (
    <span className="inline-flex items-center gap-2 rounded-chip border border-rule bg-card px-2 py-1" title={`Configured: ${status.configured}. Fallback: ${status.fallback}.`}>
      <span className="text-code"><Shape kind="square" size={12} /></span>
      <span className="text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] text-code">
        {produced ?? status.configured}
      </span>
      {fellBack ? <Mono>fell back from {status.configured}</Mono> : null}
    </span>
  );
}

/** Where the record lives: Postgres on Tiger Cloud, or memory. From GET /health. */
export function StoreBadge() {
  const { health } = useDeal();
  const store = health?.store;
  if (!store) return null;
  const tiger = store.kind === "postgres";
  const title = tiger
    ? `Postgres on Tiger Cloud, schema ${store.schema}, ledger ${store.ledger}. ${store.pending ? `${store.pending} writes queued.` : "Every write is saved."}${store.last_error ? ` Last error: ${store.last_error}` : ""}`
    : store.fallback_reason ? `Tiger Cloud was not reachable at start: ${store.fallback_reason}` : "The record is kept in memory and resets when the API restarts.";
  return (
    <span className="inline-flex items-center gap-2 rounded-chip border border-rule bg-card px-2 py-1" title={title}>
      <span className={tiger && !store.last_error ? "text-clear" : "text-muted"}><Shape kind="circle" size={12} /></span>
      <span className="text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] text-code">
        {tiger ? "Tiger Cloud" : "In memory"}
      </span>
      {store.fallback_reason ? <Mono>Tiger unreachable</Mono> : null}
      {tiger && store.last_error ? <Mono>retrying</Mono> : null}
    </span>
  );
}

export function TopBar() {
  const path = usePathname();
  const { kase } = useDeal();
  return (
    <header className="border-b border-hairline bg-card">
      <div className="mx-auto flex max-w-[1120px] flex-wrap items-center gap-x-6 gap-y-3 px-4 py-4">
        <span className="font-serif text-[26px] leading-8 font-medium">Stochastic</span>
        <span className="hidden text-muted md:inline">{kase?.deal.name ?? ""}</span>
        <span className="flex-1" />
        <nav className="flex items-center gap-6">
          {TABS.map((t) => {
            const on = path === t.href;
            return (
              <Link
                key={t.href}
                href={t.href}
                aria-current={on ? "page" : undefined}
                className={`border-b-2 py-1 font-semibold ${on ? "border-ink text-ink" : "border-transparent text-muted hover:text-ink"}`}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>
        <BackendBadge />
        <StoreBadge />
        <ActorChip actor={ACTOR} />
      </div>
    </header>
  );
}
