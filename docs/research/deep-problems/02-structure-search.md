# Deep problem 2 - Searching for feasible, good debt and equity mixes

Written 2026-10-23 for the Stochastic team (Cal Hacks 13.0, Hyphenate track).
Every claim is labeled "verified (URL)" or "inferred".
"Verified" here means a page I read or a search summary of that page said it, not that the number is market-accurate.
Almost all sources below are secondary (glossaries, blogs, law-firm notes).
Treat every number as a ballpark input to be stored as a labeled assumption with a range.
Secondary sources are flagged "[secondary]".
Where my searches found nothing, the text says so.

## 0. Summary of the recommendation

- Search by constrained enumeration on a coarse grid, then a Pareto filter, then Monte Carlo on the shortlist only. (inferred)
- Keep OR-Tools CP-SAT as an optional second engine, not the main one. (inferred)
- The deal math is a pure deterministic function: structure in, metrics out.
  The LLM never computes a number.
- A blocked plan is a logged denied action that cites the clause.
  The revised plan is the same search re-run with that clause added as a hard constraint.
- The biggest naive point in the model: instrument prices are not constants.
  They depend on how much leverage sits in front of the tranche and on the deal's terms.
  See section 5.

## 1. The capital stack

Priority is from first paid to last paid in a payout.
The "typical size" column is a range from secondary sources and applies to leveraged buyout style deals, not to every special-situations deal.

| Rank | Instrument | Cost (ballpark) | Core rights | Typical size |
| --- | --- | --- | --- | --- |
| 1 | Senior secured (first lien term loan, revolver, unitranche) | Lowest. Direct lending new-issue all-in yield about 9.3 percent in 2025 | First-priority lien on collateral. Maintenance covenants (leverage, coverage). Consent rights over new debt and liens. Cash interest, scheduled amortization | About 3 to 5x EBITDA |
| 2 | Second lien | About SOFR + 650 to 1000 bps (two sources disagree on the top end) | Second-priority lien. Bound by an intercreditor agreement: standstill, limited enforcement | About 0.5 to 1.5x EBITDA |
| 3 | Mezzanine / subordinated notes | 12 to 16 percent all-in (cash plus PIK), one source says up to 18 to 20. Often with warrants. Fees about 1 to 3 percent | Usually unsecured and contractually subordinated. Cash coupon plus PIK. Warrants or equity kicker. Light covenants | About 0.5 to 1.5x EBITDA |
| 4 | Convertible debt | Coupon below straight debt, because the holder owns an option | Debt claim plus right to convert into shares at a conversion price set above the current share price | Deal specific |
| 5 | Preferred equity | 15 to 25 percent gross IRR in capital-solutions deals. Older glossary says 8 to 15 percent | Equity security, not debt. Liquidation preference, dividend (cash or PIK), step-ups on non-payment, governance and consent rights, redemption or exit mechanics | Variable. A glossary gives 5 to 10 percent of total capital in an LBO |
| 6 | Common equity | Highest, no contractual return | Residual claim, votes, last in the payout | The plug. Whatever is left |

Evidence per row:

- Senior sizing 3 to 5x EBITDA, total LBO leverage 5 to 6x when mezzanine fills the gap, second lien 0.5 to 1.5x, mezzanine 0.5 to 1.5x, preferred 8 to 15 percent.
  [secondary] verified (https://ibinterviewquestions.com/blog/mezzanine-debt-preferred-equity-explained, via search summary, the page itself returned HTTP 403 to my fetch).
- Worked mezzanine example: $50M EBITDA company, mezzanine 1.5x, total debt about 6.1x, mezzanine priced 12 to 16 percent with cash and PIK parts.
  [secondary] verified (https://pipelineroad.com/glossary/mezzanine-debt, search summary).
- Ranking: second lien is secured with second-priority claim, mezzanine is usually unsecured and subordinated, preferred sits below all debt and is an equity security.
  [secondary] verified (https://vectorshift.ai/glossary/second-lien, https://altss.com/glossary/second-lien, https://altss.com/glossary/mezzanine-debt.md, search summaries).
- Senior 45 to 60 percent, mezzanine 10 to 20 percent, preferred 5 to 10 percent of capital in an LBO.
  [secondary] verified (https://angelinvestorsnetwork.com/alternative-investments/mezzanine-financing-private-credit-hybrid-debt-explained, search summary).
  Note that several hits in the same search were real estate sources and I excluded them, because that market has different ratios.
- Second-lien spread over first lien was 335 bps in 2021 and 388 bps in 2018.
  This is old and not current pricing.
  [secondary] verified (https://www.spglobal.com/market-intelligence/en/news-insights/articles/2021/2/second-lien-resurgence-reflects-risk-on-wave-in-leveraged-loan-market-62838752, search summary).
- Recovery in a default: first lien about 70 to 80 cents on the dollar historically, second lien about 30 to 45 cents with a 10 to 60 range, and second-lien recovery is very sensitive to enterprise value.
  [secondary] verified (https://www.abfjournal.com/where-the-risk-sits-a-verified-look-at-subordinate-debt-recovery-rates-and-intercreditor-dynamics-in-the-middle-market/, search summary).
- Mezzanine 8 to 12 percent cash plus 2 to 4 percent PIK plus warrants, and second lien at SOFR + 750 to 1000, come from the earlier log.
  [secondary] verified (see `../research.md`, instruments table, sources are glossaries and law-firm notes).
- Capital solutions: bespoke hybrid instruments between debt and equity, target 15 to 25 percent gross IRR versus 8 to 12 percent for conventional lending, and 20 percent or more in stressed situations.
  Instruments listed: preferred equity (PIK, cash-pay, hybrid), structured equity, holdco PIK, convertibles, stretched senior, mezzanine, second lien.
  Governance and information rights matter more than financial maintenance covenants.
  Key issues are intercreditor dynamics, consents under existing facilities, anti-dilution, change of control.
  verified (https://www.mayerbrown.com/en/insights/publications/2026/10/the-rise-of-private-capital-capital-solutions-and-the-new-architecture-of-credit, as logged in `../research.md`).
  This is a law firm, so it is a secondary source for pricing.
- Pref dividends are not tax deductible, and debt interest generally is.
  [secondary] verified (`../research.md`, glossary sources).
- Convertibles carry lower coupons than comparable straight bonds because of the embedded option.
  Conversion price is set above the current share price.
  Examples: a 2.879 percent coupon with roughly 55 percent premium, a 50 percent premium on a zero-coupon note.
  [secondary] verified (https://ryanoconnellfinance.com/convertible-bonds/, https://www.globalcapital.com/article/28my0v4z4k0g9vun23chs/equity-linked/convertibles-thrill-with-windfall-terms-will-issuers-take-notice, search summaries).
  These are public-market convertibles, not private-company deals, so use as shape only.
- Participating versus non-participating preferred:
  non-participating holder takes the preference or the as-converted value, whichever is larger.
  Participating holder takes the preference and then shares in the rest.
  Capped participation stops at a multiple of the preference.
  [secondary] verified (https://www.crv.com/content/liquidation-preference, https://vcbeast.com/compare/liquidation-preference-vs-participation-rights, https://microventures.com/liquidation-preferences-explained, search summaries).
  These are venture-capital sources.
  The mechanics carry over, the pricing does not.
- PIK dividend mechanics in preferred charters: unpaid dividends cumulate as additional shares, PIK shares are valued at the liquidation preference, holders get the preference plus accrued unpaid dividends, and dividends stop accruing at redemption unless the company fails to pay.
  verified (SEC exhibits from late 1990s and early 2000s, for example https://www.sec.gov/Archives/edgar/data/0001044269/000091205702027384/a2084294zex-10_7.txt). Old charters, so use as mechanics only.
  I found no current private-credit preferred term sheet.
- Common equity rights and priority (residual claim, last in payout): inferred.
  No source retrieved, but this is standard.
- Step-up on non-payment for preferred, and governance rights on non-payment: [secondary] verified in `../research.md` (remedies are contractual, non-payment usually triggers step-ups or governance rights).
  I did not find a source with the size of the step-up.
  Do not invent one.
- Intercreditor mechanics: senior lenders can block payments on junior debt for about 90 to 180 days on a non-payment default and indefinitely on a senior payment default.
  Standstill periods run about 90 to 365 days.
  Lien-only subordination differs from debt subordination.
  [secondary] verified (https://www.bassberry.com/news/intercreditor-subordination-agreements-mezzanine-financing/, https://blakes.com/insights/intercreditor-agreements-key-areas-of-negotiation, search summaries).

Pricing conflict to note in the model: preferred equity is 8 to 15 percent in the glossary and 15 to 25 percent in Mayer Brown.
The newer, special-situations source fits our deal type better.
Store a low, base, and high value for each instrument and let the user override them.
This choice is inferred.

## 2. Deterministic deal math specification

All of this is pure functions with no randomness and no LLM.
The Monte Carlo layer feeds in scenario paths (EBITDA, SOFR) and calls the same functions.
Use integer cents or Decimal for money, so tests are exact.
Annual periods are used below for clarity.
Real agreements test quarterly on a trailing-four-quarter basis. (Minimum EBITDA covenants are "typically measured quarterly on a trailing twelve month basis": verified [secondary] https://mcdonaldhopkins.com/insights/news/Understanding-financial-covenants-in-loan-document.)
Generalize by using the period accrual fraction (for example 0.25, or actual days over 360 for SOFR loans, which is inferred).

### 2.1 Sources and uses

Let tranche i have face amount x_i, upfront fee rate f_i, and original issue discount rate o_i.

- Sources = sum of x_i over all tranches, plus common equity raised, plus cash from the balance sheet used.
- Uses = purchase price or other purpose + refinanced debt + sum of f_i * x_i + sum of o_i * x_i + transaction expenses + cash to balance sheet (the plug).
- Hard check: Sources = Uses to the cent.
  Cash to balance sheet must be at least the minimum cash input (this also feeds liquidity tests).
- OID is a use at face value: the company receives x_i * (1 - o_i) but owes x_i.

### 2.2 Interest, cash and PIK

For each debt tranche i, opening balance B_{i,t-1}:

- Floating rate: r_t = max(SOFR_t, floor_i) + spread_i.
  Fixed-rate tranches use the stated coupon.
- Cash interest_t = B_{i,t-1} * (r_t^cash) * accrual.
- PIK interest_t = B_{i,t-1} * (r^pik) * accrual.
- Closing balance: B_{i,t} = B_{i,t-1} + PIK interest_t - scheduled amortization_t - cash sweep_t.
- Use the opening balance for interest, so there is no circularity with the sweep. (Design choice, inferred.)
- Total debt service_t = cash interest_t + scheduled amortization_t.
- All-in yield including fees over a life of N years, simple approximation: y_i = r_i^cash + r_i^pik + (f_i + o_i) / N. The exact value is the IRR of the tranche cash flows.
  Store both. (inferred)

### 2.3 Preferred equity

Let A_t be the accreted liquidation preference.
A_0 = invested amount.

- Dividend rate d_t = d_0 + stepup * 1[trigger_t], where triggers are configured per instrument (missed cash dividend, covenant default, passing a date).
  Step-up size and triggers are inputs, not facts.
- Cash portion c in [0, 1].
  Cash dividend_t = A_{t-1} * d_t * c * accrual.
- PIK portion: A_t = A_{t-1} * (1 + d_t * (1 - c) * accrual), with compounding at the dividend period.
- Missed cash dividend: the unpaid amount is added to A_t and the step-up trigger fires.
- Redemption or exit claim at time T = max(A_T * (1 + premium_T), MOIC_floor * A_0) where premium and MOIC floor are optional terms.
- Pref dividends are not tax deductible.
  Cash dividends are fixed charges in many FCCR definitions and are often restricted payments (see 2.7).
- Convertible pref: holder gets max(A_T, as-converted value) if non-participating, or A_T plus as-converted share of the remainder if participating (capped versions limit the sum).

### 2.4 Payout waterfall in a downside

Inputs: enterprise value EV at the event date, balance sheet cash, liquidation or process cost rate k, claim amounts at the event date.

1. Distributable value D = EV * (1 - k) + excess cash. (Simplification: collateral value split by lien is ignored in v1.)
2. Claims in order: (a) super-priority items such as an asset-based revolver if modeled, (b) first lien (existing facility plus new senior, pari passu, so pro rata), (c) second lien, (d) mezzanine and unsecured subordinated debt, (e) preferred, (f) common.
3. For class k with claim C_k and remaining value R_k: payout_k = min(C_k, R_k).
   R_{k+1} = R_k - payout_k.
4. Within a class, pro rata: payout to holder j = payout_k * C_{k,j} / C_k.
5. Claim C_k = principal after PIK and amortization + accrued unpaid interest + prepayment premium.
   For preferred, C = A_T (plus premium if configured).
6. Recovery rate_k = payout_k / C_k.
   Common gets the remainder.
7. With conversion or warrants in the money, run the waterfall on the as-converted basis where it improves the holder's payout (non-participating conversion).
   Compute with a fixed-point loop or by comparing both cases per holder.

This is the strict absolute priority rule.
It is a model simplification, not what always happens (see section 5).

### 2.5 Ratios and tests

Definitions (every one must be overridable by what the credit agreement says, since "covenant definitions are negotiated", per https://www.lawinsider.com/dictionary/total-coverage-ratio and the McDonald Hopkins page above, both [secondary]):

- Total leverage = Total Debt / EBITDA.
  A sample agreement caps it at 4.5x trailing four quarters, stepping down over time. verified [secondary] (search summary of https://investors.livenationentertainment.com/sec-filings/annual-reports/xbrl_doc_only/293).
- Senior secured (first lien) leverage = secured first-lien debt / EBITDA.
  Different debt types use different ratio tests. verified [secondary] (https://www.creditgpt.com/content/how-to-think-about-debt-baskets, as logged in `../research.md`).
- Net variants: (Debt - cash) / EBITDA with a cap on cash netting if the agreement says so.
  The cap is inferred.
- Interest coverage = EBITDA / cash interest expense.
  A sample floor is 2.75x trailing four quarters. verified [secondary] (Live Nation filing summary above).
- Fixed charge coverage (generic) = (EBIT + fixed charges) / (interest + fixed charges).
  Credit-agreement versions are usually (EBITDA - capex - cash taxes) / (cash interest + scheduled principal + cash preferred dividends + rent).
  The generic form is verified [secondary] (https://www.wallstreetprep.com/knowledge/fccr-fixed-charge-coverage-ratio/, https://mcdonaldhopkins.com/insights/news/Understanding-financial-covenants-in-loan-document). The credit-agreement form is inferred, so take the real formula from the clause.
- Debt-like treatment of preferred: whether redeemable preferred counts in Total Debt is a definitional flag (include_pref_in_debt).
  Mandatorily redeemable preferred is often treated as debt (inferred, check with a practitioner).
  This flag is the planted trap in the worked example.
- Pro forma EBITDA: add acquired EBITDA, subject to any cap on synergies and add-backs from the clause (inferred).
- Maintenance test: check metric_t against limit_t at each test date, using the limit schedule (step-downs).
- Incurrence test: check once at closing, on a pro forma basis, as a condition to taking the new debt.
  Failing is "a closed door, not a default" and the borrower may still use a basket that does not depend on the ratio. verified [secondary] (https://www.creditgpt.com/content/how-to-think-about-debt-baskets, https://9fin.com/insights/the-debt-covenant--part-2--the-art-of-basket-weaving-9fin-educational, as logged in `../research.md`).
- Debt baskets: capacity map by basket (amount, entity, lien status, priority).
  Usage_b = sum of tranche amounts assigned to basket b.
  Test Usage_b <= Cap_b (fixed dollar, or the greater of a dollar amount and a percent of EBITDA, a grower basket, which is inferred as a common form).
- Headroom for a max-type limit L: headroom = (L - actual) / L. Equivalent EBITDA cushion = 1 - (Debt / L) / EBITDA.
- Every test returns a record: {clause_id, metric, actual, limit, pass, headroom, source_span}. The record is what the reviewer and the audit log see.

### 2.6 Dilution

Let S_0 be the existing fully diluted share count.

- Penny warrants granting fraction w of the post-exercise fully diluted equity: new shares N_w = S_0 * w / (1 - w).
- Warrants with strike K at price P: net shares by the treasury method = N_w * (1 - K / P) when P > K, else 0. (inferred, standard)
- Conversion of preferred or convertible debt: new shares N_c = A_T / conversion_price, where A_T includes accreted PIK.
- Fully diluted total = S_0 + N_w + N_c + new common issued.
  Ownership of group g = shares_g / total.
- Dilution to existing holders = 1 - S_0 / total.
- Value cost of warrants is not just percent ownership.
  It is an option value, which needs an equity value and a volatility. v1 uses percent ownership at a fixed equity value input.
  State that in the UI.

### 2.7 Tests that block a plan (clause library)

The planner must evaluate at least:

- Incurrence ratio test for new debt (total or first-lien leverage, pro forma).
- Debt basket capacity and which basket the tranche uses.
- Lien capacity (can the new tranche be secured, and at what priority).
- Restricted payments: cash dividends on preferred or warrants/equity payments may be restricted, so a cash-pay pref can be blocked while a PIK pref is allowed (inferred, a common structure, practitioner check).
- Maturity: new junior debt may need to mature after the existing term loan (inferred).
- Consent requirements and intercreditor terms (consent is a path, not just a block: it costs time and a fee).
- Debt-like treatment of preferred (flag above).
- Maintenance covenants over the horizon (done by the simulator).
- Lender and investor eligibility and check sizes (section 3).

### 2.8 Worked example for a unit test

These are test fixtures I made up for arithmetic, not market data and not Buyers Edge terms.
All amounts are in $M.

Inputs:

- LTM EBITDA = 50.
  Capex = 5.
  Cash taxes = 4 (given, not computed).
- Existing first-lien term loan stays in place: 60, cash rate 7.5 percent, amortization 1 percent of face per year (0.6).
- New senior (first lien, pari passu with existing): 50, cash rate 8.0 percent, amortization 1 percent (0.5), fee 2 percent.
- Junior (mezzanine): 30, cash 11 percent, PIK 3 percent, fee 3 percent.
- Preferred: 20, 12 percent dividend, fully PIK, compounding annually, fee 2 percent.
- Purchase price = 95.
- Covenant: total leverage incurrence and maintenance limit 3.0x.

Expected outputs:

| Quantity | Formula | Value |
| --- | --- | --- |
| Sources | 50 + 30 + 20 | 100.0 |
| Fees | 0.02*50 + 0.03*30 + 0.02*20 = 1.0 + 0.9 + 0.4 | 2.3 |
| Uses | 95 + 2.3 + cash to balance sheet | 97.3 + 2.7 = 100.0 |
| Blended new-money cost, cash plus PIK | (50*0.08 + 30*0.14 + 20*0.12) / 100 = (4.0 + 4.2 + 2.4) / 100 | 10.60 percent |
| Blended with fees over 5 years, simple | 10.60 + 2.3/100/5 | 11.06 percent |
| After-tax blended cost at 25 percent tax on deductible parts | (4.0*0.75 + 4.2*0.75 + 2.4) / 100 | 8.55 percent |
| Year-1 cash interest | 60*0.075 + 50*0.08 + 30*0.11 = 4.5 + 4.0 + 3.3 | 11.8 |
| Year-1 junior PIK | 30*0.03 | 0.9 (balance 30.9) |
| Year-1 pref accretion | 20*1.12 | 22.4 |
| Total debt at close | 60 + 50 + 30 | 140.0 |
| Total leverage at close, pref not counted | 140 / 50 | 2.80x (pass, limit 3.0x) |
| Headroom | (3.0 - 2.8) / 3.0 | 6.667 percent |
| EBITDA at which the test breaks | 140 / 3.0 | 46.667 (cushion 6.667 percent) |
| First-lien leverage at close | 110 / 50 | 2.20x |
| Total leverage with redeemable pref counted | (140 + 20) / 50 | 3.20x (FAIL, limit 3.0x) |
| EBITDA needed to pass that case | 160 / 3.0 | 53.333 |
| Interest coverage | 50 / 11.8 | 4.2373x |
| FCCR (credit-agreement form) | (50 - 5 - 4) / (11.8 + 0.6 + 0.5) = 41 / 12.9 | 3.1783x |
| Year-1-end debt | (60 - 0.6) + (50 - 0.5) + 30.9 | 139.8 (2.796x) |
| Year-1-end claims for waterfall | first lien 108.9, junior 30.9, pref 22.4 | total 162.2 |

Waterfall checks at the year-1-end claims:

- D = 120: first lien 108.9 (100 percent), junior gets 11.1 (recovery 11.1/30.9 = 0.35922), pref 0, common 0.
- D = 150: first lien 108.9, junior 30.9 (100 percent), pref gets 10.2 (recovery 10.2/22.4 = 0.45536), common 0.
- D = 170: first lien, junior, pref all 100 percent, common gets 7.8.

Dilution checks (S_0 = 100M shares, junior carries penny warrants for w = 5 percent, pref converts at 10 per share on the year-1 accreted amount):

- N_w = 100 * 0.05 / 0.95 = 5.2632M shares.
- N_c = 22.4 / 10 = 2.24M shares.
- Total = 107.5032M.
  Existing 0.9302, warrants 0.0490, pref 0.0208 (tolerance 1e-4).

Use the failing "pref counted as debt" case as the demo trap: plan A passes on the headline test and fails after the definition is applied.

## 3. How to search the space of mixes

### 3.1 Decision variables

For each instrument k in {senior, second lien, mezzanine, convertible, preferred, common}:

- Amount x_k on a grid (for example $2.5M or $5M steps).
- A term variant v_k from a small menu (for example mezz: cash 11 plus PIK 3 with 5 percent warrants, or cash 9 plus PIK 5 with 8 percent warrants; pref: cash-pay, full PIK, or toggle).
- A lender or investor assignment (who holds it), used for eligibility and check-size tests.
- Optionally a path flag: "seek consent from existing lenders" with an assumed cost in fee and time.

### 3.2 Hard constraints

1. Sources = Uses, with the gap = total need minus existing resources.
2. Per-instrument bounds: 0 or between the minimum and maximum check of the eligible holders.
   Lender eligibility: instrument types the holder can own, minimum hold, maximum hold, maximum attachment or detachment leverage it will accept.
   These parameters come from a lender table that must be sourced, not invented.
3. Every clause test in 2.7 passes at closing on a pro forma basis.
4. Intercreditor consistency: a lien ranking is only allowed if the intercreditor path exists.
   Subordination must be consistent with the stack order.
5. Minimum liquidity at close and year-1 cash flow after debt service is nonnegative on the base case.
6. Chance constraint, applied only on the shortlist: P(any maintenance covenant breach over the horizon) <= alpha, where alpha is a reviewer risk setting (default input).
7. Floor on headroom in the base case (for example at least a configured percent EBITDA cushion), because lenders and boards ask for cushion (practitioner check on the usual level).

### 3.3 Objectives

Report all three, then rank:

1. Cost of capital: blended after-tax all-in cost of the new money (2.8 table row), including the required return on common as a labeled assumption.
   Lower is better.
2. Risk: P(breach) from the Monte Carlo, plus expected shortfall in cushion as a tie-breaker.
   Lower is better.
3. Dilution: fully diluted ownership given to new investors, including warrants and conversion.
   Lower is better.

Optional fourth: execution complexity (count of distinct parties, consents needed).
Ranking default: constraint filter, then Pareto frontier on (cost, breach probability, dilution), then a weighted score from the reviewer's stated preferences, with the weights shown to the reviewer.
That design choice is inferred.

### 3.4 Method comparison

| Method | Strength | Weakness for this build |
| --- | --- | --- |
| Constrained enumeration + Pareto + MC on shortlist | Simple, exact on the grid, trivially explainable, supports the "rejected because of clause X" trace, easy to unit test | Grid resolution limits optimality, size grows with variants |
| MILP / CP-SAT (OR-Tools) | Proven optimizer for linear/integer models. Ratio tests with fixed EBITDA are linear in the amounts | CP-SAT requires integer-only models, so you must scale to integers (verified, https://developers.google.com/optimization/cp/cp_solver). PIK compounding, waterfall, MC breach probability, and step-up triggers are nonlinear or simulated. It gives one optimum, and explaining why a plan is infeasible needs extra work (inferred) |
| Heuristic or genetic search | Handles any objective | Hard to explain, no guarantee, tuning time |
| LLM proposes mixes | Creative term variants | Cannot be trusted for feasibility. Use only to propose term menus, with code checking everything (inferred) |

Size of the enumeration (inferred arithmetic): splitting a gap into 5 tranche amounts on a grid of 20 units has C(24,4) = 10,626 combinations.
On 40 units it has C(44,4) = 135,751.
If four instruments each have 3 term variants, multiply by 81, giving about 0.86M and 11M.
Both are fine with vectorized closed-form metrics.
Pruning with the cheap constraints first (sums, bounds, lender eligibility, ratio tests) cuts this a lot.
Monte Carlo only runs on the Pareto set (say 20 to 50 mixes), because Monte Carlo costs thousands of paths per mix.

### 3.5 Recommendation for 36 hours

Use constrained enumeration with a Pareto filter and Monte Carlo on the shortlist (inferred).
Why:

- The feasible set is small enough to enumerate in seconds.
- Every pruned candidate stores the first violated clause id.
  That table is the evidence for the "denied transition" and the revised-plan story.
  A solver hides it.
- The code is simple enough to unit test with the worked example above, which matters because the LLM must not produce numbers.
- The risk metric (breach probability) comes from simulation, so an exact optimizer would not give a true optimum anyway.
- If time remains, use CP-SAT only to double-check that the enumerated best is not beaten on the linear part.
  This is optional polish, not the core.

Pipeline (prose):

1. Build the clause set from deep problem 1 (the capacity map and tests).
2. Generate candidates on the grid and term menus.
3. Reject candidates in cheap-first order, logging the first violated clause per rejection.
4. Compute deterministic metrics for survivors.
5. Take the Pareto set.
6. Run seeded Monte Carlo on the Pareto set (deep problem 3).
7. Apply the chance constraint, rank, and hand the top plan and its two nearest alternatives to the master agent.

## 4. When a clause blocks the first plan

### 4.1 What changes in the search

- The new clause becomes a hard constraint (or modifies a definition, such as pref counted as debt).
  It is added to the clause set with its source span, and the search re-runs.
  The earlier plan stays in the log as "denied, clause C, actual vs limit".
- A revised plan is not a small tweak of the old one by default.
  The Pareto frontier may move to a different region of the stack.
  Typical moves, by what the clause does (all inferred, practitioner check):
  - Ratio test fails: cut total debt, move capital to instruments that do not count as debt (non-redeemable pref, common), or ask for a consent or amendment.
  - Basket cap: split the new debt across baskets, or use a non-debt instrument.
  - Lien restriction: make the tranche unsecured or place it at a holdco.
  - Restricted payment limit: switch cash-pay pref to PIK.
  - Consent needed: mark the plan as conditional on consent, add a consent fee and time cost, and show the consent-free alternative next to it.
- The simulation must be re-run, because the covenant set and the mix both changed.

### 4.2 Explaining the trade-off in numbers

The reviewer should see a fixed comparison table, produced by code:

| Item | Plan A (blocked) | Plan B (revised) | Change |
| --- | --- | --- | --- |
| Amounts by tranche | 50 / 0 / 30 / 20 / 0 | e.g. 50 / 0 / 20 / 10 / 20 common | per tranche |
| Blended cost of new money | 10.60 percent | computed | bps |
| Total leverage (as the clause defines it) | 3.20x vs limit 3.0x | computed | |
| Breach probability over horizon | n/a (illegal) | from MC | |
| Dilution to existing holders | computed | computed | pp |
| New conditions (consents, fees, timing) | | | |

Include these derived numbers:

- Price of the constraint: cost(best feasible plan) - cost(best plan if the clause were waived), in bps and dollars per year.
  This shows what the clause costs the company and what a waiver would be worth.
  For example, in the worked example, a waiver would have to cover 20 of pref that counts as debt, or EBITDA would need to be 53.333 instead of 50.
- Minimum change to unblock: the smallest cut to a tranche or the EBITDA needed (160 / 3.0 = 53.333).
- Nearest alternatives: the next two Pareto plans, with deltas.
- Sensitivity: how the ranking flips if a named assumption moves (for example junior spread plus or minus 100 bps).
- Evidence: the clause text span, the formula, and the inputs for every number.
  Every number must be reproducible from the test records of 2.5.

Dilution needs an equity value input, so show it only when the valuation input is labeled and provided.

## 5. What a practitioner would call naive or missing

Items marked (check) need a practitioner review before the pitch claims them.
All are inferred from general finance knowledge unless a URL is given.

1. Pricing as a constant (check).
   Real pricing rises with attachment point and detachment point (leverage in front of and through the tranche), size, industry, and market state.
   A flat price per instrument will pick mixes that no lender would fund at that price.
   The pricing function needs at least a table by leverage band.
2. Market clearing (check).
   A feasible mix is not a placeable mix.
   There may be no holder for $10M of second lien, or no holder at this spread.
   Minimum check sizes, hold limits, and appetite should be explicit, and current data is thin.
   The Lord Abbett and Houlihan Lokey notes in `../research.md` suggest a lender-friendly market in 2026, which is a search summary only.
3. Debt versus equity classification in definitions (check).
   Whether pref or PIK counts as debt, whether PIK accretes into the covenant debt, and how lease debt is treated differ by agreement.
   This is the main planted-trap mechanism, so confirm with a real agreement from EDGAR.
4. EBITDA definitions (check).
   Add-backs, synergy caps, pro forma acquired EBITDA, and cash netting caps drive the covenant outcome.
   A single "EBITDA" number is naive.
5. Tax (check).
   Interest deductibility has limits (a cap on net interest deduction, and special rules for high-yield discount obligations and PIK).
   I believe these exist but did not source them.
   Pref dividends are not deductible (secondary, `../research.md`).
   The after-tax cost in the worked example is simplified.
6. Returns are IRR and MOIC, not coupons (check).
   Pref investors price a minimum multiple, call protection, make-wholes, and exit timing.
   Redemption premiums and non-call periods change the real cost and the covenant on refinancing.
   Mayer Brown quotes returns as IRR (15 to 25 percent) with "guaranteed minimum returns" in structured equity.
   The model needs an exit date and an IRR calculation per tranche.
7. Warrant and conversion cost as option value (check).
   Percent dilution at a fixed valuation understates cost when the company does well and overstates it when it does not.
8. Waterfall realism (check).
   Absolute priority is a simplification.
   Real recoveries depend on collateral by entity, structural subordination (holdco versus operating company), guarantees, deficiency claims, super-priority rescue financing, process costs, and negotiated outcomes.
   Second-lien recovery is very sensitive to enterprise value, with a wide published range (secondary, abfjournal link above).
9. Cash flow mechanics (check).
   Excess cash flow sweeps, mandatory prepayments, revolver draws and liquidity, delayed-draw tranches, minimum liquidity covenants, and interest rate hedges are missing from v1.
10. Covenant cures and resets.
    Equity cures, step-downs, and amendment costs matter for breach risk.
    A breach is a negotiation, not a switch (inferred).
    The McDonald Hopkins page did not address equity cures.
11. Non-financial terms matter most in these deals.
    Governance rights, consent rights over future debt, board seats, transfer limits, anti-dilution, and change of control drive the negotiation (verified [secondary], Mayer Brown above).
    The model handles only the financial layer and should say so.
12. Covenant-lite versus maintenance reality.
    Cov-lite share reached 41 percent in upper middle market and large-cap in 1H 2026 but stayed under 4 percent for borrowers under $50M EBITDA (verified [secondary], as logged in `../research.md`).
    The fictional borrower's size therefore decides whether maintenance tests apply.
13. Objective realism (check).
    Practitioners optimize for certainty of close, speed, flexibility, relationship, and covenant room, and not only for lowest blended cost.
    A "minimum cost" answer may be the wrong product.
    The reviewer weights should include these.
14. Distribution risk.
    Breach probability depends on the shock model (fat tails, correlation between revenue drop and rate rise).
    Results are not predictions and must be labeled assumptions.
15. Calibration.
    We have no deal database.
    Nothing here is calibrated to real transactions.
    The Buyers Edge deal terms are not public in the sources found, so do not present a rate as theirs (`../research.md`).

Assumptions that most need a practitioner check before demo day (ordered by impact on the story):

1. Whether a mandatorily redeemable or PIK preferred counts as debt in the leverage definition, and how.
2. The leverage-dependent price table for each tranche.
3. Whether cash preferred dividends are restricted payments, and whether PIK is allowed.
4. Typical cushion that a lender or board requires (the headroom floor).
5. Whether a second lien or mezzanine tranche of the sizes in the example could be placed at all, and by what type of holder.
6. The tax treatment of PIK and preferred in the cost number.
7. The set of term variants (warrant coverage, step-up size and triggers, call protection) that reflect actual market.
8. Whether a reviewer would accept "blended cost" as the headline metric.

## 6. Open items for the team

- Find one real credit agreement on EDGAR and copy the real definitions of Total Debt, EBITDA, Indebtedness, and Disqualified Stock into the clause library.
  This replaces the flag assumption in 2.5.
- Ask a practitioner (a former banker as reviewer, or a Hyphenate contact) to review items 1 to 8 above.
- Decide the term menus and keep them small (two or three per instrument).
- Agree the interface with deep problems 1 and 3: the clause set comes in, the shortlist and Pareto table go out, and the simulator calls the same deterministic functions.
