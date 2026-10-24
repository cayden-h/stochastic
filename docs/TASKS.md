# Tasks: who builds what

Last updated: 2026-10-23.
The product and scope are in `STOCHASTIC.md`. This file only splits the work.
We do not know each person's strengths from our notes. [inferred]
The split below follows the work, so swap tasks freely and tell the team when you do.
Josie owns UI and UX only. She gets no other task.

## Per-person files, branches, and folders

Each person has a task file in `tasks/`, a branch, and a set of folders they own.
The table and the rules for parallel work are in `tasks/README.md`.

## The four seats

| Person | Area |
| --- | --- |
| Cayden | Agent layer, gateway changes, and the demo run |
| Josie | UI and UX only |
| Eric | Data: the two input files, the brief, the answer key, and the real-deal facts |
| Tri | Math tools, tests, and the API that the console reads |

## Shared contract (agree first, 30 minutes)

Write these down before anyone builds. Put them in `architecture/gateway-and-api.md`.

1. The shape of a source line: `company`, `line`, `section` (income statement or balance sheet), `period`, `amount`, `unit`, `source_ref`.
2. The shape of a mapping: `target_line`, `platform_line`, `confidence`, `reason`, `flagged`.
3. The shape of the result: the combined table rows, the leverage figure, the limit, the verdict, and a run id for each number.
4. The three API reads and writes the console needs: get the case, answer the flag, approve the result.

## Cayden

1. Run `list_models()` on the Factory key and answer: can Droid run Claude? Do this first, because it decides the backend.
2. Write `run_agent(role, item)` with two backends (`anthropic` and `droid`), switched by `AGENT_BACKEND`.
3. Write the three agents (Mapper, Preparer, Reviewer) with typed outputs. The Preparer and Reviewer call tools through `@tool` functions that hit the gateway.
4. Update the gateway: new work-item types for mapping, flag, result, and approval. Keep maker-checker and the audit chain, and keep the existing tests green. The architecture review found four gaps in the current gateway: no reverse method, no run-id check on numbers, no check of the Reviewer's verdict before approval, and a default actor named `human:reviewer` that should be the controller.
5. Write the job runner that moves items between the agents.
6. Record one full run, and add the switch to replay it. Rehearse the failure switch once.
7. Write the 1:30 pitch and the 30-second demo script, and run the rehearsals.

## Eric

1. Pull the Kewaunee and Nu Aire filings from the links in `research/real-deal-candidates.md`. Cache them in `data/` (git-ignored). Use a real contact email in the SEC User-Agent.
2. Build the platform file (Kewaunee) and the target file (Nu Aire) as CSVs of statement lines. Use Nu Aire's audited September 2024 statements as the raw target input.
3. Build the answer key from Note 2 of Ex 99.2: each Nu Aire line and its Kewaunee line. Mark it as preliminary and aligned in shape only.
4. Write the one-paragraph brief: the 2.50x limit and the covenant's definitions of Senior Funded Bank Debt and EBITDA, with the section numbers.
5. Write down the facts behind the flag: the "Financing liability" line, its parts, and what the credit agreement excludes. Quote the filing under 15 words, with the exhibit and section.
6. Write the Devpost text and the real-versus-simulated proof list. Draft it by Saturday night.

## Tri

1. Build the tools in `backend/app/tools/`: consolidate two sets of lines, compute EBITDA with the covenant's add-backs, compute Senior Funded Bank Debt, compute leverage, and test it against the limit. Every output carries a run id.
2. Get what is missing from the filings: Kewaunee's D&A (10-K cash flow) and the revolver draw at close (10-Q or 8-K). Compute the leverage twice, a naive version and the covenant version, and write down both with sources.
3. Write tests with the real figures: a tie-out test, a test that a naive and a covenant answer differ, and the existing trust-rule tests stay green.
4. Replace the demo fixture (the invented "Northwind Foods") with the Kewaunee case in `backend/app/db/fixtures/`.
5. Write the API routes the console needs, following the shared contract, and keep them thin.
6. Cut the demo video if the team agrees on one. Hyphenate wants a video that opens with the moment. [verified: `hyphenate-workshop.md`]

## Josie (no new tasks)

Josie works on the design only.
The console now has one working screen: the flag card, the combined table, and the verdict line, plus a log link.
The older mockups in Figma show four screens for a different workflow, so she decides what to keep.
These are inputs for her, not tasks:
- The shape of the data comes from the shared contract above.
- The frontend lives in `frontend/`. The API base URL is `NEXT_PUBLIC_API_URL`.
- The design rules are in `design/README.md`.

## Order of work

1. **Friday night.** The shared contract. The `list_models()` answer. The filings cached. The two input files started.
2. **Saturday morning.** Tools and tests (Tri). Both backends and the Mapper (Cayden). The input files and answer key finished (Eric). The first screen on fixtures (Josie).
3. **Saturday afternoon.** The Preparer, the Reviewer, and the job runner. The API routes. The console reads real data.
4. **Saturday night.** The recorded run. Full rehearsals. Devpost draft. Freeze new features.
5. **Sunday morning.** Fix only blockers. Submit before 9am. Practice the 2 minutes once more before judging at 10:30am.

## Risks to watch

- The covenant ratio is not computed yet. If it comes out under the limit with either treatment of the flag, the verdict does not change, and the moment is weaker. Tri computes it early. Then we choose the flag wording. [inferred]
- The fiscal years differ (April and September). Do not try to match the pro forma column to the dollar.
- The Droid subprocess can fail live. The switch and the recorded run are the answer.
