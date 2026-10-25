# Hyphenate (Cal Hacks 13.0)

## Status after the 2026-10-23 evening reframe

Stochastic is now a PE add-on integration tool.
It merges the books of a newly acquired company into the platform company's books, flags the few lines a human must decide, and checks the combined result against the lender's limit.
Three stateful agents do the work (Mapper, Preparer, Reviewer), code does all the math, and a controller approves.
What the controller decides once, the agents keep.
The demo uses a real public deal: Kewaunee Scientific buying Nu Aire. [verified: `../STOCHASTIC.md` section 12]

### How Hyphenate fits now

Hyphenate stays the main track. [verified: `../STOCHASTIC.md` section 15]
The fit is still good, but one thing is open: we do not know if PE add-on integration counts as a corner of a finance team.
The seat is a portfolio controller at a PE-backed company, right after an add-on closes. [inferred: no practitioner has checked this]
The seat is one add-on deal, from the two data files to the controller's approval.

Questions to ask at the Friday 7pm workshop:
1. Is PE add-on integration a valid corner of a finance team?
2. What separates a hireable demo from one that is not?
3. What may an agent do alone, and what goes to a human?

### Which old notes still apply

- The official brief, the prize text, and the four judging questions still apply.
- The judging notes below still apply.
  "Would you hire it" is still the make-or-break question.
- Anything that describes plan search, Monte Carlo, forks for what-if plans, the eight situations, or the clause reader is from the earlier framing.
- The earlier "special situations" idea is now roadmap only.

---

- Prize: "The Hyphenated Enterprise: Autonomous Systems for Finance" - $8,000 / $5,000 / $3,000 for 1st to 3rd, plus an expedited, shortened interview for every member of the top 5 teams.
- Status: **main track** (team decision 2026-10-15, reconfirmed 2026-10-23).
  The idea is now Stochastic, special-situations financing, see `../Stochastic/README.md`.
  Securitization (`../domains/securitization/`) is shelved.
- Brief read: 2026-10-15, full text pasted by the team from the organizers' document (Cal_Hacks_Hyphenate_Track).

## What they do

Hyphenate is the new name of Maximor, an autonomous finance platform for the office of the CFO. [verified: https://hyphenate.ai]
The rebrand was announced 2026-10-01, with 86x revenue growth self-reported by the company. [verified: https://thenextweb.com/news/maximor-rebrands-hyphenate-86x-growth-autonomous-finance]
TNW labels that piece a contributed article that does not reflect its editorial stance, so treat all growth and customer numbers as self-reported. [verified: same URL]
Agents run order-to-cash, treasury, GL accounting and close, procure-to-pay, and reporting on top of existing ERPs, banks, and payroll. [verified: https://hyphenate.ai]
The email calls Hyphenate the Cal Hacks co-host. [verified: pre-event email]

## The official brief, summarized

Source: the track document pasted by the team on 2026-10-15.
Quoted phrases are verbatim.

**Thesis.** Agents can already take a task when prompted.
"The frontier is autonomy inside a company: systems that pick up work on their own, across the software and the people that run it, with decisions that are explainable when someone asks and accountable whenever someone looks back."
Finance is "where this gets hard fastest": one refund changes revenue, cash, a customer's balance, and the forecast, "every number has to agree with every other number, and nothing moves without the right person's sign-off".

**The ask.**
Pick a company and one corner of its finance team, "a few seats that work closely together" (example: the accountant who applies customer payments and the person who chases the late ones).
Build the autonomous system you would hire to fill those seats, "and the company it works in: the software it uses, the people it answers to, and the mistakes hiding in its data".
Be "as imaginative as you like about who the company is (a Formula 1 team, a music festival, a three-person startup, a colony on Mars) and strict about how it works underneath".
No finance background needed.

**What makes it hard (their list, and where the judges will probe).**
1. Sources that disagree: the bank, the ledger, and the contract tell different stories, so the system must know which to trust and say why.
2. Time: finance runs for months, so what happened in March should change what the system does in June.
3. Working with others: approvers are busy, colleagues hand over half-done work, the controller sometimes says no, and the system must ask at the right moment and handle the answer.
4. Limits: no one employee has access to everything, and "whoever requests a payment can't be the one who approves it" (segregation of duties).
5. Explainable and accountable: every call traces back to the data, rule, or person behind it, "no matter how long ago it was made".

**Sample workflows (pick a corner of one, or one not listed).**
Revenue Accounting, Accounts Receivable, Cash and Treasury, Accounts Payable, Accruals, Expenses (prepaids, fixed assets, leases, capitalized R&D), Payroll, Close and Consolidation, FP&A, Reporting.
Each is only an outline; "the exceptions and judgment calls that make the work hard are yours to discover", including by finding the Hyphenate team at the booth.

**How they judge: four questions for every submission.**
1. Is it real enough?
   Realistic data, a messy problem, and proof that it works.
2. Would you hire it?
   For which seats, and would it earn them: limited access, a clean record of its work, and knowing when to ask?
3. Did we see something new?
   A company, problem, or approach not seen made autonomous before.
4. The moment: when it catches what others missed, recovers from something going wrong, or defends a decision when questioned.

**What to submit.**
- Code.
- A demo video that opens with the moment.
- A live demo at judging, running for real; judges "may ask you to try a scenario of our own", so the system must handle unseen input.
- One line on the seats the system would fill.
- Proof it works: what is real, what is simulated, and how you know (a test set, planted errors with an answer key, or a benchmark score).

**Workshop.**
"Beyond Agentic Harnesses: Engineering the Autonomous Enterprise" - online Oct 21 (time not given), and in person Oct 23 at 7pm, "an hour after hacking starts" (so hacking starts around 6pm).

**Places to start (free references from the brief).**
- Sandboxes: Stripe, Increase, Lago, Odoo, ERPNext.
- Ledgers: Formance Ledger, Blnk, TigerBeetle, Beancount and Fava.
- Mocks: Mockoon, Prism, stripe-mock.
- Data: SEC EDGAR, public GitHub repositories.
- Benchmarks: AccountingBench, APEX-Accounting, Finance Agent Benchmark, DABstep, BenchRec, Invoice Sandbox Benchmark.
- People: a model can play the approver, colleague, or auditor.
- Models and frameworks: any.

The brief has no "must use Hyphenate's product" rule and no scope exclusions.
Earlier notes that consumer banking, trading, lending, or payments were excluded came from Maximor's own 2026 hackathon, not this brief, so they do not apply here. [verified: brief]

## What Hyphenate is pushing (context for the pitch)

Marketing language: "audit-ready agents that execute the work, show what they did," "every entry carries its own audit trail," "Approvals route on your rules," an "Input Needed" status. [verified: https://hyphenate.ai]
Exceptions are a loop: "Every exception, judgment call, and escalation after that feeds back in." [verified: https://hyphenate.ai]
The company says 98% of touched work is automated and about 2% escalates (self-reported). [verified: agilebrandguide.com rebrand article]
The brief's vocabulary (audit trail, segregation of duties, controller sign-off, explainable) matches that marketing, so mirror it in the demo. [inferred]

## Precedent: Maximor's own hackathon (weaker evidence)

"Syndicate by Maximor" Track 2: "Build an agent that automates a real workflow handled by a company's accounting, finance, or treasury team," end to end "including exceptions and human review". [verified: https://luma.com/d0kq45ek]
No formal criteria or winners were found there. [verified: same page]
The Cal Hacks brief is far more detailed, so use it as the primary source.

## What a winning entry looks like (inferred from the four questions)

It picks one corner (for example AR cash application and collections, or AP with vendor bank-detail changes) and builds a believable company around it with deliberately messy data: a bank feed, a ledger, and contracts that disagree.
The demo opens with the moment: the agent catches a planted error others would miss, such as a changed vendor bank account the day before a large payment, a short-paid invoice bundled with another, or a refund that breaks a revenue schedule.
It shows a second moment of recovery or defense: a controller (a model playing the approver) says no or asks "why", and the agent explains the call by tracing it to the data, rule, or person, even for a decision made months earlier in simulated time.
It enforces limits visibly: the requester agent cannot approve its own payment, and each agent has scoped credentials.
It reports honest proof: a planted-error answer key ("seeded 40 errors, caught 36, escalated 4, 0 wrong postings") or a score on a public benchmark.
It handles a judge's surprise scenario without breaking.

## What loses

A chat wrapper over a spreadsheet, or a single agent with full access that can request and approve its own actions.
Perfect toy data that never hits an exception, or a company that is imaginative on the surface but has no real rules underneath.
Unproven autonomy claims, with no answer key or benchmark, or only simulated parts passed off as real.
A demo video that buries the moment.
A scenario that only works on the rehearsed input.

## How our existing work maps

Our git-for-AI-coding direction (see `../tracks.md`) does not fit this track as a coding tool, but its core ideas are exactly what the brief asks for: per-action attribution, an append-only history, approvals before risky actions, and replay.
The honest move is to carry those ideas into finance, with the ledger and the decision trail as the differentiator, and to drop the coding framing.
The git idea stays recorded in `../ideas.md` as a fallback, not the plan.

## Idea seeds (all unvetted, written against the brief)

1. **AR seat pair.** An agent that applies customer payments (short, late, bundled) and a second agent that chases overdue invoices, for a company with usage-based billing; the hard part is deciding which source to trust when bank, ledger, and contract disagree.
2. **AP with a fraud moment.** Bills arrive in odd formats, approvals stall, and a vendor's bank details change the day before a large payment; the agent holds the payment, explains why, and routes to a human who is not the requester.
3. **Revenue accounting for amended contracts.** Bundles, ramps, and mid-term amendments become revenue schedules that stay right when a deal changes; the demo changes a deal in June and the system restates March correctly and explains the difference.
4. **Accruals agent.** Estimates costs for work done but not yet billed, confirms with vendors (a model plays the vendor), and reverses when the bill arrives.
5. **Close and auditor mode.** Reconciliations and sign-offs for a month, then an auditor model asks for evidence on a random entry and the system reconstructs the full decision trail.
6. **Cross-cutting layer.** A reusable "accountable agent runtime" with scoped credentials, segregation of duties, and an append-only decision ledger, demoed on one corner.
   The risk is looking like infrastructure with no company, so keep a concrete corner as the demo.

Pick the company first for memorability (the brief invites a Formula 1 team, festival, or colony) but keep its books strict.

## Risks and open questions

No public API from Hyphenate, so all data is ours; budget real time to seed a believable, messy company (bank feed, ledger, contracts, planted errors with an answer key). [inferred]
We have no finance domain expertise on the team; plan to talk to the Hyphenate team at the booth early to learn the real exceptions of the corner we pick. [inferred]
Many teams will build a "reconciliation agent"; the "something new" question favors an unusual company or an unusual corner. [inferred]
Live demo may include a judge-supplied scenario, so test on unseen inputs before Sunday. [inferred]
Confirm interview terms for the top 5 (roles, locations, eligibility).
Confirm the workshop times (online Oct 21, in person Oct 23 at 7pm) and attend at least the in-person one.

## Sources

- Cal_Hacks_Hyphenate_Track brief (pasted by the team, 2026-10-15)
- https://hyphenate.ai
- https://thenextweb.com/news/maximor-rebrands-hyphenate-86x-growth-autonomous-finance
- https://agilebrandguide.com/maximor-rebrands-as-hyphenate-after-86x-yoy-growth-expanding-across-the-office-of-the-cfo/
- https://www.startuphub.ai/news/hyphenate-bets-finance-wants-fewer-tools
- https://luma.com/d0kq45ek (Syndicate by Maximor, prior hackathon prompt)
- Pre-event email, 2026-10-15

## Workshop and Slack update (2026-10-23)

The Oct 21 online workshop and its slide deck are analyzed in `../Stochastic/hyphenate-workshop.md`.
The main new facts: the system-of-work blueprint (gateway, state machine, append-only diff log, learned policies), the "would you hire it" emphasis, precision over recall, and a list of strong and weak submissions.
In `#cohost-hyphenate` a Hyphenate rep said you do not sign up separately: you participate normally and select the Hyphenate track on Devpost at submission.
Abdul, a Hyphenate founding engineer, said they will judge as part of the Hyphenate team.
The recording and slide PDF are pinned in the channel, and the in-person workshop is Friday Oct 23 at 7pm in the Theater.
