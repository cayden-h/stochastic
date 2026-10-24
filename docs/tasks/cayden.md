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
- Task 9: a one-shot launchd job (`~/Library/LaunchAgents/com.stochastic.sunday-wake.plist`, script `~/.stochastic/sunday-wake.sh`) runs Sunday 07:50 whether or not a Claude session is open: it starts the Tiger service if paused, logs `/health` to `~/Library/Logs/stochastic-sunday-wake.log`, shows a notification, and removes itself. Dry run passed 2026-10-24 09:02. The laptop must be awake.
- Task 7, in progress at 09:10: on the existing Devpost draft ("Stochastic", 2 of 5 steps), the story (Inspiration through the real-versus-simulated list, from `devpost/devpost.md`) and 17 built-with tags are filled in. Not saved yet: Cayden reviews and presses Save & continue. Still empty: the video link (required by the form), images, and the next steps (Additional info with the track opt-ins and the table number).
- Tiger, done 2026-10-24 afternoon (Cayden's agent): `ANALYTICS_SQL` in `postgres.py` (continuous aggregate, columnstore policy, BM25 search, `covenant_runs`, `ledger_runs`, `run_stats`), applied to the live schema; the Tiger MCP password saved; the "Tiger in SQL" part of `demo-script.md` section 5; two rows of Tiger cards on the Schocastic team board in Figma (`technologies` page); four gallery images in `devpost/images/`. Tests at merge on top of 56749cc: 150 offline, 159 with Tiger.
- Task 4: Anthropic is out of the default fallback chain (no key); the default is `scripted`.
- Task 5, the machine part: three cold runs in a headless browser, timed. The stopwatch run of the 2:00 is still Cayden's.
- Task 7, the prepared part: the backend line in `devpost/devpost.md` is filled in as planned. Submitting on devpost.com is still Cayden's (it needs his login).
- Task 8: `devpost/one-pager.html` and `one-pager.pdf` (page 1 the summary, page 2 the honest-limits card), Letter size.
- Found and fixed on the way: the count-everything reading on every covenant flag, the Learned chip from `policy_id`, 409 on a second run, live runs no longer overwrite the pinned replay, the Mapper on Sonnet 5.5, and console overflow at 768 and 1440.

## Task list (from the risk review, 2026-10-24 evening)

The six-part risk review is the source for the new items.
Checked items were verified against the tree or the Done list above on 2026-10-24.
Items in another person's folder say who to ask.

### Earlier open items

- [x] Make the demo run on Tiger (`STORE=postgres`, `GET /health` shows postgres). Done 08:50.
- [x] Rehearse the restart moment and write it into `demo-script.md` section 5. Done 08:50.
- [x] Tiger forks, one per flag option (D17). Done 09:00.
- [x] Anthropic backend: cut from the default fallback chain; the default is `scripted`.
- [x] Honest-limits card and one-page summary (`devpost/one-pager.html` and `.pdf`).
- [x] Sunday wake for Tiger: the launchd job runs Sunday 07:50. The laptop must be awake.
- [ ] Rehearse the 2:00 with a stopwatch on Josie's console and `STORE=postgres`. The machine runs are done; the stopwatch run is not.
- [ ] Mentor questions: Hyphenate (does PE add-on integration fit; does a learned policy count as "improves with every correction"), Factory (Droid SDK), Tiger (fork limit, a measured number).
- [ ] Submit the Devpost first draft by Saturday night: save the story, add the four teammates, tick the track opt-ins, fill in the table number.

### 1. The moment must show up on stage (tonight, about 1 hour)

- [x] Pin a first-run recording for replay. `backend/recordings/mapper.json` is a copy of `droid-console-0751` (a memory run, no covenant flag). Copy `recordings/sonnet-5-5/*.json` to the top level, and add a test that the pinned replay raises a covenant flag. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Reset with memory cleared between judges. `/dev/reset` keeps memory by default (`backend/app/main.py:61`). Use `POST /dev/reset?keep_memory=false`, fix `demo-script.md` section 9, and ask Josie for a "Fresh deal (clear memory)" button. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Set `DROID_TIMEOUT=75` in `.env`. It is not set, so a hung Droid waits 240 s per role. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Fall back to scripted when the gateway refuses the Mapper twice, instead of failing the run (`backend/app/agents/runner.py`, `jobs.py`). Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Clear the fork slot and the running-job set on reset (`whatif.py`; the route part is Tri's). Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Run the `ANALYTICS_SQL` in its own try block after the migration, run the tests with `TEST_DATABASE_URL`, then commit it. Done in `cayden/tiger-sql`: a failure sets `store.analytics_error` on `GET /health`, and the store stays on Postgres.
- [x] Fix the stage words in `demo-script.md`: line 52 "forty-eight million" becomes "about forty-nine million"; lines 237 and 246 and Q&A 8, 9 and 21 say live Droid with the backend on the badge, not "recorded or scripted"; Q&A 17 drops the Postgres store; Q&A 4 says three debts; Q&A 12 matches the hypertable refusal. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Fix the "Anthropic never ran" claims: Eric ran it on his key (one full run, 32 of 33, and 50 Mapper trials). Docs and the `runner.py` comment done 2026-10-24 evening.
- [x] One test count everywhere (167 offline, 176 with Tiger, after the risk fixes): README says 103, the one-pager says 125. Re-render the PDF. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Refresh the README status: Postgres is built, intercompany removal is cut. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Prepare shell aliases: `source scripts/demo.sh`, then `demo_fresh`, `demo_again`, `demo_scripted`, `demo_replay`, `demo_run droid`, `demo_health`.

### 2. Close the gateway holes (about 3 hours, `backend/app/gateway/`)

"The gateway, not the prompt, enforces it" is the pitch line, and today a model can get around it in three ways.

- [x] The gateway refuses a `not_debt` tag from any model unless it cites a live policy learned on that company's line. Policies are scoped to the company instead of shown as a pre-selected flag, so the second-run moment stays. This also closes the prompt-injection path through line names. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] The final result must cite the Preparer's own debt run (naive=false, made after the last answer), and the leverage run must cite those run ids. Remove the raw value inputs from `leverage` (ask Tri, `backend/app/tools/`). Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] The gateway works out the Reviewer pass itself from the tie_out and limit_test runs on this result, and refuses a pass with no run ids or with runs from another deal. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] A reversal retires the policy it created and writes an audit row. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [ ] Optional, not done: the gateway opens a covenant flag for any debt-like line with a covenant note that no policy settles. The not_debt rule and the first-run replay cover most of it: a model can no longer exclude the line itself.

### 3. Option a, before the video (ask Tri for `finance.py`, Eric for the fixture)

- [x] Redefine the naive reading as balance-sheet debt over reported EBITDA (2.84x, $3,470K of EBITDA margin). Today option a counts the Statesville lease as debt and still deducts its rent, which is 2.37x if made consistent. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Update the tests, `flag-card.md`, `demo-script.md`, the one-pager, and the Devpost text with the new figures, and record a new replay. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Say "covenant headroom of about $49M" with the $5M acquisition basket and the undrawn revolver, not "room for the next deal". Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Label the check as the pro forma test in the acquisition compliance certificate, not "at close". Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Do not rebuild Kewaunee to LTM 2024-10-31 tonight. Put it on the honest-limits card and rehearse the one-line answer. Done 2026-10-24 evening (0e3829f, 3938ca9).

### 4. Submission

- [ ] Record a 60 to 90 s video that opens on the flag card, after section 3. Upload it unlisted and add the link to Devpost.
- [ ] Make `cayden-h/stochastic` public before 9am Sunday. It is private now. The secret scan was clean.
- [x] Run Droid once on a second sample deal and keep the result: the QuickBooks sample company raised 2 questions (scripted: 40) and ended at 1.03x, Reviewer pass (`evals/unseen-input-quickbooks.md`). A judge's own trial balance runs with `scripts/run_unseen_deal.py`.
- [x] Fix `ideation/tracks.md` in the CalHacks repo: Tiger Data is a target in both places now.
- [x] Add one Tiger benchmark line: BM25 top 10 in 0.09 ms against 3.9 ms for an ILIKE scan; the continuous aggregate in 0.14 ms against 0.38 ms from the raw log (`scripts/tiger_bench.py`, in the Devpost and `sponsors/tiger-data.md`).
- [ ] Learn the one-line competitor answer: "They read the agreement or combine the books; this does both, and stops on the ambiguous line." It is written into `demo-script.md` Q&A 6a.

### 5. Hand to Josie

- [x] Put the option ratios directly under the flag question, as large numbers, with "Over the limit" in red. The evidence goes in a collapsed block. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Keep "read as filed, counting the whole financing line: 2.84x, over the limit" next to the final verdict. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] A progress row during the runs ("Mapper... 23 s"). Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Turn off the Next.js dev indicator, or demo from `next build && next start`. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Count "Learned" only from a real `policy_id`, not the reason text. Done 2026-10-24 evening (0e3829f, 3938ca9).
- [x] Review screenshots: superseded, the issues they showed are fixed in the console (commit 3938ca9) and checked at 1280 and 1920 in a headless browser.
