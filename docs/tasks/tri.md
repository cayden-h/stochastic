# Tri: math tools, tests, API

Branch: `tri/tools`. Pull `main` into it first; it is behind.
Folders: `backend/app/tools/`, `backend/app/api/`, `backend/app/db/` (except `postgres.py`, which Cayden owns), `backend/tests/`.

## Done (2026-10-24, merged in PR #1)

1. `finance.py` reviewed against Ex 10.1; covenant EBITDA subtracts interest income as Addendum I requires.
2. Per-tool tests with hand-computed values, the unapproved-flag refusal in `consolidate`, and `limit_test` at exactly 2.50x.
3. `debt_capacity` and `debt_capacity_run_id` on the verdict in `GET /deals/{id}/case`.
4. `POST /deals` takes two CSVs and a brief; a 422 names the file, row, and column.
5. `GET /deals/{id}/stream` sends `stage` events as well as audit rows.

## Open, in order

1. **Run the Tiger tests on every merge.** The 5 tests in `tests/test_postgres_store.py` skip unless `TEST_DATABASE_URL` is set, so the normal run never touches the real database. Set it to the Tiger URL with your own `DB_SCHEMA` (for example `stochastic_tri`) so you do not take the demo schema's lock. Add the command to `backend/README.md` and to the merge rule in `docs/tasks/README.md`. About 20 minutes.
2. **Compliance certificate route** (the strongest "would you hire it" proof). `GET /deals/{id}/certificate` returns the draft certificate the controller would send PNC: the test period, covenant EBITDA with its build, Senior Funded Bank Debt with its parts, the ratio against 2.50x under Section 4.8(a), the verdict, the controller's flag answers, and the run id behind every number. Refuse it (409) until the result is approved. Return Markdown, and HTML if it is cheap; no PDF library. Write the wording too (moved from Eric): find what Ex 10.1 says the compliance certificate must contain, the test period, and the delivery deadline, and put the sections and fixed wording in `docs/devpost/certificate.md` with the exhibit and section for each and quotes under 15 words. Tests: refused before approval, and every figure equals its tool run. Tell Josie the route so she can add a Download button. About 3 hours with the wording.
3. **Sensitivity in `limit_test`.** (Superseded on 2026-10-24 evening: the whole-line reading is now as filed; see the note at the end of this file.) Add the EBITDA add-back that would bring the whole-line reading under 2.50x (about $403K today), and the rent deduction at which it would cross. Put both on the verdict as `naive_flip_addback` and `naive_flip_rent`, each with its run id. This covers our weakest input, the inferred $1,970K rent. Test it by hand like the other tools. About 1 hour.
   - Recheck the two inferred inputs while you are in there (moved from Eric). The Statesville cash rent ($1,970K): is the 10-K obligations-table figure right for the test period? Transaction costs ($698K expected, kept at zero): does the 8-K/A or Ex 10.1 say whether they count in the test period? Applying them would put the whole-line reading under 2.50x. Write the sources or a better figure into `evals/fixture_check.md`, and tell Cayden if a figure changes so the pitch words follow.
4. **Timeline route on the hypertable** (for "performance-driven" in the Tiger prize). `GET /deals/{id}/timeline` returns audit rows counted per actor and per stage in time buckets (`time_bucket` on `audit_log.at`) when the store is Postgres, and the same shape computed in memory otherwise. Built by Tri in e233566 on `audit_log`. Optional later: read the continuous aggregate `audit_activity` (bucket, ledger, actor, action, rows; real time) for widths of one minute or more. `ledger_runs` has one row per run (both added by Cayden's agent, 2026-10-24 afternoon). Also add the store's average write time (queue to commit) to `GET /health`, so we can quote one measured number. About 1 hour.
5. **Keep the tests green** on every merge, including the Tiger tests from task 1.
6. **Cut the demo video** if the team agrees on one. Hyphenate wants a video that opens with the flag moment. Record it after Josie's UI lands; a draft on the current console is fine before that.

## Changed in your folders on 2026-10-24 evening (Cayden's agent, commits 0e3829f and 3938ca9 on `cayden/risk-fixes`)

From the risk review (D18 in `decisions.md`); every change has tests, 167 offline and 176 with Tiger.
- `backend/app/tools/finance.py`: `ebitda(..., as_filed=True)` stops at reported EBITDA (no add-backs, no deductions) and returns `basis`; `limit_test(..., naive_ebitda=...)` divides the naive debt by that EBITDA and returns `naive_ebitda`. The whole-line reading is now 2.84x with `naive_flip_addback` 3,470K, so your task 3 numbers ($403K, the $698K flip) no longer apply. The leverage tool description says run ids only.
- `backend/app/api/routes.py`: the sensitivity run uses the whole-line option's covenant_debt and as-filed ebitda runs (`naive_ebitda_run_id`), so `naive_flip_rent` is no longer on `/case`; a failed background run sets the `run_failed` stage; `gw.running` is shared with `/dev/reset`.
- `backend/app/api/schemas.py`: `naive_ebitda` replaces `naive_flip_rent` in the verdict.
- `backend/app/main.py`: `/dev/reset` refuses with 409 during a run, frees the fork slot, and returns `keep_memory`; `app.state.gateway` is set for tests.
- The gateway (Cayden's) now refuses numbers from agents in `leverage` (system only), and checks that `debt_run_id` and `ebitda_run_id` name runs of those tools.
- Tests touched in `backend/tests/`: `test_api.py`, `test_demo_run.py`, `test_trust_rules.py`, `test_mapper_retry.py`, and new `test_gateway_guards.py` and `test_demo_reset.py`.
