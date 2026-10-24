# frontend

The console. Next.js, React, TypeScript, and Tailwind.
The current code implements an earlier workflow and is being updated per `docs/TASKS.md`.
The target is one working screen: a flag card, a combined table, a verdict line, and a log link.
The design notes are in `docs/design/README.md`.

## Screens in the current code

| Route | Screen | One job |
| --- | --- | --- |
| `/` | Desk | Show the one question that needs the reviewer now |
| `/plans` | Plans | Compare plans and decide |
| `/log` | Log | Prove what happened |
| (slide-over) | Source | Show the page and the exact quote behind a fact or a denial |

## Run

```
cd backend && .venv/bin/uvicorn app.main:app --port 8000     # terminal 1
cd frontend && npm install && npm run dev                      # terminal 2
```

Open http://localhost:3000.
The console reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
To reset the demo data, call `POST /dev/reset` on the API.

## Status

Surface-level prototype on invented fixture data.
The console calls the real gateway API, so approvals, denials, and the audit log are real in the prototype.
The agents and the new deal math tools are not wired in yet.

## Rules

- Do not overbloat. Apply the checklist in `docs/design/README.md` before adding any screen or control.
- State is always color plus a word plus a shape.
- Nothing is smaller than 14px. Numbers are right-aligned with tabular digits.
