# Tasks: who builds what

Last updated: 2026-10-24, 08:15.
The product and scope are in `STOCHASTIC.md`. This file only splits the work.
Josie owns UI and UX only. She gets no other task.
Swap tasks freely and tell the team when you do.

## State of the build

The backend runs the whole deal end to end on the scripted backend: mapping, two flags with computed effects, consolidation with a tie-out, covenant EBITDA and debt, leverage 0.76x against 2.50x, Reviewer pass, controller approval, hash-chained log, and policies the Mapper applies on the second run. 115 tests pass. [verified: `backend/tests/`]
The Droid backend ran the whole deal live with Claude Sonnet 5.5 at 03:30 and is recorded. Not yet run live: the Anthropic backend (no key in `.env`).
Done 2026-10-24 and merged to `main`: the Note 2 answer key and Mapper score (Eric), the Devpost text (Eric), the recorded model runs (Sonnet 5.5 is the default replay), the tool guardrails, typed case, stage events, and CSV upload (Tri).
Done 2026-10-24, evening: the console on `GET /deals/{id}/case` (flag card, verdict line, combined table, mapping, log, backend badge, second-run moment), and the EBITDA items (stock compensation and the $4,019K pension figure applied, transaction costs kept at zero).
Done 2026-10-24, 08:00 (commit 08b2629): the Tiger Cloud store (`STORE=postgres`), with the audit log as an append-only TimescaleDB hypertable and a reload on start. Tiger Data is a target track (D15).
Not yet done: Tiger forks, the compliance certificate, the sensitivity figures, the timeline route, the Anthropic run or its removal, the rehearsals, the Devpost submission, the demo video.
Each person's open list, in order, is in their task file in `tasks/`. The lists below are the summary.

## The four seats

| Person | Area | Branch | Folders |
| --- | --- | --- | --- |
| Cayden | Agent layer, gateway, demo run | `cayden/agents` | `backend/app/agents/`, `backend/app/gateway/`, `backend/app/core/` |
| Josie | UI and UX only | `josie/design` | `frontend/`, `docs/design/` |
| Eric | Data, answer key, facts, Devpost | `eric/data` | `data/`, `scripts/`, `evals/` |
| Tri | Math tools, tests, API | `tri/tools` | `backend/app/tools/`, `backend/app/api/`, `backend/app/db/`, `backend/tests/` |

Cayden wrote first versions of `backend/app/tools/finance.py`, `backend/app/api/routes.py`, `backend/app/db/fixtures/kewaunee.py`, and `backend/tests/test_trust_rules.py` so the pipeline could run. Tri and Eric own them from here.

## Shared contract (done)

The contract is in `backend/app/core/models.py` and described in `architecture/gateway-and-api.md`.
The console reads one route, `GET /deals/{id}/case`, and writes three: `POST /deals/{id}/run`, `POST /work-items/{id}/answer`, `POST /work-items/{id}/approve`.
Change requests go to Cayden.

## Cayden

Done on 2026-10-24: the contract, the gateway rewrite (per-role permissions, run-id checks, Reviewer-pass check, reverse, controller default, agent memory), the three roles, `run_agent` with four backends, the job runner, the recording and replay, the Droid probe script, and the docs.

Done at 03:30: the `droid` CLI, the probe (Claude models are on our key), and a full Droid run with Claude Sonnet 5.5, recorded.

Done at 05:10: Haiku 5.5 as the default model with per-role overrides, the failure switch rehearsed, the pitch words written, the Haiku run recorded. See `tasks/cayden.md` and `agents.md`.

Done at 08:00: the Tiger Cloud store and Tiger Data as a target.

Done at 08:50 (`tasks/cayden.md`): tasks 1 to 4 and 8, plus the machine half of 5 and 7. Done at 09:00: Tiger forks (task 3), after Cayden chose to delete `larp-city`. Still open, and each needs a person: the stopwatch rehearsal, the mentor questions, and the Devpost submission. The Sunday wake-up is scheduled in Cayden's Claude session for 07:52 (it runs only if that session is still open).

Open (details in `tasks/cayden.md`):
1. Run the demo on `STORE=postgres` and rehearse the restart moment (the case, the log, and the policy come back).
2. Tiger forks, one per flag option: spike the fork time first, build only if it is fast enough, drop it by 8pm if not.
3. The Anthropic backend: record a run with a key, or remove it from the fallback chain.
4. Rehearse the 2:00 with a stopwatch, with the forced failure, and log the credit total.
5. Ask the Hyphenate, Factory, and Tiger mentors the questions in `tasks/cayden.md`.
6. Submit the Devpost first draft by Saturday night, with the four tracks opted in (from Eric).
7. The honest-limits card and a printed one-page summary (from Eric).
8. Sunday 8am: wake the Tiger service and check `GET /health`.
9. Decide when to build the Brief Reader's stage 1 (D20), given the 8pm freeze. The build list is in `architecture/brief-reader.md` sections 7 and 8. Until it is built, the pitch says a person writes the brief.

## Eric

Tasks 1 to 6 done 2026-10-24, merged in PR #2. Figures were refreshed to the post-interest-income values the same day.

No open tasks. On 2026-10-24 at 08:20 his open work moved: the Devpost submission and the one-page summary to Cayden, the certificate wording and the input checks to Tri.

Done:

1. Check every figure in `backend/app/db/fixtures/kewaunee.py` against the filings. The links are in the file header and in `research/real-deal-candidates.md`. Flag any difference to Cayden; the tools recompute from the fixture.
2. Export the two input files as CSVs in `data/` (git-ignored) with the fixture's columns, and write the loader script in `scripts/` so the fixture can read CSVs later.
3. Build the answer key from Note 2 of Ex 99.2 in `evals/`: each Nu Aire line and its Kewaunee line. Score the Mapper's output from `GET /deals/{id}/mappings` against it, and write the score down with the date and the backend.
4. Write the facts behind the flag on one card: the "Financing liability" line, its three parts ($27,782K, $20,563K, $22,540K), and the agreement's exclusions, with quotes under 15 words and the exhibit and section.
5. Write the brief as prose for the Devpost and the slide: the 2.50x limit, Section 4.8(a), the definitions of Senior Funded Bank Debt and EBITDA.
6. Write the Devpost text and the real-versus-simulated list by Saturday night. Include: statement lines are real, account detail is not claimed, the rent and transaction-cost inputs are inferred, which backend produced the shown run, and that agent memory is policies written by the gateway.

## Tri

Tasks 1 to 5 done 2026-10-24, merged in PR #1.

Open (details in `tasks/tri.md`):
7. Run the Tiger store tests (`TEST_DATABASE_URL`) on every merge.
8. `GET /deals/{id}/certificate`: the draft compliance certificate, refused until approved, with its wording from Ex 10.1 (from Eric).
9. Sensitivity on the verdict: the add-back and the rent figure that flip the whole-line reading, and a recheck of the rent and transaction-cost inputs (from Eric).
10. `GET /deals/{id}/timeline` on the hypertable, and the store's average write time on `GET /health`.

Done, plus the video:

1. Review `backend/app/tools/finance.py` and own it. Check the EBITDA build (net income plus interest, taxes, D&A; add-backs; rent deduction) against Ex 10.1's definition. Add any add-back the agreement names that we left at zero, with its source. Done 2026-10-24. Reviewed against Ex 10.1; covenant EBITDA now subtracts interest income as Addendum I requires.
2. Add tests: a test per tool with hand-computed expected values from the fixture, a test that `consolidate` refuses an unapproved flagged mapping, and a test for `limit_test` at exactly 2.50x. Done 2026-10-24. Per-tool tests with hand-computed values, the unapproved-flag refusal, and `limit_test` at exactly 2.50x.
3. Add `debt_capacity` to the verdict in `GET /deals/{id}/case` (it is already in the `limit_test` output) so the console can show the covenant headroom. Done 2026-10-24. `debt_capacity` and `debt_capacity_run_id` are on the verdict.
4. Make `POST /deals` accept two CSV uploads and a brief, using Eric's loader, so a judge can try an unseen input. Keep the route thin. Done 2026-10-24. `POST /deals` takes two CSVs and a brief; 422 names the file, row, and column.
5. Make the SSE stream also emit stage changes, so the console can refresh the case without polling. Done 2026-10-24. `GET /deals/{id}/stream` sends `stage` events as well as audit rows.
6. Cut the demo video if the team agrees on one. Hyphenate wants a video that opens with the moment. [verified: `hyphenate-workshop.md`]

## Josie (UI and UX only)

Josie works on the design only. She has no other task.
Done 2026-10-24: the console is on `GET /deals/{id}/case` and the three write routes (`frontend/README.md`). Josie owns its look from here.
Inputs for the design:
- The case shape, the flag shape, and the verdict shape are in `architecture/gateway-and-api.md`.
- The flag card shows the question, the evidence quotes, and the options with their computed effects; the default option is marked.
- The verdict line shows leverage against the limit, OK or Over the limit, the room left, and the Reviewer badge; the Approve button is live only when `approval_state` is `PROPOSED`.
- A small "learned" chip on a mapping or a tag whose reason starts with "Policy", and a second-run moment: after `POST /dev/reset`, Run again shows no flag.
- The backend badge from `GET /health` ("scripted", "anthropic", "droid", "replay").
- The design rules are in `design/README.md`, and the Figma file is linked there. The Figma track needs the frame on screen in the pitch.
- Coming from the backend today (each owner tells Josie when it lands): a Download certificate button (Tri), a fork id and state on each flag option (Cayden), the store badge from `GET /health` (`memory` or `postgres`), and the sensitivity line on the verdict (Tri).

## Everyone

- Claim Factory credits with the form in `sponsors/factory.md`, if you want them.
- Install the `droid` CLI on the demo laptop.
- Pull `main` and run `backend/.venv/bin/python -m pytest` in `backend/` before you merge.

## Track checklist

| Track | Owner of the proof | What must be true by Saturday night |
| --- | --- | --- |
| Hyphenate | Cayden (demo, Devpost, the real-versus-simulated list) | The real deal runs end to end with the flag on the console. The video opens with the flag moment. The second run shows memory. |
| Factory | Cayden | Done: all three agents ran on Droid with Claude Sonnet 5.5, recorded. Keep it working through the rehearsals. |
| Figma | Josie (design) | The console frame exists in Figma and the console follows it. Figma is on screen in the pitch. |
| Tiger Data | Cayden (store, forks), Tri (timeline, write time) | Done: the store writes through to Postgres on Tiger Cloud, with the audit log as a TimescaleDB hypertable. Done: `STORE=postgres` on the demo laptop, the restart moment rehearsed, and what-if forks per covenant flag (D17). Still to do: show the fork line and the restart once in the pitch, and opt in on Devpost. |

## Order of work

1. **Saturday morning (done).** Console on `/case`, figure check and CSVs, tool review and tests, Droid runs, the Tiger store.
2. **Saturday until 6pm.** Josie: the UI. Cayden: `STORE=postgres`, the restart moment, the fork spike, then forks. Tri: Tiger tests, certificate with its wording, sensitivity with the input recheck, timeline. Cayden also: the one-page summary. Mentor questions asked.
3. **Saturday night.** Feature freeze at 8pm. Devpost draft submitted (Cayden). Full rehearsals with the failure switch and the restart. Demo video.
4. **Sunday morning.** Fix only blockers. Submit before 9am. Practice the 2 minutes once more before judging at 10:30am.

## Risks to watch

- The naive-versus-covenant gap rests on the inferred rent deduction and zero transaction costs. If Tri or Eric change them, re-read the flag effects before the pitch. The code recomputes; the words must follow.
- The EBITDA definition items moved EBITDA to 28,379 and leverage to 0.76x on 2026-10-24; the pitch words, the Devpost, and the tests use the new figures. Since 2026-10-24 evening the whole-line reading is computed as filed, 2.84x, with $3,470K of EBITDA to spare, so the inferred rent and the transaction costs no longer move it (D18).
- The Droid subprocess can fail live. The switch, the fallback chain, and the recording are the answer. Rehearse it.
- The console is on the new API as of 2026-10-24. Rehearse the 2:00 on it with the stopwatch.
- The Tiger service is on the free shared tier and can pause when idle. If it cannot be reached, the API starts in memory and `/health` says why; wake it before judging.
- A Droid run from the console overwrites `backend/recordings/*.json`. Check `git status` before committing, and move a new run into its own folder instead of replacing the default replay.
