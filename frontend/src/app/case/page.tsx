"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CombinedPending, CombinedTable } from "@/components/combined-table";
import { FlagCard, MoreFlags, WaitingVerdict } from "@/components/flag-card";
import { Page } from "@/components/shell";
import { Button, Card, Label, Mono, PageHeader, Shape, Tag } from "@/components/ui";
import { VerdictLine } from "@/components/verdict-line";
import { api } from "@/lib/api";
import { useDeal } from "@/lib/deal-context";
import { canStart, fmtX, learnedPolicies, plural } from "@/lib/format";
import type { AuditRow, Stage } from "@/lib/types";

/** The three agents in order, which stage means each one is working, and the work item the gateway opens for it. */
const STEPS: { role: string; item: string; working: Stage[]; done: Stage[] }[] = [
  { role: "Mapper", item: "map_lines", working: ["mapping"], done: ["awaiting_flag", "mapped", "flags_answered", "preparing", "awaiting_review", "awaiting_approval", "needs_attention", "posted"] },
  { role: "Preparer", item: "prepare_result", working: ["mapped", "flags_answered", "preparing"], done: ["awaiting_review", "awaiting_approval", "needs_attention", "posted"] },
  { role: "Reviewer", item: "review_result", working: ["awaiting_review"], done: ["awaiting_approval", "needs_attention", "posted"] },
];

/** While the agents run (30 to 60 s on a live model), show who is working and for how long.
 * The clock starts when this session saw the stage begin. On a fresh load it starts at the audit row where the
 * gateway opened the working agent's item, unless a failed run came after that row: a rerun reuses the item and
 * logs no new row (backend/app/agents/jobs.py), so then it counts from when the row appeared. */
function Progress({ stage, rows, stageSince }: { stage: Stage; rows: AuditRow[]; stageSince: number }) {
  const step = STEPS.find((s) => s.working.includes(stage));
  const opened = step ? rows.findLast((r) => r.action === `create:${step.item}`)?.at : undefined;
  const failed = rows.findLast((r) => r.action === "run:failed")?.at;
  const [shown] = useState(() => Date.now());
  const since = stageSince || (opened && (!failed || opened > failed) ? new Date(opened).getTime() : shown);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const seconds = Math.max(0, Math.round((now - since) / 1000));
  return (
    <ol className="flex w-full flex-wrap items-center gap-x-[24px] gap-y-[8px] rounded-card border border-line bg-fog p-[14px] text-[16px]" aria-live="polite">
      {STEPS.map((s) => {
        const done = s.done.includes(stage);
        const working = !done && s.working.includes(stage);
        return (
          <li key={s.role} className={`flex items-center gap-[8px] font-semibold ${done ? "text-clear" : working ? "text-forest" : "text-slate"}`}>
            <Shape kind={done ? "check" : "circle"} size={12} />
            {s.role}
            {working ? <span className="font-medium text-slate">working, {seconds} s</span> : null}
          </li>
        );
      })}
    </ol>
  );
}

/** A tile in the right column: a label, one figure, one line under it. Each opens its page. */
function CaseTile({ href, label, value, sub, children }: { href: string; label: string; value: string; sub: string; children?: React.ReactNode }) {
  return (
    <Link href={href} className="flex w-full flex-col gap-[4px] rounded-card border border-line bg-white p-[16px] transition-colors duration-150 hover:border-mint-edge">
      <Label>{label}</Label>
      <span className="flex items-center gap-[8px] text-[20px] font-semibold text-forest">{value}{children}</span>
      <span className="text-[13px] text-slate">{sub}</span>
    </Link>
  );
}

/**
 * V3-3, the case: one screen from one read, GET /deals/{id}/case.
 * Run, answer the flags, read the verdict, approve. Mapping, Review and Log are tiles on the right.
 */
export default function CaseScreen() {
  const { kase, refresh, stageSince, audit: { rows: auditRows } } = useDeal();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [currentId, setCurrentId] = useState<string | null>(null);

  if (!kase) return null;
  const { deal, stage, flags, open_flags, verdict, result, mappings, source_lines, policies, audit } = kase;
  const open = flags.filter((f) => open_flags.includes(f.id));
  const answered = flags.filter((f) => f.answer);
  // One flag is expanded at a time: the one the controller opened, else the first open one.
  const current = open.find((f) => f.id === currentId) ?? open[0] ?? null;
  const runIds = result?.run_ids_by_tool ?? {};
  const applied = learnedPolicies(mappings, source_lines);
  const learned = applied.size;
  const learnedLines = mappings.filter((m) => m.policy_id).length + source_lines.filter((l) => l.covenant_policy_id).length;
  const earlierAnswers = new Set(policies.filter((p) => applied.has(p.id)).map((p) => p.learned_from)).size;
  const noFlagThisTime = Boolean(verdict) && answered.length === 0 && learned > 0;
  // The whole-line reading as filed, from the answered covenant flag: the comparison stays on screen after the answer.
  const covenantFlag = answered.find((f) => f.payload.kind === "covenant_tag");
  const asFiledOpt = covenantFlag?.options.find((o) => o.basis === "as_filed" && o.leverage != null);
  const asFiled = asFiledOpt && deal.ebitda_basis !== "as_filed"
    ? { leverage: asFiledOpt.leverage!, ok: Boolean(asFiledOpt.ok), run_id: asFiledOpt.run_id } : null;
  const failed = stage === "run_failed";
  const idle = canStart(stage);
  const working = !idle && !open.length && (!verdict || !verdict.review);
  const review = verdict?.review?.verdict ?? null;
  const over = verdict?.verdict === "over_limit";
  const canApprove = verdict?.approval_state === "PROPOSED" && review === "pass" && !over;

  // The lines an open flag is about, by name, so the combined books can show them in amber.
  const flaggedIds = new Set(open.flatMap((f) => (Array.isArray(f.payload.line_ids) ? (f.payload.line_ids as string[]) : [])));
  const flaggedNames = new Set(source_lines.filter((l) => flaggedIds.has(l.id)).map((l) => l.line));

  const unsure = mappings.filter((m) => m.flagged || m.confidence < 0.8).length;

  async function act(fn: () => Promise<unknown>) {
    setBusy(true); setNote(null);
    try { await fn(); await refresh(); } catch (e) { setNote(e instanceof Error ? e.message : "Action failed"); }
    finally { setBusy(false); }
  }

  const sub =
    verdict?.posted ? "Posted to the record. The answer you gave is now a policy the Mapper applies next time."
    : noFlagThisTime ? `No flag this time. The Mapper applied ${earlierAnswers === 1 ? "your earlier answer" : `your ${earlierAnswers} earlier answers`} to ${plural(learnedLines, "line")} and asked nothing. Code combined the books and tested the limit again.`
    : verdict ? "Code combined the books and tested the limit. The Reviewer re-ran the checks. Your approval posts it."
    : null;

  return (
    <Page>
      <PageHeader title="Case">
        {idle ? (
          <Button kind="primary" disabled={busy} onClick={() => act(() => api.start(deal.id))}>
            {policies.length || failed ? "Run again" : "Run the deal"}
          </Button>
        ) : verdict?.posted ? (
          <span className="flex min-h-11 items-center gap-[6px] text-[14px] font-semibold text-clear"><Shape kind="check" size={12} />Approved and posted</span>
        ) : (
          <>
            {verdict?.approval_state === "PROPOSED" ? (
              <Button kind="link" disabled={busy} onClick={() => act(() => api.reject(verdict.approval_item!, "Rejected by the controller."))}>Reject</Button>
            ) : null}
            <Button kind="primary" disabled={busy || !canApprove} onClick={() => act(() => api.approve(verdict!.approval_item!))}>Approve</Button>
          </>
        )}
      </PageHeader>

      {note ? <p role="alert" className="rounded-[8px] bg-denied-tint px-[12px] py-[8px] font-semibold text-denied">{note}</p> : null}

      <div className="flex w-full items-start gap-[20px]">
        <div className="flex min-w-0 flex-1 flex-col gap-[20px]">
          {idle ? (
            <Card className="flex flex-col gap-[6px] p-[20px]">
              <h2 className="text-[22px] font-semibold text-forest">
                {failed ? "The run stopped before it finished." : policies.length ? "Run again. The Mapper now applies what you decided." : "Two sets of books. One lender's limit."}
              </h2>
              <p className="text-[14px] leading-[20px] text-slate">
                {failed
                  ? "Nothing was posted. Run again to continue from where it stopped; the log has the reason."
                  : `${deal.platform} acquires ${deal.target}. The limit is ${deal.brief.debt_term} below ${fmtX(deal.brief.limit)}, ${deal.brief.limit_section} of the ${deal.brief.lender} agreement.`}
              </p>
              <Mono>
                {plural(source_lines.filter((l) => l.company === deal.platform).length, `${deal.platform} line`)}, {plural(source_lines.filter((l) => l.company === deal.target).length, `${deal.target} line`)}, from public filings.
              </Mono>
            </Card>
          ) : null}

          {current ? (
            <FlagCard
              key={current.id}
              item={current}
              lines={source_lines}
              busy={busy}
              position={`${open.indexOf(current) + 1} of ${open.length}`}
              onAnswer={(id) => act(() => api.answer(current.id, id))}
              onHold={() => act(() => api.hold(current.id))}
            />
          ) : null}
          <MoreFlags items={open.filter((f) => f !== current)} onOpen={setCurrentId} />

          {/* While an agent works the row shows who and for how long, also beside a verdict the Reviewer is checking. */}
          {working ? <Progress stage={stage} rows={auditRows} stageSince={stageSince} /> : null}

          {verdict ? (
            <VerdictLine
              verdict={verdict}
              runIds={runIds}
              asFiled={asFiled}
              note={sub ? <>{noFlagThisTime ? <><Tag tone="agent">Learned</Tag>{" "}</> : null}{sub}</> : null}
            />
          ) : open.length ? (
            <WaitingVerdict text={open.length === 1 ? "Verdict waits on the flag." : `Verdict waits on ${open.length} flags.`} limit={deal.brief.limit} />
          ) : null}

          {result ? (
            <CombinedTable result={result} flagged={flaggedNames} />
          ) : !idle ? (
            <CombinedPending text={open.length ? "Code combines the books after you answer." : "Code is combining the books."} />
          ) : null}

          {answered.length ? (
            <section className="flex flex-col gap-[8px]">
              <Label>Answered ({answered.length})</Label>
              {answered.map((f) => (
                <div key={f.id} className="flex items-center gap-[12px] rounded-[12px] border border-line bg-white px-[16px] py-[10px]">
                  <span className="text-clear"><Shape kind="check" size={12} /></span>
                  <span className="min-w-0 flex-1 truncate text-[14px] text-body" title={f.question ?? ""}>{f.question}</span>
                  {/* A model-written label can be a long sentence; it truncates instead of widening the page. */}
                  <strong className="max-w-[45%] min-w-0 truncate text-[14px] font-semibold text-forest" title={f.options.find((o) => o.id === f.answer)?.label}>
                    {f.options.find((o) => o.id === f.answer)?.label}
                  </strong>
                  <Mono>{f.id}</Mono>
                </div>
              ))}
            </section>
          ) : null}

          <footer className="flex flex-wrap items-center gap-x-[16px] gap-y-[8px] border-t border-line pt-[14px]">
            {verdict?.posted ? (
              <Button kind="link" disabled={busy} onClick={() => act(() => api.reset(true))}>Run it again with what was learned</Button>
            ) : null}
            {stage !== "new" || policies.length ? (
              <Button kind="link" disabled={busy} onClick={() => act(() => api.reset(false))}>Fresh deal (clear memory)</Button>
            ) : null}
            <span className="flex-1" />
            <Mono>Figures from public SEC filings. Code does the math; a human approves. Not advice.</Mono>
          </footer>
        </div>

        <div className="flex w-[280px] shrink-0 flex-col gap-[16px]">
          <CaseTile
            href="/mapping"
            label="Mapping"
            value={mappings.length ? `${mappings.length} placed` : "Not run"}
            sub={mappings.length ? `${mappings.length - unsure} sure · ${unsure} unsure${learnedLines ? ` · ${plural(learnedLines, "line")} learned` : ""}` : "The Mapper runs first"}
          >
            {learned > 0 ? <Tag tone="agent">Learned</Tag> : null}
          </CaseTile>
          <CaseTile
            href="/agents"
            label="Review"
            value={review === "pass" ? "Pass" : review === "needs_attention" ? "Needs attention" : "Waiting"}
            sub={review === "pass" ? "The Reviewer re-ran the checks" : review === "needs_attention" ? "Read the reasons on the verdict" : open.length ? "Reviewer runs after your answer" : "Reviewer runs after the Preparer"}
          />
          <CaseTile
            href="/log"
            label="Log"
            value={plural(audit.rows, "row")}
            sub={`Chain ${audit.chain_valid ? "intact" : "broken"}${audit.denied ? ` · ${audit.denied} denied` : ""}`}
          />
        </div>
      </div>
    </Page>
  );
}
