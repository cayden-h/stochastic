# frontend

The console. Next.js, React, TypeScript, and Tailwind.
One working screen on `GET /deals/{id}/case`: the flag card, the verdict line, the combined table, the mapping, and a log link.
The design notes are in `docs/design/README.md`.

## Screens

| Route | Screen | One job |
| --- | --- | --- |
| `/` | Case | Run the deal, answer the flags, read the verdict, approve |
| `/log` | Log | Prove what happened |
| (slide-over) | Source | Show the exact quote and the document behind a flag |

## Routes the console uses

Reads: `GET /deals` (to find the deal), `GET /deals/{id}/case`, `GET /health` (the backend badge), `GET /deals/{id}/audit`, and `GET /deals/{id}/stream` for `stage` and `audit` events.
Writes: `POST /deals/{id}/run`, `POST /work-items/{id}/answer`, `POST /work-items/{id}/hold`, `POST /work-items/{id}/approve`, `POST /work-items/{id}/reject`, and `POST /dev/reset` for the second-run moment.
Every write carries `X-Actor: human:controller`.
The console computes no number. Every figure comes from a tool run and shows its run id.

## Run

```
cd backend && .venv/bin/uvicorn app.main:app --port 8000     # terminal 1
cd frontend && npm install && npm run dev                      # terminal 2
```

Open http://localhost:3000.
The console reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

## What the screen shows

- The backend badge in the top bar names which backend produced the agent output: scripted, anthropic, droid, or replay. If the runner fell back, the badge says from what.
- The flag card shows the question, the flagged lines with the filing's note, the evidence quotes, and the options with their computed effects. The default option is marked "Agent suggests".
- The verdict line shows leverage against the limit, OK or Over the limit, the room left, the debt capacity, and the Reviewer badge. Approve is live only when `approval_state` is `PROPOSED` and the Reviewer passed.
- A "Learned" chip marks a mapping or a tag whose reason starts with "Policy". After "Reset the deal, keep what was learned", Run again shows no flag.

## Rules

- Do not overbloat. Apply the checklist in `docs/design/README.md` before adding any screen or control.
- State is always color plus a word plus a shape.
- Nothing is smaller than 14px. Numbers are right-aligned with tabular digits and carry their unit.
