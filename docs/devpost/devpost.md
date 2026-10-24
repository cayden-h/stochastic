# Devpost draft

Owner: Eric.
Final pass of 2026-10-24, for submission by Sunday 9am.
The sections below follow the Devpost form, in pitch order: the problem, then what Stochastic does, then the proof.
Tags are for the reader: [verified] means a file, a filing, or a test in the repo shows it, and [inferred] means our judgment.
Sponsor and vendor figures are marked self-reported.
The facts behind the flag, with quotes and sections, are in `flag-card.md`, and the lender's definitions are in `brief.md`.
What is still open is listed at the end, with who must answer it.

## Tagline

Merge an add-on's books into the platform's, flag the lines a human must decide, and test the result against the lender's own limit.

## Inspiration

A private equity firm that keeps buying small companies has a gate on every deal.
The lender sets a limit, such as debt below 2.50 times EBITDA, and tests it on the combined company.
So the next deal waits until someone merges two sets of books.
Today that is a controller, a spreadsheet, and weeks: pull the statements, map each line of the new company to the platform's chart, add them up, adjust EBITDA, and prepare the lender's pack.
One vendor playbook puts a full integration at about 12 weeks, and says compliance certificates are due 45 to 60 days after quarter end. [self-reported, Aleph; terms vary per deal]
One wrong mapping flows silently into every number after it. [inferred]

## What it does

Stochastic does the repeatable part of an add-on integration, asks a human about the rest, and remembers the answer.

1. Inputs: the platform's statement lines, the target's statement lines, and a short brief with the lender's limit and its own definitions of debt and EBITDA.
2. Map: a Mapper agent matches each target line to a platform line, with a confidence and a reason, and tags each balance sheet line as covenant debt or not.
3. Flag: the Mapper stops on the lines it should not decide alone. Each flag carries the question, the filing evidence, and the effect of each answer on leverage, computed by code.
4. Combine and test: a Preparer agent calls code tools that combine the books, tie them out, compute covenant EBITDA and debt, and test the limit. A Reviewer agent re-runs the tie-out and the limit test.
5. Approve: the controller approves, and only then does the gateway post the result.

The controller's answer to a flag becomes a policy, written by the gateway.
On the next run the Mapper applies the policy and cites it instead of asking again. [verified: `test_controller_answer_becomes_a_policy_and_the_mapper_applies_it`]

The output is a mapped, combined set of books and a limit check that a human approves.
It is not advice.

## The proof: a real public deal

We ran it on a real add-on: Kewaunee Scientific buying Nu Aire, closed November 1, 2024, for $55M, from public SEC filings. [verified: `docs/STOCHASTIC.md`]
The two companies use different charts of accounts.
The buyer's pro forma filing includes a reclassification table, Note 2, that we use as an answer key for the mapping. [verified: 8-K/A Ex 99.2]

The lender's test is Section 4.8(a) of the PNC Loan Agreement: a "ratio of Senior Funded Bank Debt to EBITDA of less than 2.50 to 1.00". [verified: 8-K Ex 10.1, Section 4.8(a)]
One Kewaunee line, "Financing liability", holds three debts after the close: a Statesville sale-leaseback ($27,782K), the new PNC term loan and revolver ($20,563K), and 8% seller notes ($22,540K). [verified: 10-Q Note G; Ex 99.2 Note 4(h)]
The agreement's definition of Senior Funded Bank Debt excludes subordinated debt and capitalized leases on the Statesville property. [verified: Ex 10.1, definitions]
The Mapper flags the line, and the gateway computes each reading with the tools:

| Reading | Debt | Leverage | Verdict |
| --- | --- | --- | --- |
| Whole line counts, read as filed (reported EBITDA $25,312K) | $71,955K | 2.84x | Over the 2.50x limit |
| PNC debt only (the agreement's reading, the default) | $21,633K | 0.76x | OK |
| PNC debt plus the seller notes | $44,173K | 1.56x | OK |

The same books read two ways are 2.08x apart: a covenant breach, or about $49.3M of covenant headroom. [verified: `test_the_demo_run_beat_by_beat`; headroom is the `limit_test` run's debt capacity]
The headroom is a covenant figure, not money to spend: the next add-on is still capped by the agreement's $5M acquisition basket (Section 5.8(ii)) and the undrawn revolver, about $14.4M. [verified: Ex 10.1; revolver arithmetic]
The whole-line reading is computed as filed, balance sheet debt over reported EBITDA, because counting the Statesville financing as debt while still deducting its rent would mix two readings. [verified: `test_choosing_the_whole_line_reading_is_as_filed_end_to_end`]
The table is the flag the scripted backend raises. [verified: scripted run of the fixture]
The recorded model runs raised the same flag with a different middle reading: 1.76x on Sonnet 5.5, and 0.74x on Haiku 5.5, as computed at the time, before interest income was subtracted. [verified: `docs/agents.md`, run log]

These figures are preliminary.
Covenant EBITDA is $28,379K, built the way the agreement defines it: interest income subtracted, the pension termination expense and stock-based compensation added back, Statesville cash rent deducted. [verified: `evals/fixture_check.md`]
The as-filed reading would need $3,470K more EBITDA to pass, so no add-back or rent estimate in question flips it. [verified: arithmetic, `limit_test` sensitivity run]
The agreement's reading stays far under the limit with or without the inferred inputs. [verified: arithmetic]

Mapping score against Note 2: 33 of 33 scored Nu Aire lines go to the same Kewaunee line as the filed table, on both recorded model runs (Claude Sonnet 5.5 and Claude Haiku 5.5, requested through Factory Droid, 2026-10-24). [verified: `evals/README.md`]
23 of those lines are mapped directly in Note 2, and 10 are inferred from a Note 2 total. [verified: `evals/README.md`]
Four lines Note 2 does not cover are not scored. [verified: `evals/README.md`]
The score covers the line mapping, not the covenant tags. [verified: `evals/README.md`]

## How we built it

- Three stateful agents, Mapper, Preparer, and Reviewer, each a role on a real finance team. Each keeps a session and its policies in the store, not in a process. [verified: `docs/agents.md`, section 6]
- The agents never write to the record and never talk to each other. They call tools only through the gateway, and a plain job runner, which is code, moves work items between them. [verified: `backend/app/agents/jobs.py`]
- The gateway is the only writer. It enforces work-item states, maker-checker (the preparer of an item cannot approve it), tool permissions per role, and a run id on every number. [verified: `backend/tests/test_trust_rules.py`]
- Code does all the deal math: consolidation, tie-out, covenant EBITDA, covenant debt, leverage, and the limit test. A number no tool run produced is refused. [verified: `test_model_made_number_is_refused_even_with_real_run_ids`]
- Every action, allowed or denied, goes in an audit log, and each row is chained to the one before it by hash. [verified: `test_tampering_breaks_the_chain`, `test_agents_cannot_approve_and_denial_is_logged`]
- One function, `run_agent(role, item)`, runs the same role on four backends: Factory Droid, the Anthropic API, scripted rules, and replay of a recorded run. It falls back along a set order, and every result names the backend that produced it. [verified: `backend/app/agents/runner.py`]
- Droid runs each agent in an empty directory with only our gateway tools allowed (`restrict_tools`) and a typed output. [verified: `docs/agents.md`, section 7]
- The store is Postgres on Tiger Cloud: every gateway write goes through to it, the audit log is a TimescaleDB hypertable that refuses UPDATE and DELETE, and a restart loads the record, the log, and the agents' memory back. [verified: `backend/tests/test_postgres_store.py`]
- Each covenant flag's what-ifs go to a zero-copy fork of the ledger on Tiger Cloud, made in about 35 s, so the live record never holds a hypothetical. The controller's answer keeps one option and deletes the fork. [verified: `backend/tests/test_whatif_forks.py`, live run 2026-10-24]
- The record is readable in SQL on Tiger features: BM25 keyword search over every line, reason, flag, and policy (pg_textsearch), a real-time continuous aggregate of the audit log, a columnstore policy on the audit log, and run statistics from the TimescaleDB Toolkit. One view, `ledger_runs`, shows the learning: with agent memory cleared the Mapper asks 2 questions, and with memory kept it asks none and applies 6 policies. [verified: `test_the_record_reads_in_sql_and_survives_the_columnstore`, live ledgers 19 to 23]
- Backend: Python 3.12, FastAPI, Pydantic, Uvicorn, pytest. [verified: `backend/pyproject.toml`]
- Console: Next.js 16, React 19, TypeScript, Tailwind CSS 4. [verified: `frontend/package.json`]
- Design: the Figma file "Stochastic - Reviewer Console" holds a `Tokens` variable collection, seven text styles, five components, and four screen frames. [verified: `docs/design/README.md`]
  The console follows its tokens and rules: one look ("Paper and ink"), state shown by color plus word plus shape, and nothing smaller than 14px. [verified: `docs/design/README.md`]
  The mockups were made for an earlier four-screen workflow, and their numbers are placeholders, not engine output. [verified: `docs/design/README.md`]

## Challenges we ran into

- The face of the balance sheet and the lender's definitions disagree. One line holds three debts with different covenant treatment, and only the agreement says which count.
- Public filings give statement lines, not trial balances, so we map statement lines.
- The two companies have different fiscal years, April 30 and September 30.
- An early Mapper run decided the debt exclusions itself instead of asking. The prompt said not to, so we moved the rule into the gateway: a model's "not debt" tag is refused unless it cites a policy the controller made for that company's line. [verified: `backend/tests/test_gateway_guards.py`]
- A review of our own gateway found that a model could cite the what-if run of an option the controller did not pick, pass raw numbers to the leverage tool, or pass a review with no checks. Each is now refused, with a test per attack. [verified: `backend/tests/test_gateway_guards.py`]
- Our first naive reading counted the sale-leaseback as debt but still deducted its rent from EBITDA. We now compute the whole-line reading as filed, end to end. [verified: `test_choosing_the_whole_line_reading_is_as_filed_end_to_end`]

## Accomplishments that we're proud of

- The backend runs the whole deal end to end on the real filing figures, through the gateway, the tools, and the audit log. [verified: `backend/tests/`, 167 tests pass offline, 176 with Tiger Cloud]
- The flag is real. It comes from a real line in a real filing, and the answer moves the leverage verdict. [verified: `test_mapper_flags_the_financing_liability_and_effects_are_computed`]
- The whole deal ran through Factory Droid with our gateway tools, once with Claude Sonnet 5.5 and once with Claude Haiku 5.5 requested, and both passed review at 0.77x as computed then; the Sonnet recording replays at 0.76x today, after the EBITDA definition items were applied. [verified: `docs/agents.md`, run log]
- After a reset, the same deal runs with no flag, because the Mapper applies the controller's policy, and the log shows `policy:apply`. [verified: `test_controller_answer_becomes_a_policy_and_the_mapper_applies_it`]

## What we learned

- Depth on one workflow says more than breadth. The hard part of an add-on is not adding numbers, it is deciding what each line is under the lender's rules.
- Agents are most useful when they know what they must not decide. Precision before recall: an unsure line becomes a flag.

## What's next

These are roadmap.
None is built.
- An upload screen and route for new deals.
- A fourth agent, the Brief Reader, that drafts the brief from the credit agreement with a verbatim quote for every field, checked by code and approved by the controller.
- A covenant schema for sponsor-style agreements: several covenants, step-downs, cash netting, percent-of-EBITDA caps, and pro forma acquisitions.
- Purchase accounting with a provisional label, and intercompany eliminations.
- A second deal, to show the policies carrying over.
- Confidence calibration from the answer key.
- Checking the NetSuite, Sage Intacct, Microsoft Dynamics 365, Epicor, and Infor layouts against real exports.
- Live connectors that pull the trial balance from those systems instead of a file export.
- Other corporate-finance situations.

## Built with

Python, FastAPI, Pydantic, Uvicorn, pytest, Factory Droid SDK, Claude, Anthropic Python SDK, Tiger Cloud (PostgreSQL, TimescaleDB, TimescaleDB Toolkit, pg_textsearch), Tiger CLI, Tiger MCP, psycopg, Next.js, React, TypeScript, Tailwind CSS, Figma.
All are in `backend/pyproject.toml`, `frontend/package.json`, or `docs/design/README.md`. [verified]
The Anthropic SDK backend ran on a teammate's key: one full recorded run (0.76x, Reviewer pass, 32 of 33 against Note 2) and about 50 Mapper trials scoring 27 to 33. The demo laptop has no key, so it is not in the stage fallback chain. [verified: `evals/README.md`, `backend/recordings/anthropic-haiku-5-5/`]

## What is real and what is simulated

Say this list on stage, and paste it into Devpost as is.
It covers the honest-limits statement in `docs/demo-script.md`, section 6.

Real:
- The deal, the filings, and the lender's covenant are real and public. [verified]
- Every amount in the input files matches its SEC filing. [verified: `evals/fixture_check.md`]
- The gateway, the math tools, the tie-out check, and the audit log with its hash chain are real code, and they run live in the demo. [verified: `backend/tests/test_trust_rules.py`]
- The flag and the leverage effect of each answer are computed by the tools, not written by a model. [verified: `test_mapper_flags_the_financing_liability_and_effects_are_computed`]
- Agent memory is real: it is policies the gateway wrote from the controller's answers. It is not a change to model weights. [verified: `backend/app/gateway/gateway.py`, `_learn`]
- The store is real: with `STORE=postgres`, every gateway write reaches Postgres on Tiger Cloud, and a restart loads the record, the log, and the memory back. If Tiger Cloud is unreachable, the API runs in memory and the console says so. [verified: `backend/tests/test_postgres_store.py`, `backend/tests/test_store_fallback.py`]
- The what-if forks are real: each covenant flag's options are written into a zero-copy fork of the ledger on Tiger Cloud, never into the live record, and the controller's answer deletes the fork. On the free plan there is room for one fork at a time; if a fork fails, the flag works the same and says so. [verified: `backend/tests/test_whatif_forks.py`, live run 2026-10-24 09:00]

Not real, or not claimed:
- The statement lines come from public filings, not from the companies' internal books.
- Account-level detail is not public, so we do not claim it. The demo maps statement lines, not trial balances.
- The demo loads the deal from a fixture. `POST /deals` accepts two statement CSVs and a brief, so a judge can try an unseen input through the API; the console has no upload screen. [verified: `backend/app/api/routes.py`, `test_upload_creates_deal_and_runs`]
- As an extra, the loader script reads a QuickBooks Online trial balance export with its Account List, so a private company with no filings could be an input. It is not used in the demo. [verified: `scripts/README.md`]
  It was checked against real exports from the QuickBooks Online test-drive demo company, and the loaded totals match that company's own Balance Sheet report. [verified: `scripts/test_load_lines.py`, `scripts/samples/qbo/`]
- On the scripted backend the Mapper knows only the demo deal's line names, so a new company's lines arrive as flags. [verified: the QuickBooks demo company raised 40 flags on the scripted backend, reproduced 2026-10-24]
  On live Droid the same QuickBooks company raised 2 questions instead of 40, mapped all 53 lines, and ended at 1.03x with a Reviewer pass and no gateway refusals. One run, not a trial. [verified: `evals/unseen-input-quickbooks.md`, `scripts/run_unseen_deal.py`, 2026-10-24]
- The loader also has layout profiles for NetSuite, Sage Intacct, Microsoft Dynamics 365, Epicor, and Infor. They are not integrations. [verified: `scripts/README.md`]
  We wrote them from how those reports are usually laid out, tested them only on small files we made ourselves, and never ran them on a real export. [verified: `scripts/README.md`, `scripts/test_load_lines.py`]
- Agent output comes from one of four backends (droid, anthropic, scripted, or replay), and the API names the backend on every result. [verified: `backend/app/agents/runner.py`]
- Droid does not report which model served a run, so the model names above are what we requested. [verified: `docs/agents.md`, section 8]
- The default replay is the Sonnet 5.5 first run, which raises the covenant flag and runs through. [verified: `backend/tests/test_demo_reset.py`] The Haiku 5.5 run is kept in `backend/recordings/haiku-5-5/`; the gateway now rejects its Mapper output, because one option left "Short-term borrowings" unclear. [verified: `evals/README.md`, `test_flag_option_that_leaves_a_line_unclear_is_refused`]
- The fiscal years differ, April 30 and September 30, so the combined income statement adds two different years and does not match the filed pro forma.
- The combined table is historical plus target. No purchase accounting is applied.
- Two inputs are our estimates: the Statesville cash rent we deduct ($1,970K, the 10-K's next-year obligation), and transaction and integration costs, which we set to zero. [inferred]
  The filing estimates transaction costs after the close, and we have not decided whether they fall in the tested period; either way they move only the agreement's reading, which stays far under the limit. [verified: Ex 99.2, Note 5(b); timing inferred]
- The leverage figures are preliminary: the rent and transaction-cost inputs are our estimates, and we use each company's latest fiscal year, while the agreement tests the last twelve months to the closing quarter. [verified: `evals/fixture_check.md`; the period is the next step]
- The filing calls its own reclassification table, Note 2, preliminary. We use it as an answer key for which line goes where, not for amounts. [verified: Ex 99.2, Note 2]
- The scripted Mapper's synonym table was written with Note 2 at hand, so its 33 of 33 is not independent evidence. The model runs are the score that matters. [verified: `evals/README.md`]
- The agreement's reading of the financing liability is our reading. No controller or lender has checked it. [inferred]
- The agreement also has a fixed charge coverage test, Section 4.8(b). We do not check it. [verified: Ex 10.1, Section 4.8(b)]
- No practitioner has used the tool yet. [verified]
- Other deals and other situations are roadmap, not built.
- The output is a combined set of books and a limit check that a human approves. It is not advice.

## Tracks

Claim nothing unconfirmed.
- Hyphenate: select it on Devpost. One-line seat: "A portfolio controller at a PE-backed company, right after an add-on closes."
- Factory: the agents ran through the Droid SDK on 2026-10-24, with Sonnet 5.5 and Haiku 5.5 requested. [verified: `docs/agents.md`, run log]
  Say "built with the Droid SDK" only about `droid` runs.
- Figma: the console's design system and screen frames are in the Figma file. The team board (Schocastic) has a card per piece of evidence for each track, including Tiger Data. [verified: `docs/design/README.md`]
- Tiger Data: the record, the audit log, and the agents' memory are stored in Postgres on Tiger Cloud, and the audit log is a TimescaleDB hypertable that refuses edits. Each covenant flag's what-ifs live in a zero-copy fork of the ledger, made in about 35 s and deleted by the answer. The record is searchable with BM25, and the runs are readable in SQL through a continuous aggregate, typed views, and Toolkit statistics. [verified: `backend/tests/test_postgres_store.py`, `backend/tests/test_whatif_forks.py`]
  Measured on the live schema (3,892 records, 748 log rows; server time, median of 25): BM25 returns the ranked top 10 for "lease" in 0.09 ms against 3.9 ms for an unranked ILIKE scan, and the continuous aggregate answers the activity rollup in 0.14 ms against 0.38 ms from the raw log. The data is small, so these show the shape, not scale. [verified: `scripts/tiger_bench.py`, 2026-10-24]
  Say how the shipped screen was built from it only once Josie confirms.

## Images for the gallery

- `images/tiger-ledger-runs.png`: `ledger_runs` in the Tiger Cloud SQL Editor. With agent memory cleared, the Mapper asks 2 questions. With memory kept, it asks none and applies 6 policies.
- `images/tiger-bm25.png`: one BM25 search over the record in the Tiger Cloud SQL Editor.
- `images/console-tiger-badge.png`: the console after a posted run, with the TIGER CLOUD badge in the top bar (a capture from before Hi-fi v3; the store now shows in the sidebar's model card).
- `images/console-log-forks.png`: the log, with the three FORK rows of one covenant flag and the policies learned from the answer.

All four are from 2026-10-24, ledger 23. [verified]

## Open before submission

- Done 2026-10-24: the one-screen console (flag card, verdict line, combined table, mapping, log link) is built against `GET /deals/{id}/case` and shows the backend badge from `GET /health`. [verified: `frontend/README.md`]
- Josie: what was done in Figma and through the Figma MCP (`use_figma`), and is there a frame for the new one-screen console? `docs/decisions.md` D11 says the design system was built through `use_figma`, but `docs/design/README.md` does not say so.
- Cayden, on the day: which backend produced the run in the video and at the table. Planned: `droid`, with the Mapper on Claude Sonnet 5.5 and the Preparer and Reviewer on Claude Haiku 5.5 (`agents.md` section 9, 08:30). Confirm it from the badge, then write it into the list above.
- Done 2026-10-24: the EBITDA items are decided (stock compensation and the $4,019K pension figure applied, transaction costs kept at zero), and every leverage figure in this file, `flag-card.md`, and `brief.md` was updated.
- Anyone, with a Cal Hacks organizer: can one project enter several sponsor tracks?
