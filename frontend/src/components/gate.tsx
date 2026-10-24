"use client";

import { useDeal } from "@/lib/deal-context";
import { API_URL } from "@/lib/api";

/** Shows a plain note when the gateway API is not running. */
export function Gate({ children }: { children: React.ReactNode }) {
  const { error, kase, loading } = useDeal();
  if (loading) return <div className="px-[32px] py-[28px] text-slate">Loading the deal.</div>;
  if (error?.kind === "no_deal") {
    return (
      <div className="drag flex flex-col gap-[12px] px-[32px] py-[28px]">
        <h1 className="font-serif text-[32px] text-forest">No deal is loaded.</h1>
        <p className="text-slate">The gateway at {API_URL} is running but holds no deal. Reset it to load the demo deal, then reload.</p>
        <pre className="max-w-[640px] rounded-[12px] border border-line bg-white p-4 font-mono text-[12px]">
          curl -X POST &apos;{API_URL}/dev/reset?keep_memory=false&apos;
        </pre>
      </div>
    );
  }
  if (error && kase) {
    // The API dropped after the first load: say so instead of leaving a stale screen that looks live.
    return (
      <>
        <p role="status" className="sticky top-0 z-10 bg-escalation-tint px-4 py-2 text-center font-semibold text-escalation">
          Reconnecting to the gateway at {API_URL}. The screen below is the last state it sent.
        </p>
        {children}
      </>
    );
  }
  if (error && !kase) {
    return (
      <div className="drag flex flex-col gap-[12px] px-[32px] py-[28px]">
        <h1 className="font-serif text-[32px] text-forest">The gateway is not running.</h1>
        <p className="text-slate">The console could not reach {API_URL}. Start the backend, then reload.</p>
        <pre className="max-w-[640px] rounded-[12px] border border-line bg-white p-4 font-mono text-[12px]">
          cd backend{"\n"}.venv/bin/uvicorn app.main:app --port 8000
        </pre>
      </div>
    );
  }
  return <>{children}</>;
}
