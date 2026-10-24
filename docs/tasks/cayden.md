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

Open:
1. Install the `droid` CLI in your own shell: `curl -fsSL https://app.factory.ai/cli | sh`. The script was read: it downloads version 0.249.0, checks the SHA-256, and copies it to `~/.local/bin/droid`. The agent's attempt to run it was blocked by a safety classifier.
2. Run `backend/.venv/bin/python scripts/droid_probe.py`. Write the model list and the "can Droid run Claude" answer into `sponsors/factory.md`. If the probe shows MCP tool ids in a different format, set `DROID_RESTRICT_TOOLS` in `.env`.
3. Record a Droid run: `backend/.venv/bin/python scripts/record_run.py --backend droid`. Then an Anthropic run with a key in `.env`. Commit `backend/recordings/`.
4. Rehearse the failure switch once with a real failure.
5. Write the pitch words in `demo-script.md` and run the rehearsals.
6. Ask a Hyphenate mentor the two questions in `TASKS.md`.
