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

## Build phase 2: D19 and D20 (2026-10-24 night)

The split for everyone is in `../TASKS.md`, "Build phase 2".
Specs: `design/review-companion.md` (D19) and `architecture/brief-reader.md` (D20).
Branch: `tri/phase2`, cut from `main` after Cayden's contract (C1) lands.

### T1. Edit-aware tools (about 2 hours, blocks Cayden's C2)

In `backend/app/tools/finance.py`:
- `consolidate`, `ebitda`, `covenant_debt`, and `tie_out` take an optional `edits` list (the `Edit` model from C1).
  - An `amount` edit replaces that company's value on that line before the sums.
  - A `remap` edit moves the target line to its new platform line, which can change its section.
- Each tool returns the edits it applied, with their ids, so a run shows which edits it used.
- Reverted edits are ignored.
- Update (Cayden's agent, 2026-10-24): the gateway's contract is the "T1 contract" section of `architecture/gateway-and-api.md`; `tie_out` takes no edits, and `consolidate`, `ebitda`, and `covenant_debt` return `edits_applied`.
Tests in `backend/tests/test_tools_edits.py`, with hand-computed values:
- An amount edit on a target income-statement line moves covenant EBITDA by exactly the change, and leverage by the hand-computed amount.
- A remap from cash to other current assets moves the amount between those lines, and the balance sheet still ties out.
- An edit that breaks the tie-out makes `tie_out` fail, and approval is then refused.
- Reverting the edit restores every figure exactly.

### T2. Edit routes (about 1.5 hours, with C2)

In `backend/app/api/routes.py` and `schemas.py`, thin over the gateway:
- `POST /deals/{id}/edits` with `{"kind": "amount", "company", "line", "value"}` or `{"kind": "remap", "company", "line", "platform_line"}`. Returns the edit, the new `verdict` and `result`, and `reasons`.
- `POST /edits/{id}/reason` with `{"chip": 0}` or `{"text": "..."}`, and `{"remember": true}`.
- `DELETE /edits/{id}`.
- `GET /deals/{id}/case` includes `edits` and `adjustments`.
- Errors: 409 when the result is not `PROPOSED`, and 422 that names the field on a bad value.
- Add an `edit` stage event to `GET /deals/{id}/stream`, so the console refreshes.
Tests in `backend/tests/test_api_edits.py`: the demo beat end to end through the routes.

### T3. The final files (about 2 hours)

- `GET /deals/{id}/export.xlsx`, which returns 409 before approval. Use `openpyxl` and add it to `backend/requirements.txt`. Three sheets, from `review-companion.md` section 8:
  - **Combined**: the final values in platform order. Each edited cell has a light amber fill (`FBEBC8`) and a cell note with who, when, the old value, the reason, and the policy id.
  - **Edits**: one row per edit, with the line, company, agent value, final value, reason, who, when, and policy id.
  - **Audit**: the run id behind every number.
- The certificate (`backend/app/api/certificate.py`) lists each edit and its reason, and uses the edited figures.
- Tests: refused before approval, every figure in the workbook equals its tool run, and an edited cell has its note.

### T4. Brief Reader routes and tests (about 2 hours, with C3)

- `POST /deals` takes `agreement_txt` (a `.txt` upload) or `brief`, exactly one. Sending a Brief JSON still skips the reader.
- A route for the controller to enter the adjustment amounts on a draft Brief, with their source: `POST /deals/{id}/brief/amounts`.
- `POST /deals/{id}/brief/approve`.
- `GET /deals/{id}/case` includes `brief_draft` and its citations.
- `db/memory.py`: the `agreement` kind.
- `backend/tests/test_brief_reader.py`: the ten tests in `architecture/brief-reader.md` section 8. Use the synthetic agreement text from Eric (E3), never the cached filings.
- Status (2026-10-24, verified by `backend/tests/test_api_brief.py`, 27 tests): the three routes and `brief_draft` on `/case` are in, the `stage` event carries `brief_status`, and only `human:controller` amends or approves the Brief.
  The gateway rule tests are Cayden's `test_brief_reader_gateway.py`; the route tests use a synthetic agreement written in the test and the Ex 10.1 excerpt in `backend/tests/fixtures/`, not Eric's E3 text, which is not in the repo yet.

### T5. Keep the tests green

Run the full suite and the Tiger tests on every merge (rule 5 in `tasks/README.md`). The count goes up from 176, so update it in `backend/README.md`.

## Notes for Cayden (phase 2, from tri/tool/new)

These come from the review of `tri/tool/new` (findings C-1, I-1, I-4, I-6, M-1, M-4, M-6) and need changes in files Tri does not own.
- `backend/app/db/postgres.py` needs three `KINDS` entries, or edits, learned adjustments, and agreements are lost on a Tiger restart: `"edit": ("edits", Edit, False)`, `"adjustment": ("adjustments", LearnedAdjustment, True)`, `"agreement": ("agreements", AgreementText, False)`.
- A Tiger round-trip test of one `Edit` and one `LearnedAdjustment` across `reset_deals(keep_memory=True)` would prove those entries.
- `gateway.run_tool` must pass `edits=store.active_edits(deal_id)` to `consolidate`, `tie_out`, `ebitda`, and `covenant_debt`, and record the edit ids in the run inputs.
- `Edit.line` must be the source line name (`SourceLine.line`) of the company named, not the row name the Combined table shows (I-1).
- A table cell that holds several target lines is edited one source line at a time; the console has `row.target_lines` for that.
- The comment on `Edit.line` in `models.py` and the e_001 example in `docs/architecture/gateway-and-api.md` should say this, since "Selling, general and administrative" is not a Nu Aire line.
- The remap path must replace the stored mapping's `platform_line` rather than add a second `Mapping`, or `consolidate` raises "mapped twice" (I-4).
- The simpler path is to store only the `Edit` and pass it as `edits=`, since `apply_remap_edits` already moves the line; revert is then just status "reverted".
- C-1 roll-up rule (P4a, verified by `backend/tests/test_tools_edits.py`): an amount edit on an income statement detail line now carries into the totals by a defined rule in `backend/app/tools/edits.py`.
- The sign of a line is inferred from its name, not read from the filing (the fixture figures are verified by the tests): it is -1 when its name contains "cost", "expense", "tax", "provision", or "attributable to the non-controlling", else +1 when it contains "revenue", "sales", "income", "profit", "earnings", or "gain", else -1 (named under `rollup_notes` in the run output).
- With delta = new value - old value in USD thousands, the first total after the edited line moves by +delta when its name starts with "Total" (a group total), and every later total whose name does not start with "Total" (a running total such as Net Income) moves by sign * delta.
- No other line moves and taxes are not recomputed, so a 500 cut in Nu Aire "General and Administrative" raises covenant EBITDA by exactly 500 (28,378.845 to 28,878.845, leverage 0.749).
- Every line the carry moved is listed under `rollup` as `{edit_id, company, line, delta}` in the consolidate, ebitda, and covenant_debt outputs.
- An income statement detail edit is refused when no later total line of that company is a net income line (its name holds "net income", "net earnings", or "net loss"), because the edit could not reach EBITDA and would look applied.
- A balance sheet detail edit stays refused, because its nesting is not derivable from order alone and the tie-out would hide a wrong carry.
- A `rolls_into` field with a sign on each fixture line would replace this rule later.
- `tie_out` lists the edits passed to it; the gateway should take `edits_applied` from the consolidate run it checks (M-1).
- Each result revision C2 writes should carry the Reviewer's run ids (`limit_test` with `debt_capacity`, `tie_out`), or the Audit sheet shows "no run" (M-4).
- C2 should copy the chip label into `reason_text`, or the final files say "Reason: chip 1." (M-6).
