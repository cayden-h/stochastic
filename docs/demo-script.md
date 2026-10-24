# Demo script: the 2:00 pitch

Last updated: 2026-10-23.
The product and scope are in `STOCHASTIC.md`. This file only says what we show and say.
Claims are tagged [verified] when a source file shows them and [inferred] when they are our judgment.
Figures come only from `research/real-deal-candidates.md`. Anything else is marked PLACEHOLDER.

## 1. The 2:00 plan

The budget is 1:30 for the pitch and 0:30 for the live demo. [verified: `STOCHASTIC.md`, section 2]
Order: the problem, then what Stochastic does, then the proof. Do not lead with the demo or the deal name.

| Time | Part | Goal | On screen |
| --- | --- | --- | --- |
| 0:00 - 0:25 | Problem | The judge feels the gate: the next deal waits on the books. | Title slide or the empty console. No demo yet. |
| 0:25 - 0:55 | What Stochastic does | Five steps in plain words: map, flag, combine, test, approve. | A simple flow slide, or the console at rest. |
| 0:55 - 1:30 | Proof and honesty | A real public deal. Small stateless agents. Math is code. Say what is simulated. | The real-versus-simulated list. |
| 1:30 - 2:00 | Live demo | One flag, one approval, one verdict line. | The one console screen. |

Who speaks: one presenter talks. A second person drives the keyboard. The rest of the team stands back. [inferred]

### Words for each part

Part 1, the problem (0:00 - 0:25). Say it casual, in your own words. This is the shape:

```text
A PE firm that keeps buying small companies has a gate on every deal.
The lender sets limits, like a max debt-to-EBITDA, and they test them on the combined company.
So the next deal waits until someone combines the two sets of books.
Today that is a spreadsheet and weeks of work.
And one wrong mapping flows into every number after it.
```

Part 2, what it does (0:25 - 0:55):

```text
Stochastic does the repeatable part.
It maps the new company's lines to the platform's lines, and says how sure it is.
It only asks a human about the lines it is not sure about.
Then code combines the books and checks the result against the lender's limit.
A controller approves, and every step goes in an audit log.
```

Part 3, proof and honesty (0:55 - 1:30):

```text
We ran it on a real public deal, Kewaunee Scientific buying Nu Aire, closed November 2024.
The agents are small and stateless, like roles on a real team.
They never do math. Code does all of it.
The gateway is the only thing that writes, and it logs every action.
Here is what is simulated. [say the honest-limits statement from section 6]
```

## 2. The 30-second live demo, beat by beat

Rules:
- The console shows one screen: the flag card, a small combined table of about ten rows, and one verdict line. The audit log is a small link. [verified: `STOCHASTIC.md`, section 12]
- The presenter does not read numbers aloud unless they are final. See section 4.
- Do not stage a denied action. Show a DENIED row only if a judge asks to see the log. [verified: `STOCHASTIC.md`, section 9]

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

Use only these figures. All are from filings. [verified: `research/real-deal-candidates.md`]

| Item | Figure | Source |
| --- | --- | --- |
| Deal | Kewaunee Scientific buys Nu Aire | Ex 99.2 |
| Close date | 2024-11-01 | 8-K |
| Price | $55M, subject to adjustments | Ex 99.2 |
| Funding | $15M PNC term loan, a $20M PNC revolver, $23M of 8% subordinated seller notes | Ex 99.2 |
| Leverage covenant | Senior Funded Bank Debt to EBITDA below 2.50 to 1.00, Section 4.8(a) | Ex 10.1 |
| Fixed charge covenant | At least 1.20 to 1, Section 4.8(b) | Ex 10.1 |
| Acquisition basket | $5,000,000, Section 5.8(ii) | Ex 10.1 |
| Kewaunee fiscal 2024 net sales | $203,755K | Ex 99.2 |
| Nu Aire reclassed fiscal 2024 net sales (April year) | $80,875K | Ex 99.2 |
| Nu Aire audited net revenues (year to 2024-09-30) | $74,850,302 | Ex 99.1 |
| Nu Aire D&A (year to 2024-09-30) | $1,830,395 | Ex 99.1 |
| Pro forma operating profit, year to 2024-04-30 | $20,817K (Kewaunee $18,281K, Nu Aire $5,652K, transaction adjustments $(3,105)K, financing adjustments $(11)K) | Ex 99.2 |
| Pro forma operating profit, six months to 2024-10-31 | $7,304K | Ex 99.2 |
| Kewaunee pension expense, fiscal 2024 | $(4,177)K | Ex 99.2 |
| Kewaunee financing liability at 2024-10-31 | $750K current plus $27,032K long-term | 10-Q |
| Sale-leaseback carrying value | $27,782,000 | 10-Q |
| Pro forma addition to financing liability | $3,000K current plus $40,103K long-term | Ex 99.2 |
| Pro forma total financing liability | $3,750K current plus $67,135K long-term, so $70,885K | Ex 99.2 |
| Example reclasses (Note 2) | Accrued Commissions to Employee compensation and amounts withheld, $0.9M. Accrued Compensation to Other accrued expenses, $0.2M. Interest Income - Net to Other income, net, $0.3M | Ex 99.2 |

Placeholders. These are not computed yet, and the screen must show the word PLACEHOLDER or a dash until Tri fills them:

| Item | State | Owner |
| --- | --- | --- |
| Kewaunee D&A | PLACEHOLDER. Needs the 10-K cash flow statement. | Tri |
| Revolver draw at close | PLACEHOLDER. Needs the 10-Q or 8-K. | Tri |
| Covenant EBITDA (with add-backs) | PLACEHOLDER | Tri |
| Senior Funded Bank Debt (covenant version) | PLACEHOLDER | Tri |
| Naive leverage (all of financing liability as debt) | PLACEHOLDER | Tri |
| Covenant leverage | PLACEHOLDER | Tri |
| Combined table rows beyond the figures above | PLACEHOLDER | Eric and Tri |

Leverage ratios are not computed yet. [verified: `STOCHASTIC.md`, section 12]
Do not show or say any ratio until Tri writes both versions down with sources.
The expectation that covenant leverage is well under 2.50x and naive leverage is much closer is [inferred], not computed.

## 4. The flag moment and the two verdicts

### The flag

The flag is Kewaunee's "Financing liability" line. [verified: `STOCHASTIC.md`, section 12]
It holds the Statesville sale-leaseback ($27,782K carrying value) and, after the deal, the acquisition financing. [verified]
The credit agreement's Senior Funded Bank Debt excludes the capital lease on the property at 2700 West Front Street and excludes the seller notes. [verified: Ex 10.1]
So the card asks which part of the line is covenant debt.

The card shows:
- The question, in one sentence.
- The evidence: the line and its filing reference, with any quote under 15 words.
- Two options, each with its effect on leverage.
- A suggested default, if the Mapper has one.

Option wording is an example. [inferred]
- Option A: the whole line counts as debt. Effect: leverage PLACEHOLDER (higher).
- Option B: only the covenant part counts as debt. Effect: leverage PLACEHOLDER (lower).

The effect text on the card must come from real tool runs by the demo date. Do not ship the words "goes up" or "goes down" without a computed number behind them.

### Two outcomes

The verdict line depends on the controller's answer.

| Answer | Verdict line | Presenter says | Reviewer badge |
| --- | --- | --- | --- |
| Treatment that gives leverage below 2.50x | OK. Combined leverage PLACEHOLDER next to 2.50x. | "Under the limit, with the covenant's own definition of debt." | pass |
| Treatment that gives leverage at or above 2.50x | Over the limit. Combined leverage PLACEHOLDER next to 2.50x. | "Over the limit. The item goes back to the controller as needs-attention. It cannot be approved." | needs_attention |

Notes:
- Over the limit returns the item to the human as needs-attention. The Reviewer found a breach. [verified: `STOCHASTIC.md`, section 8]
- A result cannot be approved while its review verdict is needs-attention. This is a new gateway check, so confirm it is built before the demo. [inferred: `architecture/gateway-and-api.md`, check 5]
- If the covenant ratio is under 2.50x with both treatments, the verdict does not change and the moment is weaker. Tri computes it early. Then the team picks the flag wording. [verified: `TASKS.md`, risks]
- Fallback moment if both treatments give OK: say what the naive and covenant numbers are, and show that they differ. That still shows why the covenant definition matters.
- Pick which answer to click before the demo. Do it by what the computed numbers show, not by hope.

## 5. Failure plan

The agent layer has one function, `run_agent(role, item)`, with two backends. `AGENT_BACKEND` switches them. A recorded run is the last fallback. [verified: `architecture/gateway-and-api.md`]
The gateway, math tools, and log are plain code and do not depend on either backend.

| Failure | Sign | Action | What to say |
| --- | --- | --- | --- |
| Droid fails | The subprocess errors or hangs for more than 5 seconds | Set `AGENT_BACKEND=anthropic` and rerun. Keep the same screen. | "The Droid run dropped. This one runs on the Anthropic API. Same roles, same gateway." |
| Anthropic backend fails | API error, timeout, or no network | Switch to `droid` if it is up. | "Switching the backend." |
| Both fail | Both backends error | Play the recorded run. The recorded run feeds the same gateway and tools, or it replays the saved screen. | "Both model backends are down, so this is the recorded run. The data is the same." |
| Recorded run fails | The replay will not start | Open the saved demo video or screenshots of each beat. | "Here is the run from earlier today." |
| Console fails | Blank page or API error | Reload once. Then use the video. | "Let me show the recorded video." |
| Wi-Fi fails | No network | Run locally. The demo makes no live SEC calls, and public data is cached. [verified: `STOCHASTIC.md`, section 10] | None needed. |

Rules for failure:
- Never hide a failure. Say it in one short line and move on.
- Say "built with the Factory Droid SDK" only about runs that went through the `droid` backend. [verified: `architecture/gateway-and-api.md`]
- Rehearse the switch at least once, with a real failure. [verified: `TASKS.md`, Cayden task 6]
- The time limit still applies. If the demo has eaten 30 seconds, stop and take questions.

## 6. The honest-limits statement

The presenter must say this in the proof part, in these words or close to them:

```text
A few things are not real, so you know what you are looking at.
The statement lines come from public filings, not from the companies' internal books.
Account-level detail is not public, so we do not claim it. Any account-level detail is synthetic.
The agent messages you see are hardcoded or recorded.
The gateway, the math, and the audit log are real.
The two companies have different fiscal years, April and September, so we do not match the filed pro forma to the dollar.
And the filing says its own reclassification review, Note 2, is preliminary.
```

Checklist of the five points. All five must appear:
1. Statement lines from public filings. [verified: `STOCHASTIC.md`, section 2]
2. Account-level detail is synthetic or not claimed. [verified]
3. Agent text is hardcoded or recorded. [verified]
4. Fiscal-year mismatch: Kewaunee April 30, Nu Aire September 30. [verified: `research/real-deal-candidates.md`]
5. Note 2 is preliminary. [verified: the filing says Kewaunee is "conducting a more detailed review of reclassifications"]

Also say, if time allows: other situations are roadmap, not built. The output is a combined set of books and a limit check that a human approves. It is not advice. [verified: `STOCHASTIC.md`, section 2]

## 7. Rehearsal checklist

Before the first rehearsal:
- [ ] Both input CSVs and the brief are final. Cached filings are in `data/` and stay out of git.
- [ ] Tri has written both leverage figures with sources. No PLACEHOLDER shows on screen.
- [ ] The flag card effect text matches the computed numbers.
- [ ] The tests with the real figures pass, including the tie-out test and the naive-versus-covenant test.
- [ ] The recorded run exists and replays.
- [ ] `list_models()` answer is known, so we know if `droid` can run Claude.
- [ ] Keys are in `.env` only. None are in docs, slides, or screenshots.

Each rehearsal:
- [ ] Time the 2:00 with a stopwatch. Target 1:55.
- [ ] Run the demo from a cold start (fresh `POST /dev/reset`, fresh browser tab).
- [ ] Run once with `anthropic`, once with `droid`, once from the recording.
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
| 2 | Would you hire it? (Q2) | It does the repeatable mapping and combining, and it asks a human only when unsure. It cannot approve its own work, and every step is logged. We have not tested it with a real controller. [inferred] |
| 3 | What did we see that is new? (Q3) | The flagged line that changes the covenant verdict, and a gateway that enforces maker-checker and logs denied actions. The check against the lender's own definitions is the new part. |
| 4 | Was there a moment? (Q4) | One line, Financing liability, holds two kinds of debt. The model stops and asks. The controller's answer moves the leverage result. [inferred: depends on the computed figures] |
| 5 | How is this different from VistaAI? | VistaAI, HackMIT 2026 first place (self-reported), ingests messy CSV and XLSX and proposes field mappings with provenance. We work on accounting lines, check the result against a lender's limit, and post through a gateway with maker-checker and an audit log. [verified: `STOCHASTIC.md`, section 16] |
| 6 | Why not Excel plus a consolidation tool? | Consolidation tools add books after the mapping is done. The mapping is the slow, error-prone part, and it needs a human for the unclear lines. We also test the covenant with its own definitions and log who decided what. Excel has no maker-checker. [inferred] |
| 7 | What does the model do and what does code do? | The model proposes mappings, with a confidence and a reason, and writes the explanations. Code does all the math: consolidation, EBITDA, leverage, and the limit test. The model never produces a number. [verified: `STOCHASTIC.md`, section 11] |
| 8 | What is simulated? | Agent text is hardcoded or recorded. Account-level detail is synthetic or not claimed. The gateway, the math, and the audit log are real. |
| 9 | Why is the agent text hardcoded? | The real path is the `run_agent` function with two backends, so a live call can fail on stage. Hardcoded or recorded text keeps the demo steady. The tool calls behind it are real. |
| 10 | What stops the agent from approving its own work? | The gateway. The preparer of an item cannot approve it, and no agent has the approve permission. A forbidden action is denied and logged. |
| 11 | How do you know the mapping is right? | We check it against Note 2 in the filing, as an answer key for shape, not to the dollar. Note 2 is preliminary, and the fiscal years differ. Unsure lines become flags. Precision comes before recall. |
| 12 | What does the audit log hold, and can it be edited? | Every action, allowed or denied, with actor, target, reason, and evidence. Each row stores the hash of the row before it, so a change in the past breaks the chain. Postgres would use a role with no update or delete rights. |
| 13 | Why Kewaunee and Nu Aire? | It is small, it has a real 2.50x leverage covenant and a $5M acquisition basket, a filed reclass table, and one unclear line that needs a human. [verified: `research/real-deal-candidates.md`] |
| 14 | What is the leverage result? | Only answer with computed numbers. If Tri's figures are not final, say: "We computed both versions, and they differ. Here is the one on screen." Never invent a ratio. |
| 15 | Does covenant EBITDA match the pro forma EBITDA? | No. Covenant EBITDA is a defined term with capped add-backs, so it is a negotiated number, not the pro forma operating profit. [verified: `research/real-deal-candidates.md`] |
| 16 | Does it work for other deals or other situations? | Not yet. Other deals and situations are roadmap. We built one workflow deep. [verified: `STOCHASTIC.md`, section 2] |
| 17 | What would you build next? | A second flag, such as the seller notes, learning policies from the controller's corrections, and a real Postgres store. Learning from corrections is not built. [verified: `hyphenate-workshop.md` lists it as a gap] |
| 18 | Is this advice? | No. It produces a mapped, combined set of books and a limit check that a human approves. |
| 19 | Who is the user? | A portfolio controller or a PE associate who owns the integration, right after an add-on closes. [inferred: no practitioner has checked this] |
| 20 | How long does it take today without this? | One vendor playbook says about 12 weeks for a full integration (self-reported, Aleph). The compliance certificate is due 45 to 60 days after quarter end in the samples we found. We do not claim a speedup we have not measured. |
| 21 | Where do the Factory and Droid parts fit? | `run_agent` has a `droid` backend. We say "built with the Factory Droid SDK" only about runs that went through it. Whether Droid can run Claude on our key is still open. [verified: `STOCHASTIC.md`, section 18] |
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
