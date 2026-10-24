"use client";

import { useState } from "react";
import { type MappingFilter, Mappings, isUnsure } from "@/components/mappings";
import { Page } from "@/components/shell";
import { PageHeader } from "@/components/ui";
import { useDeal } from "@/lib/deal-context";
import { plural } from "@/lib/format";

const FILTERS: { key: MappingFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "unsure", label: "Unsure" },
  { key: "policy", label: "By policy" },
];

/** V3-4: where each target line went, how sure the Mapper was, and which lines an earlier answer settled. */
export default function MappingScreen() {
  const { kase } = useDeal();
  const [filter, setFilter] = useState<MappingFilter>("all");
  if (!kase) return null;
  const { mappings, source_lines } = kase;
  const unsure = mappings.filter(isUnsure).length;
  return (
    <Page>
      <PageHeader title="Mapping">
        <span className="font-mono text-[12px] whitespace-nowrap text-slate">
          {plural(mappings.length, "line")} &middot; {mappings.length - unsure} sure &middot; {unsure} unsure
        </span>
      </PageHeader>

      <div className="flex gap-[8px]" role="group" aria-label="Filter the mappings">
        {FILTERS.map((f) => {
          const on = f.key === filter;
          return (
            <button
              key={f.key}
              aria-pressed={on}
              onClick={() => setFilter(f.key)}
              className={`rounded-full border px-[12px] py-[6px] text-[13px] font-semibold transition-colors duration-150 ${
                on ? "border-forest bg-forest text-white" : "border-line bg-white text-body hover:bg-mint-select"
              }`}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      <Mappings key={filter} mappings={mappings} lines={source_lines} filter={filter} />
    </Page>
  );
}
