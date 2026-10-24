# Josie: UI and UX

Branch: `josie/design`.
Folders: `frontend/`, `docs/design/`.

Josie works on the design only. She has no other task.
The console needs one working screen: the flag card, the combined table, the verdict line, and a log link.
The old routes the console calls (`/plans`, `/facts`, `/clauses`, `/events`) are gone. The screen now reads `GET /deals/d_kequ_nuaire/case`.

Inputs for the design (2026-10-24):
- The case, flag, and verdict shapes are in `docs/architecture/gateway-and-api.md`, with example JSON.
- Writes: `POST /deals/{id}/run` (the Run button), `POST /work-items/{id}/answer` with `{"option_id": "b"}` (the flag card), `POST /work-items/{id}/approve` (the Approve button, live when `verdict.approval_state` is `PROPOSED`). `POST /dev/reset` resets the deal and keeps the agents' memory.
- The flag card: question, evidence quotes with their document id, options with label and computed effect, the default marked. The first flag is the financing liability; a second, smaller one is the certificates of deposit.
- The combined table: `result.rows`, platform order, USD thousands, `is_total` rows can be bold. Show about ten rows and expand.
- The verdict line: `verdict.leverage` against `verdict.limit`, `verdict.verdict` as OK or Over the limit, `verdict.headroom_turns`, the Reviewer badge from `verdict.review.verdict`, and the backend badge from `verdict.backend`.
- Memory: a small "learned" chip on a mapping or a tag whose reason starts with "Policy". After a reset, Run again shows no flag; that is a moment worth one visible state.
- The audit log link: `GET /deals/{id}/audit`, with `chain_valid`, and DENIED rows in red if any.
- Coming from the backend on 2026-10-24 (each owner tells you when it lands): a Download certificate button for `GET /deals/{id}/certificate` (Tri), a fork id and state on each flag option (Cayden), the store badge from `GET /health` `store.kind` (`memory` or `postgres`), and a sensitivity line on the verdict (Tri).
- The design rules are in `design/README.md`. The Figma file is https://www.figma.com/design/KDbPUruO6f5oPLyzyLgUZh. The Figma track needs the frame on screen in the pitch.

## Changed in your folder on 2026-10-24 evening (Cayden's agent, commit 3938ca9 on `cayden/risk-fixes`)

From the risk review's UI pass; please check the look on your screen and change anything you would design differently.
- `src/components/flag-card.tsx`: each covenant option shows its ratio large with the Over the limit or OK chip, read from new option fields `leverage`, `ok`, `basis` (no text parsing). The evidence is folded into a `details` block under the options (open by default on mapping flags). The kind label says "Lender definition question" or "Mapping question". The empty spacer above the label is gone.
- `src/components/verdict-line.tsx`: a line under the ratio keeps the comparison after the answer: "Read as filed, counting the whole financing line: 2.84x, over the limit." Labels are "Room (turns of EBITDA)" and "Covenant headroom" ($49.3M of debt).
- `src/app/page.tsx`: a progress row names the working agent and its seconds, from new stages `mapping` and `preparing`; a `run_failed` stage offers Run again; the footer has "Fresh deal, clear memory" (reset between judges) and "Run it again with what was learned"; the memory subline counts answers and lines from policy ids.
- `src/lib/format.ts`: "Learned" counts only `policy_id`, never the reason text; `fmtM` shows one decimal ($49.3M).
- `src/components/top-bar.tsx`: the backend badge says plain words ("Agents: live Claude via Droid", "Agents: scripted rules, no model"), and names a fallback backend if one ran; the deal name is removed so the bar fits on one row at 1280.
- `src/components/gate.tsx`: a "Reconnecting to the gateway" bar when the API drops after the first load.
- `src/components/combined-table.tsx`: opens collapsed; the "Line" header is aligned. `src/components/mappings.tsx`: "in a mapping question" instead of "flagged".
- `src/lib/api.ts` (`reset(keepMemory)`), `src/lib/types.ts` (new option, deal, and sensitivity fields), `next.config.ts` (`devIndicators: false`).

## Desktop app and review edits (D19, 2026-10-24 evening)

Spec: `docs/design/review-companion.md`. The Figma checklist is in its section 12.
- [ ] Figma: editable cells, the remap dropdown, the reason bubble, the companion states, the Your edits section, and the Download final files button.
- [ ] Top bar: 72px left padding for the macOS traffic lights (hidden title bar).
- [ ] Build the editable table and the Your edits section against `edits` on the case once Cayden's routes land.
