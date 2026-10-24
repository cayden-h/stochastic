"use client";

import { useState } from "react";
import { type MappingFilter, Mappings, editOf, isUnsure } from "@/components/mappings";
import { Page } from "@/components/shell";
import { Button, PageHeader } from "@/components/ui";
import { useDeal } from "@/lib/deal-context";
import { useEdits } from "@/lib/edit-context";
import { canEdit } from "@/lib/edits";
import { plural } from "@/lib/format";

const FILTERS: { key: MappingFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "unsure", label: "Unsure" },
  { key: "policy", label: "By policy" },
  { key: "edited", label: "Edited" },
];

/** V3-4: where each target line went, how sure the Mapper was, which lines an earlier answer settled, and which
 * lines the controller remapped. While the result waits for approval, the Platform line is where remaps happen. */
export default function MappingScreen() {
  const { kase } = useDeal();
  const { edits, error, clearError } = useEdits();
  const [filter, setFilter] = useState<MappingFilter>("all");
  if (!kase) return null;
  const { mappings, source_lines } = kase;
  const unsure = mappings.filter(isUnsure).length;
  const byId = new Map(source_lines.map((l) => [l.id, l]));
  const edited = mappings.filter((m) => editOf(byId.get(m.target_line_id), edits)).length;
  const editable = canEdit(kase);
  return (
    <Page>
      <PageHeader title="Mapping">
        <span className="font-mono text-[12px] whitespace-nowrap text-slate">
          {plural(mappings.length, "line")} &middot; {mappings.length - unsure} sure &middot; {unsure} unsure{edited ? ` · ${edited} edited` : ""}
        </span>
      </PageHeader>

      {error ? (
        <p role="alert" className="flex items-center gap-[12px] rounded-[8px] bg-denied-tint px-[12px] py-[8px] font-semibold text-denied">
          <span className="flex-1">The remap was not saved: {error}</span>
          <Button kind="link" className="text-[13px] text-denied" onClick={clearError}>Dismiss</Button>
        </p>
      ) : null}

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
        {editable ? <span className="text-[13px] text-slate">Pick a platform line to remap a target line.</span> : null}
      </div>

      <Mappings key={filter} mappings={mappings} lines={source_lines} filter={filter} platform={kase.deal.platform} editable={editable} />
    </Page>
  );
}
