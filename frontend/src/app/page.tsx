"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Page } from "@/components/shell";
import { Button, Card, Label, PageHeader, Shape } from "@/components/ui";
import { UploadModal } from "@/components/upload-modal";
import { useDeal } from "@/lib/deal-context";
import { ago, canStart, clock, fmtX, stageWords } from "@/lib/format";
import type { DealSummary } from "@/lib/types";

// As in V3-1, every stage sits in a chip; state is color, a word, and a shape. A stage that waits on the controller is
// the pale teal one.
const STAGE_TONE = {
  you: { chip: "bg-mint text-forest", shape: "triangle" },
  work: { chip: "bg-fog text-forest", shape: "circle" },
  done: { chip: "bg-clear-tint text-clear", shape: "check" },
  bad: { chip: "bg-denied-tint text-denied", shape: "cross" },
  idle: { chip: "border border-line bg-white text-forest", shape: "square" },
} as const;

/** The case column names the platform: "Kewaunee Scientific acquires Nu Aire" is the Kewaunee Scientific case. */
function caseName(d: DealSummary): string {
  return d.name.replace(/\s+acquires\s+.*$/i, "") || d.platform;
}

/** V3-1: every case with its stage, verdict, and last update. A row opens its case. Run the demo resets the demo deal
 * and plays it in about 15 seconds; Begin runs the current deal at its normal pace; Upload loads a new one. */
export default function Dashboard() {
  const router = useRouter();
  const { deals, kase, audit, select, startRun, runDemo, running, reloadDeals } = useDeal();
  const [upload, setUpload] = useState(false);
  const [busy, setBusy] = useState<"begin" | "demo" | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 30_000);  // "just now" turns into "1 min ago" on its own
    return () => clearInterval(t);
  }, []);
  // The other cases move without an event on this page's stream (the gateway seeds them after it starts, and their
  // runs go on), so the list is read again every few seconds while the Dashboard is open.
  useEffect(() => {
    const t = setInterval(() => void reloadDeals(), 4_000);
    return () => clearInterval(t);
  }, [reloadDeals]);

  if (!kase) return null;
  const current = kase.deal.id;
  // The current deal's row reads the case, which the stream keeps fresher than the list.
  const stageOf = (d: DealSummary) => (d.id === current ? kase.stage : d.stage);
  const verdictOf = (d: DealSummary) => (d.id === current ? (kase.verdict ? { leverage: kase.verdict.leverage, verdict: kase.verdict.verdict } : null) : d.verdict);
  const lastAt = audit.rows[audit.rows.length - 1]?.at;
  const updatedOf = (d: DealSummary) => (d.id === current ? lastAt ?? d.updated_at : d.updated_at);
  const open = deals.filter((d) => stageOf(d) !== "posted").length;
  const needsYou = deals.filter((d) => stageWords(stageOf(d)).tone === "you").length;
  const policies = kase.policies.length;

  async function go(kind: "begin" | "demo") {
    setBusy(kind); setNote(null);
    try {
      // The run goes in the background, so the Case opens at once and the judge watches it happen.
      if (kind === "demo") await runDemo();
      else if (canStart(kase!.stage)) await startRun(current);
      router.push("/case");
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Could not start the run");
    } finally {
      setBusy(null);
    }
  }

  async function openCase(id: string) {
    if (id !== current) await select(id);
    router.push("/case");
  }

  // The frame writes "Needs you" in ink, apart from the teal figures beside it.
  const stats: [number, string, string][] = [
    [open, open === 1 ? "Open case" : "Open cases", "text-forest"],
    [needsYou, "Needs you", "text-ink"],
    [policies, policies === 1 ? "Policy learned" : "Policies learned", "text-forest"],
  ];
  const wait = running ? "Wait for the agents to finish this step" : undefined;

  return (
    <Page>
      <PageHeader title="Dashboard">
        <Button disabled={running} title={wait} onClick={() => setUpload(true)}>Upload</Button>
        <Button disabled={busy !== null || running} title={wait ?? "Run the current case at its normal pace"} onClick={() => void go("begin")}>Begin</Button>
        <Button
          kind="primary"
          disabled={busy !== null || running}
          title={wait ?? "Reset the demo deal with memory cleared and run it in about 15 seconds"}
          onClick={() => void go("demo")}
        >
          {busy === "demo" ? "Starting the demo" : "Run the demo"}
        </Button>
      </PageHeader>

      {note ? <p role="alert" className="rounded-[8px] bg-denied-tint px-[12px] py-[8px] font-semibold text-denied">{note}</p> : null}

      <div className="flex w-full gap-[16px]">
        {stats.map(([n, label, ink]) => (
          <Card key={label} className={`flex min-w-0 flex-1 flex-col gap-[4px] p-[18px] ${ink}`}>
            <span className="text-[28px] font-semibold" data-stat={label}>{n}</span>
            <span className="text-[13px]">{label}</span>
          </Card>
        ))}
      </div>

      <Card className="flex w-full flex-col">
        <div className="flex w-full gap-[12px] border-b border-line px-[20px] py-[12px]">
          <Label className="min-w-0 flex-1">Case</Label>
          <Label className="w-[200px]">Target</Label>
          <Label className="w-[190px]">Stage</Label>
          <Label className="w-[130px]">Verdict</Label>
          <Label className="w-[100px]">Updated</Label>
        </div>
        {deals.map((d) => {
          const on = d.id === current;
          const stage = stageWords(stageOf(d));
          const tone = STAGE_TONE[stage.tone];
          const verdict = verdictOf(d);
          const updated = updatedOf(d);
          return (
            <button
              key={d.id}
              data-deal={d.id}
              aria-current={on ? "true" : undefined}
              onClick={() => void openCase(d.id)}
              className={`flex w-full items-center gap-[12px] border-b border-line px-[20px] py-[14px] text-left last:border-b-0 transition-colors duration-150 ${
                on ? "bg-mint/50 hover:bg-mint" : "hover:bg-mint-select"
              }`}
            >
              <span className="flex min-w-0 flex-1 items-center gap-[10px]">
                <span className={`min-w-0 truncate text-[15px] text-forest ${on ? "font-semibold" : ""}`} title={d.name}>{caseName(d)}</span>
                {d.data_source === "sample" ? (
                  <span
                    className="shrink-0 rounded-chip border border-line bg-white px-[6px] py-[2px] text-[10px] font-semibold tracking-[0.6px] whitespace-nowrap text-slate uppercase"
                    title={d.note ?? "Sample data, not from a filing"}
                  >
                    Sample data
                  </span>
                ) : null}
              </span>
              <span className="w-[200px] truncate text-[14px] text-body" title={d.target}>{d.target}</span>
              <span className="flex h-[30px] w-[190px] items-center">
                <span className={`inline-flex items-center gap-[6px] rounded-[6px] px-[8px] py-[4px] font-ui text-[13px] font-semibold whitespace-nowrap ${tone.chip}`}>
                  <Shape kind={tone.shape} size={10} />
                  {stage.text}
                </span>
              </span>
              <span className="w-[130px] text-[14px]">
                {verdict ? (
                  <span className={`inline-flex items-center gap-[6px] font-semibold whitespace-nowrap ${verdict.verdict === "ok" ? "text-clear" : "text-denied"}`}>
                    <Shape kind={verdict.verdict === "ok" ? "check" : "cross"} size={10} />
                    {fmtX(verdict.leverage)} {verdict.verdict === "ok" ? "OK" : "Over"}
                  </span>
                ) : <span className="text-faint">-</span>}
              </span>
              <span className="w-[100px] font-mono text-[12px] whitespace-nowrap text-slate" title={updated ? clock(updated) + " PT" : undefined}>{updated ? ago(updated, now) : "-"}</span>
            </button>
          );
        })}
      </Card>

      {upload ? <UploadModal onClose={() => setUpload(false)} /> : null}
    </Page>
  );
}
