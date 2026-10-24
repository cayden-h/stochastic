# frontend

The console. Next.js, React, TypeScript, and Tailwind.
Five pages on `GET /deals/{id}/case`, built from the Figma Hi-fi v3 frames (V3-1 to V3-6), each in a 240 px sidebar shell.
The design notes are in `docs/design/README.md`.

## Screens

| Route | Screen | One job |
| --- | --- | --- |
| `/` | Dashboard (V3-1) | See every case with its stage, verdict, and last update; Begin runs the deal |
| (modal) | New deal (V3-2) | Load two statement CSVs and a Brief JSON or the credit agreement as text (`POST /deals`), then run |
| `/case` | Case (V3-3) | Run the deal, answer the flags, read the verdict, edit the books, approve, download |
| `/mapping` | Mapping (V3-4) | Where each target line went and how sure the Mapper was: All, Unsure, By policy, Edited; remap a line |
| `/agents` | Agents (V3-6) | The agents' conversation and timeline, from the audit log |
| `/log` | Log (V3-5) | Prove what happened |
| (slide-over) | Source | Show the exact quote and the document behind a flag |

## Routes the console uses

Reads: `GET /deals` (the Dashboard rows and the current deal), `GET /deals/{id}/case`, `GET /health` (the backend badge), `GET /deals/{id}/audit`, and `GET /deals/{id}/stream` for `stage` and `audit` events.
Writes: `POST /deals` (the upload), `POST /deals/{id}/run`, `POST /work-items/{id}/answer`, `POST /work-items/{id}/hold`, `POST /work-items/{id}/approve`, `POST /work-items/{id}/reject`, and `POST /dev/reset` for the second-run moment.
Review edits (D19, Tri's T2): `POST /deals/{id}/edits`, `POST /edits/{id}/reason`, and `DELETE /edits/{id}`; `/case` carries `edits` and `adjustments`.
The Brief Reader (D20, Tri's T4): `POST /deals` with `agreement_txt`, `POST /deals/{id}/brief/amounts` (`field`, `value`, `source_ref`), and `POST /deals/{id}/brief/approve`; `/case` carries `brief_draft`.
After approval, Download final files reads `GET /deals/{id}/export.xlsx` (Tri's T3) and `GET /deals/{id}/certificate`.
Every write carries `X-Actor: human:controller`.
The console computes no number. Every figure comes from a tool run and shows its run id.

## Run

```
cd backend && .venv/bin/uvicorn app.main:app --port 8000     # terminal 1
cd frontend && npm install && npm run dev                      # terminal 2
```

Open http://localhost:3000: `/` is the Dashboard and `/case` the Case.
The console reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
On another port, also set the backend's `CORS_ORIGINS`, for example `CORS_ORIGINS=http://localhost:3010`.

In the Electron window (`titleBarStyle: hiddenInset`), the layout detects Electron from the user agent and moves the sidebar's brand row below the traffic lights. Page headers and the brand row are drag regions; their buttons and links are not.

## What the screen shows

- The sidebar's model card names which backend produced the agent output (scripted, anthropic, droid, or replay) and where the record lives (Tiger Cloud or memory). If the runner fell back, the card says from what.
- The sidebar's "Always learning from" counts human answers, policies, and reasoned edits (`case.edits`).
- The flag card shows the question, the flagged lines with the filing's note, the evidence quotes, and the options with their computed effects. The default option is marked "Agent suggests".
- The verdict line shows leverage against the limit, OK or Over the limit, the room left, the debt capacity, and the Reviewer badge. Approve is live only when `approval_state` is `PROPOSED` and the Reviewer passed.
- While the result waits for approval, the platform and target amounts in Combined books are editable (click, type, Enter; Esc cancels; Tab moves on). A row that gathers several target lines opens to show them, because an edit names one source line. The Combined cell shows the change from the agents' value, taken from the edits' own old and new values.
- A change of more than half the agents' value asks for confirmation in the bubble before it is sent.
- Your edits sits under the verdict: a click scrolls to the cell and flashes it, and Undo reverts the edit. Approve stays off while an edit has no reason.
- After approval, Download final files calls `window.stochastic.saveFiles([{url, name}])` in the Electron window (Eric's preload), and downloads both files in a browser.
- An adjustment flag (a learned adjustment the Preparer offers on a later deal) shows as "Learned adjustment" with apply and skip.
- On a deal made from agreement text, the Case opens on the Brief card before mapping: every field with the quote it came from, the open questions on the Brief, the EBITDA adjustment amounts to enter from the books with their source, and "Approve the Brief and map". `deal.brief` is null until the reader has drafted it.
- A "Learned" chip marks a mapping or a tag the gateway tied to a live policy (`policy_id`). After "Run it again with what was learned", Run again shows no flag. "Fresh deal (clear memory)" resets for the next judge.

## The companion

`src/components/companion.tsx` is a 14 px agent-blue mark that trails the cursor about 48 px below and to the right, on the spring from Squeek's `halo.js` (credited in the file).
It fades to 40% and parks at the edge when the cursor leaves the window.
When an edit is saved, it glides to the cell (250 ms) and opens the reason bubble: chips (keys 1 to 3), a typed reason, the remember box, Later (Esc) and Save reason (Enter).
After Save the bubble shrinks into it and a one-line "Learned" note shows for 4 s.
An edit left for later puts a waiting dot on it; clicking the dot opens the oldest edit without a reason.
With reduced motion it does not follow: it sits at the bottom-right, and the bubble opens there.
It is pointer-transparent except for the dot and the bubble.
The edit state the table, Your edits, Mapping, and the companion share is in `src/lib/edit-context.tsx`.

## Rules

- Do not overbloat. Apply the checklist in `docs/design/README.md` before adding any screen or control.
- State is always color plus a word plus a shape.
- Type sizes follow the v3 frames (11 px caps labels, 12 px mono, 13 to 14 px text). Numbers are right-aligned with tabular digits and carry their unit.
