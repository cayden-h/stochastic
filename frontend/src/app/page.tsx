"use client";

import Link from "next/link";
import { useState } from "react";
import { CombinedTable } from "@/components/combined-table";
import { FlagCard } from "@/components/flag-card";
import { Mappings } from "@/components/mappings";
import { Button, Mono, Shape } from "@/components/ui";
import { VerdictLine } from "@/components/verdict-line";
import { api } from "@/lib/api";
import { useDeal } from "@/lib/deal-context";
import { fmtX, isLearned, isLearnedTag, plural } from "@/lib/format";

/**
 * The case: one screen from one read, GET /deals/{id}/case.
 * Run, answer the flags, read the verdict, approve. The log is a link.
 */
export default function CaseScreen() {
  const { kase, refresh } = useDeal();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  if (!kase) return null;
  const { deal, stage, flags, open_flags, verdict, result, mappings, source_lines, policies, audit } = kase;
  const open = flags.filter((f) => open_flags.includes(f.id));
  const answered = flags.filter((f) => f.answer);
  const runIds = result?.run_ids_by_tool ?? {};
  const learned = mappings.filter(isLearned).length + source_lines.filter(isLearnedTag).length;
  const noFlagThisTime = Boolean(verdict) && answered.length === 0 && learned > 0;

  async function act(fn: () => Promise<unknown>) {
    setBusy(true); setNote(null);
    try { await fn(); await refresh(); } catch (e) { setNote(e instanceof Error ? e.message : "Action failed"); }
    finally { setBusy(false); }
  }

  const headline =
    stage === "new" ? (policies.length ? "Run again. The Mapper now applies what you decided." : "Two sets of books. One lender's limit.")
    : open.length ? `${open.length === 1 ? "One line needs" : `${open.length} lines need`} your answer.`
    : verdict ? `${verdict.verdict === "ok" ? "Under" : "Over"} the limit at ${fmtX(verdict.leverage)}.${noFlagThisTime ? " No flag this time." : ""}`
    : "The agents are working.";

  const sub =
    stage === "new" ? `${deal.platform} acquires ${deal.target}. The limit is ${deal.brief.debt_term} below ${fmtX(deal.brief.limit)}, ${deal.brief.limit_section} of the ${deal.brief.lender} agreement.`
    : open.length ? "The Mapper stopped on what it must not decide alone. Each option shows its effect, computed by the tools."
    : verdict?.posted ? "Approved and posted. The answer you gave is now a policy the Mapper applies next time."
    : noFlagThisTime ? `The Mapper applied ${learned} ${learned === 1 ? "policy" : "policies"} from your earlier answers and asked nothing. Code combined the books and tested the limit again.`
    : verdict ? "Code combined the books and tested the limit. The Reviewer re-ran the checks. Your approval posts it."
    : "Mapping, combining, and testing the limit. The screen updates on its own.";

  return (
    <div className="mx-auto flex max-w-[1120px] flex-col gap-6 px-4 pt-6 pb-12">
      <header className="flex flex-col gap-2">
        <h1 className="font-serif text-[40px] leading-[48px] font-medium">{headline}</h1>
        <p className="text-muted">{sub}</p>
      </header>

      {note ? <p role="alert" className="rounded-chip bg-denied-tint px-4 py-3 font-semibold text-denied">{note}</p> : null}

      {stage === "new" ? (
        <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
          <Button kind="primary" disabled={busy} onClick={() => act(() => api.start(deal.id))}>
            {policies.length ? "Run again" : "Run the deal"}
          </Button>
          <span className="text-muted">
            {plural(source_lines.filter((l) => l.company === deal.platform).length, `${deal.platform} line`)}, {plural(source_lines.filter((l) => l.company === deal.target).length, `${deal.target} line`)}, from public filings.
          </span>
        </div>
      ) : null}

      {open.map((f) => (
        <FlagCard
          key={f.id}
          item={f}
          lines={source_lines}
          busy={busy}
          onAnswer={(id) => act(() => api.answer(f.id, id))}
          onHold={() => act(() => api.hold(f.id))}
        />
      ))}

      {verdict ? (
        <VerdictLine
          verdict={verdict}
          runIds={runIds}
          busy={busy}
          onApprove={() => act(() => api.approve(verdict.approval_item!))}
          onReject={() => act(() => api.reject(verdict.approval_item!, "Rejected by the controller."))}
        />
      ) : null}

      {result ? <CombinedTable result={result} platform={deal.platform} target={deal.target} /> : null}

      {mappings.length ? <Mappings mappings={mappings} lines={source_lines} /> : null}

      {answered.length ? (
        <section className="flex flex-col gap-2">
          <span className="text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] text-muted">Answered ({answered.length})</span>
          {answered.map((f) => (
            <div key={f.id} className="flex items-center gap-3 rounded-chip border border-hairline bg-card px-4 py-2">
              <span className="text-clear"><Shape kind="check" /></span>
              <span className="hidden min-w-0 flex-1 truncate sm:block" title={f.question ?? ""}>{f.question}</span>
              {/* A model-written label can be a long sentence; it truncates instead of widening the page. */}
              <strong className="min-w-0 flex-1 sm:max-w-[55%] sm:flex-none sm:truncate" title={f.options.find((o) => o.id === f.answer)?.label}>
                {f.options.find((o) => o.id === f.answer)?.label}
              </strong>
              <Mono>{f.id}</Mono>
            </div>
          ))}
        </section>
      ) : null}

      {/* One row only from lg: at tablet width the disclaimer was squeezed to a word per line and widened the page. */}
      <footer className="flex flex-col items-start gap-4 border-t border-hairline pt-4 lg:flex-row lg:items-center">
        <Link href="/log" className="font-semibold sm:whitespace-nowrap underline underline-offset-4 hover:text-code">
          Log: {plural(audit.rows, "row")}, {audit.denied} denied, chain {audit.chain_valid ? "intact" : "broken"}
        </Link>
        <span className="hidden flex-1 lg:block" />
        {verdict?.posted ? (
          <Button kind="link" className="text-left sm:whitespace-nowrap" disabled={busy} onClick={() => act(() => api.reset())}>Reset the deal, keep what was learned</Button>
        ) : null}
        <Mono>Figures from public SEC filings. Code does the math; a human approves. Not advice.</Mono>
      </footer>
    </div>
  );
}
