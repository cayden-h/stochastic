"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { CombinedCollapsed, CombinedPending, CombinedTable } from "@/components/combined-table";
import { FlagCard, MoreFlags, WaitingVerdict } from "@/components/flag-card";
import { Page } from "@/components/shell";
import { Avatar, Button, Card, Label, Mono, PageHeader, Shape, Tag } from "@/components/ui";
import { VerdictFigures } from "@/components/verdict-figures";
import { BriefCard } from "@/components/brief-card";
import { VerificationCard } from "@/components/verification-card";
import { AskingBanner, Pipeline, agentName } from "@/components/process-flow";
import { api } from "@/lib/api";
import { useDeal } from "@/lib/deal-context";
import { useEdits } from "@/lib/edit-context";
import { isAdjustmentFlag } from "@/lib/edits";
import { canStart, fmtX, isBriefStage, learnedPolicies, mappingCounts, openQuestionLines, plural } from "@/lib/format";
import { isReadyForApproval } from "@/lib/conversation";

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
 * Run, answer the flags, watch the pipeline, read the limit check's figures. The combined books start hidden behind
 * Show combined books. The books are read-only here: editing, the reasons, the leverage against the limit, approval,
 * and the final files are on the Review page (V3-7), which the Reviewer's hand-off opens. The agents' conversation is
 * on the Agents and Log pages. Mapping, Review and Log are tiles.
 */
export default function CaseScreen() {
  const { kase, deals, refresh, messages, agentStates, startRun, starting, reset, running, mappings: liveRows, focus } = useDeal();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [showBooks, setShowBooks] = useState(false);
  const editsCtx = useEdits();
  const flagRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLElement>(null);

  // A notification's Decide: open that flag and bring its card into view, with the focus on it.
  const focusAt = focus?.at ?? 0;
  const focusItem = focus?.item_id ?? null;
  useEffect(() => {
    if (!focusAt || !focusItem) return;
    const t0 = setTimeout(() => setCurrentId(focusItem), 0);
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // The card for the item is drawn on the next render; the case read may also be a moment behind the event.
    let tries = 0;
    let t: ReturnType<typeof setTimeout>;
    const go = () => {
      const card = cardRef.current;
      if (card && card.dataset.flag === focusItem) {
        card.scrollIntoView({ block: "start", behavior: reduced ? "auto" : "smooth" });
        card.focus({ preventScroll: true });
      } else if (tries++ < 20) t = setTimeout(go, 100);
    };
    t = setTimeout(go, 50);
    return () => { clearTimeout(t0); clearTimeout(t); };
  }, [focusAt, focusItem]);

  // A new question from an agent brings its flag card into view, even if the controller scrolled down to read.
  const asked = messages.filter((m) => m.kind === "question" && m.to === "human:controller").length;
  const askedSeen = useRef(asked);
  useEffect(() => {
    if (asked > askedSeen.current) {
      const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      // The card is drawn from the next /case read, a moment after the message.
      const t = setTimeout(() => flagRef.current?.scrollIntoView({ block: "nearest", behavior: reduced ? "auto" : "smooth" }), 400);
      askedSeen.current = asked;
      return () => clearTimeout(t);
    }
    askedSeen.current = asked;
  }, [asked]);

  if (!kase) return null;
  const { deal, stage, flags, open_flags, verdict, result, mappings, source_lines, policies, audit } = kase;
  // The Brief's own questions sit in the Brief card, not the flag card (D20).
  const open = flags.filter((f) => open_flags.includes(f.id) && f.payload.kind !== "brief_field");
  const fromAgreement = kase.work_items.some((w) => w.type === "draft_brief") || stage === "reading_brief";
  const briefing = isBriefStage(stage) || deal.brief_status === "draft";
  const draft = deal.brief_status === "draft" ? kase.brief_draft ?? null : null;
  const answered = flags.filter((f) => f.answer && f.payload.kind !== "brief_field");
  // A learned adjustment flag (D19) is decided on the finished books: it does not hold the agents, only approval.
  const openAdjustments = open.filter(isAdjustmentFlag);
  const blocking = open.filter((f) => !isAdjustmentFlag(f));
  // One flag is expanded at a time: the one the controller opened, else the first open one.
  const current = open.find((f) => f.id === currentId) ?? open[0] ?? null;
  const runIds = result?.run_ids_by_tool ?? {};
  const applied = learnedPolicies(mappings, source_lines);
  const learned = applied.size;
  const learnedLines = mappings.filter((m) => m.policy_id).length + source_lines.filter((l) => l.covenant_policy_id).length;
  const failed = stage === "run_failed";
  // Where the figures come from: the filings for the demo deal, made-up figures for a sample case.
  const sample = deals.find((d) => d.id === deal.id)?.data_source === "sample";
  const idle = canStart(stage) && !starting;
  // The question the open flag came with, so its card can say who is asking (the gateway asks for some covenant flags).
  const askedBy = current ? messages.findLast((m) => m.kind === "question" && m.item_id === current.id)?.from ?? current.proposed_by : null;
  const handoff = messages.findLast(isReadyForApproval) ?? null;
  const review = verdict?.review?.verdict ?? null;
  const over = verdict?.verdict === "over_limit";
  const reviewReady = verdict?.approval_state === "PROPOSED" && review === "pass" && !over && !openAdjustments.length;

  // The lines an open flag is about, by name, so the combined books can show them in amber.
  const flaggedIds = new Set(open.flatMap((f) => (Array.isArray(f.payload.line_ids) ? (f.payload.line_ids as string[]) : [])));
  const flaggedNames = new Set(source_lines.filter((l) => flaggedIds.has(l.id)).map((l) => l.line));

  // Unsure: a line in an open question. Totals are not counted (they are not mapped by design).
  const counts = mappingCounts(liveRows, source_lines, openQuestionLines(flags, open_flags));
  const approvalWaiting = verdict?.approval_state === "PROPOSED" && !verdict.posted;
  const showProcess = messages.length > 0 || running;

  async function act(fn: () => Promise<unknown>): Promise<boolean> {
    setBusy(true); setNote(null);
    try { await fn(); await refresh(); return true; } catch (e) { setNote(e instanceof Error ? e.message : "Action failed"); await refresh(); return false; }
    finally { setBusy(false); }
  }

  return (
    <Page>
      <PageHeader title="Case">
        {idle ? (
          <Button kind="primary" disabled={busy || running} onClick={() => act(() => startRun(deal.id))}>
            {!deal.brief ? "Read the agreement" : policies.length || failed ? "Run again" : "Run the deal"}
          </Button>
        ) : briefing ? null : verdict?.posted ? (
          <span className="flex min-h-11 items-center gap-[6px] text-[14px] font-semibold text-clear"><Shape kind="check" size={12} />Approved and posted</span>
        ) : reviewReady ? (
          // V3-3 keeps Approve in the header; approval itself happens on the Review page, after the books are read.
          <Link href="/review" className="inline-flex min-h-11 items-center justify-center whitespace-nowrap rounded-chip bg-forest px-[18px] py-[10px] font-ui text-[14px] leading-[28px] font-semibold text-paper transition-colors duration-150 hover:bg-forest-deep">
            Review and approve
          </Link>
        ) : (
          <Button kind="primary" disabled title="Approval opens on the Review page after the Reviewer's pass">Review and approve</Button>
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
                  : deal.brief
                    ? `${deal.platform} acquires ${deal.target}. The limit is ${deal.brief.debt_term} below ${fmtX(deal.brief.limit)}, ${deal.brief.limit_section} of the ${deal.brief.lender} agreement.`
                    : `${deal.platform} acquires ${deal.target}. The Brief Reader reads the credit agreement first and drafts the Brief: the limit, what counts as debt, and the EBITDA adjustments, each with its quote. You check it before the agents map.`}
              </p>
              <Mono>
                {plural(source_lines.filter((l) => l.company === deal.platform).length, `${deal.platform} line`)}, {plural(source_lines.filter((l) => l.company === deal.target).length, `${deal.target} line`)}, {sample ? "sample data, not from a filing" : "from public filings"}.
              </Mono>
            </Card>
          ) : null}

          {draft ? (
            <BriefCard deal={deal} draft={draft} flags={flags} busy={busy} onAct={act} verification={kase.brief_verification ?? null} />
          ) : kase.brief_verification ? (
            <VerificationCard report={kase.brief_verification} />
          ) : null}

          {current ? (
            <div ref={flagRef} className="scroll-mt-[20px]">
            <FlagCard
              banner={askedBy && !isAdjustmentFlag(current) ? <AskingBanner party={askedBy} count={blocking.length} /> : null}
              approvalReady={verdict?.approval_state === "PROPOSED"}
              key={current.id}
              cardRef={cardRef}
              asker={askedBy ? agentName(askedBy).replace(/^The /, "") : "Mapper"}
              more={blocking.filter((f) => f.id !== current.id).length}
              item={current}
              lines={source_lines}
              busy={busy}
              position={`${open.indexOf(current) + 1} of ${open.length}`}
              onAnswer={(id) => act(() => api.answer(current.id, id))}
              onHold={() => act(() => api.hold(current.id))}
            />
            </div>
          ) : null}
          <MoreFlags items={open.filter((f) => f !== current)} onOpen={setCurrentId} />

          {approvalWaiting && review === "pass" ? (
            <Card className="flex w-full items-center gap-[14px] border-mint-edge p-[16px]">
              <Avatar role="reviewer" size={34} />
              <span className="flex min-w-0 flex-1 flex-col gap-[2px]">
                <strong className="text-[16px] font-semibold text-forest">The Reviewer passed the books. Ready for your approval.</strong>
                <span className="truncate text-[13px] text-slate" title={handoff?.text}>{handoff?.text ?? "Tie-out and the limit test pass."}</span>
              </span>
              <Link href="/log" className="text-[14px] font-semibold text-slate underline-offset-4 hover:text-forest hover:underline">See the log</Link>
              <Link href="/review" className="inline-flex min-h-11 items-center justify-center whitespace-nowrap rounded-chip bg-forest px-[18px] py-[10px] font-ui text-[14px] leading-[28px] font-semibold text-paper transition-colors duration-150 hover:bg-forest-deep">
                Review the books
              </Link>
            </Card>
          ) : null}

          {/* The process as it happens: who is working and who waits on whom. What they told each other is on the
              Agents and Log pages. */}
          {showProcess ? (
            <section className="flex w-full flex-col gap-[12px]" aria-label="The process">
              <Card className="p-[8px]">
                <Pipeline
                  agents={agentStates}
                  readerUsed={fromAgreement}
                  posted={Boolean(verdict?.posted)}
                  approvalWaiting={approvalWaiting || stage === "brief_ready"}
                  verifier={{
                    state: stage === "verifying_brief" ? "working" : kase.brief_verification ? (kase.brief_verification.failed ? "failed" : "done") : "idle",
                    passed: kase.brief_verification?.passed ?? 0,
                    total: kase.brief_verification?.checks.length ?? 0,
                  }}
                />
              </Card>
            </section>
          ) : null}

          {verdict ? (
            <VerdictFigures verdict={verdict} runIds={runIds} />
          ) : open.length ? (
            <WaitingVerdict text={open.length === 1 ? "Verdict waits on the flag." : `Verdict waits on ${open.length} flags.`} limit={deal.brief?.limit} />
          ) : null}

          {result && showBooks ? (
            <CombinedTable result={result} flagged={flaggedNames} kase={kase} onHide={() => setShowBooks(false)} />
          ) : result ? (
            <CombinedCollapsed result={result} onShow={() => setShowBooks(true)} />
          ) : !idle && !briefing ? (
            <CombinedPending text={open.length ? "Code combines the books after you answer." : stage === "mapping" || starting ? "Code combines the books after the Mapper." : "Code is combining the books."} />
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
              <Button kind="link" disabled={busy || running} onClick={() => act(() => reset(true))}>Run it again with what was learned</Button>
            ) : null}
            {stage !== "new" || policies.length ? (
              <Button kind="link" disabled={busy || running} title={running ? "Wait for the agents to finish this step" : undefined} onClick={() => act(() => reset(false))}>Fresh deal (clear memory)</Button>
            ) : null}
            <span className="flex-1" />
            <Mono>{sample ? "Sample figures, not from a filing." : "Figures from public SEC filings."} Code does the math; a human approves. Not advice.</Mono>
          </footer>
        </div>

        <div className="flex w-[280px] shrink-0 flex-col gap-[16px]">
          <CaseTile
            href="/mapping"
            label="Mapping"
            value={counts.placed ? `${counts.placed} placed` : stage === "mapping" ? "Mapping" : "Not run"}
            sub={counts.placed ? `${counts.sure} sure · ${counts.unsure} unsure${learnedLines ? ` · ${plural(learnedLines, "line")} learned` : ""}` : briefing ? "Starts after you approve the Brief" : "The Mapper runs first"}
          >
            {learned > 0 ? <Tag tone="agent">Learned</Tag> : null}
          </CaseTile>
          <CaseTile
            href="/agents"
            label="Review"
            value={editsCtx.rechecking ? "Re-checking your edit" : review === "pass" ? "Pass" : review === "needs_attention" ? "Needs attention" : "Waiting"}
            sub={editsCtx.rechecking ? "Tie-out and the limit test run again on the edited books" : review === "pass" ? "The Reviewer re-ran the checks" : review === "needs_attention" ? "Read the reasons on the verdict" : open.length ? "Reviewer runs after your answer" : "Reviewer runs after the Preparer"}
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
