# frontend

The console. Next.js, React, TypeScript, and Tailwind.
Six pages on `GET /deals/{id}/case`, built from the Figma Hi-fi v3 frames (V3-1 to V3-7).
Every page but Review sits in a 240 px sidebar shell; Review is a full-window workbook with its own title bar and ribbon.
The design notes are in `docs/design/README.md`.

## Screens

| Route | Screen | One job |
| --- | --- | --- |
| `/` | Dashboard (V3-1) | See every case with its stage, verdict, and last update; Begin runs the deal |
| (modal) | New deal (V3-2) | Load two statement CSVs and a Brief JSON or the credit agreement as text (`POST /deals`), then run |
| `/case` | Case (V3-3) | Watch the run live, answer the flags, read the verdict and the read-only books; "Review the books" after the Reviewer's hand-off |
| `/review` | Review (V3-7) | The combined books as a workbook: change an amount or remap a line, give each edit a reason to the Reviewer companion, approve or reject, download the final files |
| `/mapping` | Mapping (V3-4) | Where each target line went and how sure the Mapper was, line by line as it happens: All, Unsure, By policy, Edited (read-only) |
| `/agents` | Agents (V3-6) | The Agent House plays the conversation live, with the timeline beside it |
| `/log` | Log (V3-5) | Prove what happened: the audit rows, or the conversation |
| (slide-over) | Source | Show the exact quote and the document behind a flag |

## Routes the console uses

Reads: `GET /deals` (the Dashboard rows and the current deal), `GET /deals/{id}/case`, `GET /health` (the backend badge), `GET /deals/{id}/audit`, `GET /deals/{id}/conversation` (the history, on load), and `GET /deals/{id}/runs` (the Review page reads the agents' own leverage run for its "was" figures), and `GET /deals/{id}/stream` for `stage`, `audit`, `edit`, `conversation`, and `mapping` events.
Writes: `POST /deals` (the upload), `POST /deals/{id}/run` (always `{"sync": false}`: the console follows the run on the stream), `POST /work-items/{id}/answer`, `POST /work-items/{id}/hold`, `POST /work-items/{id}/approve`, `POST /work-items/{id}/reject`, and `POST /dev/reset` for the second-run moment.
Review edits (D19, Tri's T2): `POST /deals/{id}/edits`, `POST /edits/{id}/reason`, and `DELETE /edits/{id}`; `/case` carries `edits` and `adjustments`.
The Brief Reader (D20, Tri's T4): `POST /deals` with `agreement_txt`, `POST /deals/{id}/brief/amounts` (`field`, `value`, `source_ref`), and `POST /deals/{id}/brief/approve`; `/case` carries `brief_draft`.
After approval, Download final files reads `GET /deals/{id}/export.xlsx` (Tri's T3) and `GET /deals/{id}/certificate`.
Every write carries `X-Actor: human:controller`.
The console computes no number. Every figure comes from a tool run and shows its run id.
The one exception is the Change column on Case and Review, which shows an edit's own new value minus its old value.

## Run

```
cd backend && .venv/bin/uvicorn app.main:app --port 8000     # terminal 1
cd frontend && npm install && npm run dev                      # terminal 2
```

Open http://localhost:3000: `/` is the Dashboard and `/case` the Case.
The console reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
On another port, also set the backend's `CORS_ORIGINS`, for example `CORS_ORIGINS=http://localhost:3010`.

In the Electron window (`titleBarStyle: hiddenInset`), the layout detects Electron from the user agent and moves the sidebar's brand row below the traffic lights. Page headers and the brand row are drag regions; their buttons and links are not.
On Review the title bar is the drag region, 44 px in a browser and 52 px in Electron so it clears the traffic lights.

## Tests

`npm run lint`, `npx tsc --noEmit`, `npm run build`, and `npm run test:lib` (node's test runner on `src/lib/__tests__`: the conversation reducers and the Review workbook rows).

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

## The live run

One stream per page, opened by `src/lib/deal-context.tsx`, feeds every page; the Agents page reads it too and opens none of its own.
The reducers are pure and live in `src/lib/conversation.ts` with their tests (`npm run test:lib`, plain `node --test`):
the message list (ordered by id, the stream's replay deduplicated, a reset detected when an id comes back with another time), each agent's state, the mappings (upserted by `mapping_id`), and the Agent House's reading (`settle`, `fromAudit` for a backend without conversation events, `verbOfEvent`).
The agent state rules: a `handoff` to an agent sets it working and the sender done; a `question` to the controller sets the sender asking until the `answer` with the same `item_id`; a `message`, `check`, or `refusal` shows the speaker talking for 1.8 s, then working.

- Begin and Run start the run with `{"sync": false}` and open the Case at once.
- The Case shows the pipeline (Brief Reader, Mapper, Preparer, Reviewer, You) with each agent's state, and the conversation under it, newest at the bottom.
  A question opens its flag card with "The Mapper is asking you" and the pipeline shows the Mapper waiting on You.
  After the Reviewer's hand-off a card offers "Review the books" (`/review`) and "See the log".
- The Mapping page adds each row as its `mapping` event arrives, highlights the newest for about a second, and keeps the counts and filters on screen.
- The Log highlights rows that arrive while it is open and has a Conversation view (`/log?view=conversation`).
- With `DEMO_PACE=1` the paced Mapper holds the gateway lock for about 16 s. Run, Upload, and the reset links stay disabled while an agent works, so no write waits on the lock.
  A reset in the second after the Reviewer's hand-off (the run is still finishing) is retried until the gateway takes it.

## The companion

`src/components/companion.tsx` is a 14 px agent-blue mark that trails the cursor about 48 px below and to the right, on the spring from Squeek's `halo.js` (credited in the file).
It shows only where editing happens: on the Case, and on the Mapping page while a remap asks for its reason.
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
