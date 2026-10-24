"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Gate } from "./gate";
import { Sidebar, themeOf } from "./sidebar";

const WASH = { green: "wash-green", pink: "wash-pink", purple: "wash-purple" } as const;

/** The v3 window: the sidebar on the left and the page on the right, over the page's tint. Only the page scrolls. */
export function Shell({ children }: { children: ReactNode }) {
  const theme = themeOf(usePathname());
  return (
    <div className={`flex h-screen w-full overflow-hidden ${WASH[theme]}`}>
      <Sidebar />
      <main className="flex min-w-0 flex-1 flex-col overflow-y-auto">
        <Gate>{children}</Gate>
      </main>
    </div>
  );
}

/** A page's column: 32 px sides, 28 px top, 20 px between blocks, as in the v3 frames. */
export function Page({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`flex w-full flex-col gap-[20px] px-[32px] pt-[28px] pb-[28px] ${className}`}>{children}</div>;
}
