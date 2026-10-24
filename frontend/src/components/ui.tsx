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
  if (kind === "human") return { kind: "Human", label: "Reviewer" };
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

export function Verdict({ status }: { status: "ok" | "blocked" | "needs_consent" }) {
  const map = {
    blocked: { word: "Blocked", tone: "bg-denied-tint text-denied", shape: "cross" as const },
    needs_consent: { word: "Needs consent", tone: "bg-escalation-tint text-escalation", shape: "triangle" as const },
    ok: { word: "Clear", tone: "bg-clear-tint text-clear", shape: "check" as const },
  }[status];
  return (
    <span className={`inline-flex items-center gap-2 rounded-chip px-3 py-1 font-semibold ${map.tone}`}>
      <Shape kind={map.shape} />
      {map.word}
    </span>
  );
}

export function Tag({ children }: { children: ReactNode }) {
  return (
    <span className="inline-block rounded-chip bg-ink px-2 py-1 text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] text-paper">
      {children}
    </span>
  );
}

export function Label({ children }: { children: ReactNode }) {
  return <span className="text-[14px] leading-5 font-semibold uppercase tracking-[0.04em] text-muted">{children}</span>;
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { kind?: "primary" | "secondary" | "link" };

export function Button({ kind = "secondary", className = "", ...props }: ButtonProps) {
  const base = "font-semibold transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed";
  const tone =
    kind === "primary" ? "min-h-11 rounded-chip bg-ink px-6 py-3 text-paper hover:bg-code"
    : kind === "secondary" ? "min-h-11 rounded-chip border border-rule bg-card px-6 py-3 text-ink hover:bg-paper"
    : "px-2 py-3 text-ink underline underline-offset-4 hover:text-code";
  return <button className={`${base} ${tone} ${className}`} {...props} />;
}
