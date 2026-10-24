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
- The design rules are in `design/README.md`. The Figma file is https://www.figma.com/design/KDbPUruO6f5oPLyzyLgUZh. The Figma track needs the frame on screen in the pitch.
