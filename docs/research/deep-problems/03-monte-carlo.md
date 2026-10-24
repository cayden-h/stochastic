# Deep problem 3: the Monte Carlo risk simulation

Written 2026-10-23.
Every claim is tagged "verified (URL)" or "inferred".
"Verified" means I opened the page in this session or a search result showed the quoted fact.
"Inferred" means my own reasoning, a standard textbook method I did not re-open, or a URL I have not read.
No number below is a prediction.
Every model parameter in this doc is a placeholder until it is filled from a source in section 3 and logged in the assumptions registry (section 4).

## 0. Summary of the recommendation

- Quarterly time step, 5-year horizon (20 steps), 10,000 to 50,000 paths per structure. [inferred]
- One macro regime chain (expansion or recession) drives revenue growth, margin, cost shocks, rate level, and exit multiple together. [inferred]
- Fat-tailed shocks (Student-t, 5 degrees of freedom) joined by a one-factor correlation. [inferred]
- Common random numbers: every candidate structure is run on the exact same shock array. [inferred]
- All deal math (interest, waterfall, covenants, preferred dividend, tranche loss) is plain deterministic code. The LLM only passes parameters in and quotes results out. [inferred, matches the README rule that the LLM must never invent numbers]
- A hand-computed answer key plus closed-form tests ship with the simulator, and the memo validator rejects any number that has no run id. [inferred]

## 1. Design of the simulation

### 1.1 Time step and horizon

- Step: one quarter.
  Reasons: covenants are tested quarterly on LTM (last twelve months) figures, public companies report quarterly, and the step is small enough to see liquidity troughs but cheap to run. [inferred]
  Maintenance covenants are tested on a schedule while incurrence tests apply only when an action is taken. [verified (https://www.creditgpt.com/content/maintenance-versus-incurrence-covenants), cited in research.md as title and summary only]
- Horizon: 5 years (20 quarters) by default, with the structure's maturity as an upper bound.
  Reason: typical private-credit hold and the window where a recession realistically lands. Make it a parameter. [inferred]
- Do not use a monthly step in the first build. Monthly adds seasonality and working-capital noise that you cannot calibrate in 36 hours. [inferred]

### 1.2 State variables per path

For quarter t = 1..T:

- R_t: quarterly revenue.
- m_t: EBITDA margin.
- E_t = R_t * m_t: EBITDA. LTM EBITDA = sum of the last 4 quarters.
- s_t: regime, 0 = expansion, 1 = recession.
- r_t: SOFR level (floating base rate).
- mult_t: enterprise value multiple, used only for recovery and refinancing tests.
- cash_t, revolver_t, balances of each tranche, accrued PIK, accrued unpaid preferred dividends.

### 1.3 Regime process (the recession regime)

Use a two-state Markov chain, with transition probabilities per quarter:

- p_er = P(expansion -> recession), p_re = P(recession -> expansion).
- Stationary share of time in recession: pi_rec = p_er / (p_er + p_re).
- Expected recession length in quarters: 1 / p_re.

Why this model: it is the simplest object that produces the correlated, clustered bad quarters that a financier fears, it is explainable in one sentence, and it can be calibrated from public NBER dates.
It is the discrete version of the Hamilton regime-switching idea. [inferred]

Calibration sketch from the NBER table (my arithmetic, so inferred):

- NBER lists these recessions as peak to trough: Jan 1980 to Jul 1980 (6 months), Jul 1981 to Nov 1982 (16), Jul 1990 to Mar 1991 (8), Mar 2001 to Nov 2001 (8), Dec 2007 to Jun 2009 (18), Feb 2020 to Apr 2020 (2). [verified (https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions)]
- Those six total 58 recession months, mean about 9.7 months, or about 3.2 quarters. So p_re is roughly 0.3 per quarter. [inferred]
- Six recessions in the roughly 46 years from 1980 to 2026 gives about 494 expansion months, or about 165 quarters. So p_er is roughly 0.036 per quarter. [inferred]
- Recompute these from the full NBER list and the monthly FRED indicator before use. The indicator is a 1 in recession months and a 0 otherwise. [verified (https://fred.stlouisfed.org/series/USREC)]

Important honesty point: a restaurant chain's own downturn does not line up with NBER dates.
Add an idiosyncratic shock (section 1.4) so the company can have a bad quarter in an expansion. [inferred]

Also run named deterministic scenarios (a "2008-style" path and a "2020-style" path) next to the random paths, because reviewers trust a path they can recognize. [inferred]

### 1.4 Revenue growth

Log growth per quarter, year-over-year style to avoid modeling seasonality:

g_t = mu[s_t] + sigma_sys[s_t] * z_sys,t + sigma_idio * z_idio,t

R_t = R_{t-1} * exp(g_t)  (apply on a seasonally adjusted base, or model YoY growth on the same quarter last year)

- mu[0] > mu[1], with mu[1] negative and sigma[1] > sigma[0] (volatility rises in recession). [inferred]
- z are Student-t with df = 5, rescaled to unit variance. Reason: revenue and margin shocks are fat-tailed and a normal understates tail loss. [inferred]
- Calibrate mu and sigma by regime from public data: Census restaurant sales (monthly, hosted on FRED) split by the USREC flag, plus company 10-K quarterly revenue for comparable chains. [verified (https://fred.stlouisfed.org/series/MRTSSM7225USN) for series existence and units: Retail Sales, Restaurants and Other Eating Places, monthly, millions of dollars, not seasonally adjusted, Census Bureau]
- Industry-level volatility is lower than single-company volatility because of diversification. Scale sigma_idio up for a single mid-sized borrower. [inferred]

### 1.5 EBITDA margin and cost shocks

Mean-reverting margin with regime-dependent target and operating leverage:

m_t = m_{t-1} + kappa * (m*[s_t] - m_{t-1}) + beta_lev * (g_t - g_bar) + sigma_m * z_m,t + J_t

- m*[1] < m*[0]: the long-run margin target is lower in recession. [inferred]
- beta_lev * (g_t - g_bar): a revenue miss drops margin through fixed costs (operating leverage). This is the main mechanism that turns a revenue dip into a covenant breach. [inferred]
- J_t: cost shock jump (food, wage, commodity). Poisson arrival with probability p_J per quarter, size drawn from a one-sided distribution (a lognormal in basis points). Persistent, so it decays through the kappa term. [inferred]
- Floor and cap m_t to a sane range. Log how often the floor binds, and treat frequent binding as a calibration bug. [inferred]
- Anchor the base margin on a real number: Damodaran's January 2026 US sector table lists Restaurant/Dining at 19.47 percent EBITDA/Sales across 64 firms (operating margin 15.79 percent). [verified (https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/margin.html)]
  This is a US-firm average and includes large, franchised, asset-light companies, so a mid-sized operator is likely lower. Use the fictional company's own statements for the base and Damodaran as a sanity range. [inferred]

### 1.6 Interest rates

Floating-rate debt pays SOFR + spread.
Use a discrete mean-reverting (Vasicek or AR(1)) rate process, because it is closed-form testable and defensible:

r_t = r_{t-1} + a * (theta[s_t] - r_{t-1}) + sigma_r * z_r,t,  then floor at 0

- theta[1] < theta[0]: policy rates usually fall in recession, which partly offsets the revenue hit for floating-rate borrowers. [inferred]
- Stagflation is the case that hurts: allow a named scenario with a rate rise during a revenue decline (rates up, revenue down). Do not hard-wire a negative rate/revenue correlation. [inferred]
- Starting level r_0 comes from the latest SOFR print, a daily series from the New York Fed hosted on FRED. [verified (https://fred.stlouisfed.org/series/SOFR) for series name, daily frequency, percent units]
- Use the 10-year Treasury yield as a long-run anchor for theta. [verified (https://fred.stlouisfed.org/series/DGS10) for series name, daily, Federal Reserve H.15]
- Add a hedge ratio parameter h: the fraction of floating debt fixed by swap or cap. Effective rate = h * fixed + (1 - h) * (r_t + spread). [inferred]
- Fixed-rate tranches (most preferred equity and mezzanine coupons) ignore r_t. Say so in the output, since it shows why junior capital is "expensive but stable". [inferred]
- Note: SOFR is a post-2018 series, so its own history is short. Calibrate rate volatility on a longer series (Fed funds or Treasury yields) and say so. [inferred]

### 1.7 Exit multiple and credit spread (needed for recovery)

mult_t = mult_0 * exp(-lambda_m * 1{s_t = 1} + sigma_mult * z_mult,t)

- Multiples fall in recession and when distress is visible, so recovery is lower exactly when defaults are highest. Ignoring this is a classic error (section 6). [inferred]
- Calibrate the level range from Damodaran's EV/EBITDA data (page not read, so inferred: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/vebitda.html) and the High Yield index spread as a stress indicator. [verified (https://fred.stlouisfed.org/series/BAMLH0A0HYM2) for series existence: ICE BofA US High Yield OAS, daily, percent. FRED notes that from April 2026 it keeps only 3 years of observations, so download and archive older data under license rules before the deadline, or use a different source.]

### 1.8 Correlations

Use a one-factor structure plus the regime, so the number of parameters stays small and the matrix is always positive definite.

- Systematic shock for revenue, margin, and multiple loads on one common factor f_t: z_i = rho_i * f_t + sqrt(1 - rho_i^2) * e_i.
- Keep rate shock with its own correlation rho_rate_rev (an input, default 0, tested as a sensitivity from -0.5 to +0.5). [inferred]
- Check that the correlation matrix is positive semi-definite before the Cholesky step. [inferred]
- Because the regime already creates correlation (everything gets worse together in state 1), the residual correlations can be modest. Report both the within-regime and the total correlation of simulated revenue and margin so a reviewer can compare to history. [inferred]

### 1.9 Cash flow, debt service, and the waterfall

Per quarter, in this order (the order is part of the contract with the lender, so keep it in one function):

1. EBITDA_t = R_t * m_t.
2. Cash taxes = tax_rate * max(0, EBITDA_t - D&A - deductible interest). Interest is deductible, preferred dividends are not. [inferred, consistent with research.md note that preferred dividends are not tax deductible]
3. Capex_t (maintenance share fixed, growth share cut in stress by a management response rule, see 1.10).
4. Change in working capital (set to zero in v1, flagged as a simplification).
5. Cash interest on senior and junior: balance * (rate_t / 4). Cash-pay versus PIK share per tranche.
6. Mandatory amortization of senior.
7. Cash available for dividends: CFADS_t = cash_t-1 + EBITDA - taxes - capex - cash interest - amortization.
8. Revolver draws if CFADS < minimum cash. If revolver is exhausted and cash < 0, record a liquidity event.
9. Preferred dividend: pay in cash if CFADS above minimum cash after senior and junior service, else accrue or PIK according to the term sheet, and record "dividend missed" (section 2.2).
10. Optional cash sweep to senior.
11. Test covenants (section 2.1) on LTM figures.

### 1.10 Management response (do this in a simple form)

A real company does not sit still. A rule such as "cut growth capex by 50 percent when net leverage exceeds 0.5x below the covenant" is realistic, and a practitioner will ask for it.
Keep it as an explicit parameter with an on/off switch, and report results with and without it. [inferred]

## 2. Outputs a financier cares about, with formulas

Let N be the number of paths, and path i have indicator functions. A hat denotes a Monte Carlo estimate.

### 2.1 Covenant breach probability

For covenant c with threshold K_c tested at quarters in set Q_c:

- Net leverage_t = (Total debt_t - Cash_t) / LTM EBITDA_t. Breach if > K_lev.
- Interest coverage_t = LTM EBITDA_t / LTM cash interest_t. Breach if < K_icr.
- Fixed charge coverage_t = (LTM EBITDA - capex - taxes) / (cash interest + scheduled principal). Breach if < K_fccr.
- Minimum liquidity_t = cash_t + undrawn revolver_t. Breach if < K_liq.

Definitions here must use the term sheet's own definitions (EBITDA addbacks, whether leases count as debt). That is the planted-trap area in the README. [inferred]

Estimates:

- Probability of first breach by quarter t: P_c(t) = (1/N) * sum_i 1{ exists s <= t, s in Q_c, breach_c,i,s }.
- Time to first breach: tau_c,i = min{ s : breach }, report median and 10th percentile among breached paths.
- Standard error: SE = sqrt( P(1 - P) / N ).
- Headroom distribution: (K_c - ratio_t) / K_c at each quarter, with 5th, 50th, 95th percentiles (a fan chart). Headroom is the metric lenders actually discuss. [inferred]
- Cure rights: if the agreement allows an equity cure, model it as a separate "cured" counter rather than hiding the breach. [inferred]

### 2.2 Probability of missing a preferred dividend

For scheduled dividend D_t on the preferred:

- Cash-pay miss at t: 1{ cash available after senior and junior service and minimum cash < D_t } on paths where the instrument requires cash pay.
- P(miss at least once by T) = (1/N) * sum_i 1{ exists t: miss_i,t }.
- P(miss in two or more consecutive quarters), because many terms trigger a rate step-up or governance rights after consecutive misses. Remedies for preferred are contractual, usually step-ups or governance rights rather than creditor enforcement. [verified (research.md, secondary law-firm and glossary sources)]
- Expected accrued unpaid dividend at T and its 95th percentile.
- For a PIK toggle: the share of paths that toggle to PIK and the resulting liquidation preference at exit, A_T = A_0 * prod(1 + d_t/4) on paths that accrue.

### 2.3 Liquidity exhaustion

- P(liquidity event by t) = (1/N) * sum_i 1{ exists s <= t: cash_s < 0 after full revolver draw }.
- Minimum liquidity across the horizon: the 5th percentile of min_t(cash_t + undrawn_t).
- Months of runway at the 5th percentile. [inferred]

### 2.4 Default and distress definition (needed for tranche losses)

Define default on path i at the first quarter where either:

- (a) a payment default: liquidity event, or interest not paid when due on a cash-pay debt tranche, or
- (b) an uncured maintenance covenant breach that the lender accelerates. Use a parameter p_accel (probability the lender accelerates given a breach; default is a judgment value, flagged as such) because breaches are usually waived for a fee rather than accelerated. [inferred]

Treating every covenant breach as a default overstates loss. Treating none as default understates it. Show both (section 6). [inferred]

### 2.5 Expected and tail loss to each tranche

At default quarter tau on path i:

- Enterprise value: EV_i = mult_tau * LTM EBITDA_tau * (1 - h_dist), where h_dist is a distress haircut and costs of administration are subtracted. [inferred]
- Net distributable value: V_i = max(0, EV_i + cash_tau - admin_costs).
- Absolute priority waterfall, tranche k ordered senior first, claim C_k (principal plus accrued interest plus accrued dividends):
  - Recovery_k = min( C_k, max(0, V_i - sum_{j senior to k} C_j) ).
  - Tranches of equal rank share pro rata.
- Loss_k,i = C_k - Recovery_k, expressed as a fraction: LGD_k,i = Loss_k,i / C_k.
- Time-discounted loss uses a discount rate d: PVLoss_k,i = Loss_k,i / (1 + d)^(tau/4). Use the tranche's own contractual rate as a simple choice, and state it. [inferred]

Estimators over N paths:

- Probability of any loss: PL_k = (1/N) * sum 1{ Loss_k,i > 0 }.
- Expected loss: EL_k = (1/N) * sum PVLoss_k,i (non-default paths contribute 0).
- Conditional loss given default: LGD_k = sum Loss_k,i / sum_{defaults} C_k.
- Value at Risk at level a: VaR_a = the a-quantile of PVLoss_k.
- Expected shortfall (CVaR): ES_a = mean of PVLoss_k over paths where PVLoss_k >= VaR_a.
- For the preferred, also report the realized IRR distribution and P(IRR < hurdle), because a preferred investor prices on return, not only on loss. [inferred]
- Sanity check of EL against agency history, section 3 (do not claim they must match, only that the gap is explainable). [inferred]

Report for the whole structure as well:

- Probability that the sponsor/equity is wiped out.
- Cost of capital: blended cash cost at time 0, and expected all-in cost including PIK and dilution.
- Ownership dilution under conversion or warrants, if any.

### 2.6 Which scenario drives each breach (attribution)

Three layers, from cheapest to most rigorous:

1. Regime tag.
   For each breach path, record the regime path and count the share of breaches with at least one recession quarter in the previous 4 quarters.
   Output sentence example: "83 percent of leverage breaches occur on paths with a recession in the prior year." (illustrative, not a result) [inferred]
2. Driver decomposition using common random numbers.
   Re-run the same shocks with one driver frozen at its base-case value: revenue, margin, rates, multiple.
   Contribution of driver x = P(breach) - P(breach with x frozen).
   This is a "leave-one-out" attribution, not a strict Shapley value, and the contributions will not sum exactly when drivers interact. Say so. [inferred]
3. Representative paths.
   Cluster breached paths (k-means on the quarterly revenue growth and margin vectors, k = 3 or 4), name each cluster ("early recession with margin squeeze", "slow bleed", "rate spike"), and show the median path of each cluster.
   This gives the human reviewer a story, not only a number. [inferred]

The LLM may write the narrative sentences, but each number in them must be pulled from the result JSON by key (section 4.4). [inferred]

## 3. Calibration sources

Rule: only the source gives the number. This doc supplies no calibrated values on purpose. Each row becomes an entry in the assumptions registry with the retrieval date.

| Parameter | Source | URL | Status |
| --- | --- | --- | --- |
| Recession dates, durations, p_er, p_re | NBER business cycle dates | https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions | verified (page read, table above) |
| Monthly recession indicator for splitting data by regime | FRED USREC (monthly; daily and quarterly versions exist) | https://fred.stlouisfed.org/series/USREC | verified |
| Starting base rate r_0 | NY Fed SOFR on FRED, daily, percent | https://fred.stlouisfed.org/series/SOFR | verified (series), level not copied |
| Long-run rate anchor | 10-year Treasury constant maturity, Fed H.15 on FRED | https://fred.stlouisfed.org/series/DGS10 | verified (series) |
| Rate volatility and mean reversion | Estimate AR(1) on a long series (Fed funds, Treasury yields) from FRED | https://fred.stlouisfed.org | inferred (method), series IDs not checked |
| Restaurant revenue growth, volatility by regime | Census restaurant sales (monthly) on FRED | https://fred.stlouisfed.org/series/MRTSSM7225USN | verified (series existence, through Aug 2026, not seasonally adjusted) |
| Company-level revenue and EBITDA volatility | SEC EDGAR 10-K and 10-Q filings of comparable public chains | https://www.sec.gov/edgar/search/ | inferred (source type); nothing pulled yet |
| Margin level, sector range | Damodaran margins by sector, January 2026: Restaurant/Dining EBITDA/Sales 19.47 percent, 64 firms | https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/margin.html | verified |
| EV/EBITDA multiple range | Damodaran multiples data | https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/vebitda.html | inferred (page not read) |
| Credit stress indicator, spread level | ICE BofA US High Yield OAS on FRED (only 3 years kept from April 2026) | https://fred.stlouisfed.org/series/BAMLH0A0HYM2 | verified (series) |
| Bank lending tightening (refinancing risk input) | Fed Senior Loan Officer Survey: net percent tightening C&I standards, large and middle-market, quarterly | https://fred.stlouisfed.org/series/DRTSCILM | verified (series) |
| Default rates, recovery by seniority | Moody's annual default study. The 2007 edition says senior unsecured bond recovery averaged 38.4 percent historically (1920-2006) and was 58.3 percent in 2006 | https://www.moodys.com/sites/products/DefaultResearch/2006400000429618.pdf | verified (search result summary only, PDF not opened); use the latest edition for a current figure |
| Default rates by rating and horizon | S&P Global annual global corporate default and rating transition study, or Moody's equivalent | https://www.spglobal.com/ratings (search for the annual study) | inferred (document not located) |
| Private credit pricing ranges for instruments | research.md tables (Mayer Brown 15 to 25 percent gross IRR for capital solutions; direct lending about 9.3 percent all-in in 2025) | https://www.mayerbrown.com/en/insights/publications/2026/10/the-rise-of-private-capital-capital-solutions-and-the-new-architecture-of-credit | verified in research.md (law firm source, ballpark) |
| Covenant-lite share, so maintenance covenants are realistic for a mid-sized borrower | Houlihan Lokey private credit newsletter, summer 2026: 41 percent cov-lite for upper middle market and large cap, under 4 percent for borrowers with under $50M EBITDA | https://cdn.hl.com/pdf/2026/hl-u.s.-private-credit-market-newsletter-summer-2026.pdf | verified in research.md (search summary) |
| Regime-switching method | Hamilton (1989), "A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle", Econometrica | https://www.jstor.org/stable/1912559 | inferred (cited from memory, link not opened) |
| Mean-reverting rate method | Vasicek (1977), "An Equilibrium Characterization of the Term Structure", J. Financial Economics | https://doi.org/10.1016/0304-405X(77)90016-2 | inferred (cited from memory, link not opened) |
| Structural default / recovery reasoning | Merton (1974), "On the Pricing of Corporate Debt", J. Finance | https://doi.org/10.2307/2978814 | inferred (cited from memory, link not opened) |

Notes on calibration (all inferred):

- Industry data tells you about the industry. The borrower is one company, so inflate idiosyncratic volatility, and say the number is a judgment.
- Agency default statistics are for rated companies, which are larger than most special-situations borrowers. Use them as a sanity band only.
- Prefer to estimate a regime parameter on two samples (all data, and data excluding 2020) and show both, since 2020 is a very short, very sharp recession (NBER: Feb 2020 to Apr 2020, 2 months). [verified (https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions)]
- Parameter uncertainty: draw each uncertain parameter from a range at the start of each path (a "hierarchical" draw), so the output spread includes "we may have the wrong sigma". The default is to run a fixed-parameter version and a parameter-uncertain version and report the difference. [inferred]

## 4. Reproducibility, testing, and the answer key

### 4.1 Reproducibility

- One seed per run, stored with the output. Use a counter-based or spawnable generator (for example NumPy `SeedSequence.spawn` with PCG64) so each path and each shock family has its own stream, and the result does not change if you run on 1 or 8 workers. [inferred]
- Generate the full shock array first: Z of shape (N, T, k) for k shock families. Save a hash of Z. Each structure reads the same Z (common random numbers). [inferred]
- Run record (immutable, goes in the Postgres audit log): inputs hash, assumption registry version, code git SHA, seed, N, library versions, runtime, and the output JSON. A run id is the key the LLM cites. [inferred]
- Floating-point determinism: fix the numeric library version and avoid parallel reductions whose order varies. Compare outputs with a tolerance (for example 1e-9 relative), not exact equality. [inferred]

Illustrative snippet only:

```python
ss = np.random.SeedSequence(20261023)
streams = ss.spawn(4)               # revenue, margin, rate, regime
rng_rev = np.random.Generator(np.random.PCG64(streams[0]))
Z_rev = rng_rev.standard_t(5, size=(N, T)) / np.sqrt(5/3)   # unit variance
```

### 4.2 Number of paths and convergence

- Probability estimate standard error: SE = sqrt(p(1 - p)/N).
- p = 5 percent, N = 10,000: SE is about 0.22 percentage points. (my arithmetic) [inferred]
- p = 1 percent, N = 50,000: SE is about 0.045 percentage points. (my arithmetic) [inferred]
- Expected shortfall in the tail is noisier than a probability, because it uses only the worst (1 - a) share of paths. Plan for at least 50,000 paths for ES at 95 percent and a bootstrap confidence interval. [inferred]
- Convergence checks to run and display:
  1. Running estimate of each headline probability versus N, with a 95 percent band (p +/- 1.96 SE).
  2. Two independent seeds should agree within about 2 SE. If not, N is too small or there is a bug.
  3. Antithetic variates (pair z with -z) for a free variance cut on the mean outputs. Do not use them blindly for breach probabilities, check the variance empirically. [inferred]
  4. Optional: Sobol sequences for the common factor only. Skip in a 36-hour build. [inferred]
- Because the run is cheap (20 quarters, vectorized across paths in NumPy), use N = 20,000 on the demo and N = 100,000 for the final recommendation, and say which one was used. [inferred]
- Report the SE next to every probability in the memo. A number like "breach probability 12.3 percent" with no band invites the wrong confidence. [inferred]

### 4.3 Unit tests with closed-form answers (the "answer key")

Each test has an expected value from math or a hand calculation, a tolerance, and a pass or fail printed in the demo UI.

| # | Test | Expected answer | Method |
| --- | --- | --- | --- |
| 1 | Zero volatility, no regime switching | Path equals the hand-built spreadsheet for the base case, to the cent | Deterministic replay |
| 2 | Revenue log-growth, normal shocks, one regime | Mean of log(R_T/R_0) = T * mu, variance = T * sigma^2 | Sample moments within 3 SE |
| 3 | Student-t shocks after rescaling | Sample variance equals 1, kurtosis above 3 | Moment check |
| 4 | Markov chain | Fraction of time in recession converges to p_er/(p_er + p_re); mean recession length 1/p_re | Long-run frequency |
| 5 | AR(1) rate process | Stationary mean = theta, variance = sigma^2 / (1 - (1 - a)^2) (before flooring) | Long-run sample moments |
| 6 | Single-period binary default | One tranche, one period, default prob p, recovery fraction rho: EL = p * (1 - rho) * C | Exact |
| 7 | Merton check | With lognormal asset value, no regime, one zero-coupon debt of face D: P(V_T < D) = N(-d2), d2 = (ln(V_0/D) + (mu - sigma^2/2)T)/(sigma * sqrt(T)) | Simulated versus formula |
| 8 | Waterfall conservation | Sum of recoveries to all tranches plus residual to equity equals distributable value; no tranche recovers more than its claim | Property test on random inputs |
| 9 | Seniority order | Junior recovery above zero only if senior recovery equals its full claim | Property test |
| 10 | Monotonicity with common random numbers | Raising the leverage covenant threshold cannot raise breach probability; adding senior debt cannot lower senior EL | Property test on identical Z |
| 11 | Trivial structures | Zero debt gives breach probability 0; debt larger than 100 times EBITDA gives breach probability 1 | Boundary |
| 12 | Determinism | Same seed and inputs give identical output hash; different seed gives output within 2 SE | Reproducibility |
| 13 | Correlation | Sample correlation of revenue shock and margin shock matches the input rho within 3 SE; the matrix passes positive semi-definite check | Moment check |
| 14 | Day-count and rate arithmetic | Interest for one quarter at SOFR + spread equals hand calculation | Unit |

All of the formulas above are standard results. [inferred]

How to show the "answer key" on stage:

- A "Model checks" panel listing the 14 tests, green ticks, and the tolerance. Click one to see expected versus simulated. [inferred]
- A frozen golden scenario: a tiny fictional company with 3 quarters, hand-computed in a spreadsheet by a teammate (not by the code or an LLM). The code must reproduce every cell. [inferred]
- This links to Hyphenate's request for an answer key with a score (see `../hyphenate-workshop.md`, item 5 of the gaps list: "No answer key"). The simulation answer key is separate from the covenant-trap catch-rate score, so keep both. [verified (hyphenate-workshop.md)]

### 4.4 Never let the LLM invent a number

- The simulator returns a typed JSON result with a run id.
- The memo template is rendered from fields, or the LLM writes prose with placeholders like `{run_17.breach_prob.net_leverage.q8}`, which code fills in.
- A validator extracts every number from the final memo and checks it against the run JSON (value, rounding, units). Unmatched numbers fail the memo and are logged. [inferred]
- Rewording is allowed. New numbers are not.

### 4.5 Label inputs as assumptions, not predictions

- Assumptions registry: one row per input with name, value, unit, low and high range, source and URL, retrieval date, status (`sourced`, `derived from sourced data`, `judgment`), and owner.
  Judgment values must be visible in the UI with a different color. [inferred]
- Output header on every page: "Conditional on assumptions A1 to A27 (6 are judgment). These are model-implied probabilities under those assumptions, not forecasts." [inferred]
- Use "model-implied" and "under the stated assumptions" in the language, never "will" or "is expected to default". [inferred]
- Show a tornado chart: change each key assumption across its range and show the change in the headline breach probability. The reviewer sees which assumption the answer depends on. [inferred]
- Include "what would change this conclusion" as one line per recommendation. [inferred]
- Do not publish numbers that we only pulled from search summaries as facts. Mark them "self-reported" or "secondary", as the repo CLAUDE.md requires. [verified (CalHacks/CLAUDE.md rule)]

## 5. How the system uses the simulator in the loop

(Brief, so this doc fits the master-agent design in README.md.)

- Tool signature: `simulate(structure, assumptions_version, seed, N) -> result_json`. [inferred]
- The structuring agent proposes structures. The simulator evaluates all candidates on the same Z. A Pareto view (cost of capital versus breach probability versus tail loss to junior capital) goes to the reviewer. [inferred]
- When the clause reader rejects a structure (the README autonomous moment), the new candidates reuse the cached Z, so the re-run is fast and differences come only from the structure. [inferred]
- Time inside the deal: if an event arrives (rate move, lender term change), only the assumption changes, with the same seed, so the human sees the delta caused by that event alone. [inferred]

## 6. Common mistakes and how a practitioner would critique the model

### 6.1 Mistakes to avoid

1. Ignoring correlation. Independent shocks make a recession look like a lucky streak of small misses, and breach probability comes out too low. Fix: regime plus common factor. [inferred]
2. Normal shocks. Understates tail loss. Fix: Student-t with a stated df, and a sensitivity to df. [inferred]
3. Different random numbers per structure. Differences between structures then include Monte Carlo noise and the ranking can flip. Fix: common random numbers. [inferred]
4. Constant volatility. Volatility rises in downturns. Fix: regime-dependent sigma. [inferred]
5. Recovery independent of the cycle. In recessions, defaults rise and multiples and recoveries fall together. Fix: multiple tied to the regime. [inferred]
6. Treating a covenant breach as a default, or never treating it as one. Fix: p_accel parameter and both views. [inferred]
7. Testing covenants on the wrong EBITDA definition (no addbacks, wrong lease treatment). Fix: take definitions from the credit agreement, which is the planted-trap territory. [inferred]
8. Ignoring PIK accrual, accrued dividends, and fees in the claim at default. Fix: claims include accruals. [inferred]
9. Terminal-only measurement. Looking only at year 5 misses mid-path breaches. Fix: first-passage statistics. [inferred]
10. Reporting a mean and no tail. Financiers read the 95th and 99th percentile, not the mean. [inferred]
11. Hard-coding a rate level. Even in a short deal the base rate moves. Fix: stochastic r_t plus hedge ratio. [inferred]
12. No SE on estimates, and no seed record. [inferred]
13. Calibrating to the wrong sample (large public chains, 2020 only, or the 2009 case only). Fix: show two windows. [inferred]
14. Letting the LLM pick parameters silently. Fix: assumptions registry with a human-visible status. [inferred]
15. Over-precision. "12.347 percent" with an SE of 0.3 points. Fix: round to the SE. [inferred]

### 6.2 What a practitioner would say about this model (expect these questions)

- "Your recession is an NBER recession. My borrower's downturn is its own." Answer: idiosyncratic shock and named scenarios; sector-specific regime as a next step.
- "Management would cut capex and sell stores long before default." Answer: management response rule, switchable, with the two views shown.
- "Covenants get waived or amended all the time, so breach is not default." Answer: p_accel and the waiver-fee view; we report breach as "forces a negotiation", not "loss".
- "Where do the lender's term sheet definitions enter?" Answer: covenant formulas are parameterized by the clause reader's capacity map, not hard-coded.
- "Preferred equity is not debt. What happens on a missed dividend?" Answer: contractual remedies modeled as step-up and governance rights, not as a default. Waterfall puts preferred above common and below all debt.
- "Rate hedges and floors?" Answer: hedge ratio and SOFR floor parameters.
- "Refinancing risk at maturity?" Answer: add a maturity test: can the company refinance at the then-prevailing multiple and spread; uses the High Yield spread and the Fed loan officer survey as stress indicators.
- "Your tail is a model tail." Answer: yes. We show parameter uncertainty and a stress ladder, and do not claim the 99th percentile is precise.
- "Why a regime model and not a full stochastic volatility or copula model?" Answer: a 36-hour build needs a model that can be explained, tested against closed forms, and calibrated from free data. The code is built so that each shock family can be swapped later.
- "Backtest?" Answer: a full backtest is not possible with a handful of public deals. We can replay the model on two historical windows (2008 to 2010 and 2019 to 2021) for a public chain and compare the simulated percentile of the realized revenue and margin path. Report this as a check, not a validation. [inferred]
- "Agency default tables say a B-rated 5-year default rate is X." Answer: compare the simulated senior default probability with the agency history for the equivalent rating, explain the gap, and never tune parameters to hit the table. [inferred]

## 7. 36-hour build order (suggested)

1. Spec the result JSON and the assumptions registry first (2 hours).
2. Deterministic engine for one company and one structure, with the golden scenario test (5 hours).
3. Shock generators, regime chain, and tests 2 to 5 (4 hours).
4. Waterfall, covenants, preferred dividend logic, tests 6 to 11 (5 hours).
5. Multi-structure run with common random numbers, attribution by freezing drivers (3 hours).
6. Convergence panel, model checks panel, memo validator (3 hours).
7. Calibration pull from FRED, NBER, and one or two EDGAR filings, logged in the registry (3 hours).
8. Keep time at the end for the demo story. The Monte Carlo is a tool, and the workshop notes say to put demo time on the loop, not on the simulator. [verified (hyphenate-workshop.md, item 7 of the gaps list)]

(Hour estimates are my planning guesses, inferred.)

## 8. Open items and unverified points

- The Moody's 2007 PDF was seen only as a search result. Open the latest edition before quoting any default or recovery statistic.
- The Damodaran EV/EBITDA page, S&P study, Hamilton, Vasicek, and Merton links were not opened.
- The FRED series IDs for Fed funds and the 2-year rate used for rate volatility are not checked.
- No restaurant revenue volatility figure was computed. Pull the Census series and compute it by regime in a notebook, then enter it into the registry.
- A practitioner check of the covenant formulas, the waterfall order, and the distress haircut is still needed.
