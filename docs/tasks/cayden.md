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

Open:
1. Record an Anthropic run once a key is in `.env`: `backend/.venv/bin/python scripts/record_run.py --backend anthropic`.
2. Set `AGENT_BACKEND=droid` and `DROID_MODEL=claude-sonnet-5-5` in `.env` for the demo laptop, and rehearse the failure switch once with a real failure (kill the droid process mid-run; the fallback chain should land on scripted and `GET /health` should show it).
3. Read the Droid Mapper's flags before each rehearsal. The prompt now keeps exclusions for the controller; if a run still decides them itself, say so and show the scripted run instead.
4. Write the pitch words in `demo-script.md` and run the rehearsals.
5. Ask a Hyphenate mentor the two questions in `TASKS.md`.
