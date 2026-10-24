# Stochastic: reference for Claude

Last updated: 2026-10-23 (evening, after the reframe to PE add-on integration).
Read this file first in any session about Stochastic.
It holds the main features, the architecture, and the scope.
If this file and a PDF or an older note disagree, this file is correct.
Claims are tagged [verified] when a source file or a filing shows them, and [inferred] when they are our judgment.

## 1. What Stochastic is

Stochastic merges the books of a newly acquired company into the books of the platform company that bought it.
It flags the few lines that need a human, and then checks the combined result against the lender's limit.
It is built for private equity buy-and-build firms, which keep buying add-on companies.
Small agents do the repeatable work, code does all the math, and a human controller approves.
Every step goes in an audit log.

This replaces two earlier framings.
The first was an all-in-one platform for any corporate-finance special situation.
The second was an investment-bank analysis tool that recommends plans.
Both are archived in `planning-notes.md` and `research/`.
They are roadmap ideas only. The product is the integration workflow in this file.

## 2. The pitch rules

- Lead with the problem. Do not lead with the demo or with the name of the deal. [set by Cayden]
- Pitch order: the problem, then what Stochastic does, then the proof.
- Time budget: 1:30 for the pitch and 0:30 for the live demo. [verified: Cayden, 2026-10-23]
- The agent messages in the demo are hardcoded or recorded. Say so. The gateway, the math, and the audit log are real.
- Say that the demo uses a real public deal, with statement-line data from public filings. Account-level detail is not public, so it is not in the demo.
- Do not claim other situations are built. They are roadmap.
- Do not call the output advice. The output is a mapped, combined set of books and a limit check that a human approves.
- Hyphenate rewards a few roles done deep. Depth on one workflow is the proof. [inferred]

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
2. **Map.** The Mapper matches each target line to a platform line, with a confidence and a reason.
3. **Flag.** Lines the Mapper cannot place with confidence go to the human. The human approves a mapping or changes it.
4. **Combine and test.** The Preparer calls code tools that add the books, remove intercompany amounts, compute combined EBITDA, and compute leverage. The Reviewer checks that the totals tie and tests leverage against the limit.
5. **Approve.** The controller approves the result. The gateway posts it and writes the log.

The user sees one screen with a flag card, a small combined table, and one verdict line.

## 5. Main features

1. **Mapping with confidence.** Each target line gets a platform line, a confidence, and a short reason.
2. **Human flags.** Only unclear lines reach the human, with both options and the effect on the result.
3. **Combined books.** A combined table of platform, target, and total. Code does the arithmetic.
4. **Limit check.** Combined leverage next to the lender's limit, with the covenant's own definition of debt and EBITDA.
5. **Maker-checker.** The agent that prepares a result cannot approve it. A reviewer agent checks it, and a human approves it.
6. **Audit log.** Every action is logged, and each row is chained to the row before it.
7. **Replicable agents.** The same stateless agent definition can run once per company, or once per batch of lines.

## 6. Architecture

The system has four parts.

- **People and files.** The console, the two data files, and the brief.
- **Agents.** Three small stateless agents and a plain job runner.
- **The gateway.** It is the only writer. It checks permissions, enforces work-item states, and writes the log.
- **The store.** The MVP can keep the same tables in memory. Postgres on Tiger Cloud is a later swap.

Code tools hold all the math: line matching helpers, consolidation, EBITDA, leverage, and the limit test.
Agents call tools through the gateway. They do not talk to each other.
A job runner moves work items from one agent to the next. The runner is code, not a model.
The console talks only to the gateway.

The agent layer uses one function, `run_agent(role, item)`, with two backends. [inferred, from `research/agent-framework-options.md`]
The Anthropic API is the real path and the stage fallback.
The Factory Droid Python SDK runs the agents that we show as built with Droid.
An `AGENT_BACKEND` setting switches between them, and a recorded run exists as a last fallback.

## 7. The three agents

Each agent is stateless.
It receives one work item with all its inputs, returns one typed result, and keeps no memory.
State lives in the store.

| Agent | Real-team role | Gets | Returns | Never |
| --- | --- | --- | --- | --- |
| Mapper | Staff accountant | One company's lines, the platform's chart, and the covenant definitions from the brief | A mapping with confidence and reasons, a covenant tag for each line (debt, not debt, or unclear), and a list of flags | Guesses a low-confidence match or an unclear tag |
| Preparer | Senior accountant | Both mapped books and the approved flags | The draft combined table and the leverage figure, from tool calls | Computes a number itself, or approves its own draft |
| Reviewer | Reviewer | The draft and the limit | Pass or needs-attention, with reasons | Changes the draft |

The human controller approves flagged lines and the final result.

## 8. Human moments

There are two.

- **Flag.** A line is unclear, and the human chooses how to treat it.
- **Approval.** The controller approves the combined result before it posts.

If the Reviewer finds a tie-out error or a breach of the limit, the item returns to the human as needs-attention.
An earlier design had six escalation points (E1 to E6). They are archived. Two are enough for this workflow.

## 9. Work items and gateway rules

A work item moves through these states: NEW, PROPOSED, NEEDS_INFO, APPROVED, POSTED.
It can also end as REJECTED or REVERSED.
A forbidden action is DENIED. The gateway does not apply it, and it writes a row to the log.

The gateway enforces these rules:
1. Only the gateway posts to the record.
2. The preparer of an item cannot approve it (maker-checker).
3. An agent can call only the tools it was given.
4. Every number carries a run id from the math code.
5. A reversal is a new item linked to the original. The system never deletes.
6. Every action goes in the log, and each row is chained to the previous row.

Denied actions stay in the log as proof.
The demo does not stage an attack. A denied row is shown only if a judge asks to see the log.

## 10. Data

Inputs for the demo:
- A statement file for the platform (CSV), built from the acquirer's filings.
- A statement file for the target (CSV), built from the target's audited statements.
- A short brief: the lender's limit and the covenant's definition of debt and EBITDA.

Tables (a design proposal, and the first prototype keeps them in memory):
- `deal`, `source_line`, `mapping`, `work_item`, `result`, `audit_log`.

The rule "vectors find, tables decide" still holds, but the MVP has no vector search.
Public data is cached before the demo. The demo makes no live SEC calls.
SEC EDGAR needs a User-Agent header with a real contact email. The file still has a placeholder.
Whether we may redistribute cached filings is unresolved, so the cached files stay out of git.

## 11. Math rules

- Code does all deal math. The model never produces a number.
- Consolidation, EBITDA, and leverage are deterministic and have tests.
- Use the covenant's own definitions, not the generic ones. A naive and a covenant leverage figure can differ a lot.
- A tie-out check runs on every combined table: the parts must add to the total.
- Precision before recall. If a mapping is unsure, it becomes a flag.

## 12. The demo

### The real deal

The proof deal is Kewaunee Scientific buying Nu Aire, closed 2024-11-01, for $55M. [verified: `research/real-deal-candidates.md`]
Kewaunee is the platform (fiscal year ends April 30). Nu Aire is the target (fiscal year ends September 30).
Backups, in the agent's ranking: DLH and GRSi, Mama's Creations and Crown I, Shutterstock and Envato.

What the filings give us:
- Nu Aire's audited statements for the year to 2024-09-30 (8-K/A Ex 99.1).
- Kewaunee's pro forma combined statements, with a "Nu Aire, Inc. Reclassed" column and a Note 2 that maps Nu Aire's lines to Kewaunee's lines (Ex 99.2).
- The PNC credit agreement (Ex 10.1): leverage covenant in Section 4.8(a), senior funded bank debt to EBITDA below 2.50 to 1.00, and a $5M acquisition basket in Section 5.8(ii).
- Links are in `research/real-deal-candidates.md`.

Rules for using it:
- Use Nu Aire's audited September statements as the raw target input.
- Use Note 2 as the answer key for the shape of the mapping, not to the dollar. The filing says its own reclassification review is preliminary, and the fiscal years differ.
- Public filings give statement lines, not trial balances. The demo maps statement lines. Account-level detail would be synthetic, so we do not claim it.
- The demo is a reconstruction from public filings. It does not show the lender's or the company's internal views.

### The flag

The one flag is real: Kewaunee's "Financing liability" line.
It holds a sale-leaseback of the Statesville property ($27,782K carrying value in the 10-Q) and, after the deal, the new acquisition financing. [verified: research report]
The credit agreement's "Senior Funded Bank Debt" excludes the capital lease on that property and excludes the seller notes.
The flag belongs to the platform side, not the target side. So it comes from the covenant tag that the Mapper gives each line, and not from the line-to-line match.
The Mapper cannot tag the line as debt or not debt, so the agent asks the controller which part of the line is covenant debt.
The answer changes the leverage result. [inferred: not computed yet]

### The output screen

One screen, three parts:
1. The flag card, with Approve and Change.
2. A small combined table of about ten rows, with columns platform, target, and combined.
3. One verdict line: combined leverage against the 2.50x limit, with OK or Over the limit.

The audit log is a small link. There is no other screen in the demo.

### The 30-second run

Two files and a brief go in. The mapping runs. One flag appears, and the controller approves it. The verdict line shows the leverage next to the limit.
The agent text is hardcoded or recorded. The gateway, tools, and log run for real.

### The 1:30 pitch outline

- 0:00 to 0:25: the problem. A PE firm's next deal is gated by lender limits, and the team combines the books by hand, in weeks.
- 0:25 to 0:55: what Stochastic does. It maps, flags, combines, tests against the limit, and a controller approves.
- 0:55 to 1:30: the proof and the honesty. It runs on a real public deal. The agents are small and stateless, like roles on a real team. The math is code. The log is real. Say what is simulated.

## 13. MVP scope

Must (the demo does not work without these):
1. The two input files and the brief for the Kewaunee and Nu Aire deal, built from the filings.
2. The Mapper, with a typed output, running through `run_agent`.
3. Consolidation, EBITDA, and leverage tools, with tests that use the real figures.
4. The gateway with work-item states, maker-checker, and the audit log.
5. The Preparer and the Reviewer (hardcoded text is fine, but the tool calls are real).
6. The console screen: flag card, combined table, verdict line.
7. A recorded run and a backend switch, so the demo survives a failure.

Should (if the schedule holds):
- A live Droid-backed agent call in the demo.
- An answer-key score for the mapping against Note 2.
- A second flag, such as the seller notes.
- Tiger Cloud Postgres in place of the memory store, and a fork to compare two answers to the flag.
- A downloadable draft compliance certificate.

Cut (do not build this weekend):
- Purchase accounting beyond a "provisional" label.
- Intercompany schedules and eliminations beyond one seeded example.
- Other situations, other deals, arbitrary uploads, accounts, login, mobile.
- Plan search, Monte Carlo, and rejection-to-policy. These belong to the earlier framing.
- A live SEC call on stage.
- A staged denied-action demo.

## 14. Tech stack (proposed)

- Frontend: Next.js, React, TypeScript, Tailwind. Josie leads the design.
- Backend: Python, FastAPI. The gateway, tools, and tests are in Python.
- Agents: Python, `run_agent(role, item)`. The Anthropic API is the default backend. The Factory Droid Python SDK is the second backend.
- Store: in memory first. Postgres on Tiger Cloud is optional.
- Models: Claude through the Anthropic API. Droid model access is unconfirmed.
- Keys: `FACTORY_API_KEY` and the Anthropic key live in `.env`, which git ignores.

## 15. Tracks and sponsors

Status as of 2026-10-23. Sponsor research is in `sponsors/`.

| Track | Status | Note |
| --- | --- | --- |
| Hyphenate (main) | Target | $8K, $5K, $3K, plus interviews for the top 5. Select it on Devpost. |
| Factory | Target (build runner) | Cayden has a Factory account on the Plus plan. Droid runs the agents we show. Confirm prize rules and Claude model access at the workshop. |
| Tiger Data (MLH) | Maybe | Only if the Postgres store gets built. A fork can hold the two answers to the flag. |
| Microsoft | Maybe | Ask whether Microsoft products are required. |
| Most Technically Advanced | Maybe | Costs no extra work. |
| Mana | Skip, lean | Needs the founders' confirmation that it counts. |
| GoDaddy, Vultr, Gemini API (MLH) | Cheap | Count only if the integration is real. |
| Others | Skip | No honest fit. |

Stacking three or more prizes is rare. Plan for Hyphenate and Factory first. [verified: 22 of 1,324 winners in the scrape]
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
For us: the messy corner is the mapping of two different charts, the answer key is Note 2, and the limit is in code.
The moment is the flagged line that changes the leverage verdict. [inferred]
Judging runs Sunday 10:30am to 12:30pm. The whole team stays at the table.

The closest prior winner is VistaAI (HackMIT 2026, first place, self-reported).
It ingests messy CSV and XLSX from acquired companies, proposes field mappings, and keeps provenance.
Ours differs in three ways. It works on accounting lines and not operational records. It checks the result against a lender's limit. It posts through a gateway with maker-checker and an audit log.
Do not lead the pitch with ingestion.

## 17. Fixed rules

- No project code before Friday Oct 23, about 6pm. This is satisfied.
- Devpost is due Sunday 9am, with a table number.
- The team has four people: Cayden, Josie (UI and UX), Eric, and Tri. The task split is in `TASKS.md`.
- Mark every claim verified or inferred. Label sponsor and vendor numbers as self-reported.
- Do not invent prizes or numbers.
- Keep keys in `.env`. Never put them in docs or git.
- Use a plain hyphen and never an em dash.

## 18. Open questions

- Does PE add-on integration count as a corner of a finance team for Hyphenate? Ask at the Friday 7pm workshop.
- Which part of Kewaunee's financing liability counts as covenant debt? A practitioner should confirm. We have not computed the ratio.
- Kewaunee's D&A and revolver draw were not in the pages the agent read. Tri must get them from the 10-K and 10-Q.
- Can Droid run Claude models on our key? Run `list_models()`, and ask Factory.
- Does the Python Droid SDK qualify for "Building with the Droid SDK" when the tools call our own gateway?
- Does the SEC allow us to redistribute the cached filings?
- Does a former-banker or controller reviewer count as the human seat?

## 19. Where to find more

All paths are inside `docs/`.

- `TASKS.md`: who builds what. `tasks/` holds one file per person, with branches and owned folders.
- `demo-script.md`: the 2:00 plan, the 30-second demo beat by beat, the failure plan, and judge Q&A prep.
- `glossary.md`: finance and product terms in plain language.
- `decisions.md`: the dated decision log and the open decisions.
- `architecture/`: parts, agents and work items, gateway and API, data model, repo structure.
- `design/`: Figma links, tokens, and UI rules. The mockups predate the reframe to PE add-on integration. Josie updates them.
- `research/ma-workflow-research.md`: the three M&A users, pain, time, and existing products.
- `research/post-close-deliverables.md`: what a PE finance team gets after an add-on closes.
- `research/real-deal-candidates.md`: the real deal, with EDGAR links.
- `research/agent-framework-options.md`: Droid, ADK, Anthropic API, and others.
- `hyphenate-workshop.md`: the workshop blueprint and the gaps.
- `sponsors/`: Hyphenate, Tiger Data, Microsoft, Factory, Mana, and the Slack notes.
- `planning-notes.md`, `research/research.md`, `research/deep-problems/`: archive from earlier framings.
- `diagrams/`: PDFs from the first framing. They are stale and are not re-rendered.
