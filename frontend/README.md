# frontend

The console. Next.js, React, TypeScript, and Tailwind.
Five pages on `GET /deals/{id}/case`, built from the Figma Hi-fi v3 frames (V3-1 to V3-6), each in a 240 px sidebar shell.
The design notes are in `docs/design/README.md`.

## Screens

| Route | Screen | One job |
| --- | --- | --- |
| `/` | Dashboard (V3-1) | See every case with its stage, verdict, and last update; Begin runs the deal |
| (modal) | New deal (V3-2) | Load two statement CSVs and a brief JSON (`POST /deals`), then run |
| `/case` | Case (V3-3) | Run the deal, answer the flags, read the verdict, approve |
| `/mapping` | Mapping (V3-4) | Where each target line went and how sure the Mapper was: All, Unsure, By policy |
| `/agents` | Agents (V3-6) | The agents' conversation and timeline, from the audit log |
| `/log` | Log (V3-5) | Prove what happened |
| (slide-over) | Source | Show the exact quote and the document behind a flag |

## Routes the console uses

Reads: `GET /deals` (the Dashboard rows and the current deal), `GET /deals/{id}/case`, `GET /health` (the backend badge), `GET /deals/{id}/audit`, and `GET /deals/{id}/stream` for `stage` and `audit` events.
Writes: `POST /deals` (the upload), `POST /deals/{id}/run`, `POST /work-items/{id}/answer`, `POST /work-items/{id}/hold`, `POST /work-items/{id}/approve`, `POST /work-items/{id}/reject`, and `POST /dev/reset` for the second-run moment.
Every write carries `X-Actor: human:controller`.
The console computes no number. Every figure comes from a tool run and shows its run id.

## Run

```
cd backend && .venv/bin/uvicorn app.main:app --port 8000     # terminal 1
cd frontend && npm install && npm run dev                      # terminal 2
```

Open http://localhost:3000.
The console reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
On another port, also set the backend's `CORS_ORIGINS`, for example `CORS_ORIGINS=http://localhost:3010`.

In the Electron window (`titleBarStyle: hiddenInset`), the layout detects Electron from the user agent and moves the sidebar's brand row below the traffic lights. Page headers and the brand row are drag regions; their buttons and links are not.

## What the screen shows

- The sidebar's model card names which backend produced the agent output (scripted, anthropic, droid, or replay) and where the record lives (Tiger Cloud or memory). If the runner fell back, the card says from what.
- The sidebar's "Always learning from" counts human answers, policies, and reasoned edits. Edits read `case.edits` and show 0 until the edit API exists.
- The flag card shows the question, the flagged lines with the filing's note, the evidence quotes, and the options with their computed effects. The default option is marked "Agent suggests".
- The verdict line shows leverage against the limit, OK or Over the limit, the room left, the debt capacity, and the Reviewer badge. Approve is live only when `approval_state` is `PROPOSED` and the Reviewer passed.
- A "Learned" chip marks a mapping or a tag the gateway tied to a live policy (`policy_id`). After "Run it again with what was learned", Run again shows no flag. "Fresh deal (clear memory)" resets for the next judge.

## Rules

- Do not overbloat. Apply the checklist in `docs/design/README.md` before adding any screen or control.
- State is always color plus a word plus a shape.
- Type sizes follow the v3 frames (11 px caps labels, 12 px mono, 13 to 14 px text). Numbers are right-aligned with tabular digits and carry their unit.
