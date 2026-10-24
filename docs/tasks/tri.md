# Tri: math tools, tests, API

Branch: `tri/tools`.
Folders: `backend/app/tools/`, `backend/app/api/`, `backend/app/db/`, `backend/tests/`.

Cayden wrote first versions of `tools/finance.py`, `api/routes.py`, `db/fixtures/kewaunee.py`, and `tests/test_trust_rules.py` on 2026-10-24 so the pipeline could run. They are yours now.

1. Review `finance.py` against Ex 10.1's definitions. EBITDA is net income plus interest, taxes, D&A, plus the brief's add-backs, less the rent deduction. Add any add-back the agreement names that we left at zero, with its source and amount, or write down why it stays zero.
2. The computed figures today: EBITDA $27,519K, covenant debt $21,633K, leverage 0.79x; whole-line debt $71,955K, 2.61x. Reproduce them by hand once and keep the hand calculation in `tests/`.
3. Add tests: one per tool with expected values from the fixture; `consolidate` refuses an unapproved flagged mapping; `limit_test` at exactly 2.50x fails ("less than").
4. Add `debt_capacity` (room for the next deal, already in the `limit_test` output) to the verdict in `GET /deals/{id}/case`.
5. Make `POST /deals` accept two CSV uploads and a brief, using Eric's loader, so a judge can try an unseen input.
6. Make the SSE stream emit stage changes as well as audit rows.
7. Keep the trust-rule tests green on every merge.
8. Cut the demo video if the team agrees on one. Hyphenate wants a video that opens with the moment.
