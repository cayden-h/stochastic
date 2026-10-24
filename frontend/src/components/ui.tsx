"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import { titleCase } from "@/lib/format";

type ShapeKind = "square" | "circle" | "triangle" | "cross" | "check";

const PATHS: Record<ShapeKind, ReactNode> = {
  square: <rect x="2" y="2" width="10" height="10" />,
  circle: <circle cx="7" cy="7" r="5.5" />,
  triangle: <path d="M7 1.5L13 12.5H1Z" />,
  cross: <path d="M3 1.5L7 5.5L11 1.5L12.5 3L8.5 7L12.5 11L11 12.5L7 8.5L3 12.5L1.5 11L5.5 7L1.5 3Z" />,
  check: <path d="M1.5 7.5L5 11L12.5 3.5L11 2L5 8L3 6Z" />,
};

/** State is always color + word + shape. These are the shapes. */
export function Shape({ kind, size = 14 }: { kind: ShapeKind; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="currentColor" aria-hidden="true">
      {PATHS[kind]}
    </svg>
  );
}

export function actorOf(actor: string): { kind: "Agent" | "Human" | "Gateway"; label: string } {
  const [kind, name] = actor.split(":");
  if (kind === "human") return { kind: "Human", label: titleCase(name ?? "controller") };
  if (kind === "system") return { kind: "Gateway", label: "Gateway" };
  return { kind: "Agent", label: titleCase(name ?? "agent") };
}

export function ActorChip({ actor }: { actor: string }) {
  const { kind, label } = actorOf(actor);
  const tone =
    kind === "Agent" ? "bg-agent-tint text-agent"
    : kind === "Human" ? "bg-ink text-paper"
    : "bg-card text-code border border-rule";
  return (
    <span className={`inline-flex items-center gap-2 whitespace-nowrap rounded-chip px-2 py-1 text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] ${tone}`}>
      <Shape kind={kind === "Human" ? "circle" : "square"} size={12} />
      {label}
    </span>
  );
}

type VerdictKind = "ok" | "over_limit" | "pass" | "needs_attention" | "waiting";

/** The verdict word with its color and shape. The word comes from the API; this only dresses it. */
export function Verdict({ kind, word }: { kind: VerdictKind; word?: string }) {
  const map = {
    ok: { word: "OK", tone: "bg-clear-tint text-clear", shape: "check" as const },
    pass: { word: "Reviewer pass", tone: "bg-clear-tint text-clear", shape: "check" as const },
    over_limit: { word: "Over the limit", tone: "bg-denied-tint text-denied", shape: "cross" as const },
    needs_attention: { word: "Reviewer needs attention", tone: "bg-escalation-tint text-escalation", shape: "triangle" as const },
    waiting: { word: "Waiting", tone: "bg-paper text-muted border border-hairline", shape: "circle" as const },
  }[kind];
  return (
    <span className={`inline-flex items-center gap-2 whitespace-nowrap rounded-chip px-3 py-1 font-semibold ${map.tone}`}>
      <Shape kind={map.shape} />
      {word ?? map.word}
    </span>
  );
}

export function Tag({ children, tone = "ink" }: { children: ReactNode; tone?: "ink" | "agent" }) {
  const cls = tone === "agent" ? "bg-agent-tint text-agent" : "bg-ink text-paper";
  return (
    <span className={`inline-block whitespace-nowrap rounded-chip px-2 py-1 text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] ${cls}`}>
      {children}
    </span>
  );
}

export function Label({ children }: { children: ReactNode }) {
  return <span className="text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] text-muted">{children}</span>;
}

export function Mono({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <span className={`font-mono text-[14px] leading-5 text-muted ${className}`}>{children}</span>;
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { kind?: "primary" | "secondary" | "link" };

export function Button({ kind = "secondary", className = "", ...props }: ButtonProps) {
  const base = "font-semibold transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed";
  const tone =
    kind === "primary" ? "min-h-11 whitespace-nowrap rounded-chip bg-ink px-6 py-3 text-paper hover:bg-code"
    : kind === "secondary" ? "min-h-11 whitespace-nowrap rounded-chip border border-rule bg-card px-6 py-3 text-ink hover:bg-paper"
    : "px-2 py-3 text-ink underline underline-offset-4 hover:text-code";
  return <button className={`${base} ${tone} ${className}`} {...props} />;
}
