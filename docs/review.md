# Review of the problem, the solution, and the research (2026-10-24, 01:00 to 02:30)

Written by Cayden's agent after reading every doc in `docs/`, the research, the sponsor notes, and the code, and after building the backend end to end.
Tags: [verified] means a file, a filing, or a test shows it. [inferred] means judgment.

## Is this a good problem?

Yes, with two honest caveats.

Why it is good:
- It has a hard check. Totals must tie and the ratio is arithmetic, so a judge can verify the output in seconds. Most finance-agent demos cannot say that. [verified: `tie_out`, `limit_test`]
- It has a real gate with a real clock. The lender tests the covenant on the combined company, the compliance certificate has a deadline, and the next add-on waits on it. [verified: `research/ma-workflow-research.md`, self-reported vendor sources]
- It has a real messy corner on real data. Two different charts of accounts from a filed deal, a filed reclassification table as an answer key, and one line that honestly holds three kinds of debt. [verified: Ex 99.1, Ex 99.2 Note 2 and Note 4(h), Ex 10.1]
- The moment is real and it works. Counting the whole "Financing liability" line gives 2.54x, over the limit; the agreement's own reading gives 0.76x. The controller's answer flips the verdict. [verified: `test_mapper_flags_the_financing_liability_and_effects_are_computed`]
- It fits every Hyphenate signal: a few roles done deep, limits enforced in code, a denied action in the log, precision over recall, and now a correction that becomes a policy. [verified: `hyphenate-workshop.md`]

Caveats:
- The user is unconfirmed. No practitioner has said the portfolio controller owns this work or wants it this way. The market scan was a handful of searches, and the closest products (Aleph, OneStream, Keboola) cover the consolidation layer without the covenant tie-out. [inferred; the research says so itself]
- The moment rests on two inferred inputs: the Statesville cash rent ($1,970K) and transaction costs at zero. If a practitioner sets the rent at a different figure, the naive ratio moves. It is still over 2.50x for any rent deduction above about $1.2K thousand... more precisely, the naive reading crosses the limit as long as covenant EBITDA stays below $28,782K, which holds unless an add-back above $403K is found, now that every add-back the filings quantify is applied. Say it out loud and keep the sensitivity in the pocket. [inferred from the figures]

## Is the solution right?

Mostly. Three design points were strengthened today:

1. Stateful agents. The original design said stateless, which the Hyphenate workshop lists as a weak signal ("memory that ends with the context window"). Agents now keep a session and the Mapper learns policies from the controller's answers. The second run asks nothing. The gateway writes the memory, so the trust story still holds. [verified: D12]
2. Numbers that cannot be faked. The gateway refuses a result whose EBITDA, debt, or leverage was not produced by a tool run in its run ids, not just a result without run ids. [verified: `test_model_made_number_is_refused_even_with_real_run_ids`]
3. Flag options with computed effects. The flag card never says "goes up". Each option shows the debt figure, the ratio, and the verdict from a real limit test, with a run id. [verified]

What is weaker than the docs suggested:
- The combined table is historical plus target. It does not apply the pro forma purchase accounting (goodwill, intangibles, inventory step-up). That is the cut list, and it should be said once in the honest-limits statement.
- The fiscal years differ by five months. The combined income statement adds a Kewaunee April year to a Nu Aire September year. The docs say it; the pitch must too.
- The Preparer and Reviewer are nearly mechanical. On a model backend they follow a fixed tool sequence. That is a feature for trust, but a judge may ask what the model adds there. The answer: the reasons, the reading of the brief, and the flags in the Mapper, which is where judgment lives.

## What the research got right and wrong

- Right: the Kewaunee pick. All five criteria hold, and the figures were available in four filings. [verified]
- Right: the covenant definition matters. The naive and covenant figures differ by 1.8x. [verified]
- Wrong in one place: the revolver draw and Kewaunee's depreciation were in the filings (Ex 99.2 Note 4(h) and the 10-K cash flow). They are loaded now. [verified]
- Missing: the covenant's transaction-cost and stock-compensation add-backs are not quantified in the pages read. Tri should check the 10-K for stock compensation (it is a named add-back) and the 8-K/A for transaction costs.

## What to add (ranked by value for the weekend)

1. The console on the new API. Everything else waits on it. (Josie)
2. One recorded model run (Anthropic first, Droid second) so the pitch can say the agent text came from a model at least once. (Cayden)
3. The second-run memory moment on stage: reset, run again, no flag, `policy:apply` in the log. It costs nothing and answers "did we see something new". (Cayden, Josie for the visible state)
4. The Note 2 answer-key score, as one number on the honesty slide. (Eric)
5. `debt_capacity` on the verdict line: "room for the next deal: $49M" is the line a PE associate hears. (Tri)
6. Judge-supplied input: `POST /deals` with two CSVs, so the system handles unseen input as the brief asks. (Tri, Eric)
7. A one-line statement for each sponsor: what the Droid SDK made possible (per-role sessions, `restrict_tools`, typed output), and what Figma made possible.

## What not to add

- Purchase accounting, intercompany eliminations, more deals, login, Postgres. All cut for the weekend, all roadmap.
- A staged denial. The log has real DENIED rows from the tests and from any agent that oversteps; show one only if asked.

## Open questions that need a human

See `STOCHASTIC.md` section 18. The three that matter most: a Hyphenate mentor on the seat, an Anthropic key, and the `droid` CLI install on the demo laptop.
