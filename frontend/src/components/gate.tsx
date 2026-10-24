"use client";

import { useDeal } from "@/lib/deal-context";
import { API_URL } from "@/lib/api";

/** Shows a plain note when the gateway API is not running. */
export function Gate({ children }: { children: React.ReactNode }) {
  const { error, kase, loading } = useDeal();
  if (loading) return <div className="mx-auto max-w-[960px] py-12 text-muted">Loading the deal.</div>;
  if (error && !kase) {
    return (
      <div className="mx-auto max-w-[960px] py-12">
        <h1 className="font-serif text-[40px] leading-[48px] font-medium">The gateway is not running.</h1>
        <p className="mt-2 text-muted">The console could not reach {API_URL}. Start the backend, then reload.</p>
        <pre className="mt-4 rounded-chip border border-hairline bg-card p-4 font-mono text-[14px] leading-5">
          cd backend{"\n"}.venv/bin/uvicorn app.main:app --port 8000
        </pre>
      </div>
    );
  }
  return <>{children}</>;
}
