# Demo script: the 2:00 pitch

Last updated: 2026-10-24, evening. The figures below are computed by the tools on the fixture and tested. The failure switch was rehearsed (section 5).
Changed on 2026-10-24 evening: the whole-line reading is computed as filed (2.84x), the gateway guards are in, and the stage backend is live Droid with a scripted fallback.
The product and scope are in `STOCHASTIC.md`. This file only says what we show and say.
Claims are tagged [verified] when a source file shows them and [inferred] when they are our judgment.
Figures come from the filings loaded in `backend/app/db/fixtures/kewaunee.py` and the tool runs. [verified: `backend/tests/test_trust_rules.py`]

## 1. The 2:00 plan

The budget is 1:30 for the pitch and 0:30 for the live demo. [verified: `STOCHASTIC.md`, section 2]
Order: the problem, then what Stochastic does, then the proof. Do not lead with the demo or the deal name.

| Time | Part | Goal | On screen |
| --- | --- | --- | --- |
| 0:00 - 0:25 | Problem | The judge feels the gate: the next deal waits on the books. | Title slide or the empty console. No demo yet. |
| 0:25 - 0:55 | What Stochastic does | Five steps in plain words: map, flag, combine, test, approve. | A simple flow slide, or the console at rest. |
| 0:55 - 1:30 | Proof and honesty | A real public deal. Stateful agents that learn from the controller. Math is code. Say what is simulated. | The real-versus-simulated list. |
| 1:30 - 2:00 | Live demo | One flag, one approval, one verdict line. | The console: Dashboard, then the Case page (`/case`). |

Who speaks: one presenter talks. A second person drives the keyboard. The rest of the team stands back. [inferred]

### Words for each part
These are the words. Say them casual, in your own voice, but keep every number as written. [figures verified: `backend/tests/test_trust_rules.py`]

Part 1, the problem (0:00 - 0:25):

```text
A private equity firm that keeps buying small companies has a gate on every deal.
The lender sets a limit, like debt under two and a half times EBITDA, and tests it on the combined company.
So the next deal waits until someone merges two sets of books.
Today that is a controller, a spreadsheet, and weeks.
And one wrong line flows into every number after it.
```

Part 2, what it does (0:25 - 0:55):

```text
Stochastic does the repeatable part and keeps what you decide.
A Mapper agent matches the new company's lines to the platform's lines and says how sure it is.
It stops only on the lines it should not decide alone, and shows what each answer does to the ratio.
Code combines the books, ties them out, and tests the lender's own definition of debt and EBITDA.
A controller approves. Every step is in a log that cannot be edited.
And the controller's answer becomes a policy, so the agent asks once.
```

Part 3, proof and honesty (0:55 - 1:30):

```text
We ran it on a real deal: Kewaunee Scientific buying Nu Aire, closed November 2024, from the public filings.
One line, "financing liability", holds a sale-leaseback, the new bank debt, and seller notes.
Read the filings as filed, count the whole line, and leverage is 2.84x, over the limit. Read the agreement and it is 0.76x.
That is the difference between a covenant breach and about forty-nine million dollars of covenant headroom.
The agents are roles on a real team. They never do math. Code does it, and every number carries a run id.
The gateway is the only thing that writes. An agent cannot approve its own work, and a number no tool produced is refused.
Here is what is not real. [the honest-limits statement, section 6]
```

Part 4, the live demo (1:30 - 2:00): section 2, beat by beat.
If a judge gives a second minute, the memory moment: reset, run again, no flag, and the `policy:apply` row in the log.

## 2. The 30-second live demo, beat by beat

Rules:
- The console opens on the Dashboard (`/`); the demo runs on the Case page (`/case`): the flag card, the verdict line, and the combined books, with Mapping, Review, and Log tiles on the right. [verified: `frontend/README.md`]
- The presenter does not read numbers aloud unless they are final. See section 4.
- Do not stage a denied action. Show a DENIED row only if a judge asks to see the log. [verified: `STOCHASTIC.md`, section 9]

Measured on live Droid on 2026-10-24 08:30 (Mapper Sonnet 5.5, Preparer and Reviewer Haiku 5.5, `STORE=postgres`) [verified: `agents.md` section 9]:
- Run to the flag card: 47 to 49 s. Too long for beat 2, so run the deal to the flag before each judge arrives (reset with memory cleared, press Run, wait for the card).
- Last answer to a live Approve button: 36 to 38 s (Preparer about 28 s, Reviewer about 9 s). Answer the flag early and talk over this wait: the gateway, the tools, the run ids.
- Second run after a reset with memory kept: 58 s to approval, no flag. Show it at the table only if a judge has the time, or point to the Learned chips.
- If the timing does not fit, use `AGENT_BACKEND=replay` for the pitch and say so: the recorded Sonnet 5.5 Droid run's text, with every tool run live. The pinned replay is a first run, so it raises the covenant flag. [verified: `test_demo_reset.py`]
- Between judges, reset with memory cleared: the console's "Fresh deal (clear memory)" on the Case page, or `curl -X POST 'localhost:8000/dev/reset?keep_memory=false'`. The plain reset keeps memory, and the next judge would see no flag. The reset is refused while a run is going (409) and frees the fork slot.
- The console shows a progress row while the agents work: which agent, and for how many seconds.

The beats below are the original plan; Cayden times the real version with a stopwatch (`tasks/cayden.md` task 5).

| Beat | Time | On-screen state | Presenter says | Hardcoded or real |
| --- | --- | --- | --- | --- |
| 1. Start | 1:30 - 1:35 | Console is open on the Dashboard. The Kewaunee Scientific case reads "Not started". Upload shows the two statement files and the brief already loaded. | "Two statement files and a short brief with the lender's limit." | The files and brief are real data from filings. The load is real. |
| 2. Run | 1:35 - 1:42 | Press Begin. The Case page opens, and a progress row shows the Mapper working, with its seconds. | "The Mapper matches each Nu Aire line to a Kewaunee line." | The mapping call goes through `run_agent` on the backend the sidebar's model card names (live Droid on stage). The confidences come from the typed output. |
| 3. Flag | 1:42 - 1:50 | The "Lender definition question" card appears for "Financing liability". Each option shows its ratio in large type with Over the limit or OK; the filing evidence is folded under the options. | "It stopped on the line it must not decide alone. Financing liability holds a sale-leaseback, the new bank debt, and seller notes. Which parts are covenant debt?" | The question and options are the Mapper's. Each ratio and effect comes from a gateway tool run. The flag work item and its state NEEDS_INFO are real gateway state. |
| 4. Answer | 1:50 - 1:55 | The controller clicks Approve on one option, or Change. | "The controller decides. Not the model." | The answer call is real. The gateway logs it. |
| 5. Combine and test | 1:55 - 2:00 | The verdict line shows 0.76x against 2.50x with OK and Reviewer pass, and under it "read as filed, counting the whole financing line: 2.84x, over the limit". | "Code adds the books and tests the lender's limit. That is the verdict." | The Preparer's tool calls, the math, the tie-out, and the limit test run for real. The gateway checks that every figure is the Preparer's own run and reads the Reviewer's pass from its checks. |
| 6. Close | after 2:00 if asked | The presenter clicks the Log tile on the Case page (or Log in the sidebar). | "Every step is here, and each row is chained to the one before." | Real. The chain check is real. |

What runs for real: the gateway (state changes, maker-checker, permissions), the math tools (consolidation, EBITDA, leverage, limit test), the tie-out check, and the audit log with its hash chain. [verified: `STOCHASTIC.md`, section 2]
What the model writes: the mappings, the flag question, and the option labels, on the backend the model card names.
What is a fallback: the scripted rules, used when the model run fails or the gateway refuses its result twice. See section 5.

### The paced run: agents talking, live mapping, the escalation

For a demo on the scripted or replay backend, start the API with `DEMO_PACE=1`, so the run plays at a speed people can follow instead of finishing in a blink.
Do not put it in `.env` for live Droid: a live model gets no added wait anyway, and the variable only matters for `scripted` and `replay`.

```text
cd backend
AGENT_BACKEND=replay DEMO_PACE=1 .venv/bin/uvicorn app.main:app --port 8000
```

What the room sees, with the times measured on 2026-10-24 (scripted, `DEMO_PACE=1`):
- 0 s, Run: the Gateway hands the Mapper its work item, and 2.5 s later the Mapper proposes 53 mappings and 2 questions.
- 3 to 19 s: the mapping view fills line by line, about 0.3 s per line (`mapping` events).
- 19 to 23 s: the Gateway checks and accepts the mappings, then the Mapper asks the controller two questions, 1.5 s apart. The flag cards open.
- The controller answers. The conversation shows each answer going back to the Mapper and the policies it taught.
- 0 to 12 s after the last answer: the Mapper hands off to the Preparer, the Preparer's four tool runs arrive about 1 s apart with their figures, the Preparer reports the draft books (leverage 0.76x against 2.50x, with the run id), the Gateway confirms every figure traces to a run, the Reviewer checks the tie-out and the limit test, and hands off: "Ready for your approval".
- After: open the Log for the audit rows, then the Review page for the books and the edits.

`DEMO_PACE=0.5` plays it twice as fast; `DEMO_PACE=2` twice as slow.
Every line of the conversation is written by the gateway when the thing happens, from the record (see `architecture/gateway-and-api.md`, "Live events").
The pace only spaces it out; it changes no figure, no check, and no message.
The pace on replay is honest to say: "the recorded run's text, played at reading speed, with every tool run live".

### Who clicks what

- Presenter: speaks only.
- Driver: presses Run, clicks Approve or Change, opens the log link.
- Backup driver: holds the recorded-run switch and watches the clock.

## 3. The data on screen
Use only these figures. All are from filings or computed by the tools from them. [verified: fixture and tests]

| Item | Figure | Source |
| --- | --- | --- |
| Deal | Kewaunee Scientific buys Nu Aire | Ex 99.2 |
| Close date | 2024-11-01 | 8-K |
| Price | $55M, subject to adjustments | Ex 99.2 |
| Funding | $15,000K PNC term loan, $5,563K drawn on a $20M PNC revolver, $22,540K of 8% subordinated seller notes | Ex 99.2 Note 4(h) |
| Leverage covenant | Senior Funded Bank Debt to EBITDA below 2.50 to 1.00, Section 4.8(a) | Ex 10.1 |
| Fixed charge covenant | At least 1.20 to 1, Section 4.8(b) | Ex 10.1 |
| Acquisition basket | $5,000,000, Section 5.8(ii) | Ex 10.1 |
| Kewaunee fiscal 2024 net sales | $203,755K | Ex 99.2 |
| Nu Aire audited net revenues (year to 2024-09-30) | $74,850,302 | Ex 99.1 |
| Kewaunee depreciation, fiscal 2024 | $3,125K | 10-K cash flow |
| Nu Aire D&A (year to 2024-09-30) | $1,830,395 | Ex 99.1 |
| Kewaunee financing liability at 2024-10-31 | $750K current plus $27,032K long-term; carrying value $27,782K | 10-Q |
| Statesville cash rent (deducted from EBITDA) | $1,970K, next-year obligation; inferred as the year's rent | 10-K contractual obligations |
| Covenant EBITDA | $28,379K (pension termination $4,019K and stock compensation $1,018K added back, cash rent $1,970K deducted) | tool run `ebitda` |
| Senior Funded Bank Debt, agreement's reading | $21,633K | tool run `covenant_debt` |
| Whole financing liability counted (naive) | $71,955K | tool run `covenant_debt`, naive |
| Reported EBITDA, as filed | $25,312K (net income, interest, taxes, D&A; no add-backs, no rent deduction) | tool run `ebitda`, as filed |
| Covenant leverage | 0.76x, 1.74x of room, about $49.3M of covenant headroom | tool runs `leverage`, `limit_test` |
| Whole-line leverage, as filed | 2.84x, over the limit; it needs $3,470K more EBITDA to pass | tool runs |
| Combined total assets | $182,456K, and the combined balance sheet balances | tool runs `consolidate`, `tie_out` |
| Example reclasses (Note 2) | Accrued Commissions to Employee compensation and amounts withheld. Income taxes payable to Other accrued expenses. Interest Income - Net to Other income, net | Ex 99.2 |

Two inputs are inferred and are said in the honest-limits statement: the rent deduction, and transaction and integration costs applied as zero because the filings do not quantify them.
Neither moves the whole-line reading any more: it is computed as filed, with no add-back and no rent deduction.
The covenant headroom is a covenant figure, not money to spend: the next add-on is still capped by the $5M acquisition basket (Section 5.8(ii)) and by the undrawn revolver, about $14.4M.
If Tri or Eric change a figure, the tools recompute; re-read the flag effects on screen before the pitch and do not say a number from memory.

## 4. The flag moment and the two verdicts
### The flag

The flag is Kewaunee's "Financing liability" line. [verified: fixture]
It holds the Statesville sale-leaseback ($27,782K), the new PNC term loan and revolver ($20,563K), and the 8% seller notes ($22,540K).
The credit agreement's Senior Funded Bank Debt excludes the capital lease on 2700 West Front Street and excludes subordinated debt. [verified: Ex 10.1]
So the card asks which parts count.

The card shows (all from the API, nothing typed by hand):
- The question, in one sentence.
- The evidence: the covenant wording and the two exclusions, with the exhibit and section.
- Three options, each with its ratio in large type, its computed effect, and a run id.
- The default, option b, the agreement's reading.

| Option | Effect on the card | Verdict |
| --- | --- | --- |
| a. The whole line counts | As filed: debt 71,955K over reported EBITDA 25,312K. Leverage 2.84x against 2.50x. | Over the limit |
| b. Only the PNC term loan and revolver count | Senior Funded Bank Debt 21,633K. Leverage 0.76x against 2.50x. | OK |
| c. PNC debt and the seller notes count | Senior Funded Bank Debt 44,173K. Leverage 1.56x against 2.50x. | OK |

A second, smaller flag asks where Nu Aire's Certificates of Deposit ($991K) belong. Answer it with the default (cash equivalents) in one click, or raise the Mapper threshold to drop it.

### Two outcomes

| Answer | Verdict line | Presenter says | Reviewer badge |
| --- | --- | --- | --- |
| b (the agreement's reading) | OK. 0.76x against 2.50x. Room 1.74x. | "Under the limit, with the covenant's own definition of debt. About forty-nine million of covenant headroom; the next add-on still needs the basket and the revolver." | pass |
| a (whole line) | Over the limit. 2.84x against 2.50x, as filed. | "Over the limit. The item comes back as needs-attention and cannot be approved." | needs_attention |

Notes:
- Over the limit returns the item to the human as needs-attention, and the gateway refuses approval. [verified: `test_choosing_the_whole_line_reading_is_as_filed_end_to_end`]
- Choosing a puts the deal on the as-filed basis, so the result is the same 2.84x the card showed. That is the "controller says no" path, one click, if a judge asks for it.
- Click b in the demo. Point at a on the card and say the as-filed number out loud. That is the moment: one line, two readings, 2.08x apart.
- The memory moment, if time allows: reset, run again, no flag. "It asked once. The controller's answer is now a policy, written by the gateway, and the log shows it applied."

### The honest sensitivity

The whole-line reading is one reading end to end: balance sheet debt ($71,955K) over reported EBITDA as filed ($25,312K), 2.84x.
It would need $3,470K more EBITDA to pass, so a missed add-back or a different rent figure cannot flip it.
Why not covenant EBITDA for that option: counting the Statesville financing as debt while still deducting its rent mixes two readings; made consistent it would be 2.37x. [verified: arithmetic]
The covenant reading (0.76x) uses the agreement's EBITDA, with the inferred rent and zero transaction costs; it stays far under the limit either way.
If a judge asks about the test period: "We used each company's latest fiscal year; the agreement tests the last twelve months to the closing quarter, which is next."
Know this before a judge asks.

## 5. Failure plan
The agent layer has one function, `run_agent(role, item)`, with four backends. `AGENT_BACKEND` picks one and `AGENT_FALLBACK` (default `scripted`) lists the fallbacks. [verified: `backend/app/agents/runner.py`]
The Anthropic backend has run on Eric's key (one full recorded run, about 50 Mapper trials), but there is no key on the demo laptop, so it is not in the chain.
If the gateway refuses a model's result, the Mapper retries once with the reason, then the scripted backend makes the result under the same checks. [verified: `test_mapper_retry.py`]
`DROID_TIMEOUT` is 75 s in the demo `.env` (code default 90 s), so a hung Droid run costs about a minute, not four.
The gateway, math tools, and log are plain code and do not depend on any backend.

Rehearsed on 2026-10-24, 04:50 [verified]: the API was started with the `droid` CLI missing from PATH. `POST /deals/{id}/run` returned `mapper ran on scripted`, and `GET /health` showed the attempts: droid failed ("Droid executable was not found"), anthropic failed ("ANTHROPIC_API_KEY is not set"), scripted ran. The screen kept working and the backend badge said scripted.
Also found: Droid accepts an unknown model id without an error, so a wrong `DROID_MODEL` is not a failure, it is a silent default. Keep `DROID_MODEL=claude-haiku-5-5` in `.env` and say "Claude Haiku 5.5 through Droid" only when the probe has listed that model.

| Failure | Sign | What the system does | What to say |
| --- | --- | --- | --- |
| Droid fails | The run takes more than the timeout, or `GET /health` shows a failed droid attempt | Falls to `scripted`. Same screen, same gateway. The sidebar's model card says "Scripted rules, no model". | "The Droid run dropped. This one ran on the fallback. Same roles, same gateway, same math." |
| A background run stops on an error | The headline says "The run stopped before it finished" | Nothing is posted. Run again continues where it stopped; the log has the reason. | "That run stopped; running it again." |
| You want no live model call at all | Before the demo | Set `AGENT_BACKEND=replay`: recorded outputs from the Sonnet 5.5 Droid run (`backend/recordings/`), with the tools re-run | "This is the recorded run from this morning. The tool calls are live." |
| Console fails | Blank page or API error | Reload once. Then show the API: `GET /deals/{id}/case` in a browser tab is readable. | "Let me show the raw case." |
| Wi-Fi fails | No network | `scripted` or `replay` need none. The demo makes no live SEC calls. The store keeps working in memory and queues its writes to Tiger until the network is back (`GET /health` `store.pending`). | None needed. |
| Tiger Cloud unreachable at start | The sidebar's model card says "Tiger unreachable" (in memory) | The API runs in memory; nothing is lost from the screen | "The database is down, so this run is in memory. The log and the chain are the same." |
| A Run click while a run is going | 409 "a run is already in progress" | Nothing; the running job finishes | None needed. |
| The Tiger fork fails or is slow | The flag card says "no fork (...)" or still "Forking ..." | The options and effects are computed in process as always; answer when ready | "The fork is still coming up; the figures are already computed." |

### The restart moment (Tiger), rehearsed 2026-10-24 08:09 [verified]

1. Run the deal, answer the flags, and approve, with `STORE=postgres` (the model card says Tiger Cloud).
2. Stop the API and start it again (`Ctrl-C`, then `backend/.venv/bin/uvicorn app.main:app --port 8000`; with `--reload`, saving any backend file restarts it).
3. Reload the console. The verdict, the combined table, the answered flags, the log (55 rows, chain intact, the one real DENIED row), the 11 policies, and the three Droid sessions are all back, loaded from Tiger.
4. Words: "The process just restarted. Nothing was in its memory. Everything on screen came back from Postgres on Tiger Cloud, and the log still checks."

Checked on 2026-10-24 08:09: every top-level field of `GET /deals/{id}/case` was identical before and after the restart, and the restarted process had no runs of its own.

### Tiger in SQL (optional, 30 seconds, for the Tiger Data judges)

Use this part only when a Tiger Data judge is at the table, or when a judge asks where the data lives.
Open `psql` on the `stochastic` service before the table opens (`tiger db psql p4a7k2ox3x`).
The views are made by `ANALYTICS_SQL` in `backend/app/db/postgres.py`.

1. Show the learning, one row per run:

   ```sql
   SELECT ledger, reason, flags, answers, policies_applied, stage, leverage
   FROM stochastic.ledger_runs ORDER BY ledger DESC LIMIT 4;
   ```

   Words: "Each reset is a new ledger, and nothing is erased. With memory cleared, the Mapper asks two questions. With memory kept, it asks none and applies six policies. The leverage is the same."

2. Show one BM25 search over the record:

   ```sql
   SELECT kind, id, left(search_text, 70) AS text
   FROM stochastic.record WHERE ledger = (SELECT max(id) FROM stochastic.ledger)
   ORDER BY search_text <@> 'seller notes subordinated' LIMIT 4;
   ```

   Words: "This is BM25 ranking with pg_textsearch, over every line, mapping reason, flag, and policy. The seller notes line comes first, and the flag that asked about it comes second."

3. If there is time, show the measured number:

   ```sql
   SELECT * FROM stochastic.run_stats;
   ```

   Words: "This uses the TimescaleDB Toolkit over every posted run. The time includes the time that the controller took to answer."

Other objects to name if asked: the continuous aggregate `audit_activity` (rows per minute by actor), and the columnstore policy on `audit_log` (chunks older than one day are columnar).
Live on 2026-10-24: 23 ledgers, 12 posted runs, mean 98 s, p50 84 s, p95 465 s. [verified]
The Tiger MCP can run the same queries from Claude Code. [verified: 2026-10-24]

Rules for failure:
- Never hide a failure. Say it in one short line and move on. The model card in the sidebar already says what ran.
- Say "built with the Factory Droid SDK" only about runs that went through the `droid` backend. [verified: `architecture/gateway-and-api.md`]
- The time limit still applies. If the demo has eaten 30 seconds, stop and take questions.

## 6. The honest-limits statement
The presenter must say this in the proof part, in these words or close to them:

```text
A few things are not real, so you know what you are looking at.
The statement lines come from public filings, not from the companies' internal books.
Account-level detail is not public, so we do not claim it.
The agent text comes from the backend the model card names: live Claude through Droid, or our scripted fallback if that fails. The gateway, the math, and the audit log are real.
The two companies have different fiscal years, April and September, so the combined income statement adds two different years and does not match the filed pro forma.
Two inputs are our estimates: the Statesville rent we deduct, and transaction costs, which we set to zero.
And the filing says its own reclassification table, Note 2, is preliminary.
```

Checklist. All seven must appear:
1. Statement lines from public filings.
2. Account-level detail is not claimed.
3. Which backend wrote the agent text: the model card says it.
4. Fiscal-year mismatch: Kewaunee April 30, Nu Aire September 30.
5. The combined table is historical plus target, not the filed pro forma; no purchase accounting.
6. The rent deduction and zero transaction costs are inferred.
7. Note 2 is preliminary.

Also say, if time allows: other situations are roadmap, not built. The output is a combined set of books and a limit check that a human approves. It is not advice. Agent memory is policies the gateway wrote from the controller's answers, not model weights.

## 7. Rehearsal checklist

Before the first rehearsal:
- [ ] Both input CSVs and the brief are final. Cached filings are in `data/` and stay out of git.
- [ ] Both leverage figures match the tool runs on screen (0.76x covenant, 2.84x as filed). No PLACEHOLDER shows anywhere.
- [x] The effect text is formatted from the unrounded ratio, so the card and the verdict line agree (2.84x, 1.56x). Fixed 2026-10-24, `test_flag_effect_text_matches_the_verdict_rounding`.
- [ ] The flag card effect text matches the computed numbers.
- [ ] The tests with the real figures pass, including the tie-out test and the naive-versus-covenant test.
- [x] The recorded run exists, replays, and raises the covenant flag. `test_demo_reset.py`, 2026-10-24.
- [ ] `scripts/droid_probe.py` has run, so we know if `droid` can run Claude, and a Droid run is recorded.
- [ ] Keys are in `.env` only. None are in docs, slides, or screenshots.

Each rehearsal:
- [ ] Time the 2:00 with a stopwatch. Target 1:55.
- [ ] Run the demo from a cold start (fresh `POST /dev/reset?keep_memory=false`, fresh browser tab).
- [ ] Run once with `droid`, once with `replay`, once with `scripted`. Check the model card each time.
- [ ] Force one failure on purpose and switch backends live.
- [ ] Say the honest-limits statement every time.
- [ ] Check the screen at projector size and at the table-side laptop size. Text must be readable from two meters.
- [ ] Notifications off, battery full, charger at the table, wired network or a hotspot ready.
- [ ] Both outcomes (OK and Over the limit) work, even if only one is shown.
- [ ] The audit log link opens, and `chain_valid` shows true.
- [ ] Each teammate answers three questions from section 8 without notes.

Schedule (from `TASKS.md`):
- Saturday night: recorded run, full rehearsals, freeze features.
- Sunday morning: fix only blockers. Devpost due by 9am with a table number. Practice the 2 minutes once more before judging at 10:30am.

## 8. Judge Q&A prep

Hyphenate's four questions: is it real enough, would you hire it, did we see something new, was there a moment. The workshop calls "would you hire it" make-or-break. [verified: `hyphenate-workshop.md`]
Answers are short and honest. If we do not know, say so.

| # | Question | Short honest answer |
| --- | --- | --- |
| 1 | Is it real enough? (Hyphenate Q1) | The deal, the filings, and the lender's covenant are real and public. The statement lines are real. Account-level detail is not public, so we do not claim it. |
| 2 | Would you hire it? (Q2) | It does the repeatable mapping and combining, asks a human only when unsure, and keeps what the controller decides so it asks once. It cannot approve its own work, the gateway refuses a number no tool produced, and every step is logged. We have not tested it with a real controller. [inferred] |
| 3 | What did we see that is new? (Q3) | The flagged line that changes the covenant verdict, and a gateway that enforces maker-checker and logs denied actions. The check against the lender's own definitions is the new part. |
| 4 | Was there a moment? (Q4) | One line, Financing liability, holds three debts: the sale-leaseback, the new bank debt, and the seller notes. The model stops and asks. Read as filed it is 2.84x, over; read the agreement and it is 0.76x. [verified: tool runs] |
| 5 | How is this different from VistaAI? | VistaAI, HackMIT 2026 first place (self-reported), ingests messy CSV and XLSX and proposes field mappings with provenance. We work on accounting lines, check the result against a lender's limit, and post through a gateway with maker-checker and an audit log. [verified: `STOCHASTIC.md`, section 16] |
| 6a | How is this different from Hebbia, Chronograph, Datarails, or Numeric? | Those tools either read the credit agreement or combine the books. Stochastic does both in one gated workflow: every number carries a tool run id, the agent stops when a line's covenant treatment is ambiguous, and the controller's answer becomes a policy. [inferred] |
| 6 | Why not Excel plus a consolidation tool? | Consolidation tools add books after the mapping is done. The mapping is the slow, error-prone part, and it needs a human for the unclear lines. We also test the covenant with its own definitions and log who decided what. Excel has no maker-checker. [inferred] |
| 7 | What does the model do and what does code do? | The model proposes mappings with a confidence and a reason, decides which lines it must not decide alone, and writes the flag question and the readings. Code does all the math and computes the effect of each reading. The gateway refuses a number no tool run produced. [verified: `STOCHASTIC.md`, section 11; `test_model_made_number_is_refused_even_with_real_run_ids`] |
| 8 | What is simulated? | Nothing on the agent path is hardcoded: on stage the agents run live on Claude through Droid, and the model card says if the scripted fallback ran instead. Account-level detail is not public, so we do not claim it. The gateway, the math, and the audit log are real. |
| 9 | What if the live model fails or says something wrong? | `run_agent` has four backends (droid, anthropic, replay, scripted). A failed run falls back to scripted rules, and the model card says so. A wrong result is refused by the gateway: a model cannot exclude a line itself, cite another run's number, or pass a review without the checks. |
| 10 | What stops the agent from approving its own work? | The gateway. The preparer of an item cannot approve it, and no agent has the approve permission. A forbidden action is denied and logged. |
| 11 | How do you know the mapping is right? | We check it against Note 2 in the filing, as an answer key for shape, not to the dollar. Note 2 is preliminary, and the fiscal years differ. Unsure lines become flags. Precision comes before recall. |
| 12 | What does the audit log hold, and can it be edited? | Every action, allowed or denied, with actor, target, reason, and evidence. Each row stores the hash of the row before it, so a change in the past breaks the chain. On Tiger the audit log is a hypertable that refuses UPDATE and DELETE. [verified: `test_the_audit_log_refuses_update_and_delete`] |
| 13 | Why Kewaunee and Nu Aire? | It is small, it has a real 2.50x leverage covenant and a $5M acquisition basket, a filed reclass table, and one unclear line that needs a human. [verified: `research/real-deal-candidates.md`] |
| 14 | What is the leverage result? | 0.76x under the agreement's definition, 2.84x read as filed with the whole financing liability line counted. Both are tool runs on screen with run ids. Never say a number that is not on screen. |
| 14a | What test period did you use? | We used each company's latest fiscal year; the agreement tests the last twelve months to the closing quarter, which is next. |
| 15 | Does covenant EBITDA match the pro forma EBITDA? | No. Covenant EBITDA is a defined term with capped add-backs, so it is a negotiated number, not the pro forma operating profit. [verified: `research/real-deal-candidates.md`] |
| 16 | Does it work for other deals or other situations? | Not yet. Other deals and situations are roadmap. We built one workflow deep. [verified: `STOCHASTIC.md`, section 2] |
| 16a | What about a different lender or loan agreement? | The lender's terms live in the brief, not the code, and `POST /deals` takes any brief. Today a person writes it once per agreement, and we have tested one. The next agent reads it from the contract: it only points at quotes, code checks every quote and number, and the controller approves the brief. Sponsor-style terms such as step-downs and cash netting are not in the schema yet, so they would become questions. [verified: `architecture/brief-reader.md`] |
| 17 | What would you build next? | Purchase accounting with a provisional label, intercompany eliminations, a second deal to show the policies carrying over, confidence calibration from the answer key, and the trailing-twelve-month test period. Learning from corrections is built as policies; backtesting them is not. |
| 18 | Is this advice? | No. It produces a mapped, combined set of books and a limit check that a human approves. |
| 19 | Who is the user? | A portfolio controller or a PE associate who owns the integration, right after an add-on closes. [inferred: no practitioner has checked this] |
| 20 | How long does it take today without this? | One vendor playbook says about 12 weeks for a full integration (self-reported, Aleph). The compliance certificate is due 45 to 60 days after quarter end in the samples we found. We do not claim a speedup we have not measured. |
| 21 | Where do the Factory and Droid parts fit? | Each agent runs as a Droid session with only our gateway tools allowed, an empty working directory, and a typed result. On stage the Mapper is Claude Sonnet 5.5 and the Preparer and Reviewer are Claude Haiku 5.5, through Droid; the pinned replay is the Sonnet 5.5 run. We say "built with the Droid SDK" only about runs that went through it; the sidebar's model card shows it. [verified: `agents.md`, run log] |
| 22 | Did you use real company data? | We used public SEC filings. We did not use any private or internal data. The demo makes no live SEC calls. |

## 9. Table-side checklist: judging Sunday 10:30am to 12:30pm

The whole team stays at the table. [verified: `STOCHASTIC.md`, section 16]

Before 10:30am:
- [ ] Devpost is submitted with the table number and Hyphenate selected.
- [ ] The laptop runs the app locally. The recorded run is one click away.
- [ ] A second laptop or phone holds the video and screenshots.
- [ ] `.env` is loaded. No keys are visible on screen.
- [ ] The honest-limits list is on a card or a slide, in case a judge asks.
- [ ] Charger, hotspot, and a printed one-page summary are at the table.
- [ ] Browser tabs: the console at `localhost:3000/case`, the Log page (`localhost:3000/log`), the filing links (Ex 99.1, 99.2, 10.1). Close everything else.

Roles at the table:
- [ ] Presenter: gives the 2:00 and takes the first question.
- [ ] Driver: runs the demo and the backend switch.
- [ ] Data person (Eric): answers questions about the filings, Note 2, and the brief.
- [ ] Math person (Tri): answers questions about EBITDA, leverage, and tests.
- [ ] Agent and gateway person (Cayden): answers questions about `run_agent`, maker-checker, and the log.
- [ ] Design person (Josie): answers questions about the screen and the flag card.
- [ ] Each judge gets a name written down, with their questions and any follow-up they ask for.

During judging:
- [ ] Reset the demo state before every new judge with memory cleared ("Fresh deal (clear memory)" on the Case page, or `POST /dev/reset?keep_memory=false`), and check that the screen is clean.
- [ ] Open with the problem, not the demo. The demo is the last 30 seconds.
- [ ] Say the honest-limits statement every time, before a judge asks.
- [ ] Offer the audit log if a judge asks "can it be tampered with". Show `chain_valid`.
- [ ] Offer the denied-action row only if asked. Do not stage it.
- [ ] Do not claim sponsor prizes or tracks we have not confirmed. [verified: `STOCHASTIC.md`, section 15]
- [ ] If a judge asks for a number we do not have, say "not computed yet". Do not guess.
- [ ] Keep at least one person at the table at all times, and rotate breaks.
- [ ] Sponsor judges (Factory and others) may visit. Tailor one sentence for each, and stay honest about what ran on which backend.

After judging:
- [ ] Write down every judge's feedback while it is fresh.
- [ ] Update `ideation/tracks.md` in the CalHacks repo if a track status changed.

## 10. Backend switch cheat sheet

```text
AGENT_BACKEND=droid      the Factory run; say "built with the Droid SDK" only for this
AGENT_BACKEND=anthropic  Claude with tool use; needs ANTHROPIC_API_KEY, which the demo laptop does not have
AGENT_BACKEND=replay     recorded outputs from backend/recordings/ (the Sonnet 5.5 run), tools re-run
AGENT_BACKEND=scripted   deterministic rules, no model, no network
```

Set it in `.env` and restart uvicorn, or pass `{"backend": "droid"}` in the body of `POST /deals/{id}/run`.
`GET /health` shows the configured backend, the fallback chain, which keys are present, and the last runs.
