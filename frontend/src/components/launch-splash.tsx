"use client";

import { useEffect, useState } from "react";
import { useDeal } from "@/lib/deal-context";
import { AnimatedStochasticLockup, LAUNCH } from "./stochastic-mark";

/** The longest the browser splash may hold the console, if the first read of the deal hangs. */
const CAP_MS = 8_000;
const FADE_MS = 200;

/** The launch splash in the browser (docs/design/brand.md): only the mark and the name, centered on the page
 * background, from first paint until the console's first read of the deal has finished. It stays until the
 * finished lockup has held (LAUNCH.hold, 2.1 s), then fades out. In the desktop app the Electron splash has already played, so this
 * renders nothing there and instead tells the app when the first read is done (window.stochastic.appReady). */
export function LaunchSplash() {
  const { loading } = useDeal();
  const [phase, setPhase] = useState<"on" | "out" | "gone">("on");
  const [drawn, setDrawn] = useState(false);

  // Desktop: drop the overlay at once (CSS already hides it before hydration) and report readiness to main.
  useEffect(() => {
    if (!window.stochastic?.isDesktop) return;
    const t = setTimeout(() => setPhase("gone"), 0);
    return () => clearTimeout(t);
  }, []);
  useEffect(() => {
    if (!loading) window.stochastic?.appReady?.();
  }, [loading]);

  // Browser: the full draw first, and a cap so a hung read never hides the console's own loading note.
  useEffect(() => {
    const min = setTimeout(() => setDrawn(true), LAUNCH.hold);
    const cap = setTimeout(() => setPhase((p) => (p === "on" ? "out" : p)), CAP_MS);
    return () => { clearTimeout(min); clearTimeout(cap); };
  }, []);
  useEffect(() => {
    if (phase !== "on" || !drawn || loading) return;
    const t = setTimeout(() => setPhase("out"), 0);
    return () => clearTimeout(t);
  }, [phase, drawn, loading]);
  useEffect(() => {
    if (phase !== "out") return;
    const t = setTimeout(() => setPhase("gone"), FADE_MS);
    return () => clearTimeout(t);
  }, [phase]);

  if (phase === "gone") return null;
  return (
    <div
      className={`launch-splash fixed inset-0 z-[100] flex items-center justify-center bg-white text-mark transition-opacity duration-200 ${phase === "out" ? "pointer-events-none opacity-0" : ""}`}
      role="status"
      aria-label="Loading Stochastic"
    >
      <AnimatedStochasticLockup size={232} />
    </div>
  );
}
