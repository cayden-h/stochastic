"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { parseAmount } from "@/lib/edits";
import { fmtK, fmtX, plural } from "@/lib/format";
import type { Brief, BriefAdjustment, Evidence, BriefCitation, BriefDraft, BriefVerification, Deal, WorkItem } from "@/lib/types";
import { VerificationCard } from "./verification-card";
import { ActorChip, Button, Label, Mono, Shape, Tag } from "./ui";

/** "4.8(a)" reads as Section 4.8(a); "Addendum I" and "preamble" read as they are. */
function sectionName(s: string): string {
  return /^\d/.test(s) ? `Section ${s}` : s.charAt(0).toUpperCase() + s.slice(1);
}

/** The quote behind a field, with its section and how sure the reader was. The gateway checked it is in the text. */
function Quote({ c }: { c?: BriefCitation }) {
  if (!c) return <span className="text-[13px] text-escalation">No quote. Answer the question above.</span>;
  const unsure = c.confidence < 0.8;
  return (
    <span className="flex min-w-0 items-baseline gap-[10px] border-l-2 border-line pl-[10px]">
      <q className="line-clamp-2 min-w-0 flex-1 font-serif text-[16px] leading-[21px] text-slate" title={c.quote}>{c.quote}</q>
      <Mono className="shrink-0 whitespace-nowrap">{sectionName(c.section)}{unsure ? ` · ${Math.round(c.confidence * 100)}% sure` : ""}</Mono>
    </span>
  );
}

function Row({ label, children, flagged, removed }: { label: string; children: React.ReactNode; flagged?: boolean; removed?: boolean }) {
  return (
    <div className={`flex w-full gap-[16px] border-t border-line py-[12px] first:border-t-0 ${removed ? "opacity-50" : ""}`}>
      <span className="flex w-[150px] shrink-0 items-start gap-[6px] pt-[2px]">
        <Label>{label}</Label>
        {flagged ? <span className="text-escalation" title="A question is open on this field"><Shape kind="triangle" size={10} /></span> : null}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-[6px]">{children}</div>
    </div>
  );
}

/** The Brief fields the controller can set by path through the amend route. */
const AMENDABLE = /^(lender|limit|limit_section|limit_wording|debt_term|debt_definition|ebitda_definition|test_period_note|debt_excludes\[\d+\]|ebitda_(addbacks|deductions)\[\d+\]\.(name|cap))$/;
const isNumberField = (f: string) => f === "limit" || f.endsWith(".cap");

/** The draft's current value at a path such as `debt_excludes[1]` or `ebitda_addbacks[2].cap`. */
function valueAt(brief: Brief, path: string): string {
  const m = path.match(/^(\w+)(?:\[(\d+)\])?(?:\.(\w+))?$/);
  if (!m) return "";
  let v: unknown = (brief as unknown as Record<string, unknown>)[m[1]];
  if (m[2] != null && Array.isArray(v)) v = v[Number(m[2])];
  if (m[3] && v && typeof v === "object") v = (v as Record<string, unknown>)[m[3]];
  return v == null ? "" : String(v);
}

/** One question the reader or the gateway opened on a field: confirm the reader's value, remove a list item, or
 * correct the value, so a field the reader missed (even the limit) is never a dead end. */
function Question({ flag, brief, busy, onAnswer, onCorrect }: {
  flag: WorkItem; brief: Brief; busy: boolean; onAnswer: (option: string) => void;
  onCorrect: (field: string, value: number | string, source: string) => Promise<boolean>;
}) {
  const field = String(flag.payload.field ?? "");
  const amendable = AMENDABLE.test(field);
  const numeric = isNumberField(field);
  const [value, setValue] = useState(() => valueAt(brief, field));
  const [source, setSource] = useState("");
  const [error, setError] = useState<string | null>(null);
  const correct = async () => {
    const v = numeric ? parseAmount(value) : value.trim();
    if (v === null || v === "" || (numeric && (v as number) < 0)) {
      setError(numeric ? "Enter a number" : "Enter the value"); return;
    }
    setError(null);
    await onCorrect(field, v, source.trim());
  };
  const ev = flag.evidence[0];
  const unverified = Array.isArray(flag.payload.unverified_evidence)
    ? (flag.payload.unverified_evidence as Evidence[]).filter((u) => u && typeof u.quote === "string")
    : [];
  return (
    <div className="flex flex-col gap-[8px] rounded-[12px] border border-amber-line bg-amber-tint px-[14px] py-[12px]">
      <span className="flex items-center gap-[8px]">
        <span className="inline-flex items-center gap-[6px] text-[11px] font-semibold tracking-[0.88px] text-escalation uppercase"><Shape kind="triangle" size={10} />Question</span>
        <Mono>{String(flag.payload.field ?? "")}</Mono>
        <span className="flex-1" />
        <ActorChip actor={flag.proposed_by} />
      </span>
      <p className="text-[14px] leading-[20px] text-body">{flag.question}</p>
      {ev ? (
        <p className="border-l-2 border-amber-line pl-[10px] font-serif text-[16px] leading-[21px] text-body">
          &ldquo;{ev.quote}&rdquo; <Mono>{ev.document_id}</Mono>
        </p>
      ) : null}
      {/* Evidence the gateway did not find in the agreement: the reader's own words, never shown as a quote. */}
      {unverified.map((u, i) => (
        <p key={i} className="flex flex-wrap items-baseline gap-x-[8px] border-l-2 border-line pl-[10px] text-[14px] leading-[20px] text-slate">
          <span className="text-[11px] font-semibold tracking-[0.88px] uppercase">Reader&apos;s words</span>
          {u.quote} {u.document_id ? <Mono>{u.document_id}</Mono> : null}
        </p>
      ))}
      <span className="flex flex-wrap gap-[8px]">
        {flag.options.map((o) => (
          <Button key={o.id} kind={o.id === flag.default ? "primary" : "secondary"} disabled={busy} title={o.effect} onClick={() => onAnswer(o.id)}>
            {o.label}
          </Button>
        ))}
      </span>
      {amendable ? (
        <div className="flex w-full flex-col gap-[6px] border-t border-amber-line pt-[10px]">
          <span className="text-[13px] text-escalation">Or correct it from the agreement:</span>
          <div className="flex w-full flex-wrap items-center gap-[8px]">
            <input
              aria-label={`${field}: corrected value`}
              inputMode={numeric ? "decimal" : undefined}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void correct(); }}
              className={`h-11 rounded-chip border border-rule bg-white px-[10px] text-[14px] text-ink outline-none focus:border-ink ${numeric ? "w-[140px] text-right tabular-nums" : "min-w-[240px] flex-[2]"}`}
            />
            <input
              aria-label={`${field}: source`}
              placeholder="Section, optional"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void correct(); }}
              className="h-11 min-w-[140px] flex-1 rounded-chip border border-rule bg-white px-[10px] text-[14px] text-ink outline-none focus:border-ink"
            />
            <Button kind="secondary" disabled={busy} onClick={() => void correct()}>Save correction</Button>
          </div>
          {error ? <p role="alert" className="text-[12px] text-denied">{error}</p> : null}
        </div>
      ) : null}
    </div>
  );
}

/** An adjustment the agreement allows. Its amount comes from the books, never the agreement, so the controller enters
 * it with its source, or keeps 0 (not applied). */
function AdjustmentRow({
  path, adj, flag, nameQuote, capQuote, busy, onSave, onKeep,
}: {
  path: string; adj: BriefAdjustment; flag?: WorkItem; nameQuote?: BriefCitation; capQuote?: BriefCitation; busy: boolean;
  onSave: (value: number, source: string) => Promise<boolean>; onKeep: () => void;
}) {
  const [amount, setAmount] = useState("");
  const [source, setSource] = useState("");
  const [error, setError] = useState<string | null>(null);
  const deduction = path.startsWith("ebitda_deductions");
  const save = async () => {
    const v = parseAmount(amount);
    if (v === null || v < 0) { setError("Enter the amount in USD thousands"); return; }
    if (!source.trim()) { setError("Name the filing and the line it comes from"); return; }
    setError(null);
    if (await onSave(v, source.trim())) { setAmount(""); setSource(""); }
  };
  return (
    <div className="flex w-full flex-col gap-[8px] border-t border-line py-[12px] first:border-t-0">
      <div className="flex w-full items-baseline gap-[12px]">
        <span className="min-w-0 flex-1 text-[14px] font-semibold text-body">
          {deduction ? "Less: " : "Plus: "}{adj.name}
        </span>
        {adj.cap != null ? <Mono>cap {fmtK(adj.cap)}</Mono> : null}
        {flag ? null : (
          <span className="inline-flex items-center gap-[6px] text-[14px] font-semibold text-forest">
            {adj.amount === 0 ? <span className="font-normal text-slate">Not applied</span> : fmtK(adj.amount)}
            <span className="text-clear"><Shape kind="check" size={10} /></span>
          </span>
        )}
      </div>
      <Quote c={nameQuote} />
      {capQuote ? <Quote c={capQuote} /> : null}
      {flag ? (
        <div className="flex w-full flex-col gap-[6px] rounded-[12px] border border-amber-line bg-amber-tint px-[12px] py-[10px]">
          <p className="text-[13px] leading-[18px] text-escalation">{flag.question}</p>
          <div className="flex w-full flex-wrap items-center gap-[8px]">
            <input
              aria-label={`${adj.name}: amount in USD thousands`}
              inputMode="decimal"
              placeholder="Amount, USD thousands"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void save(); }}
              className="h-11 w-[170px] rounded-chip border border-rule bg-white px-[10px] text-right text-[14px] text-ink tabular-nums outline-none focus:border-ink"
            />
            <input
              aria-label={`${adj.name}: source`}
              placeholder="Source: the filing and the line"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void save(); }}
              className="h-11 min-w-[200px] flex-1 rounded-chip border border-rule bg-white px-[10px] text-[14px] text-ink outline-none focus:border-ink"
            />
            <Button kind="primary" disabled={busy} onClick={() => void save()}>Save amount</Button>
            <Button kind="link" className="text-[13px]" disabled={busy} onClick={onKeep} title="0 means the adjustment is not applied">Keep 0</Button>
          </div>
          {error ? <p role="alert" className="text-[12px] text-denied">{error}</p> : null}
        </div>
      ) : adj.amount !== 0 ? (
        <Mono className="truncate" >{adj.source_ref}</Mono>
      ) : null}
    </div>
  );
}

/**
 * The Brief card (D20): the Brief Reader's draft at the start of a deal, before mapping. Every field shows the quote
 * it came from; the gateway checked each quote is in the agreement. The controller answers the open questions, enters
 * the adjustment amounts from the books with their source, and approves. Approval locks the Brief; then the Mapper runs.
 */
export function BriefCard({
  deal, draft, flags, busy, onAct, verification = null,
}: {
  deal: Deal; draft: BriefDraft; flags: WorkItem[]; busy: boolean;
  /** The verifier's report on this draft (D23), once it ran. */
  verification?: BriefVerification | null;
  /** Runs one write and reads the case again; returns false on failure (the page shows the error). */
  onAct: (fn: () => Promise<unknown>) => Promise<boolean>;
}) {
  const b = draft.brief;
  const cite = (field: string) => draft.citations.find((c) => c.field === field);
  const mine = flags.filter((f) => draft.flags.includes(f.id));
  const open = mine.filter((f) => f.state === "NEEDS_INFO");
  const openOn = (field: string) => open.find((f) => f.payload.field === field);
  const amountFields = new Set([...(b.ebitda_addbacks ?? []).map((_, i) => `ebitda_addbacks[${i}].amount`), ...(b.ebitda_deductions ?? []).map((_, i) => `ebitda_deductions[${i}].amount`)]);
  const questions = open.filter((f) => !amountFields.has(String(f.payload.field)));
  const removed = new Set(draft.removed);
  const left = open.length;

  const answer = (flag: WorkItem, option: string) => onAct(() => api.answer(flag.id, option));
  const adjustments: [string, BriefAdjustment][] = [
    ...(b.ebitda_addbacks ?? []).map((a, i) => [`ebitda_addbacks[${i}]`, a] as [string, BriefAdjustment]),
    ...(b.ebitda_deductions ?? []).map((a, i) => [`ebitda_deductions[${i}]`, a] as [string, BriefAdjustment]),
  ];

  return (
    <section className={`flex w-full flex-col gap-[14px] rounded-card border bg-white p-[20px] ${left ? "border-amber-line" : "border-line"}`} aria-label="Brief">
      <div className="flex w-full items-center gap-[10px] whitespace-nowrap">
        <ActorChip actor="agent:brief_reader" />
        <span className="text-[11px] font-semibold tracking-[0.88px] text-slate uppercase">Brief from the agreement</span>
        <span className="flex-1" />
        <Mono>{plural(draft.citations.length, "quote")} &middot; agreement {draft.sha256.slice(0, 12)}</Mono>
      </div>

      <div className="flex flex-col gap-[6px]">
        <h2 className="text-[22px] font-semibold text-forest">Check the Brief before the agents map.</h2>
        <p className="text-[14px] leading-[20px] text-slate">
          The Brief Reader read {b.agreement_ref}. Each field below is quoted from the agreement, and the verifier checked every quote, section, and number against it.
          {verification?.filled.length ? ` The ${plural(verification.filled.length, "adjustment amount")} came from the books, each with its source.` : ""}
          {draft.amendments_supplied ? "" : " Base agreement only: no amendments were supplied."}
        </p>
      </div>

      {verification ? <VerificationCard report={verification} /> : null}

      {questions.length ? (
        <div className="flex flex-col gap-[10px]">
          {questions.map((f) => (
            <Question
              key={f.id}
              flag={f}
              brief={b}
              busy={busy}
              onAnswer={(o) => void answer(f, o)}
              onCorrect={(field, value, source) => onAct(() => api.amendBrief(deal.id, { field, value, ...(source ? { source_ref: source } : {}) }))}
            />
          ))}
        </div>
      ) : null}

      <div className="flex w-full flex-col rounded-[12px] border border-line px-[16px]">
        <Row label="Lender" flagged={Boolean(openOn("lender"))}>
          <span className="text-[14px] text-body">{b.lender}</span>
          <Quote c={cite("lender")} />
        </Row>
        <Row label="Limit" flagged={Boolean(openOn("limit") || openOn("limit_wording"))}>
          <span className="flex items-baseline gap-[10px]">
            <span className="text-[26px] font-semibold text-forest">{fmtX(b.limit)}</span>
            <span className="text-[14px] text-slate">{b.debt_term} to EBITDA, {b.limit_section}</span>
          </span>
          <Quote c={cite("limit_wording") ?? cite("limit")} />
        </Row>
        <Row label="Debt counted" flagged={Boolean(openOn("debt_definition") || openOn("debt_term"))}>
          <span className="text-[14px] leading-[20px] text-body">{b.debt_definition}</span>
          <Quote c={cite("debt_definition")} />
        </Row>
        {b.debt_excludes.map((x, i) => {
          const path = `debt_excludes[${i}]`;
          return (
            <Row key={path} label={i === 0 ? "Debt excludes" : ""} flagged={Boolean(openOn(path))} removed={removed.has(path)}>
              <span className={`text-[14px] leading-[20px] text-body ${removed.has(path) ? "line-through" : ""}`}>{x}</span>
              {removed.has(path) ? <Mono>Removed at approval</Mono> : <Quote c={cite(path)} />}
            </Row>
          );
        })}
        <Row label="EBITDA" flagged={Boolean(openOn("ebitda_definition"))}>
          <span className="text-[14px] leading-[20px] text-body">{b.ebitda_definition}</span>
          <Quote c={cite("ebitda_definition")} />
        </Row>
        {b.test_period_note ? (
          <Row label="Tested">
            <span className="text-[14px] text-body">{b.test_period_note}</span>
            <Quote c={cite("test_period_note")} />
          </Row>
        ) : null}
      </div>

      {adjustments.length ? (
        <div className="flex flex-col gap-[8px]">
          <span className="flex items-center gap-[8px]">
            <Label>EBITDA adjustments</Label>
            <Mono>USD thousands &middot; amounts come from the books, with their source</Mono>
          </span>
          <div className="flex w-full flex-col rounded-[12px] border border-line px-[16px]">
            {adjustments.map(([path, a]) => {
              const flag = openOn(`${path}.amount`);
              return (
                <AdjustmentRow
                  key={path}
                  path={path}
                  adj={a}
                  flag={flag}
                  nameQuote={cite(`${path}.name`)}
                  capQuote={a.cap != null ? cite(`${path}.cap`) : undefined}
                  busy={busy}
                  onSave={(value, source) => onAct(() => api.amendBrief(deal.id, { field: `${path}.amount`, value, source_ref: source }))}
                  onKeep={() => flag && void answer(flag, "confirm")}
                />
              );
            })}
          </div>
        </div>
      ) : null}

      <div className="flex w-full flex-wrap items-center gap-[12px] border-t border-line pt-[14px]">
        {left ? (
          <span className="inline-flex items-center gap-[6px] text-[14px] font-semibold text-escalation">
            <Shape kind="triangle" size={10} />{plural(left, "question")} left before you can approve
          </span>
        ) : (
          <span className="inline-flex items-center gap-[6px] text-[14px] font-semibold text-clear">
            <Shape kind="check" size={10} />Every question answered
          </span>
        )}
        <span className="min-w-0 flex-1 text-[13px] text-slate">Approving locks the Brief on this deal; the run goes on and the Mapper starts.</span>
        {!draft.amendments_supplied ? <Tag tone="agent">Base agreement only</Tag> : null}
        <Button
          kind="primary"
          disabled={busy || left > 0}
          onClick={() => void onAct(() => api.approveBrief(deal.id))}
        >
          Approve the Brief and map
        </Button>
      </div>
    </section>
  );
}
