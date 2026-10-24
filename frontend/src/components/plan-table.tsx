"use client";

import type { AuditRow, Clause, Plan, WorkItem } from "@/lib/types";
import { AuditRowView } from "./audit-log";
import { SourceChip } from "./source";
import { Tag, Verdict } from "./ui";

const COLS = "grid-cols-[280px_repeat(3,minmax(0,1fr))]";

function Cell({ plan, children, right = true }: { plan?: Plan; children: React.ReactNode; right?: boolean }) {
  const tint = plan?.status === "blocked" ? "bg-denied-tint" : "";
  return <div className={`flex min-h-11 flex-col justify-center px-4 py-2 ${right ? "items-end text-right" : ""} ${tint}`}>{children}</div>;
}

function Sub({ children }: { children: React.ReactNode }) {
  return <span className="font-mono text-[14px] leading-5 text-muted">{children}</span>;
}

export function PlanTable({
  plans, recommendedId, denied, clauses, items,
}: {
  plans: Plan[]; recommendedId: string | null; denied: AuditRow | undefined; clauses: Clause[]; items: WorkItem[];
}) {
  const shown = plans.slice(0, 3);
  const row = (label: string, cell: (p: Plan) => React.ReactNode) => (
    <div key={label} className={`grid ${COLS} items-start border-t border-hairline`}>
      <Cell right={false}><span className="text-muted">{label}</span></Cell>
      {shown.map((p) => <Cell key={p.id} plan={p}>{cell(p)}</Cell>)}
    </div>
  );

  return (
    <div className="overflow-hidden rounded-card border border-rule bg-card">
      <div className={`grid ${COLS} items-start`}>
        <Cell right={false}><span className="text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] text-muted">Measure</span></Cell>
        {shown.map((p) => (
          <div key={p.id} className={`flex min-h-24 flex-col items-start gap-2 px-4 py-2 ${p.status === "blocked" ? "bg-denied-tint" : ""}`}>
            <span className="font-semibold">{p.name}</span>
            <Verdict status={p.status} />
            {p.id === recommendedId ? <Tag>Agent suggests</Tag> : null}
          </div>
        ))}
      </div>

      {denied ? <AuditRowView row={denied} items={items} plans={plans} /> : null}

      {row("All-in cost (% a year)", (p) => <span>{p.metrics.cost_of_capital_pct?.toFixed(1)}</span>)}
      {row("Dilution (% of equity)", (p) => <span>{p.metrics.dilution_pct?.toFixed(1)}</span>)}
      {row("Net leverage at close (x)", (p) => {
        const lev = p.metrics.leverage; const lim = p.metrics.leverage_limit;
        if (lev === undefined) return <span className="text-muted">Not run</span>;
        const gap = lim !== undefined ? lev - lim : 0;
        return (
          <>
            <span className="font-semibold">{lev.toFixed(2)}</span>
            {lim !== undefined ? <Sub>of {lim.toFixed(2)} max. {gap > 0 ? `Over by ${gap.toFixed(2)}` : `Room ${(-gap).toFixed(2)}`}</Sub> : null}
          </>
        );
      })}
      {row("Breach within 5 years (%)", (p) =>
        p.metrics.breach_pct === undefined ? <span className="font-semibold text-muted">Not run</span> : (
          <>
            <span className="font-semibold">{p.metrics.breach_pct}</span>
            {p.run_id ? <Sub>{p.run_id}</Sub> : null}
          </>
        ),
      )}
      {row("Consent needed", (p) =>
        p.needs_consent ? (
          <>
            <span>{p.consent_note?.split(".")[0]}</span>
            <Sub>{p.consent_note?.split(".")[1]?.trim()}</Sub>
          </>
        ) : <span className="text-muted">None</span>,
      )}
      {row("Blocked by", (p) => {
        if (p.status !== "blocked" || !p.blocked_by) return <span className="text-muted">None</span>;
        const clause = clauses.find((c) => c.evidence.quote === p.blocked_by!.quote);
        const section = clause?.section.split(" ")[0] ?? "clause";
        return <SourceChip evidence={p.blocked_by} label={`${section}, p. ${p.blocked_by.page ?? "?"}`} />;
      })}
    </div>
  );
}

