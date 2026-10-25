# Stochastic: reference for Claude

Last updated: 2026-10-24, evening (D20: a fourth agent, the Brief Reader, decided and not built).
Read this file first in any session about Stochastic.
It holds the main features, the architecture, and the scope.
If this file and a PDF or an older note disagree, this file is correct.
Claims are tagged [verified] when a source file or a filing shows them, and [inferred] when they are our judgment.

## 1. What Stochastic is
Stochastic merges the books of a newly acquired company into the books of the platform company that bought it.
It flags the few lines that need a human, and then checks the combined result against the lender's limit.
It is built for private equity buy-and-build firms, which keep buying add-on companies.
Three stateful agents do the repeatable work, code does all the math, and a human controller approves.
A fourth agent, the Brief Reader, will read the credit agreement into the brief (D20).
It is decided and not built; today a person writes the brief.
What the controller decides once, the agents keep: the next run and the next deal start with that memory.
Every step goes in an audit log.

This replaces two earlier framings.
The first was an all-in-one platform for any corporate-finance special situation.
The second was an investment-bank analysis tool that recommends plans.
Both are archived in `planning-notes.md` and `research/`.
They are roadmap ideas only.
The product is the integration workflow in this file.

Build status on 2026-10-24, 02:30: the backend runs the whole deal end to end on the real filing figures through the gateway, the tools, and the audit log, on the scripted backend. [verified: `backend/tests/test_trust_rules.py`, 103 tests pass]
The Droid backend ran the whole deal live with Claude Sonnet 5.5 at 03:30 (recorded in `backend/recordings/`).
The Anthropic backend ran later on Eric's key (one full recorded run, about 50 Mapper trials); the demo laptop has no key, so it is not in the stage fallback chain. [verified: `evals/README.md`]
Status on 2026-10-24 evening: 167 tests pass offline and 176 with Tiger.
The whole-line reading is computed as filed (2.84x), and the gateway guards against model-made exclusions, borrowed run ids, and unbacked review passes (D18). [verified: `backend/tests/test_gateway_guards.py`]
The console still implements the earlier workflow.
Josie is rebuilding it against `GET /deals/{id}/case`.
Status on 2026-10-24 night: a 15-second demo pace (`"pace": "demo"` on Run: 6.25 s to the questions, 6.64 s from the answer to the approval, measured), a `notify` event for each question, a learn message with the policy id after each answer, and four more Dashboard cases seeded through the real pipeline: three real deals from their filings (DLH and GRSi, Mama's Creations and Crown I, Shutterstock and Envato) and one QuickBooks sample. [verified: `backend/tests/test_demo_pace.py`, `backend/tests/test_demo_cases.py`; details in `architecture/gateway-and-api.md` and `demo-script.md`]
Status on 2026-10-25 (D23): the demo deal starts from the credit agreement text; the Brief Reader drafts the Brief, a code verifier checks every field (22 of 22 on the demo deal) and fills the amounts from the books with their sources, and the controller approves the Brief in one click; then the Mapper's one escalation (two questions together) is the only other human step. [verified: `backend/tests/test_brief_verifier.py`, `e2e/demo-run.spec.ts`]
Status on 2026-10-25 (D22): two demo modes, both replaying the recorded Claude Haiku 5.5 Droid run of the demo deal (`backend/recordings/haiku-5-5-run2/`) instead of the scripted rules, so the model card truthfully reads "Claude Haiku 5.5 · recorded run".
The Hyphenate beat is "Run the demo" (`"pace": "demo"`: 6.2 s to the questions, 7.2 s from the last answer to the approval, measured), and the Factory beat is Upload then Begin (`"pace": "factory"`: 14.2 s and 14.5 s).
The live demo deal plus the four seeded cases make five deals; the seeded cases hold four reasoned controller edits, each citing its source, and `GET /memory/counts` gives the sidebar's counters (human answers, live policies, reasoned edits) across all deals. [verified: `backend/tests/test_demo_replay.py`, `backend/tests/test_demo_cases.py`]

## 2. The pitch rules

- Lead with the problem.
  Do not lead with the demo or with the name of the deal. [set by Cayden]
- Pitch order: the problem, then what Stochastic does, then the proof.
- Time budget: 1:30 for the pitch and 0:30 for the live demo. [verified: Cayden, 2026-10-23]
- The agent messages in the demo are hardcoded or recorded.
  Say so.
  The gateway, the math, and the audit log are real.
- Say that the demo uses a real public deal, with statement-line data from public filings.
  Account-level detail is not public, so it is not in the demo.
- Do not claim other situations are built.
  They are roadmap.
- Do not call the output advice.
  The output is a mapped, combined set of books and a limit check that a human approves.
- Hyphenate rewards a few roles done deep.
  Depth on one workflow is the proof. [inferred]

## 3. The problem, the user, and the seat

A PE firm that buys add-on companies repeatedly has a gate on each new deal.
The lender's agreement sets limits, such as a maximum debt-to-EBITDA ratio, and these limits are tested on the combined company.
So the next deal depends on how fast and how correctly the team can combine the books.

Today a finance team does this by hand.
They pull trial balances, map each account of the new company to the platform's chart of accounts in a spreadsheet, build the combined numbers, adjust EBITDA, and prepare the lender's compliance pack.
One vendor playbook puts a full integration at about 12 weeks. [self-reported, Aleph; see `research/ma-workflow-research.md`]
The compliance certificate is due 45 to 60 days after quarter end in the samples found. [verified snippets; terms vary per deal]
Errors in the mapping flow silently into every later number. [inferred]

Stochastic does the repeatable part and asks a human only about the lines that are unclear.

The user is a portfolio controller or a PE associate who owns the integration. [inferred: no practitioner has checked this]
The human approver is the controller.
The one-line seat for Hyphenate: "A portfolio controller at a PE-backed company, right after an add-on closes."
The seat is one add-on deal, from the two data files to the controller's approval.
There is no after-close monitoring and no ongoing consolidation in the MVP.

## 4. The workflow

1. **Upload.** The user adds the platform's statement file, the target's statement file, and a short brief that states the lender's limit.
   Planned (D20): the user adds the credit agreement instead, the Brief Reader drafts the brief with a quote for every field, and the controller approves it before mapping starts.
   A brief already approved for the same agreement is reused.
2. **Map.** The Mapper matches each target line to a platform line, with a confidence and a reason.
3. **Flag.** Lines the Mapper cannot place with confidence go to the human.
   The human approves a mapping or changes it.
4. **Combine and test.** The Preparer calls code tools that add the books, remove intercompany amounts, compute combined EBITDA, and compute leverage.
   The Reviewer checks that the totals tie and tests leverage against the limit.
5. **Review and edit.** The controller can remap a line or change an amount in the combined table.
   Code recomputes at once.
   A companion asks why, and the reason teaches the agents for the next add-on (D19).
6. **Approve and download.** The controller approves the result, which is refused while an edit has no reason.
   The gateway posts it and writes the log.
   The controller downloads the final workbook and certificate, with every edit and reason in them.

The user sees one screen with a flag card, an editable combined table, and one verdict line, in a Mac desktop app.

## 5. Main features
1. **Mapping with confidence.** Each target line gets a platform line, a confidence, and a short reason.
2. **Human flags.** Only unclear lines reach the human, with the options and the computed effect of each on leverage.
3. **Combined books.** A combined table of platform, target, and total.
   Code does the arithmetic, and a tie-out check balances the combined balance sheet.
4. **Limit check.** Combined leverage next to the lender's limit, with the covenant's own definition of debt and EBITDA, and the covenant headroom left.
   The next add-on is still capped by the acquisition basket and the revolver.
5. **Maker-checker.** The agent that prepares a result cannot approve it.
   A reviewer agent checks it, and a human approves it.
   The gateway refuses approval until the review passes.
6. **Audit log.** Every action is logged, allowed or denied, and each row is chained to the row before it.
7. **Stateful agents that learn.** The controller's answer to a flag becomes a policy.
   The Mapper applies it next time with the policy as evidence instead of asking again.
   Each agent keeps a session across work items.
8. **Edits that teach.** Every edit in review is explained once through the companion's "Why did you change this?" bubble.
   A remap becomes a policy for every add-on on the platform, and an amount becomes an adjustment the Preparer proposes next time.
   Design: `design/review-companion.md`.
9. **Final files.** After approval, the workbook and the draft certificate download with the edits marked and explained.
10. **Replicable agents.** The same role definition runs on four backends (Anthropic, Droid, scripted, replay), once per work item, and the result says which backend produced it.

## 6. Architecture
The system has four parts.

- **People and files.** The console, the two data files, and the brief.
- **Agents.** Three stateful agents and a plain job runner.
  A fourth, the Brief Reader, is planned (D20).
- **The gateway.** It is the only writer.
  It checks permissions, enforces work-item states, runs the tools, writes the log, and writes the agents' memory.
- **The store.** In memory for every read, written through to Postgres on Tiger Cloud when `STORE=postgres`.
  It holds the record, the work items, the tool runs, the audit log, the policies, and the agent sessions.
  The audit log is a TimescaleDB hypertable that refuses edits, and a restart loads everything back. [verified: `backend/tests/test_postgres_store.py`, run against the `stochastic` service on 2026-10-24]
  When the Mapper raises a covenant flag, the gateway forks the ledger on Tiger Cloud (a zero-copy fork, about 35 s) and writes every option's what-if into the fork, never into the live record; the controller's answer keeps one option in the ledger and deletes the fork with the alternatives. [verified: `backend/app/gateway/whatif.py`, live on 2026-10-24 09:00]

Code tools hold all the math: consolidation, tie-out, EBITDA, covenant debt, leverage, and the limit test. [verified: `backend/app/tools/finance.py`]
Agents call tools through the gateway.
They do not talk to each other.
A job runner moves work items from one agent to the next.
The runner is code, not a model. [verified: `backend/app/agents/jobs.py`]
The console talks only to the gateway.

The agent layer uses one function, `run_agent(role, item)`, with four backends. [verified: `backend/app/agents/runner.py`]
The Factory Droid Python SDK is the stage path: one session per role, Mapper on Claude Sonnet 5.5, Preparer and Reviewer on Haiku 5.5.
The Anthropic API backend ran on a teammate's key; with no key on the demo laptop it is not in the stage chain.
The scripted backend is deterministic rules with no model, the stage fallback and the reference answer.
If the gateway refuses a model's result, the Mapper retries once with the reason and then the scripted backend makes the result under the same checks.
The replay backend plays recorded outputs from `backend/recordings/`.
`AGENT_BACKEND` picks the backend, `AGENT_FALLBACK` lists the fallbacks, and every result says which backend produced it.
The details are in `architecture/`.

## 7. The three agents
Each agent is stateful.
It receives one work item with all its inputs, plus its own session and the policies it learned, and returns one typed result.
The state lives in the store, not in a process, so a restart loses nothing and the same role can run many items in turn or in parallel.
Agents never write to the store and never talk to each other.

| Agent | Real-team role | Gets | Returns | Keeps | Never |
| --- | --- | --- | --- | --- | --- |
| Mapper | Staff accountant | The target's lines, the platform's lines, the brief, its policies, its session | A mapping with confidence and reasons, a covenant tag for each balance sheet line (debt, not debt, unclear, or n/a), and flag proposals with options | A policy per answered flag, which it applies next time and cites | Guesses a low-confidence match or an unclear tag |
| Preparer | Senior accountant | Both books, the approved mappings, the brief, its session | The draft combined table and the EBITDA, debt, and leverage figures, from tool runs, with run ids | Its session transcript | Computes a number itself, or approves its own draft |
| Reviewer | Reviewer | The draft and its run ids, its session | Pass or needs-attention, with reasons that name run ids | Its session transcript | Changes the draft |

The human controller answers flags and approves the final result.

Planned, not built (D20): a fourth role runs before the Mapper.

| Agent | Real-team role | Gets | Returns | Keeps | Never |
| --- | --- | --- | --- | --- | --- |
| Brief Reader | Credit analyst | The indexed credit agreement (sections and definitions), read-only tools to fetch more, its session | A draft brief with a verbatim quote and section for every field, and flags for what it cannot place or what the schema cannot hold | The approved brief, keyed by the agreement's hash, reused by the next add-on under the same facility | Computes a number, approves its own brief, or fills a field without a quote |

Why it is separate from the Mapper: the agreement is read once per loan and the books on every deal, and the agent that applies the definition of debt must not also write it.
The gateway refuses a quote that is not in the agreement and a number that is not in its quote.
The controller approves the brief, and mapping is refused until then.
Adjustment amounts come from the books, not the agreement, so the reader flags them and the controller enters them.
Design: `architecture/brief-reader.md`.
Research: `research/brief-reader.md`.

Memory, in detail. [verified: `backend/app/gateway/gateway.py`, `_learn`]
- When the controller answers a flag, the gateway writes a `Policy`: the line name, the decision, who decided, and the flag it came from.
- On the next run the Mapper applies the policy with confidence 0.98 and the reason "Policy p_001: human:controller decided this on wi_002", and the gateway logs `policy:apply`.
- Each role has an `AgentSession`: backend, backend session id (the Droid backend resumes it), turn count, and a short transcript that the Anthropic backend replays.
- `POST /dev/reset` keeps the memory.
  The second run of the demo deal asks no question at all. [verified: `test_controller_answer_becomes_a_policy_and_the_mapper_applies_it`]
- `POST /dev/reset?keep_memory=false` clears it, so the next judge sees the flag.
  The reset is refused while a run is going and frees the fork slot. [verified: `test_demo_reset.py`]
- A policy applies only to the company whose line it was learned on, and a reversal retires the policies the flag taught. [verified: `test_gateway_guards.py`]
- Policies are per role and per line name.
  Confidence calibration and cross-deal statistics are roadmap.

## 8. Human moments
There are two, plus one that shows memory.

- **Flag.** A line is unclear, and the human chooses how to treat it.
  Each option shows the leverage it gives, computed by the tools.
- **Approval.** The controller approves the combined result before it posts.
  The gateway refuses until the Reviewer verdict is pass.
- **Second run.** After a reset, the same deal runs with no flag, because the Mapper applies what the controller decided.
  The audit log shows `policy:apply`.

Planned (D20): a third moment comes first.
The controller approves the brief the Brief Reader drafted, field by field with its quotes, before mapping starts.

If the Reviewer finds a tie-out error or a breach of the limit, the approval item opens as needs-attention with the reasons.
An earlier design had six escalation points (E1 to E6).
They are archived.
Two are enough for this workflow.

## 9. Work items and gateway rules

A work item moves through these states: NEW, PROPOSED, NEEDS_INFO, APPROVED, POSTED.
It can also end as REJECTED or REVERSED.
A forbidden action is DENIED.
The gateway does not apply it, and it writes a row to the log.

The gateway enforces these rules:
1. Only the gateway posts to the record.
2. The preparer of an item cannot approve it (maker-checker).
3. An agent can call only the tools it was given.
4. Every number carries a run id from the math code.
5. A reversal is a new item linked to the original.
   The system never deletes.
6. Every action goes in the log, and each row is chained to the previous row.

Denied actions stay in the log as proof.
The demo does not stage an attack.
A denied row is shown only if a judge asks to see the log.

## 10. Data

Inputs for the demo:
- A statement file for the platform (CSV), built from the acquirer's filings.
- A statement file for the target (CSV), built from the target's audited statements.
- A short brief: the lender's limit and the covenant's definition of debt and EBITDA.

The brief is written by hand today, and the PNC brief is the only one. [verified: `backend/app/db/fixtures/kewaunee.py`]
`POST /deals` accepts any brief as JSON, and nothing in the math names PNC, so another agreement with one debt-to-EBITDA covenant works if a person writes its brief. [verified: `backend/app/api/routes.py`]
The schema does not hold step-downs, cash netting, percent-of-EBITDA caps, pro forma acquisitions, or a second covenant, and `ebitda()` always subtracts interest income, which two of four real agreements do not. [verified: `research/brief-reader.md` section 3]
The Brief Reader (D20) and its stage 2 schema address this.

Tables (a design proposal, and the first prototype keeps them in memory):
- `deal`, `source_line`, `mapping`, `work_item`, `result`, `audit_log`.

The rule "vectors find, tables decide" still holds, but the MVP has no vector search.
Public data is cached before the demo.
The demo makes no live SEC calls.
SEC EDGAR needs a User-Agent header with a real contact email.
The file still has a placeholder.
Whether we may redistribute cached filings is unresolved, so the cached files stay out of git.

## 11. Math rules

- Code does all deal math.
  The model never produces a number.
- Consolidation, EBITDA, and leverage are deterministic and have tests.
- Use the covenant's own definitions, not the generic ones.
  A naive and a covenant leverage figure can differ a lot.
- A tie-out check runs on every combined table: the parts must add to the total.
- Precision before recall.
  If a mapping is unsure, it becomes a flag.

## 12. The demo
### The real deal

The proof deal is Kewaunee Scientific buying Nu Aire, closed 2024-11-01, for $55M. [verified: `research/real-deal-candidates.md`]
Kewaunee is the platform (fiscal year ends April 30).
Nu Aire is the target (fiscal year ends September 30).
Backups, in the agent's ranking: DLH and GRSi, Mama's Creations and Crown I, Shutterstock and Envato.
All three are now seeded Dashboard cases built from their filings (`backend/app/db/fixtures/`), with a fourth sample case; `/dev/reset` resets only the Kewaunee deal.

What the filings give us, and what is loaded in `backend/app/db/fixtures/kewaunee.py` [verified: read from EDGAR on 2026-10-24]:
- Kewaunee's balance sheet at 2024-10-31 (10-Q), 38 lines, and its fiscal 2024 income statement (Ex 99.2 historical column) and depreciation of $3,125K (10-K cash flow).
- The closing financing from Ex 99.2 Note 4(h): term loan $15,000K, revolver draw $5,563K, seller notes $22,540K, all added to the "Financing liability" line.
- Nu Aire's audited statements for the year to 2024-09-30 (Ex 99.1), 40 balance sheet lines and 14 income statement lines in whole dollars, and D&A of $1,830,395.
- The PNC credit agreement (Ex 10.1): leverage covenant in Section 4.8(a), Senior Funded Bank Debt to EBITDA below 2.50 to 1.00, with the exclusions and add-backs loaded into the brief.
- Note 2 of Ex 99.2 as the answer key for the shape of the mapping (Eric builds the scored key in `evals/`).

Rules for using it:
- Use Nu Aire's audited September statements as the raw target input.
- Use Note 2 as the answer key for the shape of the mapping, not to the dollar.
  The filing says its own reclassification review is preliminary, and the fiscal years differ.
- Public filings give statement lines, not trial balances.
  The demo maps statement lines.
  Account-level detail would be synthetic, so we do not claim it.
- The demo is a reconstruction from public filings.
  It does not show the lender's or the company's internal views.

### The flag and the computed figures

The one flag is real: Kewaunee's "Financing liability" line. [verified: fixture and `test_mapper_flags_the_financing_liability_and_effects_are_computed`]
It holds the Statesville sale-leaseback ($27,782K), the new PNC term loan and revolver ($20,563K), and the 8% seller notes ($22,540K).
The credit agreement's Senior Funded Bank Debt excludes the capital lease on that property and excludes subordinated debt.
The Mapper tags the line "unclear" and asks which parts count.
The gateway computes the effect of each option with the tools.

| Option | Senior Funded Bank Debt | Leverage | Verdict |
| --- | --- | --- | --- |
| a. Whole line counts, read as filed (over reported EBITDA $25,312K) | $71,955K | 2.84x | Over the 2.50x limit |
| b. Only the PNC term loan and revolver count (the agreement's reading, the default) | $21,633K | 0.76x | OK, 1.74x of room, about $49.3M of covenant headroom |
| c. PNC debt plus the seller notes | $44,173K | 1.56x | OK |

Covenant EBITDA is $28,379K: Kewaunee $18,043K (net earnings 19,057, plus interest 1,799, less the tax benefit 5,938, plus depreciation 3,125), Nu Aire $7,269K (net income 5,438, plus taxes 514, plus D&A 1,830, less interest income 514), plus the noncash pension termination $4,019K and stock-based compensation $1,018K, less Statesville cash rent $1,970K. [verified: `test_naive_and_covenant_leverage_differ_on_real_figures`]
Covenant EBITDA subtracts interest income, as Addendum I of Ex 10.1 requires; Nu Aire's $514K of interest income is taken out. [verified: `test_ebitda_subtracts_interest_income`]
Two inputs are inferred and must be said out loud: the rent deduction uses the 10-K's next-year obligation, and transaction and integration costs are applied as 0 because the filings do not quantify them.
They move only options b and c.
Option a is computed as filed, with no add-back and no rent deduction, because counting the Statesville financing as debt while deducting its rent would mix two readings (D18).
It would need $3,470K more EBITDA to pass.
The test period is each company's latest fiscal year; the agreement tests the last twelve months to the closing quarter, which is next.
The verdict changes with the controller's answer, so the moment holds. [verified]

A second, smaller flag asks where Nu Aire's "Certificates of Deposit" belong (cash equivalents or other assets).
It shows a mapping flag next to the covenant flag.
It can be turned off by raising the Mapper's threshold if the 30 seconds are tight.

### The output screen

One screen, three parts:
1. The flag card, with the question, the evidence, and the options with their computed effects.
2. A combined table of platform, target, and combined, in USD thousands.
   The balance sheet balances: combined total assets $182,456K.
   The console shows about ten rows and can expand.
3. One verdict line: combined leverage against the 2.50x limit, OK or Over the limit, with the room left.

The audit log is a small link.
There is no other screen in the demo.
The whole screen comes from `GET /deals/{id}/case`. [verified: `architecture/gateway-and-api.md`]

### The 30-second run

Press Run.
The Mapper maps 54 lines and stops on one flag.
The controller picks the covenant reading.
Code combines the books and tests the limit.
The verdict line shows 0.76x against 2.50x, Reviewer pass.
The controller approves and the gateway posts.
If time allows, reset and run again: no flag, because the Mapper learned.
The agent text is hardcoded, recorded, or scripted, and we say which.
The gateway, tools, and log run for real.
Since 2026-10-25 the demo's agent text is the recorded Claude Haiku 5.5 run, replayed (D22).

### The 1:30 pitch outline

- 0:00 to 0:25: the problem.
  A PE firm's next deal is gated by lender limits, and the team combines the books by hand, in weeks.
- 0:25 to 0:55: what Stochastic does.
  It maps, flags, combines, tests against the limit, and a controller approves.
  What the controller decides, the agents keep.
- 0:55 to 1:30: the proof and the honesty.
  It runs on a real public deal.
  The agents are stateful roles on a real team.
  The math is code.
  The log is real.
  Say what is simulated.

## 13. MVP scope
Must (the demo does not work without these).
Status on 2026-10-24, 02:30:
1. The two input files and the brief for the Kewaunee and Nu Aire deal, built from the filings.
   Done as a fixture.
   Eric moves it to CSVs and checks every figure against the filings.
2. The Mapper, with a typed output, running through `run_agent`.
   Done on the scripted backend, live on Droid, and on the Anthropic API with a teammate's key.
3. Consolidation, EBITDA, and leverage tools, with tests that use the real figures.
   Done. Tri reviews and extends.
4. The gateway with work-item states, maker-checker, run-id checks, the audit log, and agent memory.
   Done.
5. The Preparer and the Reviewer, with real tool calls.
   Done on the scripted backend.
6. The console screen: flag card, verdict line, combined table, mapping, log link, on `GET /deals/{id}/case`.
   Done 2026-10-24, with the backend badge and the second-run moment.
7. A recorded run and a backend switch, so the demo survives a failure.
   Done (`backend/recordings/`, `AGENT_BACKEND=replay`).
   The default recording is the Sonnet 5.5 Droid first run of 2026-10-24, which raises the covenant flag. [verified: `test_demo_reset.py`]
8. Track proofs: at least one agent runs with `AGENT_BACKEND=droid` (Factory): done, all three ran.
   The Figma file on screen in the pitch (Figma): open.

Should (if the schedule holds):
- A live Anthropic-backed or Droid-backed agent call in the demo.
- An answer-key score for the mapping against Note 2 (Eric).
- The second-run memory moment on stage.
- A downloadable draft compliance certificate.
- The Mac desktop app (Electron), the editable review table, the companion, and Download final files (D19).
  The demo beat is in `design/review-companion.md` section 9.
- The logo and the launch splash (D21): the circle and the name, centered on a transparent background, until the whole app has loaded.
  Built in `cayden/launch-mark`.
  Spec: `design/brand.md`.
- The Brief Reader, stage 1 (D20): the role, the gateway's quote and number checks, brief approval before mapping, the scripted fallback, and the tests.
  When to build it against the 8pm freeze is open.
  Design: `architecture/brief-reader.md`.
- Tiger Cloud Postgres in place of the memory store.
  Built on 2026-10-24 as a write-through store (`backend/app/db/postgres.py`).

Cut (do not build this weekend):
- Purchase accounting beyond a "provisional" label.
  The combined table is historical plus target; the pro forma adjustments are not applied.
- Intercompany schedules and eliminations.
- Other situations, other deals, arbitrary uploads, accounts, login, mobile.
- The Brief Reader's stage 2: several covenants, step-downs, cash netting, percent caps, pro forma acquisitions, and the EBITDA base as data (D20).
- Plan search, Monte Carlo, and rejection-to-policy.
  These belong to the earlier framing.
- A live SEC call on stage.
- A staged denied-action demo.

## 14. Tech stack (proposed)
- Frontend: Next.js, React, TypeScript, Tailwind, inside an Electron window as a Mac desktop app (D19).
  Josie leads the design.
- Backend: Python 3.12, FastAPI, Pydantic.
  The gateway, tools, agents, and tests are in Python. [verified]
- Agents: `run_agent(role, item)` with backends `anthropic` (Anthropic SDK, tool use), `droid` (Factory Droid Python SDK 0.5.0), `scripted`, and `replay`. [verified: installed in `backend/.venv`]
- Store: in memory, written through to Postgres on Tiger Cloud (TimescaleDB 2.31, PostgreSQL 18.6) with `STORE=postgres`. [verified]
- Models: Claude Haiku 5.5 by default on both backends (`ANTHROPIC_MODEL`, `DROID_MODEL`), with per-role overrides (`DROID_MODEL_MAPPER` and so on).
  Haiku 5.5 produced the intended flag on the demo deal once the filing notes were on the lines.
  Details and the run log are in `agents.md`.
- Keys: `ANTHROPIC_API_KEY` and `FACTORY_API_KEY` live in the repo-root `.env`, which git ignores and the app loads.
  `.env.example` lists every setting.

## 15. Tracks and sponsors

Status as of 2026-10-24.
Sponsor research is in `sponsors/`.

| Track | Status | Note |
| --- | --- | --- |
| Hyphenate (main) | Target | $8K, $5K, $3K, plus interviews for the top 5. Select it on Devpost. |
| Factory | Target (build runner) | Cayden has a Factory account on the Plus plan. Droid runs the agents we show. Confirm prize rules and Claude model access with a Factory mentor, because the Friday workshop has passed. |
| Figma | Target | Five prizes at $1,000 each (self-reported): Best Use Case of Figma, Best Use Case of Figma Agent, Most Creative Use Case of Figma Agent, Best Design, Most Creative. Josie designs the console in Figma, and the Figma MCP is in the loop. Prompts are not published, so read the Live Site. |
| Tiger Data (MLH) | Target | Added 2026-10-24 evening, once the store ran on Tiger Cloud. MLH prize "Best Use of Tiger Data". Proof: the record, the audit log, and the agents' memory live in Postgres on Tiger Cloud, and each covenant flag's what-ifs live in a zero-copy fork that the answer discards (D17). |
| Microsoft | Not targeted | Dropped as a target. It needs Microsoft products that we do not use. |
| Most Technically Advanced | Not targeted | Costs no extra work if it is open to all. Do not build for it. |
| Mana | Skip | Needs the founders' confirmation that it counts. |
| GoDaddy, Vultr, Gemini API (MLH) | Cheap | Count only if the integration is real. |
| Others | Skip | No honest fit. |

The four target tracks are Hyphenate, Factory, Figma, and Tiger Data. [set by Cayden, 2026-10-24; Tiger Data added that evening]
Stacking three or more prizes is rare. [verified: 22 of 1,324 winners in the scrape, for three or more]
The tracks ask for different proof, so the work does not overlap much.
Cal Hacks has not confirmed that one project can opt into several sponsor tracks.
Ask a Cal Hacks organizer today.

### What each target track needs from us

Hyphenate:
- A real messy corner: two different charts of accounts from a real deal.
- An answer key: Note 2 of the Kewaunee pro forma.
- Limits in code: the covenant test, the maker-checker rule, and the gateway as the only writer.
- A moment: the flagged line that changes the leverage verdict.
- A demo video that opens with that moment, a live demo, a one-line seat, and a real-versus-simulated list.

Factory:
- The agents we show run through the Droid SDK.
  Each role keeps one Droid session and resumes it on every work item and deal.
- `AGENT_BACKEND=droid` must work for at least one agent in the demo, or we do not claim "built with Droid".
- A short statement of what the SDK made possible: a tool allowlist (`restrict_tools`), typed output, and resumable sessions per role.
- Each role runs in its own empty working directory with only our tools allowed, because Droid is a coding agent that reads files by default. [from Factory's Cal Hacks deck, see `sponsors/factory.md`]
- Each team member can claim Factory credits with the form linked in `sponsors/factory.md`.
- Open: the prize rubric, and whether our key can run Claude models.
  The deck does not answer either one.

Figma:
- The Figma file is the design source for the console, with the Tokens variables and components already built.
- The console screen is built from the Figma frame, using the Figma MCP or Code Connect, and not redrawn by hand.
- Figma is on screen in the pitch: the frame, the component set, and one agent-driven edit through `use_figma`.
- Design polish counts for Best Design: one hero screen, plain verdict words, state shown by color plus word plus shape, and a clickable prototype.
- Open: the exact prompts for the five prizes, and whether our team has Figma Agent access (the Education plan is free).

Tiger Data:
- The store runs on Tiger Cloud (`STORE=postgres`): every gateway write reaches Postgres, and a restart loads the record, the audit log, and the agents' memory back. [verified: `backend/tests/test_postgres_store.py`]
- The audit log is a TimescaleDB hypertable that refuses UPDATE and DELETE.
  A reset starts a new ledger, so nothing is deleted.
- Forks: each covenant flag's what-ifs go to a zero-copy fork of the ledger, and the answer deletes it.
  The flag card says "What-ifs held in Tiger fork ..." and the log has the three FORK rows. [verified: live run 2026-10-24 09:00; `backend/tests/test_whatif_forks.py`]
- Read in SQL (built 2026-10-24 afternoon, `ANALYTICS_SQL` in `backend/app/db/postgres.py`): a real-time continuous aggregate `audit_activity` (rows per minute by ledger, actor, and action), a columnstore policy that turns audit chunks older than a day columnar (one ledger per segment; the append-only trigger still holds), BM25 keyword search over every record with pg_textsearch (`ORDER BY search_text <@> 'seller notes'`), typed views `covenant_runs` (every limit test with its debt, EBITDA, and what-if option) and `ledger_runs` (one row per run: seconds, flags, policies applied, stage), and `run_stats` from the TimescaleDB Toolkit (mean, stddev, p50, p95 of a run). [verified: `test_the_record_reads_in_sql_and_survives_the_columnstore`, and on the live `stochastic` schema 2026-10-24]
- The learning shows in SQL: in `ledger_runs`, a run with agent memory cleared raises 2 flags, and the next run with memory kept raises 0 and applies 6 policies. [verified: ledgers 19 to 23]
- The Tiger MCP queries the demo database (password saved with `tiger db save-password` on 2026-10-24), so Claude can answer questions about the ledger live.
- The team board in Figma (Schocastic, `technologies` page) has two rows of Tiger cards for this: SQL Editor captures of these views, and two console captures (`design/README.md`).
- Show it in the pitch: the "Tiger Cloud" badge, the fork line on the flag card, then the `ledger` and `audit_log` tables in SQL after a restart, then `ledger_runs` and one BM25 search.
- Open: whether forks for comparing two flag answers are worth building this weekend (see `sponsors/tiger-data.md`).
Cal Hacks has not confirmed that one project can opt into several sponsor tracks.
Ask at kickoff.

## 16. Hyphenate judging

Hyphenate judges with four questions:
- Is it real enough?
- Would you hire it?
- Did we see something new?
- Was there a moment?

The workshop calls "would you hire it" the make-or-break question. [verified]
Strong entries have a real messy corner, an answer key, limits in code, and a moment on stage.
Weak entries are a chatbot over a spreadsheet, a one-shot extractor, ten shallow workflows, clean happy-path data, and an admin key with "the prompt tells it not to".
For us: the messy corner is the mapping of two different charts, the answer key is Note 2, and the limit is in code.
The moment is the flagged line that changes the leverage verdict. [inferred]
Judging runs Sunday 10:30am to 12:30pm.
The whole team stays at the table.

The closest prior winner is VistaAI (HackMIT 2026, first place, self-reported).
It ingests messy CSV and XLSX from acquired companies, proposes field mappings, and keeps provenance.
Ours differs in three ways.
It works on accounting lines and not operational records.
It checks the result against a lender's limit.
It posts through a gateway with maker-checker and an audit log.
Do not lead the pitch with ingestion.

## 17. Fixed rules

- No project code before Friday Oct 23, about 6pm.
  This is satisfied.
- Devpost is due Sunday 9am, with a table number.
- The team has four people: Cayden, Josie (UI and UX), Eric, and Tri.
  The task split is in `TASKS.md`.
- Mark every claim verified or inferred.
  Label sponsor and vendor numbers as self-reported.
- Do not invent prizes or numbers.
- Keep keys in `.env`.
  Never put them in docs or git.
- Use a plain hyphen and never an em dash.

## 18. Open questions
- Does PE add-on integration count as a corner of a finance team for Hyphenate?
  Ask a Hyphenate mentor on Saturday, unless Cayden already asked.
- Which part of Kewaunee's financing liability counts as covenant debt?
  We computed all three readings (section 12).
  A practitioner should confirm the default, reading b.
- Closed on 2026-10-24, 03:30: Droid runs Claude on our key (`claude-sonnet-5-5`, Opus 5.5, Fable 5.1, Haiku 5.5 listed), and the whole deal ran on `AGENT_BACKEND=droid` with our tools through MCP.
  See `sponsors/factory.md`.
- Does the Python Droid SDK qualify for "Building with the Droid SDK" when the tools call our own gateway?
- Anthropic key: answered.
  Eric's key ran the backend; the demo laptop has none.
- Does the SEC allow us to redistribute the cached filings?
  The fixture holds only line values and source references, not the filings.
- Does a former-banker or controller reviewer count as the human seat?
- Is the Statesville cash rent deduction ($1,970K, from the 10-K obligations table) the right figure for the test period?
  It is inferred.
- When to build the Brief Reader's stage 1, and on which model (D20).
  The open points are in `architecture/brief-reader.md` section 12.

## 19. Where to find more

All paths are inside `docs/`.

- The UI: the `Hi-fi - v3` page in Figma (https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=141-2). The `Technologies Used` page in the same file is for the pitch.
  Frame links are in `design/README.md`.

- `TASKS.md`: who builds what.
  `tasks/` holds one file per person, with branches and owned folders.
- `agents.md`: the agent layer in detail: roles, rules, flags, memory, backends, settings, the run log.
- `demo-script.md`: the 2:00 plan, the 30-second demo beat by beat, the failure plan, and judge Q&A prep.
- `glossary.md`: finance and product terms in plain language.
- `decisions.md`: the dated decision log and the open decisions.
- `architecture/`: parts, agents and work items, gateway and API, data model, repo structure.
- `design/`: Figma links, tokens, and UI rules.
  `design/brand.md` holds the logo and the launch splash (D21).
  The mockups predate the reframe to PE add-on integration.
  Josie updates them.
- `research/ma-workflow-research.md`: the three M&A users, pain, time, and existing products.
- `research/post-close-deliverables.md`: what a PE finance team gets after an add-on closes.
- `research/real-deal-candidates.md`: the real deal, with EDGAR links.
- `research/brief-reader.md`: four real credit agreements, what the brief schema cannot hold, and products and benchmarks for reading agreements (D20).
- `research/agent-framework-options.md`: Droid, ADK, Anthropic API, and others.
- `hyphenate-workshop.md`: the workshop blueprint and the gaps.
- `sponsors/`: Hyphenate, Tiger Data, Microsoft, Factory, Mana, and the Slack notes.
- `planning-notes.md`, `research/research.md`, `research/deep-problems/`: archive from earlier framings.
- `diagrams/`: PDFs from the first framing.
  They are stale and are not re-rendered.
