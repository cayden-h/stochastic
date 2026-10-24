"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useDeal } from "@/lib/deal-context";
import { ActorChip } from "./ui";

const TABS = [
  { href: "/", label: "Desk" },
  { href: "/plans", label: "Plans" },
  { href: "/log", label: "Log" },
];

export function TopBar() {
  const path = usePathname();
  const { deal } = useDeal();
  return (
    <header className="border-b border-hairline bg-card">
      <div className="mx-auto flex max-w-[1120px] items-center gap-6 py-4">
        <span className="font-serif text-[26px] leading-8 font-medium">Stochastic</span>
        <span className="text-muted">{deal?.name ?? ""}</span>
        <span className="flex-1" />
        <nav className="flex items-center gap-6">
          {TABS.map((t) => {
            const on = path === t.href;
            return (
              <Link
                key={t.href}
                href={t.href}
                aria-current={on ? "page" : undefined}
                className={`border-b-2 py-1 font-semibold ${on ? "border-ink text-ink" : "border-transparent text-muted hover:text-ink"}`}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>
        <ActorChip actor="human:reviewer" />
      </div>
    </header>
  );
}
