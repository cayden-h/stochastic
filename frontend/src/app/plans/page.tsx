"use client";

import { useState } from "react";
import { PlanTable } from "@/components/plan-table";
import { Button, Shape } from "@/components/ui";
import { api } from "@/lib/api";
import { useDeal } from "@/lib/deal-context";
import { clock, planLetter } from "@/lib/format";

/** Plans: compare plans and decide. This is the hero screen. */
export default function Plans() {
  const { plans, items, audit, clauses, refresh } = useDeal();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const rec = items.find((i) => i.type === "recommend");
  const recommendedId = typeof rec?.payload.recommended_plan === "string" ? rec.payload.recommended_plan : null;
  const recommended = plans.find((p) => p.id === recommendedId);
  const denied = audit.rows.find((r) => r.result === "DENIED" && r.action === "post_plan");

  const blocked = plans.filter((p) => p.status === "blocked").map(planLetter);
  const clear = plans.filter((p) => p.status === "ok").map(planLetter);
  const verb = (xs: string[]) => (xs.length > 1 ? "are" : "is");
  const headline = [
    blocked.length ? `Plan ${blocked.join(" and ")} ${verb(blocked)} blocked.` : "No plan is blocked.",
    clear.length ? `Plan ${clear.join(" and ")} ${verb(clear)} clear.` : "",
  ].join(" ");

  const e3 = items.find((i) => i.escalation === "E3");
  const e3Row = audit.rows.find((r) => r.action === "answer" && r.target === e3?.id);
  const assumption =
    e3?.answer === "equity" ? `Assumes the preferred does not count as debt (your answer at ${e3Row ? clock(e3Row.at) : "-"}).`
    : e3?.answer === "debt" ? `Assumes the preferred counts as debt (your answer at ${e3Row ? clock(e3Row.at) : "-"}).`
    : "Waiting for your answer on the Desk. Plans may change.";

  async function act(fn: () => Promise<unknown>) {
    setBusy(true); setNote(null);
    try { await fn(); await refresh(); } catch (e) { setNote(e instanceof Error ? e.message : "Action failed"); }
    finally { setBusy(false); }
  }

  const decided = rec && rec.state !== "PROPOSED";

  return (
    <div className="mx-auto flex max-w-[1120px] flex-col gap-6 pt-6 pb-8">
      <header className="flex flex-col gap-2">
        <h1 className="font-serif text-[40px] leading-[48px] font-medium">{headline}</h1>
        <p className="text-muted">Raise $60M. {assumption}</p>
      </header>

      <PlanTable plans={plans} recommendedId={recommendedId} denied={denied} clauses={clauses} items={items} />

      {note ? <p role="alert" className="rounded-chip bg-denied-tint px-4 py-3 font-semibold text-denied">{note}</p> : null}

      {rec && !decided ? (
        <div className="flex items-center gap-4">
          <p className="flex-1">
            Agent suggests plan {recommended ? planLetter(recommended) : "-"}.{" "}
            {typeof rec.payload.summary === "string" ? rec.payload.summary : ""}
          </p>
          <Button kind="link" disabled={busy} onClick={() => act(() => api.reject(rec.id, "Rejected by the reviewer."))}>Reject</Button>
          <Button disabled={busy} onClick={() => act(() => api.reject(rec.id, "Changes requested by the reviewer."))}>Ask for changes</Button>
          <Button kind="primary" disabled={busy} onClick={() => act(() => api.approve(rec.id))}>
            Approve plan {recommended ? planLetter(recommended) : ""}
          </Button>
        </div>
      ) : null}

      {decided ? (
        <p className={`flex items-center gap-2 font-semibold ${rec.state === "POSTED" ? "text-clear" : "text-denied"}`}>
          <Shape kind={rec.state === "POSTED" ? "check" : "cross"} />
          {rec.state === "POSTED" ? "Approved and posted to the record." : `Not approved. ${rec.reject_reason ?? ""}`}
        </p>
      ) : null}

      <p className="font-mono text-[14px] leading-5 text-muted">
        Reconstruction from public filings. Numbers on this prototype are illustrative.
      </p>
    </div>
  );
}
