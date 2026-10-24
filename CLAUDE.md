# CLAUDE.md

This file gives guidance to Claude Code when it works in this repository.

## What this is

Stochastic merges the books of a newly acquired company into the books of the platform company that bought it.
It flags the few lines that need a human, and then checks the combined result against the lender's limit.
It is built for private equity buy-and-build firms.
Three stateful agents (Mapper, Preparer, Reviewer) do the repeatable work, code does the math, and a human controller approves.
What the controller decides once becomes a policy the agents apply next time.
The demo deal is Kewaunee Scientific buying Nu Aire.
It is built for the Hyphenate track at Cal Hacks 13.0 (Oct 23-25, 2026).

## Read first

Read `docs/STOCHASTIC.md` before any work.
It holds the main features, the architecture, the scope, the demo plan, and the open questions.
If that file and any other file disagree, `docs/STOCHASTIC.md` is correct.
`docs/TASKS.md` splits the work between the team.

## Commands

Backend and console commands are in `README.md`, section "Getting started".
Backend tests: `cd backend && .venv/bin/python -m pytest -q` (105 tests on the real Kewaunee figures).
Run the whole deal from the command line: `backend/.venv/bin/python scripts/record_run.py --backend scripted`.
The backend runs the deal end to end as of 2026-10-24. The console still implements the earlier workflow and is being rebuilt against `GET /deals/{id}/case`.
Project code could not start before Friday Oct 23, about 6pm (Cal Hacks rule).
To rebuild a diagram PDF, run `docs/diagrams/render.sh <name>`. The diagrams are stale, so do this only if asked.

## Structure

- `docs/` holds the reference, tasks, research, design notes, and sponsor notes.
- `backend/`, `frontend/`, `evals/`, `data/`, and `scripts/` each have a README that says what goes there.

## Rules

- Lead the pitch with the problem, then what Stochastic does, then the proof. Do not lead with the demo deal.
- The product is the add-on integration workflow. The earlier all-in-one platform idea is roadmap only. Do not claim other situations are built.
- Code does all deal math. A model never produces a number.
- Only the gateway writes to the record. The agent that prepares a result cannot approve it.
- Agents are stateful. Each role keeps a session, and the Mapper applies the policies the gateway wrote from the controller's answers. Agents still call tools only through the gateway and do not talk to each other.
- Use the covenant's own definitions of debt and EBITDA, and run a tie-out check on every combined table.
- Do not call the output advice. It is a mapped, combined set of books and a limit check that a human approves.
- Say which backend produced the agent output on screen (anthropic, droid, scripted, or replay), and that the gateway, the math, and the audit log are real.
- Mark every claim as verified or inferred. Label sponsor and vendor numbers as self-reported.
- Do not invent prizes, sponsor facts, or numbers.
- Never commit secrets. Keep keys in `.env`, which is git-ignored.
- Never use the em dash. Use a plain hyphen.
- Never use Markdown blockquotes.
- In long Markdown files, put each sentence on its own line.
- Commit only when asked. Do not add an agent name as a co-author in commit messages.
