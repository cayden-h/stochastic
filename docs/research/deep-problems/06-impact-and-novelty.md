# Stochastic - impact and novelty scan

Written 2026-10-23 by a research agent.
Every claim is tagged "verified (URL)" or "inferred".
"Verified" means the URL was fetched, or a search summary of the URL said it.
Search-summary-only items are marked "(search summary)" because the page itself was not read.
Vendor claims are marked "self-reported".
Nobody has checked the practitioner-level points with a human reviewer yet.

## 1. Workflow map and where the pain is

Stage list is inferred from domain knowledge.
Sources are attached only where a page actually supports the point.

| Stage | What happens | Painful, slow, expert-heavy step | Evidence |
| --- | --- | --- | --- |
| Origination | Company or sponsor decides it needs capital and approaches advisers or funds | Choosing which funds fit a bespoke need | inferred |
| Diligence | Lender reads financials and existing debt documents | Reading cross-referenced covenants and amendment language takes days per agreement | verified, self-reported (https://www.hebbia.com/resources/credit-agreement-software) |
| Structuring | Build the mix of senior, junior, preferred | Every tranche changes cost, dilution, risk, and which consents are needed | verified (https://www.mayerbrown.com/en/insights/publications/2026/10/the-rise-of-private-capital-capital-solutions-and-the-new-architecture-of-credit) |
| Capacity check | Test the plan against ratio tests and baskets in the existing agreement | Failing a ratio test is a closed door, but a basket may still allow the debt | verified (https://www.creditgpt.com/content/how-to-think-about-debt-baskets, https://9fin.com/insights/the-debt-covenant--part-2--the-art-of-basket-weaving-9fin-educational) |
| Term sheet and lender negotiation | Compare offers, negotiate price and terms | Comparing all-in cost (fees, PIK, warrants) across offers | inferred |
| Documentation | Draft and negotiate the new agreement and intercreditor | Standstill length and payment blockage are the most negotiated intercreditor points | verified (https://www.lowenstein.com/news-insights/publications/articles/negotiating-an-intercreditor-agreement-an-art-and-a-science-december-2023-citron-turman-caporale, search summary) |
| Consents | Existing lenders must approve some steps | The agent first decides if a request needs majority or unanimous consent, then runs the vote | verified (search summary of loan agreement exhibits: https://www.sec.gov/Archives/edgar/data/0001366649/000095012310092775/a57545exv99w3.htm) |
| Closing | Conditions precedent, funds flow | Checklist tracking | inferred |
| Covenant monitoring | Compliance certificates, maintenance tests | Spreadsheet and email tracking | verified, self-reported (https://www.hebbia.com/resources/credit-agreement-software, https://www.ontra.ai/blog/ontra-introducing-insight-for-credit/) |
| Waivers and amendments | Borrower breaches or needs relief, lenders price it | Pricing the relief: fees and spread step-ups | verified, weak sources (https://ibinterviewquestions.com/guides/restructuring-investment-banking/amendments-and-waivers-first-line-of-defense, https://octus.com/resources/articles/covenants-101-amendment-and-waiver-provisions-in-european-leveraged-loans/, search summaries) |
| Restructuring and liability management | Amend and extend, PIK, uptiers, drop-downs | Designing a deal lenders accept; lenders drafting protections | verified (https://9fin.com/insights/q1-2026-lme-update, https://www.ropesgray.com/en/insights/alerts/2026/02/distressed-debt-legal-insights-2025-takeaways-and-2026-outlook, search summaries) |

Timing note.
Straightforward direct loans reportedly take about 2 to 4 weeks from commitment to close, longer for complex deals.
Verified as marketing and practitioner commentary only, not a survey (https://www.abfjournal.com/the-speed-premium-quantifying-private-credits-execution-advantage-in-middle-market-transactions/, search summary).

## 2. Proposed extra problems (9)

Hyphenate's four questions are shortened to: Real, Hire, New, Moment.
Impact and feasibility are 1 to 5, my judgment (inferred).

### P1. Answer-key eval harness
- Problem: nobody can tell if the clause-reader catches the traps. Hyphenate wants an answer key and a score.
- Who feels it: the reviewer, who needs to trust the catch rate.
- Why agents help: a second agent plants traps and scores the first, so the demo ends with "caught 7 of 8, missed 1, here is why".
- Data: a real credit agreement from EDGAR exhibits (to verify it is usable) with our own planted edits and a key.
- 36-hour demo: yes, very. Impact 4, feasibility 5.
- Fit: Real yes, Hire yes (precision matters, the workshop said so), New medium, Moment medium (a score on stage).
- Source for the workshop wanting this: `hyphenate-workshop.md` in this folder (verified there).

### P2. Consent and waiver pathway
- Problem: when the plan is blocked, the choices are redesign (already in core), or ask existing lenders for a consent. The agent should work out which vote threshold applies, which lenders are pivotal, what it will likely cost (fee, spread), and draft the consent request.
- Who feels it: the borrower CFO and the deal team. Required Lender thresholds are typically 50.1 percent, sometimes 66.67 percent, and unanimity for protected terms (verified, search summary: https://www.sec.gov/Archives/edgar/data/0001366649/000095012310092775/a57545exv99w3.htm).
- Why agents help: it reads the amendments clause, does the vote arithmetic in code, and compares "redesign" against "ask for consent" on cost.
- Data: the amendments section of the same credit agreement, a synthetic lender holder list (labeled synthetic), fee ranges as labeled assumptions.
- 36-hour demo: yes. Impact 4, feasibility 4.
- Fit: Real yes, Hire yes, New yes (most tools extract and flag, few price the way out), Moment yes (the agent finds a second path and the reviewer chooses).
- Fee ranges found are weak: 25 to 100 bps for fees and 50 to 100 bps for spread, from secondary sites, so keep them as ranges (verified as weak: the ibinterviewquestions and abfjournal pages above).

### P3. Term sheet normalization and bid comparison
- Problem: lender offers differ in coupon, PIK, OID, fees, warrants, call protection, covenants. Raw coupons are not comparable.
- Who feels it: the borrower and the placement agent.
- Why agents help: extract terms into one schema, compute all-in cost and dilution in code, then feed each into the Monte Carlo.
- Data: 2 or 3 synthetic term sheets built from instrument ranges in `research.md`.
- 36-hour demo: yes. Impact 3, feasibility 5.
- Fit: Real medium (synthetic offers), Hire yes, New low to medium, Moment low.

### P4. Cross-document conflict detector (term sheet vs credit agreement vs intercreditor)
- Problem: the new instrument can conflict with the existing agreement: lien priority, payment blockage, consent rights, transfer limits. Mayer Brown names intercreditor dynamics, consents under existing facilities, and change of control as where capital solutions deals get stuck (verified: https://www.mayerbrown.com/en/insights/publications/2026/10/the-rise-of-private-capital-capital-solutions-and-the-new-architecture-of-credit).
- Who feels it: counsel and the senior reviewer.
- Why agents help: it matches clauses across documents and cites both. This is the Hyphenate "sources that disagree" requirement, made concrete.
- Data: an existing agreement plus a drafted term sheet and a short intercreditor excerpt.
- 36-hour demo: partly. A pair of conflicting clauses is feasible. Full intercreditor review is not. Impact 4, feasibility 3.
- Fit: Real yes, Hire yes, New yes, Moment yes.

### P5. Conformed-agreement builder (original plus amendments)
- Problem: the operative text is the original agreement modified by several amendments. Ontra's page says the pain is finding the latest agreement "including the most recent amendments" (verified: https://www.ontra.ai/blog/ontra-introducing-insight-for-credit/). The page does not claim amendment functionality.
- Who feels it: anyone reading the agreement.
- Why agents help: apply amendment text to the base clause and show the current definition.
- Data: EDGAR filings usually include amendments as separate exhibits (inferred, to verify on the chosen company).
- 36-hour demo: yes for one or two amendments. Impact 3, feasibility 4.
- Fit: Real yes, Hire yes, New low to medium, Moment medium (a definition changed by amendment makes the plan legal or illegal).
- Best folded into core problem 1 as a trap rather than built separately.

### P6. Stress-path option generator (amend-and-extend, PIK toggle, equity cure)
- Problem: when the Monte Carlo shows a bad tail, the reviewer wants alternatives that avoid default.
- Who feels it: the borrower and its lenders. Private credit defaults hit a record 6 percent in the 12 months to April 2026 (Fitch, reported by Bloomberg Law, verified: https://news.bloomberglaw.com/bankruptcy-law/us-private-credit-defaults-hit-new-record-of-6-in-april-fitch), and more than half came from interest deferrals and PIK.
- Why agents help: enumerate relief tools, re-run the seeded simulation, rank by cost and tail risk.
- Data: the same simulation engine and the cost table.
- 36-hour demo: yes if core problem 3 exists. Impact 4, feasibility 3.
- Fit: Real medium, Hire yes, New medium, Moment yes.
- Caution: this drifts toward after-close restructuring, which the 2026-10-23 decision excluded. Keep it inside the live deal as "what if the tail case happens before close".

### P7. Pro forma covenant headroom
- Problem: does the proposed structure leave enough headroom on each maintenance test across the next quarters?
- Who feels it: the borrower treasury team.
- Why agents help: compute headroom per path in the simulation and warn when a path breaches.
- Data: the covenant definitions plus the model.
- 36-hour demo: yes, as an output of the simulation. Impact 3, feasibility 4.
- Fit: Real yes, Hire yes, New low (crowded, see section 3), Moment low.
- Treat as a chart in the simulator, not a standalone product.

### P8. Lender outreach and process tracker
- Problem: shortlisting lenders by mandate, sending teasers, tracking responses.
- Who feels it: the placement agent. The Buyers Edge case used a placement agent (verified in `research.md`: https://www.williamblair.com/News/Buyers-Edge-Platform-and-Atlantic-Park-Fund-Transaction).
- Why agents help: drafting and tracking.
- Data: a lender database. We have none that is real, so it would be synthetic.
- 36-hour demo: weak. Impact 3, feasibility 2.
- Fit: Real low, Hire medium, New low, Moment low.

### P9. Reviewer rejection to learned policy with backtest
- Problem: today a rejection is just noted. Hyphenate wants a rejection turned into a general policy, with evidence, backtested, approved by a controller (verified in `hyphenate-workshop.md`).
- Who feels it: the senior reviewer, who stops repeating the same corrections.
- Why agents help: search past deals in Postgres for precedents, propose a rule, show which past decisions it would have changed.
- Data: a seeded table of 10 to 20 past deals and decisions (synthetic, labeled).
- 36-hour demo: yes. Impact 4, feasibility 3.
- Fit: Real medium, Hire yes, New yes, Moment yes.
- This likely belongs to core problem 4. List it here so it is not dropped.

## 3. Novelty check

All vendor facts are self-reported unless stated.

Already common (many products):
- Credit agreement abstraction and covenant extraction.
  - Hebbia lists credit agreement analysis for private credit (self-reported: https://www.hebbia.com/blog/how-private-credit-teams-use-hebbia, https://www.hebbia.com/resources/credit-agreement-software).
  - Ontra Insight for Credit abstracts and categorizes covenants, compares terms against past agreements, tracks obligations and alerts; no performance figures given (verified page, self-reported: https://www.ontra.ai/blog/ontra-introducing-insight-for-credit/).
  - V7 Go claims review time per agreement fell from 4 to 6 hours to 30 to 45 minutes (self-reported, relayed by Hebbia: https://www.hebbia.com/resources/credit-agreement-software).
  - The Hebbia page also names Cardo AI, CovenantIQ, Sirion, Finley (acquired by Concord in February 2026 per that page), and Moody's Lending Suite.
- Covenant monitoring for lenders.
  - Levocred AI, YC S26: continuous covenant monitoring, borrowing base reports, IC memos; claims more than $500M monitored across 10+ facilities, a two-person team, one named early customer (self-reported: https://yespress.io/levocred-ai-yc-s26).
  - CovenantIQ and FutureSight (a pre-launch company hiring a CEO, translating ERP data into covenant logic and compliance certificates) appear in a search summary (search summary: https://assist-software.net/project/covenant, https://www.careerbuilder.com/job-details/co-founder-ceo-ai-for-credit-and-finance-boston-ma--24dd0138-2b75-4d47-9c5a-b67dffbfbe6e).
  - Cardo AI covenant tracking and stress testing for asset-based finance; $15M Series A in November 2024 co-led by Blackstone (self-reported, search summary: https://yespress.io/cardo-ai).
- General finance agents.
  - Anthropic's May 2026 financial agents include credit memo drafting, ratio calculation, and flagging covenant breaches (secondary, search summary: https://www.analyticsvidhya.com/blog/2026/05/claude-finance-solutions/).
  - Rogo and Hebbia are general financial AI platforms with strong revenue claims (secondary, search summary: https://cryptobriefing.com/rogo-arr-triples-50m-surpasses-hebbia/).
  - Kira, Luminance, Harvey, Legora do contract extraction, drafting, and Q&A (secondary, search summary: https://www.hostinger.com/ph/tutorials/best-legal-ai-tools/). None was shown to focus on credit agreements.
- Credit document intelligence from Octus and Covenant Review (secondary, search summary: https://workwisesolutions.org/guides/ai-credit-agreement-covenant-review.html). That site is a consultant guide, so weak.

Looks open (no product found in these searches, absence of evidence only, searches were shallow):
- Borrower-side or structuring-side agents that build the capital stack and test it against the existing agreement. Searches for AI capital structure optimization returned only startup venture debt explainers.
- Consent and waiver pathway planning with vote math and pricing. Ontra's page does not mention waivers (verified).
- Term sheet normalization across lender offers. Ontra compares terms against past agreements, which is close but not offers.
- Cross-document conflict detection with an intercreditor. Nothing found.
- Agents with a logged approval gate and learned policies. Not searched for beyond the above, so treat as unknown.
- The search tool is weak. Expect that some products exist that we did not find, so claim "we did not find" and never "nobody does this".

Honest read (inferred): covenant monitoring and abstraction is the crowded half of the field.
The open half is acting on what the documents say: finding the path around a blocker, pricing it, and routing it for approval.
That matches our existing hero moment.

## 4. Ranking and recommendation

Score is impact times feasibility (inferred).

| Rank | Proposal | Score |
| --- | --- | --- |
| 1 | P1 Answer-key eval harness | 20 |
| 2 | P2 Consent and waiver pathway | 16 |
| 3 | P3 Term sheet normalization | 15 |
| 4 | P4 Cross-document conflict detector | 12 |
| 4 | P5 Conformed-agreement builder | 12 |
| 4 | P6 Stress-path option generator | 12 |
| 4 | P7 Pro forma headroom | 12 |
| 4 | P9 Rejection to learned policy | 12 |
| 9 | P8 Lender outreach | 6 |

Recommended additions to the core four:
1. P1 Answer-key eval harness. It is cheap, and Hyphenate asked for it.
2. P2 Consent and waiver pathway. It extends the hero moment: the agent finds two ways out and prices both.
3. P4 Cross-document conflict detector, scoped to one term sheet clause against one credit agreement clause. It scores lower than P3 on the raw numbers but wins on "did we see something new" and "sources that disagree". Fold P3's all-in cost table into core problem 2 instead of building it as its own agent.
- Fold P5 into core problem 1 as a trap, P7 into core problem 3 as a chart, and P9 into core problem 4.
- Keep P6 as a stretch only if the simulator is done early.

Avoid:
- A standalone covenant monitoring dashboard. Crowded, and the team decided there is no after-close monitoring.
- P8 lender outreach. No real lender data, and it looks like a CRM.
- Final legal drafting of full loan documents. It invites a "would a lawyer sign this" test we cannot pass.
- Any claim of real lender pricing or real fund behavior. Use labeled ranges.
- Adding more agents than the core four plus a scorer. The workshop warned about ten shallow roles (verified in `hyphenate-workshop.md`).

## 5. Value at stake (cited only)

- Private credit assets under management: about $2T by May 2026, projected $3.4T by 2030, over $240B raised in 2025 (self-reported estimates in Mayer Brown, verified: https://www.mayerbrown.com/en/insights/publications/2026/10/the-rise-of-private-capital-capital-solutions-and-the-new-architecture-of-credit).
- Stress: Fitch's record 6 percent default rate for the 12 months to April 30, 2026, 99 default events, more than half from interest deferrals and PIK (secondary, via Bloomberg Law, verified: https://news.bloomberglaw.com/bankruptcy-law/us-private-credit-defaults-hit-new-record-of-6-in-april-fitch).
- Moody's: 4 percent default rate for 607 borrowers in the 12 months to June 2026, rising to 5.8 percent when PIK amendments and distressed maturity extensions count (secondary, search summary: https://www.moodys.com/web/en/us/site-assets/risk-assessments-within-private-credit.pdf).
- Houlihan Lokey: borrowers under $100M EBITDA at 3.0 percent size-weighted default in Q2 2026 (self-reported by an adviser, search summary: https://hl.com/about-us/newsroom/houlihan-lokey-finds-that-stress-among-the-smallest-private-credit-borrowers-has-climbed-more-than-tenfold-since-2023/).
- Amendment volume: 47 liability management exercises tracked in 2025, 37 with an uptier (Covenant Review via Ropes & Gray, secondary, search summary: https://www.ropesgray.com/en/insights/alerts/2026/02/distressed-debt-legal-insights-2025-takeaways-and-2026-outlook). Lincoln International reports 26 percent of tracked amendments included a sponsor infusion (secondary, date unclear, search summary: https://cdn.lincolninternational.com/wp-content/uploads/Perspective_LME-Predictions-and-Strategies.pdf).
- Time cost: 62 percent of teams lose four or more days per deal to manual re-checks (Hebbia's own research, self-reported: https://www.hebbia.com/resources/credit-agreement-software).
- Amendment pricing: fees of 25 to 100 bps and spread increases of 50 to 100 bps (weak secondary sources, search summaries).
  - Illustration, inferred arithmetic only: a 50 bps fee on a $200M loan is $1M. A 75 bps spread step-up on $200M is $1.5M a year. These are our numbers, not sourced figures.
- Not found: any sourced total of annual advisory or legal spend on special-situations structuring, or any cited total cost of waivers. Do not state one.
- One unverified claim to avoid: "80 percent or more of covenant violations end in amendments" came from an unverified secondary page (search summary: https://altstreet.investments/reference/mechanics/covenant-breaches).

## Gaps

- No practitioner has confirmed the stage map.
- Searches were broad and shallow. Several results were vendor or SEO pages.
- Not read in full: Lincoln, Moody's, Houlihan Lokey, Ropes & Gray, 9fin LME pages.
- Next check: confirm that the chosen company's EDGAR exhibits include amendments, and ask a reviewer which of P2 and P4 they would actually pay for.
