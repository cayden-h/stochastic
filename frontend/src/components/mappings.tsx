"use client";

import { useState } from "react";
import { isLearned, isLearnedTag, plural } from "@/lib/format";
import type { Mapping, SourceLine } from "@/lib/types";
import { Button, Mono, Shape, Tag } from "./ui";

/**
 * The Mapper's line-by-line answer: each target line and the platform line it goes to.
 * A "Learned" chip marks a mapping or a tag the gateway tied to a learned policy: the controller decided it once.
 */
export function Mappings({ mappings, lines }: { mappings: Mapping[]; lines: SourceLine[] }) {
  const [open, setOpen] = useState(false);
  const learned = mappings.filter(isLearned);
  const learnedTags = lines.filter(isLearnedTag);
  const flagged = mappings.filter((m) => m.flagged);
  const low = mappings.filter((m) => m.confidence < 0.8 && !m.flagged);
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <h2 className="font-serif text-[26px] leading-8 font-medium">Mapping</h2>
        <span className="text-muted">
          {plural(mappings.length, "target line")} mapped. {flagged.length} flagged. {low.length} below 0.80 confidence.
        </span>
        {learned.length + learnedTags.length > 0 ? (
          <span className="inline-flex items-center gap-2">
            <Tag tone="agent">Learned</Tag>
            <span className="text-muted">{learned.length + learnedTags.length} from earlier answers</span>
          </span>
        ) : null}
        <span className="flex-1" />
        <Button kind="link" onClick={() => setOpen((v) => !v)}>{open ? "Hide" : "Show"}</Button>
      </div>

      {learnedTags.length && !open ? (
        <div className="flex flex-col gap-1 rounded-chip border border-hairline bg-card px-4 py-2">
          {learnedTags.map((l) => (
            <div key={l.id} className="flex items-center gap-3">
              <Tag tone="agent">Learned</Tag>
              <span className="truncate">{l.line}</span>
              <Mono>{l.covenant_tag}</Mono>
              <Mono className="truncate">{l.covenant_note}</Mono>
            </div>
          ))}
        </div>
      ) : null}

      {open ? (
        <div className="overflow-x-auto rounded-card border border-rule bg-card">
          <div className="min-w-[640px]">
          {mappings.map((m) => (
            <div key={m.id} className="grid grid-cols-[1fr_24px_1fr_72px_140px] items-center gap-3 border-b border-hairline px-4 py-1 last:border-b-0">
              <span className="truncate" title={m.target_line}>{m.target_line}</span>
              <span className="text-muted"><Shape kind="square" size={10} /></span>
              <span className={`truncate ${m.platform_line ? "" : "text-muted"}`} title={m.platform_line ?? "unmapped"}>
                {m.platform_line ?? "Unmapped, listed"}
              </span>
              <Mono className="text-right">{m.confidence.toFixed(2)}</Mono>
              <span className="flex justify-end gap-2">
                {isLearned(m) ? <Tag tone="agent">Learned</Tag> : null}
                {m.flagged ? <Tag>Flagged</Tag> : null}
                {m.approved_by ? <Mono>by you</Mono> : null}
              </span>
            </div>
          ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
