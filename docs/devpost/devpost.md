# Devpost draft

Owner: Eric.
Draft of 2026-10-24, for submission by Sunday 9am.
The sections below follow the Devpost form.
Pitch order is the problem, then what Stochastic does, then the proof.
Tags in this file are for the team: [verified] means a source file, a filing, or a test shows it, and [inferred] means our judgment.
Before pasting into Devpost, keep the tags where a reader would want them and drop the rest.
Items marked "to fill" must be checked or filled before submission.

## Tagline

Merge an add-on's books into the platform's, flag the lines a human must decide, and test the result against the lender's own limit.

## Inspiration

A private equity firm that keeps buying small companies has a gate on every deal.
The lender sets a limit, such as debt below 2.50 times EBITDA, and tests it on the combined company.
So the next deal waits until someone merges two sets of books.
Today that is a controller, a spreadsheet, and weeks: pull the statements, map each line of the new company to the platform's chart, add them up, adjust EBITDA, and prepare the lender's pack.
One vendor playbook puts a full integration at about 12 weeks. [self-reported, Aleph]
In the samples we found, the compliance certificate is due 45 to 60 days after quarter end. [verified snippets; terms vary per deal]
One wrong mapping flows silently into every number after it. [inferred]

## What it does

Stochastic does the repeatable part of an add-on integration and keeps what the controller decides.
1. Upload: the platform's statement file, the target's statement file, and a short brief with the lender's limit and its definitions of debt and EBITDA.
2. Map: a Mapper agent matches each target line to a platform line, with a confidence and a reason, and tags each balance sheet line as covenant debt or not.
3. Flag: the Mapper stops on the lines it should not decide alone. The flag card shows the question, the filing evidence, and the effect of each answer on leverage, computed by code.
4. Combine and test: a Preparer agent calls code tools that combine the books, tie them out, compute covenant EBITDA and debt, and test the limit. A Reviewer agent checks the tie-out and the run ids.
5. Approve: the controller approves, and only then does the gateway post the result and write the log.

The controller's answer to a flag becomes a policy, written by the gateway.
On the next run the Mapper applies the policy and cites it instead of asking again. [verified: `test_controller_answer_becomes_a_policy_and_the_mapper_applies_it`]

The output is a mapped, combined set of books and a limit check that a human approves.
It is not advice.

## The proof: a real public deal

We ran it on a real add-on: Kewaunee Scientific buying Nu Aire, closed November 1, 2024, for $55M, from public SEC filings. [verified]
The two companies use different charts of accounts, and the buyer's pro forma filing includes a reclassification table (Note 2) that we use as an answer key for the shape of the mapping. [verified: Ex 99.2]

The lender's test is Section 4.8(a) of the PNC Loan Agreement: a "ratio of Senior Funded Bank Debt to EBITDA of less than 2.50 to 1.00". [verified: Ex 10.1, Section 4.8(a)]
One Kewaunee line, "Financing liability", holds three debts after the close: a Statesville sale-leaseback ($27,782K), the new PNC term loan and revolver ($20,563K), and 8% seller notes ($22,540K). [verified: 10-Q Note G; Ex 99.2 Note 4(h)]
The agreement's definition of Senior Funded Bank Debt excludes subordinated debt and the capitalized lease on the Statesville property. [verified: Ex 10.1, definitions]
The Mapper flags the line, and the gateway computes each reading with the tools:

| Reading | Senior Funded Bank Debt | Leverage | Verdict |
| --- | --- | --- | --- |
| Whole line counts | $71,955K | 2.57x | Over the 2.50x limit |
| PNC debt only (the agreement's reading) | $21,633K | 0.77x | OK |
| PNC debt plus the seller notes | $44,173K | 1.58x | OK |

Same books, two readings, 1.80x apart: a blocked next deal, or about $48M of room. [verified: tool runs on the fixture]
These figures are preliminary.
Covenant EBITDA is $28,033K today, and three items in how we apply the agreement's EBITDA definition are still under review. [verified: `evals/fixture_check.md`]
The margin on the first reading is thin: it stays over the limit only while covenant EBITDA is below $28,782K. [verified: arithmetic]
If add-backs above $749K that we have not applied turn out to belong, the whole-line reading drops under 2.50x, while the agreement's reading stays far under. [verified: arithmetic]
The facts behind the card, with quotes and sections, are in `docs/devpost/flag-card.md`, and the definitions are in `docs/devpost/brief.md`.

Mapping score against Note 2: to fill from `evals/README.md` once task 5 has run (score, date, backend).

## How we built it

- Three stateful agents, Mapper, Preparer, and Reviewer, each a role on a real finance team. Each keeps a session and its policies in the store, not in a process. [verified: `backend/app/gateway/gateway.py`]
- The agents never write to the record and never talk to each other. They call tools only through the gateway. A plain job runner, which is code, moves work items between them. [verified: `backend/app/agents/jobs.py`]
- The gateway is the only writer. It enforces work-item states, maker-checker (the preparer of an item cannot approve it), tool permissions, and run ids on every number. [verified: `backend/tests/test_trust_rules.py`]
- Code does all the deal math: consolidation, tie-out, covenant EBITDA, covenant debt, leverage, and the limit test. A number no tool run produced is refused. [verified: `test_model_made_number_is_refused_even_with_real_run_ids`]
- Every action, allowed or denied, goes in an audit log, and each row is chained to the row before it by hash. [verified]
- One function, `run_agent(role, item)`, runs the same role on four backends: Factory Droid, the Anthropic API, scripted rules, and replay of a recorded run. Every result says which backend produced it, and the screen shows it. [verified: `backend/app/agents/runner.py`]
- Backend: Python 3.12, FastAPI, Pydantic. Console: Next.js, React, TypeScript, Tailwind, designed in Figma. [verified for the backend; to fill: confirm the console stack and the Figma workflow with Josie]

## Challenges we ran into

- The face of the balance sheet and the lender's definitions disagree. One line holds three debts with different covenant treatment, and only the agreement says which count.
- Public filings give statement lines, not trial balances, so we map statement lines and do not claim account-level detail.
- The two companies have different fiscal years, April 30 and September 30.
- An early Mapper run decided the debt exclusions itself instead of asking. We changed the prompt so exclusions are the controller's call, and put the filing notes on the lines so the model knows what each one is. [verified: `docs/agents.md`, run log]
- The EBITDA definition has add-backs that the filings do not fully quantify for the tested period, which leaves the naive reading close to the limit.

## Accomplishments that we're proud of

- The backend runs the whole deal end to end on the real filing figures, through the gateway, the tools, and the audit log. [verified: `backend/tests/test_trust_rules.py`, 17 tests on the real Kewaunee figures]
- The flag is real. It comes from a real line in a real filing, and the answer moves the leverage verdict. [verified: `test_mapper_flags_the_financing_liability_and_effects_are_computed`]
- The whole deal ran through Factory Droid with our gateway tools, on both Claude Sonnet 5.5 and Claude Haiku 5.5 as requested models. [verified: `docs/agents.md`, run log]
- After a reset, the same deal runs with no flag, because the Mapper applies the controller's policy, and the log shows `policy:apply`. [verified]

## What we learned

- Depth on one workflow says more than breadth. The hard part of an add-on is not adding numbers, it is deciding what each line is under the lender's rules.
- Agents are most useful when they know what they must not decide. Precision before recall: an unsure line becomes a flag.

## What's next

These are roadmap.
None is built.
- Purchase accounting with a provisional label, and intercompany eliminations.
- A second deal, to show the policies carrying over.
- Confidence calibration from the answer key.
- A Postgres store in place of the in-memory store.
- Other corporate-finance situations.

## Built with

Python, FastAPI, Pydantic, Factory Droid SDK, Anthropic API, Claude, Next.js, React, TypeScript, Tailwind, Figma.
To fill: drop any item the final build does not use.

## What is real and what is simulated

Say this list on stage, and paste it into Devpost as is.
It starts from the honest-limits statement in `docs/demo-script.md`, section 6.

Real:
- The deal, the filings, and the lender's covenant are real and public. [verified]
- The statement lines are real: every amount in the input files matches its SEC filing. [verified: `evals/fixture_check.md`]
- The gateway, the math tools, the tie-out check, and the audit log with its hash chain are real code, and they run live in the demo. [verified]
- The flag and the leverage effect of each answer are computed by the tools, not written by a model. [verified]
- Agent memory is real, and it is policies the gateway wrote from the controller's answers. It is not a change to model weights. [verified: `backend/app/gateway/gateway.py`, `_learn`]

Not real, or not claimed:
- The statement lines come from public filings, not from the companies' internal books.
- Account-level detail is not public, so we do not claim it. The demo maps statement lines, not trial balances.
- Agent output on screen comes from one of four backends, and the screen badge says which. The recorded run is Factory Droid with Claude Haiku 5.5 requested, from 2026-10-24, 04:30. Droid does not prove which model served a run, so we say "requested". [verified: `backend/recordings/`, `docs/agents.md`]
- To fill on the day: which backend produced the run shown in the video and at the table (droid, anthropic, scripted, or replay).
- The flag card wording is fixed text. The question, the options, and their effects come from the API.
- The fiscal years differ, April 30 and September 30, so the combined income statement adds two different years and does not match the filed pro forma.
- The combined table is historical plus target. No purchase accounting is applied.
- Two inputs are our estimates: the Statesville cash rent we deduct ($1,970K, the 10-K's next-year obligation), and transaction and integration costs, which we set to zero. [inferred] The filing estimates $698K of expected transaction costs after the close, and we have not yet decided whether they belong in the tested period. [verified: Ex 99.2, Note 5(b); timing inferred]
- Three items in how we apply the EBITDA definition are still under review, so the leverage figures are preliminary. [verified: `evals/fixture_check.md`]
- The filing says its own reclassification table, Note 2, is preliminary. We use it as an answer key for shape, not to the dollar. [verified: Ex 99.2]
- The default reading of the financing liability is ours. No controller or lender has checked it. [inferred]
- No practitioner has used the tool yet. [verified]
- Other deals and other situations are roadmap, not built.
- The output is a combined set of books and a limit check that a human approves. It is not advice.

## Tracks

To fill before submission, and claim nothing unconfirmed:
- Hyphenate: select it on Devpost. One-line seat: "A portfolio controller at a PE-backed company, right after an add-on closes."
- Factory: claim "built with the Droid SDK" only for runs on the `droid` backend, and name the recorded run.
- Figma: describe only what Josie actually did in Figma and through the Figma MCP.
- Whether one project can enter several sponsor tracks is not confirmed by Cal Hacks.
