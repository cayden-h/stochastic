"use client";

import { IBM_Plex_Mono, Public_Sans } from "next/font/google";
import { useEffect, useImperativeHandle, useRef, useState, type Ref } from "react";
import type { AgentKey, AgentState } from "./conversation";
import type { House } from "./house";
import "./agent-house.css";

// The prototype's type, self-hosted at build time so the desktop app needs no network.
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "600"], variable: "--ah-mono" });
const sans = Public_Sans({ subsets: ["latin"], weight: ["400", "500"], variable: "--ah-sans" });

/** What a page can do to the house, the prototype's `window.agentHouse` as a ref. */
export interface AgentHouseHandle {
  setState(key: AgentKey, state: AgentState, text?: string, opts?: { to?: string }): void;
  message(from: AgentKey | "controller" | "gateway", to: AgentKey | "controller" | "gateway", seconds?: number): Promise<void>;
  hop(key: AgentKey): void;
  demo(on?: boolean): void;
}

declare global {
  interface Window {
    /** The prototype's `window.agentHouse`: setState(key, state, text), message(from, to), hop(key), demo(on). */
    agentHouse?: Pick<House, "setState" | "message" | "hop" | "demo">;
  }
}

interface Props {
  ref?: Ref<AgentHouseHandle>;
  /** The prototype's canned STEPS loop, for the pitch preview (`?demo=1`). */
  demo?: boolean;
  /** Live mode's button: replay this deal's conversation from the start. */
  onReplay?: () => void;
  /** Called once the models are in and the first frame is drawn. */
  onReady?: () => void;
  onAgentClick?: (key: AgentKey) => void;
  className?: string;
}

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const q = window.matchMedia("(prefers-reduced-motion: reduce)");
    const on = () => setReduced(q.matches);
    const t = setTimeout(on, 0);
    q.addEventListener("change", on);
    return () => { clearTimeout(t); q.removeEventListener("change", on); };
  }, []);
  return reduced;
}

/**
 * The live 3D Agent House: one WebGL canvas with the four agents, their name pills and bubbles, and the prototype's
 * bar. The scene module loads on the client only, and everything it made is freed on unmount.
 */
export function AgentHouse({ ref, demo = false, onReplay, onReady, onAgentClick, className = "" }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const house = useRef<House | null>(null);
  const queued = useRef<((h: House) => void)[]>([]);
  const reduced = usePrefersReducedMotion();
  const [demoOn, setDemoOn] = useState(demo);
  const cb = useRef({ onReady, onAgentClick });
  useEffect(() => { cb.current = { onReady, onAgentClick }; });

  useEffect(() => {
    let alive = true;
    let made: House | null = null;
    import("./house").then(({ createHouse }) => {
      if (!alive || !box.current) return;
      made = createHouse(box.current, {
        demo, reducedMotion: reduced,
        onDemoChange: setDemoOn,
        onReady: () => cb.current.onReady?.(),
        onAgentClick: (k) => cb.current.onAgentClick?.(k),
      });
      house.current = made;
      setDemoOn(demo);
      // The prototype's hook, kept for parity: drive the agents from the console or a script.
      window.agentHouse = { setState: made.setState, message: made.message, hop: made.hop, demo: made.demo };
      for (const f of queued.current.splice(0)) f(made);
    });
    return () => {
      alive = false;
      if (made && window.agentHouse?.setState === made.setState) delete window.agentHouse;
      made?.dispose(); house.current = null;
    };
  }, [demo, reduced]);

  // Calls made before the scene module arrives wait for it, so the first states are never lost.
  useImperativeHandle(ref, () => {
    const run = (f: (h: House) => void) => { if (house.current) f(house.current); else queued.current.push(f); };
    return {
      setState: (k, s, t, o) => run((h) => h.setState(k, s, t, o)),
      message: (from, to, seconds) => house.current ? house.current.message(from, to, seconds) : Promise.resolve(),
      hop: (k) => run((h) => h.hop(k)),
      demo: (on) => run((h) => h.demo(on)),
    };
  }, []);

  return (
    <div ref={box} className={`agent-house ${mono.variable} ${sans.variable} ${className}`} role="group"
      aria-label="The agents' office: the Brief Reader and the Mapper upstairs, the Preparer and the Reviewer downstairs.">
      <div className="agent-house-bar">
        {demo ? (
          <button type="button" onClick={() => house.current?.demo(!demoOn)}>{demoOn ? "Pause demo" : "Play demo"}</button>
        ) : onReplay ? (
          <button type="button" onClick={onReplay}>Replay run</button>
        ) : null}
        <span>{demo ? "Live three.js scene · agent models built in Blender · hover or click an agent" : "Live from the run · agent models built in Blender · hover an agent"}</span>
      </div>
    </div>
  );
}
