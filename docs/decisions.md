# Decision log

Last updated: 2026-10-24.
This log explains how Stochastic got to its current shape.
The source of truth for the product is `STOCHASTIC.md`.
If the two disagree, `STOCHASTIC.md` wins.

All decisions below were made on 2026-10-23, the first day of Cal Hacks 13.0.
They come from Cayden's own messages and the team's work that day.
Tags: [verified] means a file in this repo or a message from Cayden shows it. [inferred] means it is our judgment.
Vendor and author numbers are labeled self-reported.

The decisions are in the order they happened.
Later decisions replace earlier ones where they conflict.

---

## D1. First framing: one platform for any special situation

Date: 2026-10-23.

Decision:
Build one all-in-one platform for any corporate-finance special situation.
It had eight situations and six agents.
The demo raised money on the Organogenesis deal. [verified: Cayden's messages]

Why:
The Hyphenate track is about corporate finance work.
One platform looked like the biggest idea. [inferred]

Rejected:
Nothing yet. This was the starting point.

Revisit if:
Hyphenate judges ask for breadth over depth.
We do not expect this. The workshop rewards a few roles done deep. [verified: `STOCHASTIC.md` section 2]
Other situations stay as roadmap only.

Status: replaced by D2.

## D2. Pivot to M&A for banks and the buy side, then toward accounting and integration

Date: 2026-10-23.

Decision:
First we narrowed the product to investment banks and the buy side for M&A.
Then we saw that Hyphenate wanted an accounting-aligned solution with integration.
So we moved to PE add-on integration: merge the new company's books into the platform's books, then check the lender's limit. [verified: Cayden's messages, `STOCHASTIC.md` section 1]

Why:
The research compared three users.
Bankers running a sell-side process (User C) is the most crowded market, with funded products such as Rogo. [verified: `research/ma-workflow-research.md`, vendor-reported funding]
The portfolio controller after an add-on (User A) was the least served and has a hard check: totals must tie and the ratio is arithmetic. [inferred: from limited search, see the research file]
A defined deadline also exists: the compliance certificate is due 45 to 60 days after quarter end in the samples found. [verified: snippets, self-reported by Aleph]

Rejected:
- The banker as the user (User C). Too crowded, and a head-on fight with incumbents. [inferred]
- The seller-side finance lead (User B). Partly covered by QoE tools, and the data is harder to fake. [inferred]

Revisit if:
A practitioner tells us the portfolio controller is not the owner of this work.
Also revisit if Hyphenate says PE add-on integration is not a corner of a finance team. This is an open decision.

## D3. Different wedge from the closest prior work (VistaAI)

Date: 2026-10-23.

Decision:
Our wedge is accounting lines, plus a lender limit check, plus a gateway with maker-checker and an audit log.
We do not lead the pitch with ingestion. [verified: `STOCHASTIC.md` section 16]

Why:
VistaAI won first place at HackMIT 2026 (self-reported).
It ingests messy CSV and XLSX from acquired companies, proposes field mappings, and keeps provenance.
That is the closest prior work we found.
We differ in three ways:
- We work on accounting lines, not operational records.
- We check the result against a lender's limit.
- We post through a gateway with maker-checker and an audit log.

Rejected:
- A pure data-ingestion and mapping pitch. It overlaps with VistaAI too much.

Revisit if:
We learn that VistaAI, or another entry, also tests against a lender covenant.
Then we need a new differentiator.

## D4. Denied actions stay in the log but are not staged

Date: 2026-10-23.

Decision:
The gateway logs every denied action.
The demo does not stage an attack or a denied action.
A denied row is shown only if a judge asks to see the log. [verified: Cayden's feedback, `STOCHASTIC.md` section 9]

Why:
Cayden said staged denied actions feel tacky in a demo.
The log is still proof that the control works. [verified: Cayden's feedback]

Rejected:
- A staged denied-action moment, such as an agent trying to approve its own work on stage.

Revisit if:
A judge or mentor says the control is not believable without a live denial.
Hyphenate does want "a moment". Our moment is the flagged line that changes the verdict. [inferred]
We could add a short denial only if that moment is weak.

## D5. Three small stateless agents and a plain job runner

Date: 2026-10-23.

Decision:
Cut the six agents down to three small, stateless, replicable agents that mirror real accounting roles:
- Mapper (staff accountant)
- Preparer (senior accountant)
- Reviewer (reviewer)

A plain job runner moves work items between them.
There is no deal-manager agent. The runner is code, not a model. [verified: `STOCHASTIC.md` sections 6 and 7]

Why:
- Small stateless agents can run once per company or once per batch of lines.
- Real roles make maker-checker easy to explain.
- Code does all the math, so the agents do not need to coordinate. [inferred]
- Hyphenate rewards a few roles done deep. [inferred]

Rejected:
- Six agents.
- A deal-manager agent that decides what runs next.
- Agents that talk to each other.

Revisit if:
A step needs a judgment that the three agents cannot make.
Also revisit if the job runner grows decision logic. That would be a sign it needs a model.

## D6. Demo scope: two minutes, one simple screen

Date: 2026-10-23.

Decision:
- Total time is 2 minutes.
- The pitch is 1:30 and the live demo is 0:30.
- Agent text is hardcoded or recorded, and we say so.
- The gateway, the math, and the audit log are real.
- The output is one simple screen: a flag card, a small combined table, and one verdict line. [verified: Cayden, 2026-10-23; `STOCHASTIC.md` sections 2 and 12]

Why:
The time limit is short.
A simple screen lets a judge see the result in seconds.
Being honest about what is simulated builds trust. [inferred]

Rejected:
- Several screens, as in the older four-screen Figma mockups.
- Live agent calls as a must-have. A live Droid-backed call is a "should" item.
- A live SEC call on stage.

Revisit if:
The time limit changes.
Also revisit if the live agent call proves reliable in rehearsal.
Then we can show it live.

## D7. Input is two statement files plus a short brief

Date: 2026-10-23.

Decision:
The product takes the platform's statement file, the target's statement file, and a short brief.
The brief states the lender's limit and the covenant's definitions of debt and EBITDA. [verified: `STOCHASTIC.md` sections 4 and 10]

Why:
These are the minimum inputs for the workflow.
The brief keeps the covenant definitions in plain text, so code reads them and does not guess.
Definitions are bespoke per deal, so one generic definition would not be credible. [verified: `research/post-close-deliverables.md`]

Rejected:
- Reading the full credit agreement in the MVP.
- Arbitrary uploads, accounts, and login.

Revisit if:
Reading the credit agreement text turns out to be easy and reliable.
It could become a later feature.

## D8. Real deal: Kewaunee Scientific buys Nu Aire

Date: 2026-10-23.

Decision:
The proof deal is Kewaunee Scientific buying Nu Aire. It closed on 2024-11-01 for $55M.
It ranked first of five candidates.
The flag is Kewaunee's "Financing liability" line. [verified: `research/real-deal-candidates.md`]

Why:
The ranking is [inferred] by the research agent, not a measured score.
Reasons for rank 1 [verified: filing, per the research file]:
- A real leverage covenant: Senior Funded Bank Debt to EBITDA below 2.50 to 1.00.
- A real $5M acquisition basket.
- A filed reclassification table (Note 2) that works as an answer key.
- Both companies' statement lines differ enough to make mapping credible.
- It is small relative to the acquirer.

The flag is real.
The "Financing liability" line holds both the Statesville sale-leaseback and the new acquisition financing.
The credit agreement excludes the Statesville lease from covenant debt.
So a human must say which part is covenant debt.

Rejected:
- DLH and GRSi (rank 2). It has a ready combined EBITDA answer key, but the deal is larger and no acquisition basket was found.
- Mama's Creations and Crown I (rank 3). It has weak leverage drama.
- Shutterstock and Envato (rank 4). It is about $250M and uses IFRS.
- Standex (rank 5). It is too large, and its credit agreement was not retrieved.

Revisit if:
Tri computes the ratio and the verdict does not change with either treatment of the flag.
Then the moment is weak, and we pick the flag wording again or switch to a backup. [verified: `TASKS.md` risks]
Also revisit if the Kewaunee D&A or revolver draw cannot be found.

## D9. Agent runner: Factory Droid SDK, Python preferred, two backends, no A2A

Date: 2026-10-23.

Decision:
Use one function, `run_agent(role, item)`, with two backends.
The Anthropic API is the real path and the stage fallback.
The Factory Droid Python SDK runs the agents we show as built with Droid.
An `AGENT_BACKEND` setting switches between them, and a recorded run is the last fallback.
We skip A2A (agent-to-agent protocol). [verified: `STOCHASTIC.md` section 6; the framework comparison is in `research/agent-framework-options.md`, which this log did not re-read]

Why:
- Factory is a target sponsor track, and Cayden has a Factory account on the Plus plan. [verified: `STOCHASTIC.md` section 15]
- Two backends protect the demo if the Droid subprocess fails live. [verified: `TASKS.md` risks]
- Agents do not talk to each other, so A2A has no job here. [inferred]

Rejected:
- A single backend with no fallback.
- A2A.

Revisit if:
`list_models()` shows Droid cannot run Claude models on our key. That decides the backend. [verified: `TASKS.md`]
Also revisit if the Python SDK does not qualify for the "Building with the Droid SDK" prize.

## D10. Team split and per-person branches

Date: 2026-10-23.

Decision:
- Cayden: agent layer, gateway changes, and the demo run.
- Josie: UI and UX only.
- Eric: data (the two input files, the brief, the answer key, the real-deal facts).
- Tri: math tools, tests, and the API that the console reads.

Each person has a task file, a branch, and folders they own. [verified: `TASKS.md`]

Why:
The split follows the work. [verified: `TASKS.md`]
Per-person branches let four people build in parallel without conflicts.
We do not know each person's strengths from our notes, so tasks can be swapped. [verified: `TASKS.md`]

Rejected:
- Giving Josie any task other than the design.
- One shared branch.

Revisit if:
A person is blocked or finishes early.
Swap tasks and tell the team.
The shared contract must be agreed first, in a 30-minute session. [verified: `TASKS.md`]

---

## D11. Target tracks: Hyphenate, Factory, and Figma

Date: 2026-10-24.

Decision:
We target three tracks: Hyphenate (main), Factory, and Figma. [set by Cayden, 2026-10-24]
Tiger Data, Microsoft, and Most Technically Advanced are not targeted.

Why:
Each track asks for different proof, so the work overlaps little.
Hyphenate needs the real deal, the limits in code, and a moment.
Factory needs agents that run through the Droid SDK.
Figma needs the console designed in Figma and built from the Figma frame, with Figma on screen.
The Figma MCP is already in use: the design system and four screens were built through `use_figma`. [verified: `design/README.md`]
The Figma prizes are five at $1,000 each (self-reported, from the pre-event guide and Devpost). [verified: `CalHacks/ideation/sponsors/figma.md`]

Rejected:
- Tiger Data as a target. The Postgres store is a Should item, and forks add little to a one-screen demo. [inferred]
- Microsoft, because it needs Microsoft products that we do not use. [inferred]
- Chasing every sponsor. Stacking three prizes is already rare (22 of 1,324 winners for three or more). [verified]
- An earlier note that skipped Figma as "no honest fit". That note predates the design work.

Revisit if:
The Figma prompts, when read on the Live Site, ask for something we cannot show.
Our team has no Figma Agent access, so only Best Design and Most Creative remain realistic.
A Hyphenate mentor says the sponsor tracks cost too much attention.

---

## D12. Agents are stateful, with memory the gateway writes

Date: 2026-10-24.

Decision:
Agents are stateful, not stateless. [set by Cayden, 2026-10-24]
Each role keeps an `AgentSession` (backend, backend session id, turns, a short transcript).
The controller's answer to a flag becomes a `Policy` that the Mapper applies next time and cites as its reason.
The state lives in the store, and only the gateway writes it. [verified: `backend/app/gateway/gateway.py`]

Why:
- Hyphenate's workshop names "memory that ends with the context window" as a weak signal and "improves with every correction" as a strong one. [verified: `hyphenate-workshop.md`]
- A second run that asks nothing is a visible moment, and it is honest: the policy row and the `policy:apply` log row are on screen.
- The Droid SDK keeps sessions per role, so the backend supports it directly.

Rejected:
- Stateless one-shot agents (D5's wording). The runner, the roles, and the typed contracts stay the same; only the memory was added.
- Memory inside the model's context only. It would not survive a restart or reach the audit log.

Revisit if:
A judge reads the policy as the agent approving its own future work. The answer is that the controller approved the decision once, the gateway recorded it, and a reversal clears it.

## D13. The flag figures are computed, and the moment holds

Date: 2026-10-24.

Decision:
Covenant EBITDA is $28,379K. Senior Funded Bank Debt under the agreement's reading is $21,633K, leverage 0.76x. Counting the whole financing liability line gives $71,955K and 2.54x, over the 2.50x limit. [verified: `backend/tests/test_trust_rules.py`]
The default option on the flag is the agreement's reading (b).
Two inputs are inferred and are said out loud: the Statesville cash rent deduction ($1,970K from the 10-K obligations table) and transaction and integration costs applied as 0.

Why:
- Every figure comes from the filings read on 2026-10-24 (10-Q, 10-K, Ex 99.1, Ex 99.2, Ex 10.1).
- The verdict changes with the controller's answer, which is what the demo needs.

Rejected:
- Using the filed pro forma column for Nu Aire. The fiscal years differ, and the audited September year is the honest raw input.
- Annualizing the six-month figures. It would be an invented number.

Revisit if:
Eric's check of the figures against the filings finds a different depreciation, rent, or financing figure. The tools recompute; only the fixture changes.

## D14. One backend function, four backends, and the result says which ran

Date: 2026-10-24.

Decision:
`run_agent` tries `AGENT_BACKEND` and falls back along `AGENT_FALLBACK` (default `anthropic,scripted` until 2026-10-24 08:00, `scripted` since, because no Anthropic key exists). The `replay` backend plays recorded outputs; the Preparer and Reviewer re-run their tools on replay so the run ids are real. Every result carries `backend`. [verified: `backend/app/agents/runner.py`]

Why:
The pitch must be honest about which runs went through Droid, and the demo must survive any backend failing.

Rejected:
- Hiding the fallback. The console shows the backend status from `GET /health`.

Revisit if:
Factory's rubric requires the TypeScript SDK. Then a small Node runner behind the same function is the swap.

## D15. Tiger Data becomes a target track

Date: 2026-10-24, evening.

Decision:
Tiger Data is the fourth target track, beside Hyphenate, Factory, and Figma. [set by Cayden, 2026-10-24]
This replaces the "Rejected: Tiger Data as a target" line in D11.

Why:
D11 rejected Tiger Data because the Postgres store was only a Should item.
The store is now built: the record, the audit log, and the agents' memory are written through to Postgres on Tiger Cloud, and the audit log is a TimescaleDB hypertable that refuses edits. [verified: `backend/app/db/postgres.py`, `backend/tests/test_postgres_store.py`]

Revisit if:
Cal Hacks says one project cannot opt into this many sponsor tracks.

---

## Open decisions

These come from `STOCHASTIC.md` section 18.
They are not decided yet.

1. Does PE add-on integration count as a corner of a finance team for Hyphenate? Ask a Hyphenate mentor on Saturday.
2. Which part of Kewaunee's financing liability counts as covenant debt? All three readings are computed (D13). A practitioner should confirm the default.
3. Kewaunee's depreciation ($3,125K, 10-K) and the revolver draw ($5,563K, Ex 99.2 Note 4(h)) are now loaded. Eric re-checks them against the filings.
4. Can Droid run Claude models on our key? Install the `droid` CLI and run `scripts/droid_probe.py`.
5. Does the Python Droid SDK qualify for "Building with the Droid SDK" when the tools call our own gateway?
6. Does the SEC allow us to redistribute the cached filings?
7. Does a former-banker or controller reviewer count as the human seat?

## D16. The gateway owns the moment and the memory mark; Sonnet runs the demo Mapper

Date: 2026-10-24, 08:30. Decided by Cayden's agent during the live end-to-end tests, under Cayden's goal to finish his task list.

Context: live Droid runs on Haiku 5.5 showed three things the scripted runs hid. One run offered three readings of the financing liability, all under the limit, so the 2.54x moment did not appear. The model's mapping reasons read "Controller policy maps ...", so the console's Learned chip (which looked for "Policy" at the start of the reason) never showed. A second run with memory raised a new flag on lines the first run had not asked about.

Decision:
1. Every covenant flag shows the count-everything reading. When the Mapper does not offer it, the gateway adds it, computed by the same tools and labelled as the gateway's. The controller always sees what the exclusions are worth, and the trust story is unchanged: the gateway adds an option, it never removes or edits one.
2. The gateway marks a learned line from the policy record (`policy_id`), and only when the cited policy decided the same thing. No model wording decides what the console calls learned.
3. The demo Mapper runs on Sonnet 5.5 (`DROID_MODEL_MAPPER`); the Preparer and Reviewer stay on Haiku 5.5. Sonnet held both moments in two trials of two; Haiku in one of two and zero of one.
4. The default fallback is `scripted`. Anthropic returns to the chain only with a key.

Evidence: `agents.md` section 9, rows 08:06 to 08:33; tests `test_covenant_flag_always_shows_the_count_everything_reading`, `test_learned_lines_are_marked_by_the_gateway_not_by_the_model_wording`, `test_second_run_while_one_is_in_progress_is_refused`.

## D17. A covenant flag's what-ifs live in a Tiger fork

Date: 2026-10-24, 09:00. Cayden chose to delete the paused `larp-city` service (backed up first) to free the free plan's second service slot.

Decision: when the Mapper raises a covenant flag, the gateway forks the ledger on Tiger Cloud in the background and writes each option's what-if (tags, effect, tool outputs, run id) into a `what_if` table in the fork. The live record never holds a hypothetical. The controller's answer keeps one option in the ledger, and the gateway deletes the fork with the alternatives, which frees the slot. Each step is a gateway write: `fork:create`, `fork:ready`, `fork:delete` (or `fork:failed`, `fork:skip`) in the hash-chained log, and the fork state on the flag.

Why: a plain Postgres store does not stand out for Tiger Data, and forks are what Tiger Data pushes (`sponsors/tiger-data.md`). The fit is honest: a what-if is exactly a copy of the ledger that may be thrown away.

Limits: a fork takes 33 to 35 s, so it never blocks the flag; the options and effects are computed in process as before. The free plan allows one fork beside the main service, so a second covenant flag while a fork is open gets none and says so. A fork left by a crash is deleted on the next start (`FORK_PREFIX`).

Evidence: `backend/tests/test_whatif_forks.py` (lifecycle, answer before ready, failure, one slot, cleanup, and an opt-in round trip against Tiger that passed on 2026-10-24); the live browser run at 08:53 in `agents.md` section 9.


## D18. The whole-line reading is as filed, and the gateway enforces what the prompts only asked

Date: 2026-10-24, evening. Decided by Cayden after a six-part risk review of the project (finance, live demo, track fit, claims, agent design, UI).

Context: the review found two kinds of problem.
The finance review found that option a counted the Statesville financing as debt while still deducting its rent from EBITDA, which mixes two readings: made consistent it is 2.37x, under the limit, and as built it was over by only $403K of EBITDA. [verified: arithmetic]
The agent-design review reproduced, against the real gateway, a Mapper that excluded the financing lines itself (0.04x, Reviewer pass), a Preparer result that cited a what-if run (0.76x stored after the controller chose 2.54x) or passed raw numbers to leverage (0.01x), a Reviewer pass with no runs that went straight to POSTED, and a reversed answer that stayed live as a policy for the next deal.

Decision:
1. The whole-line option is computed as filed: balance sheet debt over reported EBITDA, with no add-back and no rent deduction. On the demo deal that is $71,955K over $25,312K, 2.84x, over the limit, and it needs $3,470K more EBITDA to pass. Choosing it puts the deal on the as-filed basis (`Deal.ebitda_basis`), so the result is the same 2.84x the card showed and approval is refused. The other options keep covenant EBITDA (0.76x and 1.56x).
2. A model's `not_debt` tag is refused unless it cites a live policy learned on that company's line.
3. A result must cite the Preparer's own runs made after the last answer: non-naive debt, the deal's EBITDA basis, a leverage run that divides exactly those two, and rows equal to the consolidate run. Agents call `leverage` with run ids only.
4. The gateway reads the Reviewer's pass from its `tie_out` and `limit_test` runs on this result.
5. Policies are scoped to the company, and a reversal retires the policies a flag taught.
6. A refused model result is retried once with the reason (Mapper), then made by the scripted backend under the same checks, so a refusal does not end the run on stage.
7. Demo hardening from the same review: the pinned replay is a first run that raises the flag, `/dev/reset?keep_memory=false` is the reset between judges, the reset refuses during a run and frees the fork slot, and `DROID_TIMEOUT` defaults to 90 s (75 in the demo `.env`).

Why: "the gateway, not the prompt, enforces it" is the pitch, and each of these was true only in the prompt. The as-filed reading removes the thin margin without changing the agreement's reading.

Not changed: the test period. Each company's latest fiscal year stands in for the agreement's trailing twelve months to the closing quarter; that rebuild is the next step, said out loud.

Evidence: `backend/tests/test_gateway_guards.py` (one test per attack), `backend/tests/test_demo_reset.py`, `backend/tests/test_mapper_retry.py`, `test_the_demo_run_beat_by_beat`; commits 0e3829f and 3938ca9.
