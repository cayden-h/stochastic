# Tasks: who builds what

Last updated: 2026-10-24, 02:30.
The product and scope are in `STOCHASTIC.md`. This file only splits the work.
Josie owns UI and UX only. She gets no other task.
Swap tasks freely and tell the team when you do.

## State of the build

The backend runs the whole deal end to end on the scripted backend: mapping, two flags with computed effects, consolidation with a tie-out, covenant EBITDA and debt, leverage 0.76x against 2.50x, Reviewer pass, controller approval, hash-chained log, and policies the Mapper applies on the second run. 105 tests pass. [verified: `backend/tests/`]
The Droid backend ran the whole deal live with Claude Sonnet 5.5 at 03:30 and is recorded. Not yet run live: the Anthropic backend (no key in `.env`).
Done 2026-10-24 and merged to `main`: the Note 2 answer key and Mapper score (Eric), the Devpost text (Eric), the recorded model runs (Sonnet 5.5 is the default replay), the tool guardrails, typed case, stage events, and CSV upload (Tri).
Done 2026-10-24, evening: the console on `GET /deals/{id}/case` (flag card, verdict line, combined table, mapping, log, backend badge, second-run moment), and the EBITDA items (stock compensation and the $4,019K pension figure applied, transaction costs kept at zero).
Not yet done: the Anthropic run, the rehearsals, the demo video.

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

Open:
1. Put an Anthropic key in `.env` and record a model run: `scripts/record_run.py --backend anthropic`. Commit the recordings.
2. Rehearse the 2:00 with a stopwatch on the console, and write the credit total from `GET /health` into the run log in `agents.md`.
3. Ask a Hyphenate mentor whether PE add-on integration counts as a corner of a finance team, and whether a learned policy counts as the "improves with every correction" signal.

## Eric

All six done 2026-10-24, merged in PR #2. Figures were refreshed to the post-interest-income values the same day.

1. Check every figure in `backend/app/db/fixtures/kewaunee.py` against the filings. The links are in the file header and in `research/real-deal-candidates.md`. Flag any difference to Cayden; the tools recompute from the fixture.
2. Export the two input files as CSVs in `data/` (git-ignored) with the fixture's columns, and write the loader script in `scripts/` so the fixture can read CSVs later.
3. Build the answer key from Note 2 of Ex 99.2 in `evals/`: each Nu Aire line and its Kewaunee line. Score the Mapper's output from `GET /deals/{id}/mappings` against it, and write the score down with the date and the backend.
4. Write the facts behind the flag on one card: the "Financing liability" line, its three parts ($27,782K, $20,563K, $22,540K), and the agreement's exclusions, with quotes under 15 words and the exhibit and section.
5. Write the brief as prose for the Devpost and the slide: the 2.50x limit, Section 4.8(a), the definitions of Senior Funded Bank Debt and EBITDA.
6. Write the Devpost text and the real-versus-simulated list by Saturday night. Include: statement lines are real, account detail is not claimed, the rent and transaction-cost inputs are inferred, which backend produced the shown run, and that agent memory is policies written by the gateway.

## Tri

Tasks 1 to 5 done 2026-10-24, merged in PR #1. Task 6 waits on the team.

1. Review `backend/app/tools/finance.py` and own it. Check the EBITDA build (net income plus interest, taxes, D&A; add-backs; rent deduction) against Ex 10.1's definition. Add any add-back the agreement names that we left at zero, with its source. Done 2026-10-24. Reviewed against Ex 10.1; covenant EBITDA now subtracts interest income as Addendum I requires.
2. Add tests: a test per tool with hand-computed expected values from the fixture, a test that `consolidate` refuses an unapproved flagged mapping, and a test for `limit_test` at exactly 2.50x. Done 2026-10-24. Per-tool tests with hand-computed values, the unapproved-flag refusal, and `limit_test` at exactly 2.50x.
3. Add `debt_capacity` to the verdict in `GET /deals/{id}/case` (it is already in the `limit_test` output) so the console can show "room for the next deal". Done 2026-10-24. `debt_capacity` and `debt_capacity_run_id` are on the verdict.
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

## Everyone

- Claim Factory credits with the form in `sponsors/factory.md`, if you want them.
- Install the `droid` CLI on the demo laptop.
- Pull `main` and run `backend/.venv/bin/python -m pytest` in `backend/` before you merge.

## Track checklist

| Track | Owner of the proof | What must be true by Saturday night |
| --- | --- | --- |
| Hyphenate | Cayden (demo), Eric (Devpost and the real-versus-simulated list) | The real deal runs end to end with the flag on the console. The video opens with the flag moment. The second run shows memory. |
| Factory | Cayden | Done: all three agents ran on Droid with Claude Sonnet 5.5, recorded. Keep it working through the rehearsals. |
| Figma | Josie (design) | The console frame exists in Figma and the console follows it. Figma is on screen in the pitch. |

## Order of work

1. **Saturday morning.** Josie: the console on `/case`. Eric: figure check and CSVs. Tri: tool review and tests. Cayden: Droid CLI, probe, first Droid run.
2. **Saturday afternoon.** Console reads real data and the flag card works. Answer key scored. Anthropic run recorded. `POST /deals` with uploads if time allows.
3. **Saturday night.** Recorded model run committed. Full rehearsals with the failure switch. Devpost draft. Freeze new features.
4. **Sunday morning.** Fix only blockers. Submit before 9am. Practice the 2 minutes once more before judging at 10:30am.

## Risks to watch

- The naive-versus-covenant gap rests on the inferred rent deduction and zero transaction costs. If Tri or Eric change them, re-read the flag effects before the pitch. The code recomputes; the words must follow.
- The EBITDA definition items moved EBITDA to 28,379 and leverage to 0.76x on 2026-10-24; the pitch words, the Devpost, and the tests use the new figures. The whole-line reading is 2.54x with $403K of EBITDA to spare. The $698K of expected transaction costs stays at zero; applying it would put the whole-line reading under the limit (`evals/fixture_check.md`).
- The Droid subprocess can fail live. The switch, the fallback chain, and the recording are the answer. Rehearse it.
- The console is on the new API as of 2026-10-24. Rehearse the 2:00 on it with the stopwatch.
