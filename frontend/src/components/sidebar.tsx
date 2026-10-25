"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useDeal } from "@/lib/deal-context";
import { recordedModelName } from "@/lib/format";
import type { BackendStatus, Case, Health } from "@/lib/types";
import { NavIcon, type NavIconName } from "./icons";
import { StochasticMark } from "./stochastic-mark";
import { Label } from "./ui";

const PAGES: { href: string; label: string; icon: NavIconName }[] = [
  { href: "/", label: "Dashboard", icon: "dashboard" },
  { href: "/case", label: "Case", icon: "case" },
  { href: "/mapping", label: "Mapping", icon: "mapping" },
  { href: "/agents", label: "Agents", icon: "agents" },
  { href: "/log", label: "Log", icon: "log" },
  // Review is the last step: the books are edited and approved there once the agents are done.
  { href: "/review", label: "Review", icon: "review" },
];

type Theme = "teal" | "blue" | "violet";

/** Each page's tint in v3: the Case is the Preparer's blue, the Log the Reviewer's violet, the rest the Mapper's teal. */
export function themeOf(path: string): Theme {
  if (path.startsWith("/case")) return "blue";
  if (path.startsWith("/log")) return "violet";
  return "teal";
}

/** The agents' model, the card's headline on every run. The line under it says what produced this run's text. */
const AGENT_MODEL = "Claude Haiku 5.5";

/** Plain words for the line under the headline, so a judge reads what produced the agent text without a tooltip. */
const BACKEND_WORDS: Record<string, string> = {
  droid: "live via Droid",
  anthropic: "live via the Claude API",
  replay: "recorded run",
  scripted: "scripted rules this run",
};

/** Which backend produced the agent output, from GET /health. A run that fell back says so on its own entry: its
 * `backend` is not the `asked` one. When one of the last three roles fell back, the card names that run (the weaker
 * one), not the better one. Otherwise it names the newest run. Runs are compared with the backend each one asked
 * for, so the demo paces (replay or scripted, whatever is configured) and the seeded cases' scripted runs are not
 * shown as a fallback. */
function producedBy(health: Health | null, kase: Case | null): { produced: string | null; fellBack: string | null; env: string } | null {
  const status = health?.backend ?? kase?.backend;
  if (!status) return null;
  const roles = status.last_runs.filter((r) => r.role !== "runner");
  const last = roles[roles.length - 1];
  const fell = roles.slice(-3).findLast((r) => r.asked && r.backend !== r.asked);
  const shown = fell ?? last;
  // With no run since the API started, nothing fell back: the card names the case's own backend, or no backend.
  return { produced: shown?.backend ?? kase?.verdict?.backend ?? null, fellBack: fell?.asked ?? null, env: status.configured };
}

/** The model a replayed run recorded, named for the card ("Claude Haiku 5.5"), from the newest replay run on /health or
 * the case, or from the backend info itself. Null unless the replay plays a recorded Haiku run. */
function recordedModel(...statuses: (BackendStatus | undefined)[]): string | null {
  for (const status of statuses) {
    if (!status) continue;
    const run = status.last_runs.findLast((r) => r.role !== "runner" && r.backend === "replay");
    const name = recordedModelName(run) ?? recordedModelName({ backend: "replay", model: status.model, recorded: status.recorded });
    if (name) return name;
  }
  return null;
}

/** The model card: what produced the agent text, and where the record lives (Tiger Cloud or memory). */
function ModelCard() {
  const { health, kase } = useDeal();
  const by = producedBy(health, kase);
  const store = health?.store;
  if (!by) return null;
  // The headline is always the agents' model; the line under it names this run's backend, so a scripted run still
  // reads "scripted rules this run" there.
  const model = by.produced === "replay" ? recordedModel(health?.backend, kase?.backend) : null;
  // The line under the headline is the record's status. A run that was not a model's (scripted rules, or a fallback)
  // still says so there; what produced a model run is in the tooltip.
  const runWord = model ? "recorded run" : by.produced ? BACKEND_WORDS[by.produced] ?? by.produced : null;
  const words = { title: AGENT_MODEL, sub: by.produced === "scripted" && !model ? runWord : null };
  const tiger = store?.kind === "postgres";
  const storeWord = !store ? null : tiger ? (store.last_error ? "Tiger Cloud, retrying" : "Tiger Cloud connected") : "in memory";
  const healthy = !by.fellBack && tiger && !store?.last_error;
  const title = [
    `${runWord ? `This run: ${runWord}. ` : ""}Configured: ${by.env}. Fallback: ${health?.backend.fallback ?? kase?.backend.fallback}.${by.fellBack ? ` The last run fell back from ${by.fellBack}.` : ""}`,
    tiger
      ? `Postgres on Tiger Cloud, schema ${store?.schema}, ledger ${store?.ledger}. ${store?.pending ? `${store.pending} writes queued.` : "Every write is saved."}${store?.last_error ? ` Last error: ${store.last_error}` : ""}`
      : store?.fallback_reason ? `Running in memory: ${store.fallback_reason}` : "The record is kept in memory and resets when the API restarts.",
  ].join(" ");
  return (
    <div className="flex w-full items-center gap-[8px] rounded-[8px] bg-mint p-[10px]" title={title}>
      <div className="flex min-w-0 flex-1 flex-col gap-[2px]">
        <span className="truncate text-[13px] font-semibold text-forest">{words.title}</span>
        <span className="truncate text-[11px] text-slate">
          {[by.fellBack ? `fell back from ${by.fellBack}` : words.sub, storeWord].filter(Boolean).join(" · ")}
        </span>
      </div>
      <span className={`size-[8px] shrink-0 rounded-full ${healthy ? "bg-clear" : "bg-escalation-bar"}`} aria-hidden="true" />
    </div>
  );
}

/** The selected deal's own counts, for a gateway without the cross-deal counters. Human answers: the flags answered
 * here, plus the earlier answers behind each policy. Edits: the ones saved with a reason (D19). */
function dealCounts(kase: Case | null): { human_answers: number; policies: number; edits: number } {
  return {
    human_answers: new Set([
      ...(kase?.flags.filter((f) => f.answer).map((f) => f.id) ?? []),
      ...(kase?.policies.map((p) => p.learned_from) ?? []),
    ]).size,
    policies: kase?.policies.length ?? 0,
    edits: kase?.edits?.filter((e) => e.status === "reasoned").length ?? 0,
  };
}

/** What the agents learn from, counted across every deal (GET /health `memory_counts`, the same as GET /memory/counts),
 * else the selected deal's counts. /health is read again after every answer, edit, and reason, so the counters move. */
function Learning() {
  const { kase, health, learnedAt } = useDeal();
  const counts = health?.memory_counts ?? dealCounts(kase);
  const rows: [string, number][] = [["Human answers", counts.human_answers], ["Policies", counts.policies], ["Edits", counts.edits]];
  return (
    <div className="flex w-full flex-col gap-[4px]">
      <Label>Always learning from</Label>
      {rows.map(([name, n]) => (
        // The Policies row pulses when an answer just taught one; the key restarts the pulse for the next.
        <div
          key={name === "Policies" && learnedAt ? `${name}-${learnedAt}` : name}
          data-counter={name}
          className={`flex w-full items-center gap-[8px] rounded-[8px] border border-line bg-white px-[10px] py-[7px] ${name === "Policies" && learnedAt ? "counter-pulse" : ""}`}
        >
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
  // The questions that hold the agents or wait on the controller now: the Case item's badge.
  const asks = kase?.open_flags.length ?? 0;
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
            const badge = p.href === "/case" ? asks : 0;
            return (
              <Link
                key={p.href}
                href={p.href}
                aria-current={on ? "page" : undefined}
                title={badge ? `${badge} ${badge === 1 ? "question needs" : "questions need"} you` : undefined}
                className={`flex w-full items-center gap-[10px] rounded-[8px] px-[10px] py-[9px] text-[14px] transition-colors duration-150 ${
                  on ? "bg-forest font-semibold text-white" : "font-medium text-body hover:bg-mint/60 [&_svg]:text-forest"
                }`}
              >
                <NavIcon name={p.icon} />
                <span className="flex-1">{p.label}</span>
                {badge ? (
                  <span
                    data-badge=""
                    aria-hidden="true"
                    className="flex h-[20px] min-w-[20px] items-center justify-center rounded-full bg-escalation-bar px-[6px] font-mono text-[11px] font-semibold text-white"
                  >
                    {badge}
                  </span>
                ) : null}
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
