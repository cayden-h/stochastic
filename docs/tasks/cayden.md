# Cayden: agents, gateway, demo

Branch: `cayden/agents`.
Folders: `backend/app/agents/`, `backend/app/gateway/`, `backend/app/core/`, and `backend/app/db/postgres.py` (the Tiger store, written by Cayden's session on 2026-10-24; Tri owns the rest of `backend/app/db/`).

## Done

Done on 2026-10-24 (02:30):
- The shared contract in `backend/app/core/models.py`, including agent memory (`Policy`, `AgentSession`).
- The gateway: per-role permissions, maker-checker, run-id and value checks on every number, Reviewer-pass check before approval, reverse, `human:controller` as the default actor, tool runs with run ids, flag effects computed by tools, policies learned from flag answers, sessions per role.
- The three roles, `run_agent` with the `anthropic`, `droid`, `scripted`, and `replay` backends and a fallback chain, the job runner, recording and replay.
- First versions of the tools, the fixture, the routes, and the tests, handed to Tri and Eric.
- `scripts/droid_probe.py` and `scripts/record_run.py`.
- The docs: `STOCHASTIC.md`, `architecture/`, `decisions.md`, `TASKS.md`, `demo-script.md`, `review.md`.

Done at 03:30: the `droid` CLI is installed, the probe shows Claude models on our key, and the whole deal ran on Droid with Claude Sonnet 5.5 (recorded).

Done at 05:10 (the three areas, each documented before the next):
1. Agents and settings: Haiku 5.5 is the default on both backends with per-role overrides, filing notes are on the lines, mapping flags cover several lines, run ids are named, usage and credits are captured per run. `docs/agents.md` is the reference.
2. The application: the gateway API serves `GET /deals/{id}/case` with the new fields and `GET /health` with per-role models, attempts, and credit totals; the failure switch was rehearsed (droid missing, anthropic no key, scripted ran). `docs/architecture/gateway-and-api.md` matches the code.
3. The demo run: pitch words with the computed figures are in `demo-script.md` section 1, the verified failure plan in section 5, the Sonnet 5.5 run is the default replay in `backend/recordings/`, the Haiku 5.5 run kept in `recordings/haiku-5-5/`.

Done at 08:00 (commit 08b2629): the Tiger Cloud store (`STORE=postgres`, write-through, audit log as an append-only TimescaleDB hypertable, reload on start), stateful Droid sessions, medium reasoning effort, Tiger Data as a target track (D15). A console Droid run at 07:51 is kept in `recordings/droid-console-0751/` (33 of 33).

Done at 08:50 (Cayden's agent, live end-to-end tests on Droid and Tiger; details in `agents.md` section 9 and `decisions.md` D16):
- Task 1: the demo laptop runs `STORE=postgres`; `GET /health` shows `postgres`, no fallback reason.
- Task 2: the restart moment is rehearsed and written into `demo-script.md` section 5. Every field of the case came back identical.
- Task 3: done at 09:00. Cayden chose to delete `larp-city` (backed up to `HackRice/backups/`); each covenant flag's what-ifs now live in a Tiger fork that the answer deletes (D17, `sponsors/tiger-data.md`). Tested live in the browser and against Tiger.
- Task 9: scheduled in Cayden's Claude session for Sunday 07:52 (wake the service if paused, check `/health`). It runs only if that session is still open, so keep the manual check too.
- Task 4: Anthropic is out of the default fallback chain (no key); the default is `scripted`.
- Task 5, the machine part: three cold runs in a headless browser, timed. The stopwatch run of the 2:00 is still Cayden's.
- Task 7, the prepared part: the backend line in `devpost/devpost.md` is filled in as planned. Submitting on devpost.com is still Cayden's (it needs his login).
- Task 8: `devpost/one-pager.html` and `one-pager.pdf` (page 1 the summary, page 2 the honest-limits card), Letter size.
- Found and fixed on the way: the count-everything reading on every covenant flag, the Learned chip from `policy_id`, 409 on a second run, live runs no longer overwrite the pinned replay, the Mapper on Sonnet 5.5, and console overflow at 768 and 1440.

## Open, in order

1. **Make the demo run on Tiger.** Set `STORE=postgres` in `.env` on the demo laptop, restart the API, and check that `GET /health` shows `store.kind` = `postgres` with no `fallback_reason`. The API running at 07:50 was on the memory store. About 15 minutes.
2. **Rehearse the restart moment.** Run the deal, answer the flag, approve, then stop and start the API. The case, the audit log, and the learned policy must come back, and `chain_valid` must stay true. Write the steps into `demo-script.md` section 5. About 30 minutes.
3. **Tiger forks, one per flag option (the Tiger differentiator).** A plain Postgres store will not stand out (`sponsors/tiger-data.md`).
   - Spike first: time `tiger service fork` (or the Tiger MCP `service_fork`) on the `stochastic` service, and ask the Tiger booth for the free-tier fork limit. Write the time into `sponsors/tiger-data.md`.
   - If a fork takes under about 30 seconds: when the Mapper raises a flag, the gateway forks once per option, runs `limit_test` in each fork, and puts the fork id on each option's effect. The controller's answer keeps the chosen fork's result and deletes the others. Log each fork and delete in the audit log.
   - If a fork is slow: fork in the background as soon as the flag is raised, show "computing in fork" on the option, and keep the in-process effects as the fallback. Do not let a fork block the flag card.
   - Tests: the gateway with a fake fork client (no network), plus one opt-in test against Tiger like `test_postgres_store.py`.
   - Tell Josie the new field on the option (fork id and state) so the flag card can show it.
   - About 2 to 3 hours. Drop it by Saturday 8pm if the spike fails, and say so in the Devpost.
4. **Anthropic backend: key or cut.** Either put a key in `.env` and run `backend/.venv/bin/python scripts/record_run.py --backend anthropic`, or remove `anthropic` from `AGENT_FALLBACK` and the docs. Today the chain names a backend that has never run.
5. **Rehearse the 2:00 with a stopwatch**, on Josie's console and on `STORE=postgres`. Write the credit total from `GET /health` into the run log in `docs/agents.md` after each rehearsal. Do the forced failure and the live backend switch once.
6. **Mentor questions** (in person, Saturday morning):
   - Hyphenate: does PE add-on integration count as a finance team corner, and does a learned policy count as "improves with every correction"?
   - Factory: does the Python Droid SDK count for "Building with the Droid SDK" when the tools call our own gateway?
   - Tiger: the free-tier fork limit, and whether the MLH judges want a measured number.
7. **Submit the Devpost first draft on devpost.com by Saturday night** (moved from Eric, 2026-10-24). The organizers ask for a draft Saturday night and allow edits until 10am Sunday.
   - Add all four teammates, and opt in to Hyphenate, Factory, Figma, and Tiger Data (the MLH opt-in field).
   - Fill in which backend produced the shown run (`docs/devpost/devpost.md`, the line that asks Cayden).
   - Replace the line about placeholder mockups once Josie's design is in.
8. **The honest-limits card and a one-page summary**, printable, for the table (moved from Eric): what is real, what is inferred, what is cut (purchase accounting, the five-month fiscal year gap), and the four tracks. Base it on `demo-script.md` section 6 and the real-versus-simulated list in `devpost.md`.
9. **Sunday 8am:** wake the Tiger service (free shared services can pause when idle), then check `GET /health` before the table opens.
