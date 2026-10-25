"use client";

import { useState } from "react";
import { type MappingFilter, Mappings, editOf, isUnsure } from "@/components/mappings";
import { Page } from "@/components/shell";
import { PageHeader } from "@/components/ui";
import { useDeal } from "@/lib/deal-context";
import { useEdits } from "@/lib/edit-context";
import { plural } from "@/lib/format";

const FILTERS: { key: MappingFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "unsure", label: "Unsure" },
  { key: "policy", label: "By policy" },
  { key: "edited", label: "Edited" },
];

/** V3-4: where each target line went, how sure the Mapper was, which lines an earlier answer settled, and which
 * lines the controller remapped. Read-only: remaps are made on the Review page (V3-7.7). */
export default function MappingScreen() {
  const { kase, mappings, liveMappings, starting } = useDeal();
  const { edits } = useEdits();
  const [filter, setFilter] = useState<MappingFilter>("all");
  if (!kase) return null;
  const { source_lines, stage } = kase;
  const live = starting || stage === "mapping";
  const unsure = mappings.filter(isUnsure).length;
  const byId = new Map(source_lines.map((l) => [l.id, l]));
  const edited = mappings.filter((m) => editOf(byId.get(m.target_line_id), edits)).length;
  return (
    <Page>
      {/* The title, the counts, and the filters stay on screen while the rows arrive below them. The wash is the
          page's own, fixed to the window, so the band is seamless with the page behind it. */}
      <div className="wash-teal sticky top-0 z-[5] -mx-[32px] -mt-[28px] flex flex-col gap-[20px] -mb-[8px] bg-fixed px-[32px] pt-[28px] pb-[8px]">
        <PageHeader title="Mapping">
          <span className="font-mono text-[12px] whitespace-nowrap text-slate">
            {live ? <span className="mr-[8px] font-ui font-semibold text-forest">Mapper is placing lines</span> : null}
            {plural(mappings.length, "line")} &middot; {mappings.length - unsure} sure &middot; {unsure} unsure{edited ? ` · ${edited} edited` : ""}
          </span>
        </PageHeader>

        <div className="flex items-center gap-[8px]" role="group" aria-label="Filter the mappings">
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
                {f.label}{f.key === "edited" && edited ? ` (${edited})` : ""}
              </button>
            );
          })}
          <span className="flex-1" />
        </div>
      </div>

      <Mappings key={filter} mappings={mappings} lines={source_lines} filter={filter} received={liveMappings.received} live={live} />
    </Page>
  );
}
