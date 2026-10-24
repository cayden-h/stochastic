# Cayden: agents, gateway, demo

Branch: `cayden/agents`.
Folders: `backend/app/agents/`, `backend/app/gateway/`, `backend/app/core/`.

Done on 2026-10-24 (02:30):
- The shared contract in `backend/app/core/models.py`, including agent memory (`Policy`, `AgentSession`).
- The gateway: per-role permissions, maker-checker, run-id and value checks on every number, Reviewer-pass check before approval, reverse, `human:controller` as the default actor, tool runs with run ids, flag effects computed by tools, policies learned from flag answers, sessions per role.
- The three roles, `run_agent` with the `anthropic`, `droid`, `scripted`, and `replay` backends and a fallback chain, the job runner, recording and replay.
- First versions of the tools, the fixture, the routes, and the tests, handed to Tri and Eric.
- `scripts/droid_probe.py` and `scripts/record_run.py`.
- The docs: `STOCHASTIC.md`, `architecture/`, `decisions.md`, `TASKS.md`, `demo-script.md`, `review.md`.

Done at 03:30: the `droid` CLI is installed, the probe shows Claude models on our key, and the whole deal ran on Droid with Claude Sonnet 5.5 (recorded).

Done at 05:10 (the three areas, each documented before the next):
1. Agents and settings: Haiku 5.5 is the default on both backends with per-role overrides, filing notes are on the lines, mapping flags cover several lines, run ids are named, usage and credits are captured per run. Haiku 5.5 on Droid produces the intended moment and is the current recording. `docs/agents.md` is the reference.
2. The application: the gateway API serves `GET /deals/{id}/case` with the new fields and `GET /health` with per-role models, attempts, and credit totals; the failure switch was rehearsed (droid missing, anthropic no key, scripted ran). `docs/architecture/gateway-and-api.md` matches the code.
3. The demo run: pitch words with the computed figures are in `demo-script.md` section 1, the verified failure plan in section 5, the Haiku 5.5 run recorded in `backend/recordings/`, the Sonnet 5.5 run kept in `recordings/sonnet-5-5/`.

Open, needs a human:
1. An Anthropic key in `.env`, then `backend/.venv/bin/python scripts/record_run.py --backend anthropic`.
2. Rehearse the 2:00 with a stopwatch, on the console once Josie's screen reads `/case`. Write the credit total from `GET /health` into the run log in `docs/agents.md` after each rehearsal.
3. Ask a Hyphenate mentor the two questions in `TASKS.md`.
