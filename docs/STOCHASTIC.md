# Stochastic: reference for Claude

Last updated: 2026-10-23.
Read this file first in any session about Stochastic.
It holds the main features, the architecture, and the scope.
If this file and a PDF or an older note disagree, this file is correct.
Claims are tagged [verified] when a source file or a post shows them, and [inferred] when they are our judgment.

## 1. What Stochastic is

Stochastic is one platform for any special situation in corporate finance.
A special situation is a one-off, high-stakes move outside the normal course of business.
Examples are raising money, refinancing, selling part of a company, and a company in trouble.
A team of AI agents works out what the company is allowed to do, finds what blocks it, builds and tests options, and asks a human reviewer to approve.
A situation profile tells the same agents what to look for, what to weigh, and when to ask.
The platform is built to serve all eight situations in section 5.
The weekend demo runs one situation: raising money.

## 2. The pitch rules

- Pitch Stochastic as an all-in-one platform. Do not pitch it as a tool for one deal.
- Lead with the problem that Stochastic solves. Do not lead with an example or with the demo. [set by Cayden, 2026-10-23]
- Pitch order: the problem, then what Stochastic does about it, then the proof.
- Show one real public deal only as proof of the platform.
- On slides and in the video, say "one real deal". Do not lead with the name of the deal.
- Do not claim that all eight situations are built or tested. The demo covers one. [inferred rule, set by Cayden's framing on 2026-10-23]
- Say that the demo is a reconstruction from public filings. It does not show the internal views of any lender.
- Hyphenate rewards a few roles done deep. Breadth can look like ten shallow workflows, so the proof must be depth on one real deal. [inferred]

## 3. The problem, the user, and the seat

Special situations are hard for three reasons.
The rules are buried in long agreements.
The options are many, and the terms keep changing.
A mistake is costly.

Today a small team of specialists reads the agreements, finds the limits, designs the options, tests the risk, and asks a senior person to approve.
When a term changes, the team redoes the work.
This work is slow and manual.
Stochastic solves this: it finds what is allowed and what blocks the plan, builds and tests the options, shows the evidence, and asks a human before it commits.

A common example is a company that wants more money than its existing bank loan allows.
That example is the demo case. It is not the definition of the problem.

The user is a senior reviewer who has done this work before. [verified: Cayden, 2026-10-23]
A CFO or treasury lead can also fill the seat.
The agents act as the analyst team, and the human is the approver.
This matches the split in the Hyphenate workshop between the proposer and the approver.

The seat is one deal in motion, from the first document to the human approval.
Events can arrive during the deal. Examples are a rate move, a lender change, a late document, and a reviewer rejection.
There is no after-close monitoring and no quarterly company model. [verified: decision on 2026-10-23]

## 4. Main features

1. **Document intake.** The intake agent turns documents into facts. Each fact keeps its page and exact quote.
2. **Clause reading.** The clause reader finds baskets, covenants, and defined terms. A code check makes sure that each quote is in the document.
3. **Option search.** The structuring agent builds financing mixes inside the limits. Code enumerates the mixes and keeps the best trade-offs.
4. **Risk testing.** A seeded Monte Carlo run tests each shortlisted plan. Every result carries a run id.
5. **Blocked-plan handling.** When a clause blocks a plan, the gateway logs a DENIED action that cites the clause. The agents then redesign the plan and price the consent or waiver route.
6. **Early escalation.** An agent stops and asks the human at six points (E1 to E6), not only at the end.
7. **Memo and approval.** The memo agent writes the recommendation and a side-by-side plan table. The human approves, rejects, or asks for changes.
8. **Learning from a rejection.** A rejection can become a proposed policy with evidence. A senior human must approve the policy. [inferred: needs seeded past decisions]
9. **Audit log.** The log records every action and every denied attempt. Each row is chained to the row before it.
10. **Situation profiles.** One engine serves every situation. The profile changes the agent behavior.

## 5. Scope: eight situations

The platform is designed for these eight situations.
The demo runs one of them.

| Situation | Goal | Limits checked first | Demo status |
| --- | --- | --- | --- |
| Raising money | New capital at low cost and low dilution | Debt baskets, restricted payments, liens | Live in the demo |
| Company in trouble | Buy time and avoid default | Covenant breach, cross-default, waiver terms | Second playbook, only if time allows |
| Refinancing | Replace debt on better terms | Prepayment premiums, call protection, maturity | In the design |
| Mergers and acquisitions | Fund or structure a deal | Acquisition baskets, lender consent | In the design |
| Selling part of a company | Raise cash from an asset sale | Asset-sale limits, required prepayment | In the design |
| Borrowing against assets | Secured loan on receivables or equipment | Lien limits, borrowing base, advance rates | In the design |
| Ownership changes | Buyout, recap, or new owners | Change of control, consent rights | In the design |
| Bankruptcy | Spot it early and hand it to experts | Default triggers | Hand to a human (proposed, not confirmed) |

The default profile values come from public sources and from our own inference. [inferred]
No practitioner has checked them.
The reviewer can change every value.
There is no separate agent for each situation. The deal manager picks the profile, and the reviewer can override it.

A profile sets six things:
- Scope.
- Information needed.
- Instruments allowed.
- Objective weights: cost, risk, dilution, control, and speed or certainty. No source gives these weights, so they are inferred.
- Impact measures that the reviewer sees.
- Escalation thresholds.

## 6. Architecture

The system has four parts.

- **People and sources.** The reviewer console, and the deal documents (uploaded or cached from SEC EDGAR).
- **AI agents and their tools.** The deal manager, five specialist agents, and read-only code tools.
- **The gateway.** It is the only writer. It checks permissions, enforces the work-item states, and writes the log.
- **The database.** Postgres on Tiger Cloud holds the work items, facts, clauses, plans, runs, decisions, policies, and the audit log.

The code tools are deal math, plan search and trade-off filter, the seeded Monte Carlo, the quote validator, and cached public data.
Agents do not chat with each other. They pass typed work items through the gateway.
The reviewer console talks only to the gateway.

## 7. The six agents

| Agent | Job | Asks the human at | Never |
| --- | --- | --- | --- |
| Deal manager (master) | Names the situation, loads the profile, makes tasks, marks stale results | Any conflict between results | Does the math or writes a record |
| Intake | Turns documents into facts with page and quote | E1 missing document, E2 facts to confirm | Guesses a missing number |
| Clause reader | Finds limits with exact quotes and confidence | E3 unclear clause or term | Keeps a quote that the validator cannot find |
| Structuring | Builds financing mixes and the shortlist | E4 plan blocked | Invents terms or computes numbers itself |
| Risk | Chooses scenarios and explains Monte Carlo results | E5 best plan flips after an event | Reports a number without a seed and run id |
| Memo and approvals | Writes the memo and proposes a policy after a rejection | E6 final decision | Approves its own work |

## 8. Escalation points

- **E1.** A document is missing. The agent requests it and pauses that part.
- **E2.** The reviewer confirms the facts that drive the plan.
- **E3.** A clause or a defined term is unclear. The agent asks and does not guess.
- **E4.** A clause blocks the plan. The agent shows the redesign, the consent route, and the price of the clause.
- **E5.** An event flips the best plan. The reviewer sees what changed and why.
- **E6.** The reviewer approves, rejects, or asks for changes.

## 9. Work items and gateway rules

A work item moves through these states: NEW, PROPOSED, NEEDS_INFO, APPROVED, POSTED.
It can also end as REJECTED or REVERSED.
A forbidden action is DENIED. The gateway does not apply it and writes it to the log.

The gateway enforces these rules:
1. Only the gateway posts to the record.
2. The proposer of an item cannot approve it.
3. An agent can call only the tools it was given.
4. Every number carries a run id from the math code.
5. A reversal is a new item linked to the original. The system never deletes.
6. Every action and every denied attempt goes in the log.

The design follows the Hyphenate workshop blueprint. [verified: `hyphenate-workshop.md`]

## 10. Data and memory

Postgres holds exact facts in tables.
Vectors (pgvector or pgvectorscale) only help find the right passage.
The rule is: vectors find, tables decide.

Proposed table groups:
- Source: document, document_chunk.
- Knowledge: fact, clause.
- Work: work_item, plan, simulation_run.
- Learning: decision, precedent, policy.
- Proof: audit_log.

Tiger Cloud forks can hold one copy of the database for each candidate plan. [inferred: free-tier limits are not confirmed]
Public data sources are SEC EDGAR, the NY Fed SOFR API, FRED, Census, and Damodaran data.
Cache all of it before the demo. The demo makes no live SEC calls.
SEC EDGAR needs a User-Agent header with a real contact email. The file still uses a placeholder. [verified: research file 05]

## 11. Deal math and risk rules

- Code does all deal math. The model never produces a number.
- The math is deterministic and has closed-form tests. [verified: research file 03 lists 14 tests]
- Monte Carlo is quarterly over five years, with a two-state regime and common random numbers. [verified: research file 03]
- Monte Carlo inputs are labeled assumptions. No calibrated parameters exist yet. [verified: research file 03]
- A plan can pass one covenant test and fail another if redeemable preferred counts as debt. [verified: research file 02]
- Precision comes before recall. If the agent is unsure, it escalates.

## 12. The demo

The demo runs one situation: raising money.
It uses one real public deal as the proof case.
A cached backup deal is ready in case a judge brings a different scenario.

The proof deal is Organogenesis, November 2024. [verified: research file 08]
Avista put $130M of convertible preferred into the company.
The company also signed a Third Amendment to its credit agreement, which was led by SVB.
Research found these blocking items: sections 7.6(e), 7.6(g), and 7.2, and the definitions of Disqualified Stock and Consolidated Total Indebtedness.
The backup deal is Lifecore, January 2023. [verified: research file 08]

One open point makes a good demo escalation. [inferred, from research file 09]
The Disqualified Stock definition only catches redemption by the holder within 91 days after the loan matures on Nov 5, 2026.
A redemption in 2031 falls outside that window.
So it is unclear whether the preferred counts as debt, and the agent asks the human.
If the preferred counts as debt, net leverage is about 4.1x against a 3.00x covenant. This uses an inferred adjusted EBITDA of about $41.6M.
The plan's cash-pay dividend stays blocked even after the amendment.

Replay rules:
- Use only documents that existed before the deal.
- Set cut-off dates, and keep a baseline with no documents to catch leaks.
- Build an answer key from the real clauses and what happened.
- The replay tests clause finding and re-planning only. It does not prove that the plan was best.

The 3-minute script opens with the moment: the first plan turns red, and the log shows DENIED with the clause quote.
The script then shows facts with quotes, one escalation, a new priced plan, the human approval, and the audit log.
Hyphenate wants a video that opens with the moment, plus a live demo.

## 13. MVP scope

Must (the demo does not work without these):
1. One real deal, cached, with an answer key.
2. Intake agent and clause reader, with the quote validator.
3. Gateway, work-item states, and audit log with denied actions.
4. Deal math and plan search, with the blocked plan shown as a DENIED action.
5. Monte Carlo on the shortlist, with run ids.
6. Memo agent and reviewer console.
7. At least four escalations working: E2, E3, E4, E6.

Should (if the schedule holds):
- A rejection becomes a policy, with a few seeded past decisions.
- Event injection, such as a rate move that marks results stale and raises E5.
- Database forks for what-if plans.
- A catch-rate score against the answer key.
- Adversarial tests: self-approval, a prompt hidden in the agreement, a swapped plan after approval.
- E1 with one document held back.
- A second situation through the same engine.

Cut (do not build this weekend):
- Test cases for the other seven situations.
- Arbitrary uploads beyond one working path.
- Accounts, login, mobile, and many deals.
- Live SEC calls on stage.
- Learned objective weights.

## 14. Tech stack (proposed)

- Frontend: Next.js, React, TypeScript, Tailwind. This is the reviewer console.
- Backend: Python, FastAPI, NumPy. It holds the state machine, the gateway, the math, and the Monte Carlo.
- Data: Postgres on Tiger Cloud, with pgvector or pgvectorscale and forks.
- Models: Claude through the Anthropic API. Gemini is optional, and only if a real step uses it.
- Hosting: Vultr, only if it hosts a real part of the system.

## 15. Tracks and sponsors

Status as of 2026-10-23. Sponsor research is in `sponsors/`.

| Track | Status | Note |
| --- | --- | --- |
| Hyphenate (main) | Target | $8K, $5K, $3K, plus interviews for the top 5. Select it on Devpost. |
| Microsoft | Best add-on | Finance is a named domain. Ask whether Microsoft products are required. |
| Tiger Data (MLH) | Target | Forks hold what-if plans. Ask about free-tier limits. |
| Most Technically Advanced | Maybe | Costs no extra work. |
| Factory | Maybe | Use only if each sub-agent runs as a droid session in about 3 hours. Else take the credits. |
| Mana | Maybe, lean skip | Build the console in Mana only if the founders confirm that it counts. |
| GoDaddy, Vultr, Gemini API (MLH) | Cheap | Count only if the integration is real. Register the domain after kickoff. |
| CRS, Atlassian | Maybe | Thin fit. |
| Bright Data, Apify, Spacetime, Convex, Elastic, Coinbase, Fetch.ai, Creao, Figma, Visa, Capital One, Meta, Anthropic Public Benefit | Skip | No honest fit. |

Anthropic gives each hacker $50 of API credits. We claim no Anthropic prize.
Stacking three or more prizes is rare. Plan for Hyphenate, Microsoft, and Tiger Data. [verified: 22 of 1,324 winners in the scrape]
Cal Hacks has not confirmed that one project can opt into several sponsor tracks. Ask at kickoff.

## 16. Hyphenate judging

Hyphenate judges with four questions:
- Is it real enough?
- Would you hire it?
- Did we see something new?
- Was there a moment?

The workshop calls "would you hire it" the make-or-break question. [verified]
Strong entries have a real messy corner, an answer key, limits in code, and a moment on stage.
Weak entries are a chatbot over a spreadsheet, a one-shot extractor, ten shallow workflows, clean happy-path data, and an admin key with "the prompt tells it not to".
The submission needs a demo video, a live demo, a one-line seat description, and proof of what is real and what is simulated.
Judging runs Sunday 10:30am to 12:30pm. The whole team stays at the table.

## 17. Fixed rules

- No project code before Friday Oct 23, about 6pm.
- Devpost is due Sunday 9am, with a table number.
- The team has four people.
- Mark every claim verified or inferred. Label sponsor numbers as self-reported.
- Do not invent prizes.
- Use a plain hyphen and never an em dash.

## 18. Open questions

- Does deal structuring count as a corner of a finance team? Ask at the Friday 7pm Hyphenate workshop.
- Does a former-banker reviewer work as the human seat?
- Does redeemable preferred count as debt under the demo agreement? A practitioner must confirm.
- Does bankruptcy stop and escalate? Cayden has not confirmed.
- Does the SEC allow us to redistribute the cached filings? The wording is unresolved.
- Which past decisions will we seed so the rejection-to-policy loop has evidence?
- Which Factory models can run in a droid session? Ask at the 6pm workshop.
- What does "built with Mana" require? Cayden will ask the founders.

## 19. Where to find more

All paths are inside `docs/`.

- `planning-notes.md`: the original planning README with decisions, the research table, and next steps.
- `research/research.md`: sourced research.
- `research/raw-notes.md`: the first pasted notes, kept unedited.
- `research/deep-problems/01` to `09`: agent-written research. No practitioner has checked it.
- `hyphenate-workshop.md`: the workshop blueprint and the gaps.
- `diagrams/`: four PDFs and their HTML sources. Run `render.sh` to rebuild a PDF. The platform page in `01-big-picture` still says "In the MVP", "Full playbook", and "Recognized". This file replaces that wording.
- `diagrams/stochastic-workflow.pdf`: the older tech stack and tracks sheet.
- `sponsors/`: research on Hyphenate, Tiger Data, Microsoft, Factory, and Mana, plus the Slack notes.
