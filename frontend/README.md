# frontend

The console.
Next.js, React, TypeScript, and Tailwind.
Six pages on `GET /deals/{id}/case`, built from the Figma Hi-fi v3 frames (V3-1 to V3-7).
Every page sits in a 240 px sidebar shell: Dashboard, Case, Mapping, Agents, Log, and Review last.
The design notes are in `docs/design/README.md`.

## Screens

| Route | Screen | One job |
| --- | --- | --- |
| `/` | Dashboard (V3-1) | See every case with its stage, verdict, last update, and a Sample data tag; Run the demo plays the 15-second Hyphenate demo; Upload opens New deal |
| (modal) | New deal (V3-2) | Load two statement CSVs and a Brief JSON or the credit agreement as text (`POST /deals`); Begin creates the deal and runs it as the Factory demo (`"pace": "factory"`, about 30 s) |
| `/case` | Case (V3-3) | Answer the flags, watch the pipeline, read the limit check's four figure tiles; the combined books start hidden behind Show combined books; "Review the books" after the Reviewer's hand-off |
| `/review` | Review (V3-7) | Two tabs: Review, the combined books as a workbook, and Mapping, the target lines with a menu to remap each one; give each edit a reason to the Reviewer companion, approve or reject, download the final files; Back to case |
| `/mapping` | Mapping (V3-4) | Where each target line went and how sure the Mapper was, line by line as it happens: All, Unsure, By policy, Edited (read-only) |
| `/agents` | Agents (V3-6) | The Agent House plays the conversation live, with the timeline beside it |
| `/log` | Log (V3-5) | Prove what happened: the audit rows, or the conversation |
| (slide-over) | Source | Show the exact quote and the document behind a flag |
| (toast) | Notifications | A question that needs the controller, on every page, with Decide; and what an answer taught |

## Routes the console uses

Reads: `GET /deals` (the Dashboard rows: `deal_id`, `platform`, `target`, `stage`, `verdict`, `updated_at`, `data_source`, `note`; the older Deal shape also reads), `GET /deals/{id}/case`, `GET /health` (the model card, and the cross-deal learning counters in `memory_counts`), `GET /deals/{id}/audit`, `GET /deals/{id}/conversation` (the history, on load), and `GET /deals/{id}/runs` (the Review page reads the agents' own leverage run for its "was" figures), and `GET /deals/{id}/stream` for `stage`, `audit`, `edit`, `conversation`, `mapping`, and `notify` events.
Writes: `POST /deals` (the upload), `POST /deals/{id}/run` (always `{"sync": false}`: the console follows the run on the stream; Run the demo adds `"pace": "demo"`, the Upload modal's Begin adds `"pace": "factory"`), `POST /work-items/{id}/answer`, `POST /work-items/{id}/hold`, `POST /work-items/{id}/approve`, `POST /work-items/{id}/reject`, and `POST /dev/reset` for the second-run moment and Run the demo (`keep_memory=false`).
Review edits (D19, Tri's T2): `POST /deals/{id}/edits`, `POST /edits/{id}/reason`, and `DELETE /edits/{id}`; `/case` carries `edits` and `adjustments`.
The Brief Reader (D20, Tri's T4): `POST /deals` with `agreement_txt`, `POST /deals/{id}/brief/amounts` (`field`, `value`, `source_ref`), and `POST /deals/{id}/brief/approve`; `/case` carries `brief_draft`.
After approval, Download final files reads `GET /deals/{id}/export.xlsx` (Tri's T3) and `GET /deals/{id}/certificate`.
Every write carries `X-Actor: human:controller`.
The console computes no number.
Every figure comes from a tool run and shows its run id.
The one exception is the Change column on Case and Review, which shows an edit's own new value minus its old value.

## Run

```
cd backend && .venv/bin/uvicorn app.main:app --port 8000     # terminal 1
cd frontend && npm install && npm run dev                      # terminal 2
```

Open http://localhost:3000: `/` is the Dashboard and `/case` the Case.
The console reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
On another port, also set the backend's `CORS_ORIGINS`, for example `CORS_ORIGINS=http://localhost:3010`.

In the Electron window (`titleBarStyle: hiddenInset`), the layout detects Electron from the user agent and moves the sidebar's brand row below the traffic lights.
Page headers and the brand row are drag regions; their buttons and links are not.
In Electron a question also fires a native macOS notification through `window.stochastic.notify({title, body})` (`desktop/preload.js`); in a browser only the toast shows.

## Tests

`npm run lint`, `npx tsc --noEmit`, `npm run build`, and `npm run test:lib` (node's test runner on `src/lib/__tests__`: the conversation reducers, the Review workbook rows, and the `GET /deals` rows).

## What the screen shows

- The sidebar's model card names which backend produced the agent output (scripted, anthropic, droid, or replay) and where the record lives (Tiger Cloud or memory).
  If the runner fell back, the card says from what.
- A run on the replay backend that plays a recorded Claude Haiku run (a `last_runs` entry, or the case's backend info, with `backend: "replay"`, `recorded: true`, and a Haiku `model` such as `claude-haiku-5-5`) shows "Claude Haiku 5.5", with "recorded run" and the store under it.
  A scripted run always shows "Scripted rules", and no other run shows a model name it did not use (`recordedModelName` in `src/lib/format.ts`, with its test).
- The sidebar's "Always learning from" counts human answers, policies, and reasoned edits across every deal, from `GET /health` `memory_counts: {human_answers, policies, edits, by_deal}` (the same as `GET /memory/counts`).
  On a gateway without `memory_counts` it counts the selected deal (`case.flags`, `case.policies`, `case.edits`).
- Every agent character (chips, the Agents rows and timeline, the Log, the pipeline, toasts, the asking banner, the page titles, and the Review companion) is drawn by `Avatar` from `ROLES` in `src/components/ui.tsx`, the one source: `public/v3/agent-mapper.png` (the teal star), `agent-preparer.png`, `agent-reviewer.png`, and `agent-brief-reader.png`.
  The files are served as they are (`unoptimized`), not through `/_next/image`, whose URLs the browser and the Mac app cache for hours: that cache kept the old green Mapper on the small avatars after the art changed.
- The flag card shows the question, the flagged lines with the filing's note, the evidence quotes, and the options with their computed effects.
  The default option is marked "Agent suggests".
- The Case shows, top to bottom: the flag card (or the Brief card), the pipeline, the limit check's four figure tiles (the covenant debt, Covenant EBITDA, Room in turns of EBITDA, and Covenant headroom in dollars of debt, each with its run id), and the combined books, hidden until Show combined books.
  The Case has no conversation (it is on the Agents and Log pages) and no verdict sentence: the leverage against the limit, the as-filed reading, approval, and Download final files are on the Review page.
  Over the limit, or a Reviewer that needs attention, adds its reasons under the tiles.
  Approve is live only when `approval_state` is `PROPOSED` and the Reviewer passed.
- While the result waits for approval, the platform and target amounts in Combined books are editable (click, type, Enter; Esc cancels; Tab moves on).
  A row that gathers several target lines opens to show them, because an edit names one source line.
  The Combined cell shows the change from the agents' value, taken from the edits' own old and new values.
- A change of more than half the agents' value asks for confirmation in the bubble before it is sent.
- Your edits sits under the verdict: a click scrolls to the cell and flashes it, and Undo reverts the edit.
  Approve stays off while an edit has no reason.
- After approval, Download final files calls `window.stochastic.saveFiles([{url, name}])` in the Electron window (Eric's preload), and downloads both files in a browser.
- An adjustment flag (a learned adjustment the Preparer offers on a later deal) shows as "Learned adjustment" with apply and skip.
- On a deal made from agreement text, the Case opens on the Brief card before mapping: every field with the quote it came from, the open questions on the Brief, the EBITDA adjustment amounts to enter from the books with their source, and "Approve the Brief and map".
  `deal.brief` is null until the reader has drafted it.
- A "Learned" chip marks a mapping or a tag the gateway tied to a live policy (`policy_id`).
  After "Run it again with what was learned", Run again shows no flag.
  "Fresh deal (clear memory)" resets for the next judge.

## Cases and the 15-second demo

- The Dashboard lists every case from `GET /deals`.
  A row opens its case: it becomes the current deal (kept for a reload of the window), and every page reads it.
  A case with `data_source: "sample"` shows a Sample data tag (a deal from the filings or an upload shows none), with the note as its tooltip; its Case and Source panel say the figures are not from a filing.
  The stat cards count across every case; Policies learned is the store's own count.
- The demo deal starts from its agreement (D23): the Case shows the Brief card with the verification card ("22 of 22 checks passed", Show the checks lists each field with its quote, section, and pass mark), and Approve the Brief and map is one click; the approval continues the run.
  The pipeline shows Brief Reader, Verifier (a lock chip, no avatar), Mapper, Preparer, Reviewer, You.
  A `notify` of kind `brief_approval` shows "Needs your approval" off the Case.
- Run the demo resets with memory cleared (`POST /dev/reset?keep_memory=false`, which reseeds only the demo deal and returns `kept_deals`), makes the deal it reseeded current, runs it with `"pace": "demo"`, and opens the Case.
  This is the Hyphenate demo.
- The Upload modal's Begin is the Factory demo: after the files are chosen it resets with memory cleared (`POST /dev/reset?keep_memory=false`, retried while a run finishes, so the uploaded deal's questions are asked), creates the deal (`POST /deals`), runs it with `{"sync": false, "pace": "factory"}` (about 30 s of agent time, twice the demo), and opens its Case.
  With no files chosen it runs the current case at the same pace.
  The Dashboard has no Begin.
- A `notify` event (`{id, deal_id, at, kind, item_id, from, title, body}`) shows a toast at the top right of every page: the agent's character, the title, the question, Decide, and Later.
  One question shows at a time, with how many more wait.
  Decide opens the Case on that flag card and moves the focus to it; the deal's later questions then get no toast on its Case, since the card shows them.
  A question already answered drops out, and the stream's replay of an open question on connect is not news, so it gets no toast (the sidebar's Case badge counts the open questions).
- A `conversation` message with `policy_id` ("Learned p_007: ...") shows a Learned toast for 6 s, in the agent's words ("The Mapper learned p_006: ..." or "The Mapper learned p_001 to p_005 (...): ..."), with how many more came with it, and the sidebar's Policies counter pulses.
- The flag card shows the decision, each option's reading, its effect sentence with its figures and run id, and "What happens next".

## The live run

One stream per page, opened by `src/lib/deal-context.tsx`, feeds every page; the Agents page reads it too and opens none of its own.
The reducers are pure and live in `src/lib/conversation.ts` with their tests (`npm run test:lib`, plain `node --test`):
the message list (ordered by id, the stream's replay deduplicated, a reset detected when an id comes back with another time), each agent's state, the mappings (upserted by `mapping_id`), and the Agent House's reading (`settle`, `fromAudit` for a backend without conversation events, `verbOfEvent`).
The agent state rules: a `handoff` to an agent sets it working and the sender done; a `question` to the controller sets the sender asking until the `answer` with the same `item_id`; a `message`, `check`, or `refusal` shows the speaker talking for 1.8 s, then working.

- Run the demo, the Upload modal's Begin, and the Case's Run start the run with `{"sync": false}` and open the Case at once.
- The Case shows the pipeline (Brief Reader, Mapper, Preparer, Reviewer, You) with each agent's state.
  The conversation, newest at the bottom, is on the Log page's Conversation view and on the Agents page.
  A question opens its flag card with "The Mapper is asking you" and the pipeline shows the Mapper waiting on You.
  After the Reviewer's hand-off a card offers "Review the books" (`/review`) and "See the log".
- The Mapping page adds each row as its `mapping` event arrives, highlights the newest for about a second, and keeps the counts and filters on screen.
- Unsure means a line in an open question (an open flag's `line_ids`), marked "Needs you" on its row; the Case tile and the Mapping page count only those.
  Totals are not counted anywhere: they have no platform line by design ("Total, not mapped").
  A line the Mapper placed without asking, one you approved, and one a policy placed are sure, whatever the confidence.
- The Log highlights rows that arrive while it is open and has a Conversation view (`/log?view=conversation`).
- The Agents page opened after a run shows the record at once: each actor's latest line under the house and the whole timeline.
  Before 2026-10-25 it could open empty ("The agents have not started") when the conversation changed right after the page mounted.
- With `DEMO_PACE=1` the paced Mapper holds the gateway lock for about 16 s.
  Run, Upload, and the reset links stay disabled while a job runs, so no write waits on the lock.
  The console reads whether a job runs from the gateway (`running` on `/case`, and the stream's `run` event), never from the stage, so a deal left mid-run by a restart offers Run again.
  A reset in the second after the Reviewer's hand-off (the run is still finishing) is retried until the gateway takes it.

## The companion

`src/components/companion.tsx` is a 14 px agent-blue mark that trails the cursor about 48 px below and to the right, on the spring from Squeek's `halo.js` (credited in the file).
It shows only where editing happens: on the Review page, on both of its tabs.
It fades to 40% and parks at the edge when the cursor leaves the window.
When an edit is saved, it glides to the cell (250 ms) and opens the reason bubble: chips (keys 1 to 3), a typed reason, the remember box, Later (Esc) and Save reason (Enter).
After Save the bubble shrinks into it and a one-line "Learned" note shows for 4 s.
An edit left for later puts a waiting dot on it; clicking the dot opens the oldest edit without a reason.
With reduced motion it does not follow: it sits at the bottom-right, and the bubble opens there.
It is pointer-transparent except for the dot and the bubble.
The edit state the table, Your edits, Mapping, and the companion share is in `src/lib/edit-context.tsx`.

## Rules

- Do not overbloat.
  Apply the checklist in `docs/design/README.md` before adding any screen or control.
- State is always color plus a word plus a shape.
- Type sizes follow the v3 frames (11 px caps labels, 12 px mono, 13 to 14 px text).
  Numbers are right-aligned with tabular digits and carry their unit.
