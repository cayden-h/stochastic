# Josie: UI and UX

Branch: `josie/design`.
Folders: `frontend/`, `docs/design/`.

Josie works on the design only.
She has no other task.
The console needs one working screen: the flag card, the combined table, the verdict line, and a log link.
The old routes the console calls (`/plans`, `/facts`, `/clauses`, `/events`) are gone.
The screen now reads `GET /deals/d_kequ_nuaire/case`.

Inputs for the design (2026-10-24):
- The case, flag, and verdict shapes are in `docs/architecture/gateway-and-api.md`, with example JSON.
- Writes: `POST /deals/{id}/run` (the Run button), `POST /work-items/{id}/answer` with `{"option_id": "b"}` (the flag card), `POST /work-items/{id}/approve` (the Approve button, live when `verdict.approval_state` is `PROPOSED`).
  `POST /dev/reset` resets the deal and keeps the agents' memory.
- The flag card: question, evidence quotes with their document id, options with label and computed effect, the default marked.
  The first flag is the financing liability; a second, smaller one is the certificates of deposit.
- The combined table: `result.rows`, platform order, USD thousands, `is_total` rows can be bold.
  Show about ten rows and expand.
- The verdict line: `verdict.leverage` against `verdict.limit`, `verdict.verdict` as OK or Over the limit, `verdict.headroom_turns`, the Reviewer badge from `verdict.review.verdict`, and the backend badge from `verdict.backend`.
- Memory: a small "learned" chip on a mapping or a tag whose reason starts with "Policy".
  After a reset, Run again shows no flag; that is a moment worth one visible state.
- The audit log link: `GET /deals/{id}/audit`, with `chain_valid`, and DENIED rows in red if any.
- Coming from the backend on 2026-10-24 (each owner tells you when it lands): a Download certificate button for `GET /deals/{id}/certificate` (Tri), a fork id and state on each flag option (Cayden), the store badge from `GET /health` `store.kind` (`memory` or `postgres`), and a sensitivity line on the verdict (Tri).
- The design rules are in `design/README.md`.
  The current UI is the `Hi-fi - v3` page of the Schocastic file (https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=141-2); the older Reviewer Console file is history.
  The Figma track needs the frame on screen in the pitch.

## Changed in your folder on 2026-10-24 evening (Cayden's agent, commit 3938ca9 on `cayden/risk-fixes`)

From the risk review's UI pass; please check the look on your screen and change anything you would design differently.
- `src/components/flag-card.tsx`: each covenant option shows its ratio large with the Over the limit or OK chip, read from new option fields `leverage`, `ok`, `basis` (no text parsing).
  The evidence is folded into a `details` block under the options (open by default on mapping flags).
  The kind label says "Lender definition question" or "Mapping question".
  The empty spacer above the label is gone.
- `src/components/verdict-line.tsx`: a line under the ratio keeps the comparison after the answer: "Read as filed, counting the whole financing line: 2.84x, over the limit."
  Labels are "Room (turns of EBITDA)" and "Covenant headroom" ($49.3M of debt).
- `src/app/page.tsx`: a progress row names the working agent and its seconds, from new stages `mapping` and `preparing`; a `run_failed` stage offers Run again; the footer has "Fresh deal, clear memory" (reset between judges) and "Run it again with what was learned"; the memory subline counts answers and lines from policy ids.
- `src/lib/format.ts`: "Learned" counts only `policy_id`, never the reason text; `fmtM` shows one decimal ($49.3M).
- `src/components/top-bar.tsx`: the backend badge says plain words ("Agents: live Claude via Droid", "Agents: scripted rules, no model"), and names a fallback backend if one ran; the deal name is removed so the bar fits on one row at 1280.
- `src/components/gate.tsx`: a "Reconnecting to the gateway" bar when the API drops after the first load.
- `src/components/combined-table.tsx`: opens collapsed; the "Line" header is aligned.
  `src/components/mappings.tsx`: "in a mapping question" instead of "flagged".
- `src/lib/api.ts` (`reset(keepMemory)`), `src/lib/types.ts` (new option, deal, and sensitivity fields), `next.config.ts` (`devIndicators: false`).

## Build phase 2: D19 and D20 (2026-10-24 night)

Josie stays on Figma.
The current UI is the `Hi-fi - v3` page (links in `design/README.md`).
Cayden builds the screens in code from the frames (his task C4), and Josie signs off on each one against its frame.
Tell Cayden when a frame is ready.

In order:
1. **Finish Hi-fi v3.** Dashboard, upload, Case, Mapping, Log, Agents.
   Add "Edits" as a third counter in the sidebar's "Always learning from".
2. **D19 on V3-3 Case** (`review-companion.md` sections 3, 4, 7, 8):
   - Editable amount cells: default, hover, editing, needs a reason, reason given, and a Combined cell with its change.
   - The Your edits section and its row hover.
   - The verdict with Download final files after approval.
3. **D19 on V3-4 Mapping**: the Platform line dropdown, an edited row, and the Edited filter.
4. **The reason bubble** (section 5): the amount version, the remap version, the large-change warning, and a selected chip.
5. **The companion** (section 6): idle, asking with the pulse ring, the learned note, and the waiting dot.
   Put them in `Components`.
6. **The Brief card** (D20, `architecture/brief-reader.md` section 7, Frontend): each field with its quote and section, the flagged fields, the amount inputs, and Approve.
   It sits at the start of a deal, before mapping.
7. **The macOS app icon**, for Eric's Electron shell (E1), at 1024 px.
8. **One frame of the demo beat** at 1440 by 900 for the pitch, plus a frame on the `Technologies Used` page if it helps the Figma track.
