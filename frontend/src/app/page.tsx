"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Page } from "@/components/shell";
import { Button, Card, Label, PageHeader } from "@/components/ui";
import { UploadModal } from "@/components/upload-modal";
import { useDeal } from "@/lib/deal-context";
import { ago, canStart, fmtX, stageWords } from "@/lib/format";
import type { Deal } from "@/lib/types";

// As in V3-1: a stage that waits on the controller sits in a pale teal chip; the others are plain words.
const STAGE_TONE = {
  you: "rounded-[6px] bg-mint px-[8px] py-[4px] text-forest",
  work: "text-forest",
  done: "text-clear",
  bad: "text-denied",
  idle: "text-forest",
} as const;

/** The case column names the platform: "Kewaunee Scientific acquires Nu Aire" is the Kewaunee Scientific case. */
function caseName(d: Deal): string {
  return d.name.replace(/\s+acquires\s+.*$/i, "") || d.platform;
}

/** V3-1: every case with its stage, verdict, and last update. Begin runs the current deal; Upload loads a new one. */
export default function Dashboard() {
  const router = useRouter();
  const { deals, kase, audit, select, startRun, running } = useDeal();
  const [upload, setUpload] = useState(false);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 30_000);  // "just now" turns into "1 min ago" on its own
    return () => clearInterval(t);
  }, []);

  if (!kase) return null;
  const current = kase.deal.id;
  const stageOf = (d: Deal) => (d.id === current ? kase.stage : d.stage);
  const open = deals.filter((d) => stageOf(d) !== "posted").length;
  const needsYou = deals.filter((d) => stageWords(stageOf(d)).tone === "you").length;
  const policies = kase.policies.length;
  const lastAt = audit.rows[audit.rows.length - 1]?.at;

  async function begin() {
    setBusy(true); setNote(null);
    try {
      // The run goes in the background, so the Case opens at once and the judge watches it happen.
      if (canStart(kase!.stage)) await startRun(current);
      router.push("/case");
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Could not start the run");
    } finally {
      setBusy(false);
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

  return (
    <Page>
      <PageHeader title="Dashboard">
        <Button disabled={running} title={running ? "Wait for the agents to finish this step" : undefined} onClick={() => setUpload(true)}>Upload</Button>
        <Button kind="primary" disabled={busy} onClick={begin}>Begin</Button>
      </PageHeader>

      {note ? <p role="alert" className="rounded-[8px] bg-denied-tint px-[12px] py-[8px] font-semibold text-denied">{note}</p> : null}

      <div className="flex w-full gap-[16px]">
        {stats.map(([n, label, ink]) => (
          <Card key={label} className={`flex min-w-0 flex-1 flex-col gap-[4px] p-[18px] ${ink}`}>
            <span className="text-[28px] font-semibold">{n}</span>
            <span className="text-[13px]">{label}</span>
          </Card>
        ))}
      </div>

      <Card className="flex w-full flex-col">
        <div className="flex w-full gap-[12px] border-b border-line px-[20px] py-[12px]">
          <Label className="flex-1">Case</Label>
          <Label className="w-[200px]">Target</Label>
          <Label className="w-[170px]">Stage</Label>
          <Label className="w-[150px]">Verdict</Label>
          <Label className="w-[120px]">Updated</Label>
        </div>
        {deals.map((d) => {
          const on = d.id === current;
          const stage = stageWords(stageOf(d));
          const verdict = on ? kase.verdict : null;
          return (
            <button
              key={d.id}
              onClick={() => openCase(d.id)}
              className={`flex w-full items-center gap-[12px] border-b border-line px-[20px] py-[14px] text-left last:border-b-0 transition-colors duration-150 ${
                on ? "bg-mint/50 hover:bg-mint" : "hover:bg-mint-select"
              }`}
            >
              <span className={`min-w-0 flex-1 truncate text-[15px] text-forest ${on ? "font-semibold" : ""}`} title={d.name}>{caseName(d)}</span>
              <span className="w-[200px] truncate text-[14px] text-body">{d.target}</span>
              <span className="flex h-[30px] w-[170px] items-center">
                <span className={`font-ui text-[14px] font-semibold whitespace-nowrap ${STAGE_TONE[stage.tone]}`}>{stage.text}</span>
              </span>
              <span className="w-[150px] text-[14px]">
                {verdict ? (
                  <span className={`font-semibold ${verdict.verdict === "ok" ? "text-clear" : "text-denied"}`}>
                    {fmtX(verdict.leverage)} {verdict.verdict === "ok" ? "OK" : "Over"}
                  </span>
                ) : <span className="text-faint">-</span>}
              </span>
              <span className="w-[120px] font-mono text-[12px] text-slate">{on && lastAt ? ago(lastAt, now) : "-"}</span>
            </button>
          );
        })}
      </Card>

      {upload ? <UploadModal onClose={() => setUpload(false)} /> : null}
    </Page>
  );
}
