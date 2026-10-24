"use client";

import Image from "next/image";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { titleCase } from "@/lib/format";
import { LockIcon, SilhouetteIcon } from "./icons";

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
    <svg width={size} height={size} viewBox="0 0 14 14" fill="currentColor" aria-hidden="true" className="shrink-0">
      {PATHS[kind]}
    </svg>
  );
}

export type Role = "mapper" | "preparer" | "reviewer";

/** Each agent's look in v3: its avatar, chip tint, and name color. */
export const ROLES: Record<Role, { src: string; tint: string; ink: string; blend?: boolean }> = {
  mapper: { src: "/v3/agent-mapper.png", tint: "bg-mint", ink: "text-clear", blend: true },
  preparer: { src: "/v3/agent-preparer.png", tint: "bg-preparer-tint", ink: "text-preparer" },
  reviewer: { src: "/v3/agent-reviewer.png", tint: "bg-reviewer-tint", ink: "text-reviewer" },
};

export function isRole(name: string | undefined): name is Role {
  return name === "mapper" || name === "preparer" || name === "reviewer";
}

export function actorOf(actor: string): { kind: "Agent" | "Human" | "Gateway"; label: string; role?: Role } {
  const [kind, name] = actor.split(":");
  if (kind === "human") return { kind: "Human", label: titleCase(name ?? "controller") };
  if (kind === "system") return { kind: "Gateway", label: "Gateway" };
  return { kind: "Agent", label: titleCase(name ?? "agent"), role: isRole(name) ? name : undefined };
}

export function Avatar({ role, size = 20, className = "" }: { role: Role; size?: number; className?: string }) {
  const r = ROLES[role];
  return (
    <Image src={r.src} alt="" width={size} height={size} className={`shrink-0 object-contain ${r.blend ? "mix-blend-multiply" : ""} ${className}`} />
  );
}

/** Who acted: an agent with its avatar, the controller in ink, or the gateway with a lock. */
export function ActorChip({ actor }: { actor: string }) {
  const { kind, label, role } = actorOf(actor);
  const base = "inline-flex items-center gap-[6px] whitespace-nowrap rounded-chip py-[3px] text-[13px] font-semibold";
  if (kind === "Human") {
    return <span className={`${base} bg-ink px-[6px] text-paper`}><SilhouetteIcon />{label}</span>;
  }
  if (kind === "Gateway") {
    return <span className={`${base} border border-line bg-white px-[6px] text-code`}><LockIcon />{label}</span>;
  }
  const look = role ? ROLES[role] : { tint: "bg-agent-tint", ink: "text-agent" };
  return (
    <span className={`${base} pr-[8px] pl-[6px] ${look.tint} ${look.ink}`}>
      {role ? <Avatar role={role} /> : <Shape kind="square" size={12} />}
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
    waiting: { word: "Waiting", tone: "bg-fog text-slate", shape: "circle" as const },
  }[kind];
  return (
    <span className={`inline-flex items-center gap-[6px] whitespace-nowrap rounded-chip px-[8px] py-[4px] text-[13px] font-semibold ${map.tone}`}>
      <Shape kind={map.shape} size={12} />
      {word ?? map.word}
    </span>
  );
}

/** A small caps tag: SUGGESTED in forest, or Learned in mint. */
export function Tag({ children, tone = "ink" }: { children: ReactNode; tone?: "ink" | "agent" }) {
  const cls = tone === "agent" ? "bg-mint text-forest" : "bg-forest text-white";
  return (
    <span className={`inline-block shrink-0 whitespace-nowrap rounded-chip px-[6px] py-[2px] text-[10px] font-semibold uppercase tracking-[0.6px] ${cls}`}>
      {children}
    </span>
  );
}

/** The v3 section label: 11 px caps in slate. */
export function Label({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <span className={`text-[11px] font-semibold uppercase tracking-[0.88px] text-slate ${className}`}>{children}</span>;
}

export function Mono({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <span className={`font-mono text-[12px] text-slate ${className}`}>{children}</span>;
}

/** A white v3 card: 16 px corners and a sage hairline. */
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`overflow-hidden rounded-card border border-line bg-white ${className}`}>{children}</div>;
}

/** The page title row: the serif title on the left, the page's actions on the right. The row drags the window. */
export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <header className="drag flex w-full shrink-0 items-center gap-[12px]">
      <h1 className="font-serif text-[32px] whitespace-nowrap text-forest">{title}</h1>
      <span className="flex-1" />
      {children}
    </header>
  );
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { kind?: "primary" | "secondary" | "link" };

export function Button({ kind = "secondary", className = "", ...props }: ButtonProps) {
  const base = "transition-colors duration-150 disabled:cursor-not-allowed";
  const tone =
    kind === "primary" ? "inline-flex min-h-11 items-center justify-center whitespace-nowrap rounded-chip bg-forest px-[18px] py-[10px] font-ui text-[14px] leading-[28px] font-semibold text-paper hover:bg-clear disabled:opacity-40 disabled:hover:bg-forest"
    : kind === "secondary" ? "inline-flex min-h-11 items-center justify-center whitespace-nowrap rounded-chip border border-rule bg-white px-[18px] py-[10px] font-ui text-[14px] leading-[28px] font-semibold text-ink hover:bg-fog disabled:opacity-40"
    : "text-[14px] font-semibold text-slate underline-offset-4 hover:text-forest hover:underline disabled:opacity-40";
  return <button className={`${base} ${tone} ${className}`} {...props} />;
}
