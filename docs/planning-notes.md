Archive note: this file was copied on 2026-10-23 from the CalHacks ideation repo, where it was the Stochastic README.
Links that start with `../` point to files in that older repo and do not work here.
The current reference is `STOCHASTIC.md`.

# Stochastic

Status: the team is set on this project (Cayden, 2026-10-23).
Open design choices are listed under "Decisions" below.
Track: Hyphenate, "The Hyphenated Enterprise: Autonomous Systems for Finance" (see `../sponsors/hyphenate.md`).
The short reference for Claude, with the main features, architecture, and scope, is `STOCHASTIC.md`.
Read it first.
Raw pasted notes are in `raw-notes.md`.
Research findings with sources are in `research.md`.

## One-line pitch

One platform for any special situation: when a company needs new money, a merger, a refinancing, or help in trouble, a team of AI agents reads the agreements, finds the limits, builds and stress-tests the options, and hands a recommendation to a human for approval.
A situation profile changes what the agents look for, weigh, and ask, so the same engine serves every situation.
(Reframed 2026-10-23 at Cayden's request: pitch it as all-in-one, and show one real deal only as proof. Earlier wording: an AI special-situations financing team for debt and equity mixes.)

## The problem

A company needs more capital than a senior bank loan will give.
Example from the notes: a $200M restaurant chain wants a $100M acquisition, but the bank lends only $50M.
The gap is filled with a stack of instruments, for example $50M senior loan, $30M junior debt, and $20M preferred equity.
Choosing the mix is hard because each piece changes interest cost, ownership, risk, and future profit.
Today this is done by scarce, expensive specialists over weeks.

## Real-world anchor (from the notes)

- Morgan Stanley Investment Management's Tactical Value team makes opportunistic, private, long-term, likely illiquid investments across asset classes and across the capital structure, and cites structuring experience for bespoke needs.
  [verified in `research.md`, from a search summary because the page itself returned 403]
- The notes' claim that such deals are "10 to 20 percent of portfolios" is not on the team page.
  Treat it as unverified and do not say it in the pitch.
- Buyers Edge Platform's $425M preferred equity deal (April 2024) is the case to study.
  General Atlantic Credit led, with Blackstone Tactical Opportunities and Morgan Stanley Tactical Value as co-investors, and William Blair was placement agent.
  The pasted notes had the roles blurred and said JPM was agent, which found no support. [verified in `research.md`]

## Industry vocabulary and 2026 market (added 2026-10-23, details in `research.md`)

- The industry calls this work "capital solutions": bespoke hybrid instruments between debt and equity (preferred equity, structured equity, holdco PIK, convertibles, stretched senior, mezzanine and second lien).
  Use that phrase in the pitch. [verified: Mayer Brown, October 2026]
- Target returns are 15 to 25 percent gross IRR (20 percent or more when stressed), against 8 to 12 percent for conventional lending. [verified: same, adviser estimate]
- Private credit is over $2T as of May 2026 and projected at $3.4T by 2030. [verified: same, self-reported estimate]
  These are the "impact the whole industry" numbers for the deck, labeled as estimates.
- Deals stall on consents under existing facilities, intercreditor terms, and governance rights more than on a leverage ratio. [verified: same]
- Covenant-lite was 41 percent of large deals in 1H 2026 but under 4 percent below $50M EBITDA, so a mid-sized borrower still has real maintenance covenants. [verified: Houlihan Lokey newsletter, search summary]
- No startup or hackathon project doing this was found in standard searches.
  That is weak evidence of novelty, not proof. [see `research.md`]

## What the system does

1. Intake: financial statements and existing loan agreements for the company.
2. Analyze: company financial health, risk and reward tolerance, existing covenants.
3. Combine: candidate structures across the capital stack, from senior secured loans down to common equity.
4. Simulate: Monte Carlo over thousands of futures (recession, revenue decline, rising rates) to estimate which structure leaves the company in trouble.
5. Recommend: a structure with tradeoffs, "subject to lender terms and human approval".

The system does not lend money.
It works out how a company should obtain it.

## The autonomous moment (what Hyphenate would care about)

The first plan is $80M debt plus $20M from investors.
The agents find a clause in the existing loan agreement that caps additional debt.
Without being asked, they:

1. Recognize the plan is not allowed.
2. Generate new combinations that respect the clause.
3. Re-run the simulations.
4. Recommend a revised plan and explain the tradeoffs.
5. Route it to a human approver.

Strongest version: agents keep managing the analysis, spot new problems (a covenant, a rate move, a new lender term), coordinate revisions, and prepare each decision for approval, instead of a one-shot recommendation.

## Fit against the Hyphenate brief

Mapping to the five hard parts (agent judgment, inferred):
- Sources that disagree: the term sheet, the existing credit agreement, and the financial model can conflict.
- Time: a revenue miss in one quarter changes which structure still works later.
- Working with others: the approver can reject a plan, and a lender's terms can change mid-process.
- Limits: the agent that proposes a structure cannot approve it (segregation of duties).
- Explainable: every number and clause traces to a source.

Open question: does deal structuring count as a corner of a finance team?
The brief asks for "one corner of its finance team, a few seats that work closely together", lists sample workflows (Cash and Treasury and FP&A are the closest), and says "or one not listed". [verified: `../sponsors/hyphenate.md`]
The "CFO-office" label that appeared in earlier notes came from Hyphenate's product description, not from the track rules.
This idea is closest to treasury and capital planning, but it is deal structuring, not back-office operations.
Ask at the 7pm Friday workshop.

## Risks and open questions

- Scope: a full capital-structure optimizer is a lot to build in 36 hours, so pick one fictional company, one covenant trap, and one hero scenario.
- Judges may see it as "ChatGPT for financial advice", so the demo must show the loop (find the blocker, replan, re-simulate, escalate), not a single answer.
- Realism: instrument terms, pricing, and covenants need to come from real documents, not invented numbers.
  Nobody on the team has had a practitioner check this yet.
  Ballpark pricing from secondary sources is in `research.md`: second lien about SOFR + 650 to 1000 bps (sources differ), mezzanine 8 to 12 percent cash plus 2 to 4 percent PIK, capital solutions 15 to 25 percent IRR.
  No 2026 preferred equity pricing was found.
- Hero trap design (inferred): make it a consent or incurrence restriction under the existing facility, or a covenant definition (for example debt including leases) that flips a ratio test, not a plain leverage cap.
  That is where real deals get stuck, and it is easy to log as a denied transition.
- The Monte Carlo inputs (rate paths, revenue shocks) must be labeled as assumptions, not predictions.
- Unclear whether to build the company side (borrower) or the investor side (a fund evaluating the deal).
  The notes lean borrower-side advisory, with the investor use as a second pitch.

## Workshop findings (2026-10-23)

The Hyphenate online workshop deck and transcript are analyzed in `hyphenate-workshop.md`.
Short version: build a system of work (work items as a state machine, a gateway that is the only writer, an append-only diff log, learned policies from precedents), not a calculator with agents on top.
The main gaps for Stochastic are no learning source, no self-improvement loop, no time dimension, and no answer key.
The seat question was settled on 2026-10-23: one live deal worked from start to approval, with events during the deal and no after-close monitoring (see "Decisions" below).
Slack sponsor findings that touch this idea (CRS, Microsoft) are in `../sponsors/slack-channel-notes.md`.

## Four added capabilities and borrower-side framing (ChatGPT input, 2026-10-23)

Cayden pasted a ChatGPT write-up.
It is unverified outside agent judgment, and its "9 out of 10 fit" rating is an opinion with no rubric behind it.
It proposes four capabilities:
1. Notice missing information (for example a missing debt agreement), request it, and resume.
   This maps to the NEEDS_INFO state in the Hyphenate blueprint.
2. Coordinate with humans: ask the CFO, request approval of terms, revise after feedback.
3. Remember past deals, assumptions, and why humans accepted or rejected them.
4. React to changing conditions (a rate rise, a lender changing terms) by recalculating and alerting decision-makers.
It also recommends building for the borrower's CFO or treasury team, not for an investor like Morgan Stanley, and proposes four logical roles (analyst, structuring, risk and simulation, deal manager) on one shared workflow engine.

Our read (inferred):
- Borrower-side is proposed as the answer to the open borrower versus investor question.
  Not yet confirmed by the team.
- Capabilities 3 and 4 need a simulated clock and an event feed during one deal.
  The later decision keeps those events but drops the after-close quarterly model.
- Capability 3 is memory only.
  Hyphenate wants more: a rejection becomes a proposed general policy with evidence, backtested, and approved by a controller.
- The deal math (waterfall priority, interest, dilution, covenant tests) must be deterministic code, and the LLM must never produce those numbers.
- Four named agents risks reading as "many shallow roles".
  Present one or two seats in one line and keep the rest as tools.
- Still missing from the write-up: the gateway as the only writer, denied transitions logged with the clause as evidence, and an answer key with a score.
  It also needs investor eligibility rules from real documents, and no practitioner has checked those yet.

## Decisions (2026-10-23, from Cayden)

- Deep problems, one sub-agent each, under one master agent that owns the deal:
  1. Read the existing loan agreement and find restrictive clauses.
  2. Search for debt and equity mixes that fit those restrictions.
  3. Run the Monte Carlo risk simulation (seeded, reproducible, deterministic deal math in code).
  4. Handle approvals, rejections, and missing documents.
- Seat: the special-situations financing team, working one live deal from start to approval.
  Time passes inside the deal through events.
  There is no after-close monitoring and no quarterly company model.
  This replaces the "standing seat" recommendation.
- User: a senior reviewer, someone who has done this work before and now oversees it (or the CFO or treasury lead).
  The system acts as the analyst team and the human is the approver, which matches Hyphenate's proposer and approver split.
- Memory: Postgres tables for exact facts (past deals, covenants, decisions, learned policies, audit log) plus retrieval (such as pgvector) over document text.
- Demo deal: not chosen yet.
  The $100M restaurant chain was only an example from ChatGPT.
  A fictional company modeled on the public Buyers Edge $425M preferred equity deal is the leading candidate.
  Use it as inspiration only and never claim real terms, because preferred rate and covenants were not found publicly (`research.md`).
- Correction: the notes say this work exists only inside bulge bracket banks, but the Buyers Edge deal was led by General Atlantic Credit with Blackstone and Morgan Stanley Tactical Value as co-investors, and placed by William Blair (`research.md`).
  Say "specialized private-credit and tactical funds", and do not claim bulge-bracket exclusivity.
- Data plan:
  - Primary: public SEC EDGAR filings (the Hyphenate brief lists EDGAR).
    Real financial statements and real credit agreements filed as exhibits are the likely source (to verify), with our own planted traps and an answer key on top.
  - Bright Data and Apify: only for live public inputs such as rates or comparable-deal press releases, and only if the demo truly depends on them.
    Bright Data disqualifies mocked data and Hyphenate wants a seeded company, so do not force either.
  - Nobody on the team has checked the numbers with a practitioner.
- Pitch framing (2026-10-23): Stochastic is an all-in-one platform for any special situation, not a tool for one deal.
  The demo deal is proof of the platform, so slides and videos should say "one real deal" and not lead with its name.
  Honest limits to keep in the pitch: two playbooks have full depth (raising money, company in trouble), and the other situations use the same engine with a profile and hand off to a human.
  Risk (inferred): Hyphenate rewards a few roles done deep, and breadth can read as "ten shallow workflows", so the proof must be depth on one real deal with an answer key.
- Hyphenate fit: ask at the 7pm Friday workshop whether deal structuring counts as a corner of a finance team, and whether a former-banker reviewer works as the human seat.

## Research results (2026-10-23)

Six research agents wrote findings under `deep-problems/`.
All were written by agents from web sources and a few EDGAR fetches.
Each claim is tagged verified or inferred in its file, and no practitioner has checked any of it.

| File | Topic | Headline |
| --- | --- | --- |
| `deep-problems/01-clause-reading.md` | Reading credit agreements | Five real restaurant credit agreements fetched. The Potbelly agreement has three clauses that a cash-pay preferred raise would trip: a $2M debt basket, a $1.5M restricted payments basket, and an "Indebtedness" definition that counts Disqualified Capital Stock. |
| `deep-problems/02-structure-search.md` | Searching debt and equity mixes | Enumerate a grid, filter to the best trade-offs, then simulate the shortlist. The demo trap is a plan that passes a 3.0x leverage test at 2.80x and fails at 3.20x once preferred counts as debt. Prices depend on leverage ahead of the tranche. Sources are mostly secondary. |
| `deep-problems/03-monte-carlo.md` | Risk simulation | Quarterly, 5 years, a two-state recession regime, common random numbers across structures, and 14 closed-form tests as an answer key. No calibrated parameters yet, and the restaurant volatility must be computed from Census data. |
| `deep-problems/04-approvals-and-memory.md` | Approvals and memory | Full Postgres schema, a nine-step rejection-to-policy loop, escalation rules, and five adversarial tests. No public source for how private-credit approvals work, so the path is built from adjacent sources. |
| `deep-problems/05-edgar-data-plan.md` | Data plan | EDGAR endpoints tested (needs a User-Agent with a real contact email). Red Robin, Carrols, Papa John's, and BurgerFi are candidate bases. Build a fictional company by renaming, scaling, and shifting dates, with 8 planted traps and a JSON answer key. Bright Data and Apify: no for the core. A free NY Fed SOFR API works for live rates. |
| `deep-problems/06-impact-and-novelty.md` | Adjacent problems and novelty | Contract extraction and covenant monitoring are crowded. Open areas: consent and waiver pathway planning, term sheet normalization, and term sheet versus credit agreement checks. |

Suggested additions to the core four (from file 06, not yet adopted):
1. An answer-key test harness with planted traps.
2. A consent and waiver pathway: when a clause blocks the plan, work out the vote needed, price the ask, and compare it with redesigning the plan.
3. A cross-document check limited to one term sheet clause against one credit agreement clause.

Conflicts between the files to resolve before building:
- Whether redeemable preferred counts as debt (files 01 and 02).
  It is an assumption that needs a practitioner.
- File 05 recommends Red Robin as the base, and file 01 found Potbelly's clauses fit best.
  Pick one real agreement for the structure and the clauses.
- Replace `contact@example.com` in the EDGAR User-Agent with a real team email.
  The SEC redistribution wording is unresolved, so make no SEC calls at demo time.

## Demo deal and situation types (2026-10-23, from Cayden)

Demo deal: a real, historical deal replayed from public documents (Cayden, 2026-10-23).
- Primary: Organogenesis, Nov 2024.
  Avista put in $130M of convertible preferred, and a Third Amendment to its SVB-led credit agreement is the answer key.
  Blocking clauses reported by the research agent: Sections 7.6(e), 7.6(g), and 7.2, plus the "Disqualified Stock" and "Consolidated Total Indebtedness" definitions.
  It is a healthy company, not a rescue.
  Correction from `deep-problems/09-situation-profiles.md` (agent output, not independently checked): the "Disqualified Stock" definition only catches redemption by the holder within 91 days after loan maturity (Nov 5, 2026), so a 2031 redemption falls outside it.
  Whether the preferred counts as debt is therefore a real ambiguity and not a clear block, and it is a good escalation, not a clean trap.
  The same file says the plan's cash-pay dividend stays blocked even after the amendment.
- Backup: Lifecore (formerly Landec), Jan 2023, a $38.75M PIK preferred with a waiver and Fourth Amendment.
  A true special situation but harder to explain.
- Limits: the target plan comes from the same announcement that reveals the deal, so the replay tests clause finding and re-planning, not inventing the deal.
  Run the no-documents baseline to check what the model already knows.
  Say "a reconstruction from public filings, not the lenders' internal views".
- Source: `deep-problems/08-real-deal-candidates.md` (agent output, not independently checked).

Situation types the deal manager must recognize (Cayden's list of eight), and what each means for the build (agent judgment, inferred):

| Situation | Typical clauses to test | Playbook |
| --- | --- | --- |
| Raising money | debt and lien baskets, restricted payments, preferred treated as debt | Core playbook. Generate senior, junior, and preferred mixes. Organogenesis fits here. |
| Mergers and acquisitions | permitted acquisition limits, debt incurrence, change of control | Same engine as raising money, with the acquisition tests added. The restaurant example fits here. |
| Company in financial trouble | financial covenants, defaults, cure rights | Second full playbook: covenant relief, waiver, and amend-and-extend. Lifecore fits here. |
| Refinancing | maturity, prepayment premium, lien releases | Replace or extend existing debt. Reuses the structure search. |
| Selling part of a company | asset sale limits, mandatory prepayment, collateral release | Recognize and run the clause tests. Playbook stub. |
| Bankruptcy | automatic defaults, DIP priority | Out of scope. Detect it, stop, and escalate to the human. |
| Borrowing against assets | lien baskets, borrowing base, sale-leaseback limits | Recognize and run the clause tests. Playbook stub. |
| Ownership changes | change-of-control triggers, board rights, equity transfers | Usually a second label on another deal. Run the trigger tests. |

Design rules:
- Classification is multi-label with a confidence score.
  A deal can be several types, and Organogenesis is both "raising money" and "ownership changes".
- The classifier is a step in the deal manager, not a ninth agent.
  Hyphenate rewards a few roles done deep.
- There is no agent per situation type (Cayden, 2026-10-23).
  The same agents run every deal, and the situation type only changes the inputs they get.
  A situation profile is a config object with these fields:
  - scope: which documents and clauses matter, and which are out of bounds,
  - information needed: what the intake agent must find or ask for,
  - allowed instruments: which options the structuring agent may generate,
  - objectives: weights for cost, risk, and dilution (risk versus return),
  - impact measures: what the reviewer sees (for example covenant headroom, ownership given up),
  - escalation thresholds: how confident an agent must be before it acts without asking.
  The profile is chosen by the deal manager, and the reviewer can override it.
- Build two playbooks fully (raising money, company in trouble).
  Recognize the rest and run their clause tests.
  If the type is unclear, ask the human.

## Diagrams (2026-10-23)

Four PDFs in `workflow/v2/` explain the architecture and the MVP in plain English.
They are a design proposal, not final.
The source is HTML and CSS, and `render.sh` rebuilds a PDF with headless Chrome.

- `01-big-picture.pdf`: what Stochastic does, and the four-part architecture.
- `02-deal-flowgraph.pdf`: a swimlane of one deal from start to finish, and the three loops (event, blocked plan, rejection).
- `03-agents-and-data.pdf`: the six agents, the work-item states with the gateway rules, and the database tables.
- `04-mvp-build-plan.pdf`: the Must, Should, and Cut lists, a proposed 3-minute demo script, and a six-phase build plan for four people.

The older `workflow/stochastic-workflow.pdf` stays as the tech stack and tracks sheet.

## Next steps

- The demo deal is chosen (see "Demo deal and situation types" above).
  Next: copy the covenant and basket language from the Organogenesis credit agreement and its Third Amendment into the answer key, following the replay protocol in `deep-problems/08-real-deal-candidates.md`.
- Try the Business Wire copy of the Buyers Edge release for the preferred terms: https://www.businesswire.com/news/home/20240408441127/en/ (the Morgan Stanley and General Atlantic copies returned 403).
- Find defensible Monte Carlo inputs (EBITDA volatility, rate paths), labeled as assumptions.
- Check Hypercore and Ellis (`../private-credit-market.md`) and ask the booth for prior art.
- Idea only, not decided: a data center or AI-infrastructure borrower, because 2026 AI debt is a live example of layered structures and fast-depreciating GPU collateral (`research.md`).
- Pick the fictional company and the covenant trap for the hero scenario.
- Decide how it differs from the shelved securitization idea in `../domains/securitization/` (that one was back-office checking, this one is front-office structuring).
