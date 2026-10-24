# CLAUDE.md

This file gives guidance to Claude Code when it works in this repository.

## What this is

Stochastic is one platform for any special situation in corporate finance.
A team of AI agents works out what a company is allowed to do, finds what blocks it, builds and tests the options, and asks a senior human before anything is committed.
It is built for the Hyphenate track at Cal Hacks 13.0 (Oct 23-25, 2026).

## Read first

Read `docs/STOCHASTIC.md` before any work.
It holds the main features, the architecture, the scope, the demo plan, and the open questions.
If that file and any other file disagree, `docs/STOCHASTIC.md` is correct.

## Commands

There is no build, lint, or test setup yet.
Project code must not start before Friday Oct 23, about 6pm (Cal Hacks rule).
When code lands, document its commands here.
To rebuild a diagram PDF, run `docs/diagrams/render.sh <name>` (it needs Google Chrome and `pdftoppm`).

## Structure

- `docs/` holds the reference, research, diagrams, and sponsor notes.
- `backend/`, `frontend/`, `evals/`, `data/`, and `scripts/` are planned folders. Each has a README that says what goes there.

## Rules

- Pitch Stochastic as an all-in-one platform, and lead with the problem it solves. Do not lead with the demo example.
- Do not claim that all eight situations are built or tested. The demo runs one.
- Code does all deal math. A model never produces a number.
- Only the gateway writes to the record. An agent cannot approve its own work.
- Mark every claim as verified or inferred. Label sponsor numbers as self-reported.
- Do not invent prizes or sponsor facts.
- Never commit secrets. Keep keys in `.env`, which is git-ignored.
- Never use the em dash. Use a plain hyphen.
- Never use Markdown blockquotes.
- In long Markdown files, put each sentence on its own line.
- Commit only when asked. Do not add an agent name as a co-author in commit messages.
