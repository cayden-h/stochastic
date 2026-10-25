"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useDeal } from "@/lib/deal-context";
import type { Case, Health } from "@/lib/types";
import { NavIcon, type NavIconName } from "./icons";
import { StochasticMark } from "./stochastic-mark";
import { Label } from "./ui";

const PAGES: { href: string; label: string; icon: NavIconName }[] = [
  { href: "/", label: "Dashboard", icon: "dashboard" },
  { href: "/case", label: "Case", icon: "case" },
  { href: "/review", label: "Review", icon: "review" },
  { href: "/mapping", label: "Mapping", icon: "mapping" },
  { href: "/agents", label: "Agents", icon: "agents" },
  { href: "/log", label: "Log", icon: "log" },
];

type Theme = "teal" | "blue" | "violet";

/** Each page's tint in v3: the Case is the Preparer's blue, the Log the Reviewer's violet, the rest the Mapper's teal. */
export function themeOf(path: string): Theme {
  if (path.startsWith("/case")) return "blue";
  if (path.startsWith("/log")) return "violet";
  return "teal";
}

/** Plain words for the model card, so a judge reads what produced the agent text without a tooltip. */
const BACKEND_WORDS: Record<string, { title: string; sub: string }> = {
  droid: { title: "Claude via Droid", sub: "live model" },
  anthropic: { title: "Claude API", sub: "live model" },
  replay: { title: "Recorded Claude run", sub: "replay, math live" },
  scripted: { title: "Scripted rules", sub: "no model" },
};

/** Which backend produced the agent output, from GET /health. When the Mapper and the Preparer ran on different
 * backends (a fallback), the card names the one that fell back, not the better one. */
function producedBy(health: Health | null, kase: Case | null): { produced: string; configured: string } | null {
  const status = health?.backend ?? kase?.backend;
  if (!status) return null;
  const roles = status.last_runs.filter((r) => r.role !== "runner");
  const last = roles[roles.length - 1];
  const recent = roles.slice(-3).map((r) => r.backend);
  const weakest = ["scripted", "replay"].find((b) => recent.includes(b));
  return { produced: weakest ?? kase?.verdict?.backend ?? last?.backend ?? status.configured, configured: status.configured };
}

/** The model card: what produced the agent text, and where the record lives (Tiger Cloud or memory). */
function ModelCard() {
  const { health, kase } = useDeal();
  const by = producedBy(health, kase);
  const store = health?.store;
  if (!by) return null;
  const words = BACKEND_WORDS[by.produced] ?? { title: by.produced, sub: "" };
  const fellBack = by.produced !== by.configured;
  const tiger = store?.kind === "postgres";
  const storeWord = !store ? null : store.fallback_reason ? "Tiger unreachable" : tiger ? (store.last_error ? "Tiger Cloud, retrying" : "Tiger Cloud") : "in memory";
  const healthy = !fellBack && !store?.fallback_reason && !store?.last_error;
  const title = [
    `Configured: ${by.configured}. Fallback: ${health?.backend.fallback ?? kase?.backend.fallback}.`,
    tiger
      ? `Postgres on Tiger Cloud, schema ${store?.schema}, ledger ${store?.ledger}. ${store?.pending ? `${store.pending} writes queued.` : "Every write is saved."}${store?.last_error ? ` Last error: ${store.last_error}` : ""}`
      : store?.fallback_reason ? `Tiger Cloud was not reachable at start: ${store.fallback_reason}` : "The record is kept in memory and resets when the API restarts.",
  ].join(" ");
  return (
    <div className="flex w-full items-center gap-[8px] rounded-[8px] bg-mint p-[10px]" title={title}>
      <div className="flex min-w-0 flex-1 flex-col gap-[2px]">
        <span className="truncate text-[13px] font-semibold text-forest">{words.title}</span>
        <span className="truncate text-[11px] text-slate">
          {[fellBack ? `fell back from ${by.configured}` : words.sub, storeWord].filter(Boolean).join(" · ")}
        </span>
      </div>
      <span className={`size-[8px] shrink-0 rounded-full ${healthy ? "bg-clear" : "bg-escalation-bar"}`} aria-hidden="true" />
    </div>
  );
}

/** What the agents learn from. Human answers: the flags answered here, plus the earlier answers behind each policy. */
function Learning() {
  const { kase } = useDeal();
  const answers = new Set([
    ...(kase?.flags.filter((f) => f.answer).map((f) => f.id) ?? []),
    ...(kase?.policies.map((p) => p.learned_from) ?? []),
  ]).size;
  const policies = kase?.policies.length ?? 0;
  // Edits saved with a reason (D19). Until Tri's T2 adds `edits` to /case the count is 0.
  const edits = kase?.edits?.filter((e) => e.status === "reasoned").length ?? 0;
  const rows: [string, number][] = [["Human answers", answers], ["Policies", policies], ["Edits", edits]];
  return (
    <div className="flex w-full flex-col gap-[4px]">
      <Label>Always learning from</Label>
      {rows.map(([name, n]) => (
        <div key={name} className="flex w-full items-center gap-[8px] rounded-[8px] border border-line bg-white px-[10px] py-[7px]">
          <span className="flex-1 text-[13px] text-forest">{name}</span>
          <span className="font-mono text-[12px] text-forest">{n}</span>
        </div>
      ))}
    </div>
  );
}

/** The v3 sidebar: the deal, the six pages, the model, and the learning counters. 240 px wide.
 * In the Electron window the brand row moves down to clear the traffic lights (x 20, y 20). */
export function Sidebar() {
  const path = usePathname();
  const { kase } = useDeal();
  const deal = kase?.deal;
  return (
    <aside className="flex h-full w-[240px] shrink-0 flex-col gap-[24px] overflow-y-auto border-r border-line bg-white/72 px-[20px] pb-[24px]">
      <div className="drag flex shrink-0 items-center gap-[8px] pt-[24px] [html[data-electron]_&]:pt-[52px]">
        <StochasticMark size={24} className="shrink-0 text-forest" />
        <span className="font-serif text-[26px] whitespace-nowrap text-forest">Stochastic</span>
      </div>

      <div className="flex w-full flex-col gap-[4px]">
        <Label>Deal</Label>
        <span className="truncate text-[13px] text-slate" title={deal?.name}>{deal ? `${deal.platform} · ${deal.target}` : "-"}</span>
        <span className="h-[6px]" />
        <nav className="flex w-full flex-col gap-[4px]" aria-label="Pages">
          {PAGES.map((p) => {
            const on = p.href === "/" ? path === "/" : path.startsWith(p.href);
            return (
              <Link
                key={p.href}
                href={p.href}
                aria-current={on ? "page" : undefined}
                className={`flex w-full items-center gap-[10px] rounded-[8px] px-[10px] py-[9px] text-[14px] transition-colors duration-150 ${
                  on ? "bg-forest font-semibold text-white" : "font-medium text-body hover:bg-mint/60 [&_svg]:text-forest"
                }`}
              >
                <NavIcon name={p.icon} />
                {p.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex w-full flex-col gap-[6px]">
        <Label>Model</Label>
        <ModelCard />
      </div>

      <Learning />
    </aside>
  );
}
