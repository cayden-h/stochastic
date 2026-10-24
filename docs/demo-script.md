# Demo script: the 2:00 pitch

Last updated: 2026-10-24, 05:00. The figures below are computed by the tools on the fixture and tested. The failure switch was rehearsed (section 5).
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
| 1:30 - 2:00 | Live demo | One flag, one approval, one verdict line. | The one console screen. |

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
Count the whole line and leverage is 2.54x, over the limit. Read the agreement and it is 0.76x.
That is the difference between a blocked next deal and forty-eight million dollars of room.
The agents are roles on a real team. They never do math. Code does it, and every number carries a run id.
The gateway is the only thing that writes. An agent cannot approve its own work, and a number no tool produced is refused.
Here is what is not real. [the honest-limits statement, section 6]
```

Part 4, the live demo (1:30 - 2:00): section 2, beat by beat.
If a judge gives a second minute, the memory moment: reset, run again, no flag, and the `policy:apply` row in the log.

## 2. The 30-second live demo, beat by beat

Rules:
- The console shows one screen: the flag card, a small combined table of about ten rows, and one verdict line. The audit log is a small link. [verified: `STOCHASTIC.md`, section 12]
- The presenter does not read numbers aloud unless they are final. See section 4.
- Do not stage a denied action. Show a DENIED row only if a judge asks to see the log. [verified: `STOCHASTIC.md`, section 9]

Measured on live Droid on 2026-10-24 08:30 (Mapper Sonnet 5.5, Preparer and Reviewer Haiku 5.5, `STORE=postgres`) [verified: `agents.md` section 9]:
- Run to the flag card: 47 to 49 s. Too long for beat 2, so run the deal to the flag before each judge arrives (reset with memory cleared, press Run, wait for the card).
- Last answer to a live Approve button: 36 to 38 s (Preparer about 28 s, Reviewer about 9 s). Answer the flag early and talk over this wait: the gateway, the tools, the run ids.
- Second run after a reset with memory kept: 58 s to approval, no flag. Show it at the table only if a judge has the time, or point to the Learned chips.
- If the timing does not fit, use `AGENT_BACKEND=replay` for the pitch and say so: the recorded Droid run's text, with every tool run live.

The beats below are the original plan; Cayden times the real version with a stopwatch (`tasks/cayden.md` task 5).

| Beat | Time | On-screen state | Presenter says | Hardcoded or real |
| --- | --- | --- | --- | --- |
| 1. Start | 1:30 - 1:35 | Console is open on the deal. Two files and the brief are loaded. The table is empty. The verdict line says "Waiting". | "Two statement files and a short brief with the lender's limit." | The files and brief are real data from filings. The load is real. |
| 2. Run | 1:35 - 1:42 | Press Run. A progress line shows the Mapper working. The combined table fills with mapped lines and a confidence per line. | "The Mapper matches each Nu Aire line to a Kewaunee line." | The mapping call goes through `run_agent`. The text may be hardcoded or recorded. The confidences come from the typed output. |
| 3. Flag | 1:42 - 1:50 | The flag card appears for "Financing liability". It shows the question, the filing evidence, two options, and the effect of each on leverage. The verdict line says "Waiting on a flag". | "It stopped on one line. Financing liability holds a sale-leaseback and the new deal debt. Which part is covenant debt?" | Card text is hardcoded. The flag work item and its state NEEDS_INFO are real gateway state. |
| 4. Answer | 1:50 - 1:55 | The controller clicks Approve on one option, or Change. | "The controller decides. Not the model." | The answer call is real. The gateway logs it. |
| 5. Combine and test | 1:55 - 2:00 | The combined table shows platform, target, and combined. The verdict line shows combined leverage next to 2.50x with OK or Over the limit. A small badge shows Reviewer: pass. | "Code adds the books and tests the lender's limit. That is the verdict." | The Preparer's tool calls, the math, the tie-out, and the limit test run for real. The agent text is hardcoded or recorded. |
| 6. Close | after 2:00 if asked | The presenter clicks the audit log link. | "Every step is here, and each row is chained to the one before." | Real. The chain check is real. |

What runs for real: the gateway (state changes, maker-checker, permissions), the math tools (consolidation, EBITDA, leverage, limit test), the tie-out check, and the audit log with its hash chain. [verified: `STOCHASTIC.md`, section 2]
What is hardcoded or recorded: the agent message text, and the flag card wording. [verified: `STOCHASTIC.md`, section 2]
What is a fallback: a recorded run, played when both backends fail. See section 5.

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
| Covenant leverage | 0.76x, 1.74x of room, about $49M of debt capacity | tool runs `leverage`, `limit_test` |
| Naive leverage | 2.54x, over the limit | tool runs |
| Combined total assets | $182,456K, and the combined balance sheet balances | tool runs `consolidate`, `tie_out` |
| Example reclasses (Note 2) | Accrued Commissions to Employee compensation and amounts withheld. Income taxes payable to Other accrued expenses. Interest Income - Net to Other income, net | Ex 99.2 |

Two inputs are inferred and are said in the honest-limits statement: the rent deduction, and transaction and integration costs applied as zero because the filings do not quantify them.
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
- Three options, each with its computed effect and a run id.
- The default, option b, the agreement's reading.

| Option | Effect on the card | Verdict |
| --- | --- | --- |
| a. Whole line counts (70,885K) | Senior Funded Bank Debt 71,955K. Leverage 2.54x against 2.50x. | Over the limit |
| b. Only the PNC term loan and revolver count | Senior Funded Bank Debt 21,633K. Leverage 0.76x against 2.50x. | OK |
| c. PNC debt and the seller notes count | Senior Funded Bank Debt 44,173K. Leverage 1.56x against 2.50x. | OK |

A second, smaller flag asks where Nu Aire's Certificates of Deposit ($991K) belong. Answer it with the default (cash equivalents) in one click, or raise the Mapper threshold to drop it.

### Two outcomes

| Answer | Verdict line | Presenter says | Reviewer badge |
| --- | --- | --- | --- |
| b (the agreement's reading) | OK. 0.76x against 2.50x. Room 1.74x. | "Under the limit, with the covenant's own definition of debt. Room for the next deal." | pass |
| a (whole line) | Over the limit. 2.54x against 2.50x. | "Over the limit. The item comes back as needs-attention and cannot be approved." | needs_attention |

Notes:
- Over the limit returns the item to the human as needs-attention, and the gateway refuses approval. [verified: `test_result_cannot_be_approved_before_review_passes`]
- Click b in the demo. Show a on the card as the effect text, and say the naive number out loud. That is the moment: one line, two readings, 1.8x apart.
- The memory moment, if time allows: reset, run again, no flag. "It asked once. The controller's answer is now a policy, written by the gateway, and the log shows it applied."

### The honest sensitivity

The naive reading stays over 2.50x as long as covenant EBITDA stays below $28,782K. Our figure is $28,379K, with every add-back the agreement names and the filings quantify. An add-back above $403K that we have not found, or $403K less cash rent than we inferred, would move the naive reading under the limit; the covenant reading would still be far under. The $698K of expected transaction costs in Ex 99.2 Note 5(b) is the known candidate, kept at zero because it falls after the period. Know this before a judge asks.

## 5. Failure plan
The agent layer has one function, `run_agent(role, item)`, with four backends. `AGENT_BACKEND` picks one and `AGENT_FALLBACK` (default `scripted`; no Anthropic key exists) lists the fallbacks. [verified: `backend/app/agents/runner.py`]
The gateway, math tools, and log are plain code and do not depend on any backend.

Rehearsed on 2026-10-24, 04:50 [verified]: the API was started with the `droid` CLI missing from PATH. `POST /deals/{id}/run` returned `mapper ran on scripted`, and `GET /health` showed the attempts: droid failed ("Droid executable was not found"), anthropic failed ("ANTHROPIC_API_KEY is not set"), scripted ran. The screen kept working and the backend badge said scripted.
Also found: Droid accepts an unknown model id without an error, so a wrong `DROID_MODEL` is not a failure, it is a silent default. Keep `DROID_MODEL=claude-haiku-5-5` in `.env` and say "Claude Haiku 5.5 through Droid" only when the probe has listed that model.

| Failure | Sign | What the system does | What to say |
| --- | --- | --- | --- |
| Droid fails | The run takes more than the timeout, or `GET /health` shows a failed droid attempt | Falls to `scripted`. Same screen, same gateway. The badge says scripted. | "The Droid run dropped. This one ran on the fallback. Same roles, same gateway, same math." |
| You want no live model call at all | Before the demo | Set `AGENT_BACKEND=replay`: recorded outputs from the Sonnet 5.5 Droid run (`backend/recordings/`), with the tools re-run | "This is the recorded run from this morning. The tool calls are live." |
| Console fails | Blank page or API error | Reload once. Then show the API: `GET /deals/{id}/case` in a browser tab is readable. | "Let me show the raw case." |
| Wi-Fi fails | No network | `scripted` or `replay` need none. The demo makes no live SEC calls. The store keeps working in memory and queues its writes to Tiger until the network is back (`GET /health` `store.pending`). | None needed. |
| Tiger Cloud unreachable at start | The badge says "In memory" and "Tiger unreachable" | The API runs in memory; nothing is lost from the screen | "The database is down, so this run is in memory. The log and the chain are the same." |
| A Run click while a run is going | 409 "a run is already in progress" | Nothing; the running job finishes | None needed. |
| The Tiger fork fails or is slow | The flag card says "no fork (...)" or still "Forking ..." | The options and effects are computed in process as always; answer when ready | "The fork is still coming up; the figures are already computed." |

### The restart moment (Tiger), rehearsed 2026-10-24 08:09 [verified]

1. Run the deal, answer the flags, and approve, with `STORE=postgres` (the badge says Tiger Cloud).
2. Stop the API and start it again (`Ctrl-C`, then `backend/.venv/bin/uvicorn app.main:app --port 8000`; with `--reload`, saving any backend file restarts it).
3. Reload the console. The verdict, the combined table, the answered flags, the log (55 rows, chain intact, the one real DENIED row), the 11 policies, and the three Droid sessions are all back, loaded from Tiger.
4. Words: "The process just restarted. Nothing was in its memory. Everything on screen came back from Postgres on Tiger Cloud, and the log still checks."

Checked on 2026-10-24 08:09: every top-level field of `GET /deals/{id}/case` was identical before and after the restart, and the restarted process had no runs of its own.

Rules for failure:
- Never hide a failure. Say it in one short line and move on. The backend badge on screen already says what ran.
- Say "built with the Factory Droid SDK" only about runs that went through the `droid` backend. [verified: `architecture/gateway-and-api.md`]
- The time limit still applies. If the demo has eaten 30 seconds, stop and take questions.

## 6. The honest-limits statement
The presenter must say this in the proof part, in these words or close to them:

```text
A few things are not real, so you know what you are looking at.
The statement lines come from public filings, not from the companies' internal books.
Account-level detail is not public, so we do not claim it.
The agent text you see is recorded or scripted, and the screen says which backend ran. The gateway, the math, and the audit log are real.
The two companies have different fiscal years, April and September, so the combined income statement adds two different years and does not match the filed pro forma.
Two inputs are our estimates: the Statesville rent we deduct, and transaction costs, which we set to zero.
And the filing says its own reclassification table, Note 2, is preliminary.
```

Checklist. All seven must appear:
1. Statement lines from public filings.
2. Account-level detail is not claimed.
3. Agent text is recorded or scripted, and which backend ran.
4. Fiscal-year mismatch: Kewaunee April 30, Nu Aire September 30.
5. The combined table is historical plus target, not the filed pro forma; no purchase accounting.
6. The rent deduction and zero transaction costs are inferred.
7. Note 2 is preliminary.

Also say, if time allows: other situations are roadmap, not built. The output is a combined set of books and a limit check that a human approves. It is not advice. Agent memory is policies the gateway wrote from the controller's answers, not model weights.

## 7. Rehearsal checklist

Before the first rehearsal:
- [ ] Both input CSVs and the brief are final. Cached filings are in `data/` and stay out of git.
- [ ] Both leverage figures match the tool runs on screen (0.76x covenant, 2.54x naive). No PLACEHOLDER shows anywhere.
- [x] The effect text is formatted from the unrounded ratio, so the card and the verdict line agree (2.54x, 1.56x). Fixed 2026-10-24, `test_flag_effect_text_matches_the_verdict_rounding`.
- [ ] The flag card effect text matches the computed numbers.
- [ ] The tests with the real figures pass, including the tie-out test and the naive-versus-covenant test.
- [ ] The recorded run exists and replays.
- [ ] `scripts/droid_probe.py` has run, so we know if `droid` can run Claude, and a Droid run is recorded.
- [ ] Keys are in `.env` only. None are in docs, slides, or screenshots.

Each rehearsal:
- [ ] Time the 2:00 with a stopwatch. Target 1:55.
- [ ] Run the demo from a cold start (fresh `POST /dev/reset`, fresh browser tab).
- [ ] Run once with `anthropic`, once with `droid`, once with `replay`, once with `scripted`. Check the backend badge each time.
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
| 4 | Was there a moment? (Q4) | One line, Financing liability, holds two kinds of debt. The model stops and asks. The controller's answer moves the leverage result. [inferred: depends on the computed figures] |
| 5 | How is this different from VistaAI? | VistaAI, HackMIT 2026 first place (self-reported), ingests messy CSV and XLSX and proposes field mappings with provenance. We work on accounting lines, check the result against a lender's limit, and post through a gateway with maker-checker and an audit log. [verified: `STOCHASTIC.md`, section 16] |
| 6 | Why not Excel plus a consolidation tool? | Consolidation tools add books after the mapping is done. The mapping is the slow, error-prone part, and it needs a human for the unclear lines. We also test the covenant with its own definitions and log who decided what. Excel has no maker-checker. [inferred] |
| 7 | What does the model do and what does code do? | The model proposes mappings with a confidence and a reason, decides which lines it must not decide alone, and writes the flag question and the readings. Code does all the math and computes the effect of each reading. The gateway refuses a number no tool run produced. [verified: `STOCHASTIC.md`, section 11; `test_model_made_number_is_refused_even_with_real_run_ids`] |
| 8 | What is simulated? | Agent text is hardcoded or recorded. Account-level detail is synthetic or not claimed. The gateway, the math, and the audit log are real. |
| 9 | Why is the agent text hardcoded? | The real path is the `run_agent` function with two backends, so a live call can fail on stage. Hardcoded or recorded text keeps the demo steady. The tool calls behind it are real. |
| 10 | What stops the agent from approving its own work? | The gateway. The preparer of an item cannot approve it, and no agent has the approve permission. A forbidden action is denied and logged. |
| 11 | How do you know the mapping is right? | We check it against Note 2 in the filing, as an answer key for shape, not to the dollar. Note 2 is preliminary, and the fiscal years differ. Unsure lines become flags. Precision comes before recall. |
| 12 | What does the audit log hold, and can it be edited? | Every action, allowed or denied, with actor, target, reason, and evidence. Each row stores the hash of the row before it, so a change in the past breaks the chain. Postgres would use a role with no update or delete rights. |
| 13 | Why Kewaunee and Nu Aire? | It is small, it has a real 2.50x leverage covenant and a $5M acquisition basket, a filed reclass table, and one unclear line that needs a human. [verified: `research/real-deal-candidates.md`] |
| 14 | What is the leverage result? | 0.76x under the agreement's definition, 2.54x if you count the whole financing liability line. Both are tool runs on screen with run ids. Never say a number that is not on screen. |
| 15 | Does covenant EBITDA match the pro forma EBITDA? | No. Covenant EBITDA is a defined term with capped add-backs, so it is a negotiated number, not the pro forma operating profit. [verified: `research/real-deal-candidates.md`] |
| 16 | Does it work for other deals or other situations? | Not yet. Other deals and situations are roadmap. We built one workflow deep. [verified: `STOCHASTIC.md`, section 2] |
| 17 | What would you build next? | Purchase accounting with a provisional label, intercompany eliminations, a second deal to show the policies carrying over, confidence calibration from the answer key, and a Postgres store. Learning from corrections is built as policies; backtesting them is not. |
| 18 | Is this advice? | No. It produces a mapped, combined set of books and a limit check that a human approves. |
| 19 | Who is the user? | A portfolio controller or a PE associate who owns the integration, right after an add-on closes. [inferred: no practitioner has checked this] |
| 20 | How long does it take today without this? | One vendor playbook says about 12 weeks for a full integration (self-reported, Aleph). The compliance certificate is due 45 to 60 days after quarter end in the samples we found. We do not claim a speedup we have not measured. |
| 21 | Where do the Factory and Droid parts fit? | Each agent runs as a Droid session with only our gateway tools allowed, an empty working directory, and a typed result. The recorded run is Claude Haiku 5.5 through Droid. We say "built with the Droid SDK" only about runs that went through it; the backend badge shows it. [verified: `agents.md`, run log] |
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
- [ ] Browser tabs: the console, the audit log, the filing links (Ex 99.1, 99.2, 10.1). Close everything else.

Roles at the table:
- [ ] Presenter: gives the 2:00 and takes the first question.
- [ ] Driver: runs the demo and the backend switch.
- [ ] Data person (Eric): answers questions about the filings, Note 2, and the brief.
- [ ] Math person (Tri): answers questions about EBITDA, leverage, and tests.
- [ ] Agent and gateway person (Cayden): answers questions about `run_agent`, maker-checker, and the log.
- [ ] Design person (Josie): answers questions about the screen and the flag card.
- [ ] Each judge gets a name written down, with their questions and any follow-up they ask for.

During judging:
- [ ] Reset the demo state before every new judge (`POST /dev/reset`), and check that the screen is clean.
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
AGENT_BACKEND=anthropic  Claude with tool use; the stage fallback
AGENT_BACKEND=replay     recorded outputs from backend/recordings/ (the Sonnet 5.5 run), tools re-run
AGENT_BACKEND=scripted   deterministic rules, no model, no network
```

Set it in `.env` and restart uvicorn, or pass `{"backend": "droid"}` in the body of `POST /deals/{id}/run`.
`GET /health` shows the configured backend, the fallback chain, which keys are present, and the last runs.
