# 09 - Situation profiles: what practitioners ask and weigh, and default profile values

Written 2026-10-23 by a research agent for the Stochastic team.
Scope: set defensible default values for the six profile fields (scope, information needed, allowed instruments, objectives, impact measures, escalation thresholds) for the eight situation types.
Companion files: `07-special-sits-taxonomy.md` (taxonomy), `08-real-deal-candidates.md` (Organogenesis facts), `02-structure-search.md`, `03-monte-carlo.md`.

## Label key and honesty notes

- "verified (URL)" means I fetched that page or filing in this session and read the fact there.
- "verified (URL, search summary)" means the fact came from a web search summary of that URL and I did not read the page.
  Re-open it before quoting in a deck.
- "verified in file 07 or 08" means I relied on an earlier agent file and did not re-fetch it.
- "inferred" means my judgment.
- Local EDGAR downloads are under `/private/tmp/claude-501/-Users-cayden-Documents-GitHub-hackathons-CalHacks/0bb3df36-df56-4ddb-b811-b4ae74bfaf4b/scratchpad/profiles/`.
  EDGAR requests used the User-Agent `CalHacks research contact@example.com`, at most 3 requests per second, about 12 requests in total.
- No source gives numeric objective weights.
  Every weight range below is "inferred" from the direction of sourced trade-offs.
  Treat them as starting priors for the reviewer to tune, not as findings.
- Practitioner material for private-credit approvals is thin in public sources.
  Several items I looked for were not found: a law-firm diligence checklist for preferred equity, a current S&P standard-volatility table, a Goodwin distress guide (PDF had no text layer), and the White & Case asset-sale note (HTTP 403).
  Those gaps are marked where they matter.
- Nobody has had a practitioner check this file.

## Part 1 - Evidence by situation type

Each type has (a) first diligence requests, (b) objectives and trade-offs, (c) impact metrics with ranges, (d) human or committee decision points.

### Cross-cutting evidence that applies to several types

- Capital-solutions providers apply equity-style diligence to debt-like instruments: detailed models, management presentations, sector work, downside scenarios, and recovery waterfalls.
  verified (https://www.mayerbrown.com/en/insights/publications/2026/10/the-rise-of-private-capital-capital-solutions-and-the-new-architecture-of-credit)
- The same source gives target returns of 15 to 25 percent gross IRR for capital solutions, 8 to 12 percent for conventional lending, and 20 percent or more when stressed.
  It is an adviser estimate.
  verified (same URL)
- It also says providers rely on governance and information rights, transfer restrictions, exit mechanics, anti-dilution, and change-of-control terms, and that borrowers must plan for consent requirements under existing facilities and intercreditor terms.
  verified (same URL)
- A limited process with two to four providers is suggested.
  verified (same URL)
- Macfarlanes sorts complexity in opportunistic credit into structural, situational, and documentary.
  Structural means holdco and waterfall mechanics.
  Situational means time pressure and information gaps.
  Documentary means bespoke intercreditor terms and governance rights.
  verified (https://www.macfarlanes.com/insights/102mqsg/capitalising-on-dislocation-and-complexity-opportunistic-credit-in-2026)
- S&P financial risk bands (2009 criteria, superseded, so use only as a rough scale): debt/EBITDA under 1.5x minimal, 1.5 to 2x modest, 2 to 3x intermediate, 3 to 4x significant, 4 to 5x aggressive, over 5x highly leveraged.
  FFO/debt runs from over 60 percent (minimal) to under 12 percent (highly leveraged).
  verified (https://www.efis.psc.mo.gov/Document/Display/44676, a 2009 copy)
  The current standard-volatility table was not found, so confirm it before showing bands to a judge.
- Maintenance-covenant headroom (the EBITDA fall that would cause a breach against the lender-agreed base case): historically about 25 percent, now 30 percent or more in nearly all deals, 35 percent or more called "cov-loose".
  Springing revolver covenants usually apply only when the revolver is drawn past about 40 percent.
  verified (https://www.proskauer.com/alert/private-credit-deep-dives-leverage-covenants-and-auto-resets)
- Covenant-lite was 41 percent of large deals in 1H 2026 but under 4 percent below $50M EBITDA.
  verified in `CalHacks/ideation/Stochastic/README.md` (Houlihan Lokey, search summary), not re-checked.
- Amendment and waiver voting in a real credit agreement (Organogenesis, Aug 2021): ordinary amendments and waivers need Required Lenders, defined as at least two unaffiliated lenders holding more than 50 percent.
  Extending maturity or amortization, cutting rate, or raising a commitment needs each directly affected lender.
  Releasing all or substantially all collateral, or changing the voting percentages, needs all lenders.
  Subordinating the debt or liens needs all lenders.
  A minority-lender replacement mechanism exists in Section 10.1(b).
  verified (https://www.sec.gov/Archives/edgar/data/1661181/000119312521240438/d184440dex101.htm, Section 10.1 and the definition of Required Lenders)
  Other agreements differ, so the voting rule is a per-deal extracted field and not a profile constant.

### Type 1 - Raising money (new capital: preferred, convertible, junior debt, structured equity)

(a) First diligence requests.
- The existing credit agreement and every amendment, because consent and covenant room decide feasibility.
  Capital-solutions sources name consents under existing facilities, intercreditor terms, and governance rights as where deals stall.
  verified (Mayer Brown URL above)
- Sample consents show what the existing lender checks when a borrower issues preferred stock.
  A lender can bar preferred issuance or cash payment of PIK amounts without agent consent, treat cash on preferred as a restricted payment, and scope a consent to one named issuance.
  verified (https://contracts.justia.com/companies/box-inc-3071/contract/181849 and the Four Springs S-11 exhibit https://www.sec.gov/Archives/edgar/data/1558536/000110465921139383/tm2124414d7_ex10-17.htm, both search summary)
- Financial model, downside scenarios, and a recovery waterfall (investor side).
  verified (Mayer Brown URL above)
- Use of proceeds, including any share repurchase and debt paydown.
  inferred, but it matches the Organogenesis 8-K, which splits proceeds between growth uses, $23.5M of buyback, and debt repayment.
  verified (https://www.sec.gov/Archives/edgar/data/1661181/000119312524256699/d885519d8k.htm)
- Stock exchange rules on issuing more than about 20 percent of shares without a shareholder vote.
  Organogenesis capped conversion at 19.99 percent until shareholders approve, citing Nasdaq rules.
  verified (same 8-K)

(b) Objectives and trade-offs.
- Return the provider wants (15 to 25 percent IRR) against cost to the borrower, plus equity upside such as warrants or conversion.
  verified (Mayer Brown URL)
- Cash coupon versus PIK.
  Modern capital solutions pair fixed-rate cash flows with warrants or preferred, with more upside than senior debt and more equity-like risk than classic PIK mezzanine.
  verified (Macfarlanes URL)
- Dilution and control: board seat, observer, consent rights, preemptive rights.
  Organogenesis: one director seat at 5 percent or more as-converted, class vote on dividends, new senior equity, and leverage above 3.5x.
  verified (Organogenesis 8-K URL above)
- Speed and certainty: limited process, two to four providers.
  verified (Mayer Brown URL)
- Tax: not covered by any source I found, so leave it out of default weights.

(c) Impact metrics.
- Pro forma leverage under each reading of the covenant definitions, and EBITDA headroom (30 percent or more is the market norm for new cov-lite or lite deals, per the Proskauer URL above).
- As-converted ownership percentage and implied conversion premium (Organogenesis conversion price was 20 percent above the 10-day VWAP).
  verified (Organogenesis 8-K URL)
- Cash interest or dividend burden against fixed charge coverage (Organogenesis covenant floor 1.25x, see Part 3).
- Liquidity after the deal.

(d) Human decision points.
- Consent from Required Lenders (or all or each-affected lenders for some changes).
  verified (credit agreement Section 10.1 URL above)
- Board and committee approval, especially for related-party transactions.
  Organogenesis had its Audit Committee and a Transaction Committee approve the buyback from directors and affiliates.
  verified (Organogenesis 8-K URL)
- Counsel on securities exemption and exchange rules (inferred).

### Type 2 - Mergers and acquisitions (financing an acquisition)

(a) First diligence requests.
- Sources and uses, purchase price multiple, and the target's quality of earnings (inferred, standard practice; no source fetched).
- Certainty of funds.
  Sponsors and sellers ask for narrow closing conditions in the financing: a material-adverse-change condition tied to the purchase agreement, a short list of specified representations, and collateral limited to items perfected at closing.
  verified (https://sfnet.com/home/education/glossary-detail/sungard-provisions, search summary)
- The buyer's existing credit agreement: permitted acquisition limits (Organogenesis caps consideration per acquisition at $100M with further conditions), debt incurrence, and change of control.
  verified (Organogenesis credit agreement Section 7.8 text, line search in the downloaded exhibit)

(b) Objectives and trade-offs.
- Certainty of closing and speed weigh most for the buyer, because the seller will not wait.
  verified (SFNet URL above for the purpose of these provisions)
- Leverage against equity check.
  2025 averages: closing leverage 5.1x and equity about 46 percent of capitalization in Proskauer's private-credit data; 7.2x average purchase multiple in GF Data's lower-middle-market data.
  verified (https://www.proskauer.com/report/proskauer-releases-15th-annual-private-credit-insights-report and https://www.acg.org/news-trends/news/gf-data-releases-q4-2025-ma-and-leverage-reports, both search summary)
  Another dataset showed 3.8x for the middle market, so treat leverage as a range of roughly 3.8x to 5.1x depending on deal size.
  verified (https://mercercapital.com/insights/newsletters/middle-market-transaction-update-newsletter/middle-market-transaction-update-winter-2025/, search summary)
- Covenant reset after an acquisition.
  Auto-reset clauses re-apply the original headroom to pro forma leverage, often one time, within about three years, and sometimes only for deals adding more than 20 percent EBITDA.
  verified (Proskauer deep dive URL above)

(c) Impact metrics.
- Pro forma total and senior leverage, EBITDA headroom, fixed charge coverage, equity percentage, and purchase multiple.
- Ranges: see (b).

(d) Human decision points.
- Commitment to a financing source before the purchase agreement is signed (inferred).
- Lender consent if the acquisition exceeds permitted limits.
- Board and, for a public target, a special committee (inferred).

### Type 3 - Company in financial trouble (covenant defaults, liquidity shortfall)

(a) First diligence requests.
- A rolling 13-week cash flow forecast, with actual-versus-budget variance reports.
  Forbearance agreements commonly require it and often require outside advisers.
  verified (https://www.taftlaw.com/news-events/law-bulletins/distressed-companies-q-and-a/)
- Forbearance terms: 90 or 180 days, a release of claims against the lender, and limits on dividends, repurchases, and payments to insiders.
  verified (same Taft URL)
- A forecast can itself create default risk when a liquidity floor is tied to it.
  verified (https://www.sec.gov/Archives/edgar/data/1479920/000110465911050724/a11-26129_1ex10d6.htm, search summary)
- After a default the loan often moves from the relationship banker to a troubled-loan specialist.
  verified (Taft URL)
- Lifecore (Jan 2023) shows the package: waiver of past defaults, revolver cut to $60M, margin up 2.0 percent in kind, amortization pushed out, preferred written in as permitted with a $30M proceeds test.
  verified in file 08 (not re-fetched).

(b) Objectives and trade-offs.
- Time and certainty beat price.
  Reason: the forbearance clock is 90 to 180 days and the lender controls the conditions.
  verified (Taft URL) for the clock, inferred for the weighting.
- Cure through new equity versus amendment fee and margin step-ups.
  Lenders prefer an equity injection that lowers net leverage and an earlier seat at the table.
  verified (Proskauer deep dive URL, which lists these as lender considerations)
- Control: distressed investors seek governance and veto rights.
  verified in file 08 (Lifecore preferred holders got a veto over debt above $175M).

(c) Impact metrics.
- Liquidity runway in weeks (from the 13-week forecast), covenant headroom, fixed charge coverage, cash burn.
- Recovery value by class, relevant if the plan fails.
  Long-run recovery on defaulted senior secured bonds averaged about 61 percent for 1987 to 2022, senior unsecured about 47 percent, subordinated about 28 percent.
  verified (https://www.barings.com/globalassets/2-assets/perspectives/viewpoints/insights/2023/10-october/the-investment-case.pdf, search summary, citing Moody's)
  Loans recovered more than bonds in earlier Moody's data (80.7 percent for loans, 1987 to 2008).
  verified (search summary of the same family of sources, no direct URL read)

(d) Human decision points.
- Whether to sign a forbearance or waiver (lender decides terms; board decides to accept).
- Whether to hire a restructuring adviser or chief restructuring officer (inferred from the Taft "outside experts" condition).
- Whether to go to court (see Type 6).

### Type 4 - Refinancing (replace or extend existing debt)

(a) First diligence requests.
- Maturity schedule and the maturity wall.
  Speculative-grade non-financial maturities are forecast to rise from $309.2bn in 2026 to $942.3bn in 2028.
  verified (Macfarlanes URL above)
- Call protection in the existing loan.
  A soft call is typically a 1 percent premium for repricing within about 6 months of closing.
  A hard call in riskier credits is typically a 1 to 3 percent premium regardless of purpose.
  verified (https://www.cliffordchance.com/content/dam/cliffordchance/briefings/2016/04/how-soft-is-your-soft-call.pdf, read from the downloaded PDF)
- Soft call resets are common in amend-and-extend deals: the 101 premium restarts for 6 months, and non-consenting lenders can be repaid at 101.
  verified (https://www.sec.gov/Archives/edgar/data/885590/000119312522146413/d298928dex101.htm, search summary)
- The Organogenesis revolver and term loan both mature August 6, 2026.
  verified (credit agreement URL, definition of Revolving Termination Date, and the Q2 2024 10-Q URL in Part 3)

(b) Objectives and trade-offs.
- All-in cost (margin, fees, call premium) against maturity length and covenant flexibility.
  inferred, with the call-protection numbers above as the sourced part.
- Lender mix: institutional lenders want yield protected, banks want deleveraging.
  verified (Clifford Chance PDF above)
- Extension needs each affected lender (maturity change), so a holdout can block an extension.
  verified (Section 10.1 of the Organogenesis agreement)

(c) Impact metrics.
- Interest saving net of premium and fees, weighted average maturity, covenant headroom after reset, liquidity.

(d) Human decision points.
- Consent of each affected lender for a maturity extension.
- Treasurer or CFO sign-off on call premium payments (inferred).

### Type 5 - Selling part of a company (asset sale, carve-out, divestiture)

(a) First diligence requests.
- The asset-sale definition and its exclusions, the net-proceeds sweep, reinvestment rights, and thresholds.
  A creditor-side explainer says there is no universal sweep figure and the analysis is a traceable map of proceeds.
  verified (https://www.creditgpt.com/content/asset-sale-sweeps-and-reinvestment-rights)
- Sample clauses show a 12-month reinvestment window (another uses 360 days), de minimis amounts such as $15M per 12 months, and a lender waiver tied to a minimum prepayment of US$325M for one divisional sale.
  verified (https://corporate.findlaw.com/contracts/finance/waiver-of-mandatory-prepayment-provisions-of-credit-agreement.html and https://lawinsider.com/clause/mandatory-prepayments-commitment-reductions/_1, search summary)
- Collateral release mechanics and which lenders must consent.
  Release of all or substantially all collateral needs every lender in the Organogenesis agreement.
  verified (Section 10.1 URL above)
  How a partial release works for a single asset sale was not found.

(b) Objectives and trade-offs.
- Use of proceeds: repay debt (sweep) or reinvest, against the remaining business's leverage and collateral.
  inferred.
- Closing certainty and timeline to the buyer.
  inferred.

(c) Impact metrics.
- Net proceeds after tax and fees, pro forma leverage of RemainCo, EBITDA given up, collateral coverage after release.

(d) Human decision points.
- Lender waiver of the sweep or release of liens (Required Lenders or all lenders depending on scope).
- Board approval for a sale of a significant part of the business (inferred).

### Type 6 - Bankruptcy (detect, stop, escalate; DIP shown for reference only)

(a) First diligence requests (for a DIP lender).
- A court-approved budget, usually 13 weeks, on a cash basis.
  verified (https://www.cfo.com/news/a-key-for-getting-debtor-in-possession-financing/662135/, search summary)
- Collateral value as a going concern against liquidation, adequate protection for any primed lender.
  verified (https://www.stout.com/en/insights/article/recent-trends-and-developments-dip-financing, article dated September 2014)

(b) Objectives and trade-offs.
- Lenders control spending, set milestones with no cure, and can terminate on short notice.
  Sample Southern District of Texas orders show lender budget approval, milestones, and 5-day termination.
  verified (https://researchsuite.stretto.com/landing/samples/AI Dossier - Recent SDTX DIP Financings 1.pdf, search summary, secondary)
- Roll-up of prepetition debt into the DIP is controversial and is meant for when no other DIP is available.
  verified (Stout URL)
- Maturities are now often one year or less.
  verified (Stout URL)
- Example sale milestones: auction within 75 days, plan confirmation within 150 days.
  verified (https://app.bondoro.com/preview/cases/Eew_American_Offshore_Structures_Inc/dip-terms, search summary)
- Red Lobster DIP: $275M, $100M new money and $175M roll-up.
  verified in file 07 (not re-fetched).

(c) Impact metrics.
- Weekly liquidity, milestone compliance, recovery by class, new money versus roll-up ratio.

(d) Human decision points.
- The Bankruptcy Court approves DIP financing after notice and a hearing, and priming liens need findings on adequate protection.
  verified (Stout URL)
- The product does not run this type.
  Detect, stop, and escalate to the human, as set in `CalHacks/ideation/Stochastic/README.md`.

### Type 7 - Borrowing against assets (ABL, equipment, receivables, GPU-backed)

(a) First diligence requests.
- Borrowing base certificate, receivable aging, inventory reports, and a field exam.
  A survey exam underwrites a new facility and recurring exams check for changes.
  Examiners test receivables against shipping documents and collections, and inventory against receipts and counts.
  verified (https://www.sfnet.com/home/industry-data-publications/the-secured-lender/magazine/tsl-article-detail/abl-primer-for-students--interns-and-industry-newcomers and the Vorys ABL diligence article https://www.vorys.com/publication-Four-Tips-for-Improving-ABL-Diligence-Before-the-Next-Market-Downturn, the latter search summary)
- Appraisals of inventory and equipment on net orderly liquidation value (NOLV) or forced liquidation value.
  verified (SFNet URL)
- Perfection certificate and lien searches.
  verified (Vorys URL, search summary)

(b) Objectives and trade-offs.
- Cost of a collateral-based facility against availability.
- Advance rates: 70 to 90 percent of eligible receivables and 20 to 75 percent of NOLV for inventory.
  verified (SFNet URL)
- Concentration, dilution, and ineligibles reduce the base.
  verified (SFNet URL)

(c) Impact metrics.
- Excess availability (lesser of base or commitment, minus loans and letters of credit), days sales and inventory outstanding, dilution, concentration.
  verified (SFNet URL)
- Thresholds for springing covenants and dominion triggers were not found.

(d) Human decision points.
- Lender credit committee on advance rates and reserves (inferred).
- Legal review of perfection and priority on default.
  verified (SFNet URL)

### Type 8 - Ownership changes (sponsor sale, new controlling holder, large minority stake)

(a) First diligence requests.
- The Change of Control definition in every debt document, because most agreements make it a default or a mandatory prepayment event.
  verified (https://vectorshift.ai/glossary/change-of-control, search summary of a glossary, weak source)
  The Organogenesis agreement defines Change of Control (line 849 of the downloaded exhibit).
  verified (credit agreement URL)
- Lender consents are usually transaction-specific, come from Required Lenders (or a supermajority such as two-thirds in one 2007 filing), and often come with a redefinition of the term.
  verified (https://www.sec.gov/Archives/edgar/data/0001412204/000095013707014757/c18607exv10w11.txt and a 2026 waiver https://www.sec.gov/Archives/edgar/data/0001992243/000121390026083033/ea029971101ex10-1.htm, both search summary)
- Tax: an ownership change under Section 382 occurs when 5-percent holders raise their ownership by more than 50 percentage points over a 3-year testing period, which limits use of net operating losses.
  verified (https://www.law.cornell.edu/uscode/text/26/382)

(b) Objectives and trade-offs.
- Control, board rights, and consent rights versus price and dilution.
  verified (Organogenesis 8-K URL: director seat, observer, class votes).
- Preserving tax attributes (inferred weight).

(c) Impact metrics.
- Post-deal ownership by holder, voting power, change-of-control trigger status in each document, Section 382 test.

(d) Human decision points.
- Board, special committee for related parties, and shareholder vote for large issuances.
  verified (Organogenesis 8-K URL for the Nasdaq-driven cap and committee approvals).
- Lender waiver of Change of Control (Required Lenders in the Organogenesis form).

## Part 2 - Default profiles

Conventions for every block below.
- Objective weights are relative importance on a 0 to 1 scale.
  Midpoints sum to about 1.0 so they can be normalized.
- "control" and "speed_certainty" are additions to the three weights in the README (cost, risk, dilution).
  They are proposed because the sources treat control, certainty of closing, and speed as first-order trade-offs.
  Tax is left out because no source gave a basis for a default.
- Every value carries a label.
  Where a value rests on a number from Part 1, the URL is the Part 1 source.
- Escalation thresholds on agent confidence (for example 0.85) have no public source.
  They are "inferred" knobs and belong in the reviewer console.

### What moves the weights (applies to all types)

| Driver | Moves up | Moves down | Basis |
| --- | --- | --- | --- |
| Company is stressed (forbearance, going concern, covenant default) | speed_certainty, risk | cost, dilution | sourced direction: forbearance clock 90 or 180 days (Taft URL). Magnitude inferred. |
| Company is healthy and growing | dilution, control, cost | speed_certainty | inferred. KKR and Oaktree describe capital solutions for healthy firms (file 07). |
| Sponsor-owned | cost, speed_certainty | dilution | inferred. |
| Founder or family control | control, dilution | cost | inferred. |
| Covenant headroom under 25 percent after the plan | risk | cost | Proskauer deep dive sets 25 to 30 percent as the market norm. Weighting inferred. |
| Maturity within 24 months | speed_certainty, risk | dilution | inferred. Organogenesis maturity August 2026 is about 21 months out at the deal date. |
| Time left before a seller or lender deadline | speed_certainty | cost | sourced direction: SunGard-style provisions exist because sellers want certainty (SFNet URL). |
| Public company needing a vote above 20 percent issuance | speed_certainty, control | dilution | sourced fact: Nasdaq-driven cap in the Organogenesis 8-K. Weighting inferred. |

### 1. Raising money

```jsonc
{
  "type": "raising_money",
  "scope": {
    "documents": ["credit agreement and all amendments", "most recent 10-K and 10-Q", "term sheet or certificate of designations draft", "existing preferred or warrant terms"], // inferred; Part 1 type 1 supports the first item
    "clauses": ["indebtedness and Disqualified Stock definitions", "restricted payments", "affiliate transactions", "liens", "financial covenants", "mandatory prepayment", "amendment voting"], // sourced (Organogenesis credit agreement URL in Part 3)
    "out_of_bounds": ["tax opinions", "securities law exemptions", "exchange listing rules"] // inferred; route to counsel
  },
  "information_needed": ["lender register and vote shares", "base-case model", "use of proceeds", "board approval path", "share count and exchange cap"], // inferred; share cap fact sourced (Organogenesis 8-K URL)
  "allowed_instruments": ["convertible preferred", "straight preferred", "holdco PIK", "second lien", "mezzanine", "convertible notes", "warrants"], // sourced (file 07 C1 to C3 categories)
  "objectives": {"cost": [0.20, 0.30], "risk": [0.20, 0.30], "dilution": [0.20, 0.30], "control": [0.10, 0.20], "speed_certainty": [0.05, 0.15]}, // inferred
  "impact_measures": ["pro forma net leverage under each definition reading", "EBITDA headroom", "fixed charge coverage", "as-converted ownership", "liquidity", "cash cost per year"], // sourced direction (Proskauer URL, Organogenesis 8-K URL); list inferred
  "escalation": {"consent_vote": "Required Lenders unless the document says otherwise", "min_headroom_flag": 0.25, "act_without_asking_confidence": 0.9, "always_human": ["definition ambiguity that flips a covenant test", "any related-party step"]} // vote rule sourced (credit agreement Section 10.1); other values inferred
}
```

What moves it: healthy company raises dilution and control weights toward the top of range.
A near-term maturity or a lender deadline lowers dilution and cost and raises speed_certainty.

### 2. Mergers and acquisitions

```jsonc
{
  "type": "mergers_acquisitions",
  "scope": {
    "documents": ["buyer credit agreement", "purchase agreement draft", "target financials", "commitment letter draft"],
    "clauses": ["permitted acquisitions", "debt incurrence", "liens", "change of control", "financial covenants", "equity cure"],
    "out_of_bounds": ["antitrust", "target valuation opinion"]
  }, // documents and out_of_bounds inferred; permitted-acquisition clause sourced (Organogenesis Section 7.8 text)
  "information_needed": ["sources and uses", "target LTM EBITDA", "synergy claims (flag as unverified)", "closing timeline", "financing conditionality terms"], // inferred; conditionality terms sourced (SFNet SunGard URL)
  "allowed_instruments": ["senior term loan", "second lien", "mezzanine", "seller note", "preferred equity", "revolver draw", "equity"], // inferred
  "objectives": {"cost": [0.15, 0.25], "risk": [0.20, 0.30], "dilution": [0.10, 0.20], "control": [0.10, 0.20], "speed_certainty": [0.20, 0.30]}, // inferred
  "impact_measures": ["pro forma total and senior leverage", "headroom after auto-reset", "equity percentage of capitalization", "purchase multiple", "fixed charge coverage"], // leverage 3.8x to 5.1x and equity about 46 percent are sourced (Proskauer, Mercer URLs in Part 1); list inferred
  "escalation": {"consent_vote": "Required Lenders", "min_headroom_flag": 0.25, "act_without_asking_confidence": 0.9, "always_human": ["financing commitment before purchase agreement", "pro forma leverage over 5.0x"]} // 5.0x flag inferred from Proskauer 5.1x average
}
```

### 3. Company in financial trouble

```jsonc
{
  "type": "financial_trouble",
  "scope": {
    "documents": ["credit agreements and amendments", "compliance certificates", "13-week cash flow", "latest 10-Q", "forbearance or waiver drafts", "preferred certificates with veto rights"],
    "clauses": ["financial covenants", "events of default and cure rights", "cross-default", "restricted payments", "amendment fees and PIK step-ups", "veto and consent rights in equity documents"],
    "out_of_bounds": ["filing a petition", "fraudulent transfer analysis"]
  }, // 13-week cash flow and forbearance sourced (Taft URL); veto rights in equity documents sourced in file 08 (Lifecore); rest inferred
  "information_needed": ["weekly cash forecast with variance", "covenant calculations", "list of defaults and waived defaults", "outside adviser status", "liquidity floor terms"], // sourced (Taft URL; TBS forbearance exhibit URL in Part 1)
  "allowed_instruments": ["waiver", "forbearance", "amend and extend", "PIK margin step-up", "rescue preferred", "super-senior bridge", "equity cure"], // sourced direction (file 07 C4 to C6; file 08 Lifecore); list inferred
  "objectives": {"cost": [0.05, 0.15], "risk": [0.25, 0.35], "dilution": [0.05, 0.15], "control": [0.10, 0.20], "speed_certainty": [0.30, 0.40]}, // inferred; direction sourced (Taft URL clock)
  "impact_measures": ["liquidity runway in weeks", "covenant headroom", "fixed charge coverage", "cash burn", "recovery by class", "PIK accrual"], // list sourced direction (Taft, Barings URLs in Part 1); ranges for recovery only
  "escalation": {"consent_vote": "Required Lenders for waiver, each affected lender for maturity or amortization changes", "runway_weeks_flag": 13, "act_without_asking_confidence": 0.95, "always_human": ["signing forbearance or release of claims", "any plan with under 13 weeks runway", "any hint of insolvency filing"]} // vote rule sourced (Section 10.1); 13 weeks matches the standard forecast horizon (Taft URL); rest inferred
}
```

What moves it: runway under 13 weeks pushes speed_certainty to the top of range and risk to 0.35.
A fixable one-quarter covenant miss moves it back toward the raising-money weights.

### 4. Refinancing

```jsonc
{
  "type": "refinancing",
  "scope": {
    "documents": ["existing credit agreement and amendments", "maturity schedule", "call protection terms", "new lender term sheets"],
    "clauses": ["maturity and amortization", "prepayment premium and soft call", "mandatory prepayments", "lien release", "amendment voting for extensions"],
    "out_of_bounds": ["rating agency engagement strategy"]
  }, // call protection sourced (Clifford Chance URL); voting sourced (Section 10.1); rest inferred
  "information_needed": ["all-in cost of old and new debt", "call premium amounts", "consenting lender share", "lender identities"], // inferred
  "allowed_instruments": ["new term loan", "amend and extend", "repricing", "bond", "second lien", "ABL"], // sourced (file 07 C2 and C4 examples)
  "objectives": {"cost": [0.30, 0.40], "risk": [0.20, 0.30], "dilution": [0.00, 0.10], "control": [0.10, 0.20], "speed_certainty": [0.15, 0.25]}, // inferred
  "impact_measures": ["interest saving net of premium and fees", "weighted average maturity", "covenant headroom after reset", "liquidity", "years to next maturity wall"], // inferred; call premium sizes sourced (1 to 3 percent, Clifford Chance URL)
  "escalation": {"consent_vote": "each directly affected lender for maturity extension", "max_call_premium_pct_flag": 1.0, "act_without_asking_confidence": 0.9, "always_human": ["holdout lender risk", "paying a hard call premium"]} // vote rule sourced; 1.0 percent flag is the soft call level (Clifford Chance URL); rest inferred
}
```

### 5. Selling part of a company

```jsonc
{
  "type": "selling_part",
  "scope": {
    "documents": ["credit agreement", "asset purchase agreement draft", "security documents", "intercreditor agreement"],
    "clauses": ["asset sale covenant and definition exclusions", "net proceeds sweep and reinvestment", "collateral release", "pro rata sharing", "disposition of substantially all assets"],
    "out_of_bounds": ["buyer diligence", "price negotiation"]
  }, // sweep and sharing items sourced (creditgpt URL); collateral release vote sourced (Section 10.1); rest inferred
  "information_needed": ["tax basis and tax leakage", "EBITDA and collateral of the divested part", "stranded costs", "buyer funding certainty"], // inferred
  "allowed_instruments": ["debt paydown", "reinvestment", "waiver of sweep", "special dividend only if permitted", "amend leverage covenant"], // inferred
  "objectives": {"cost": [0.10, 0.20], "risk": [0.20, 0.30], "dilution": [0.00, 0.10], "control": [0.15, 0.25], "speed_certainty": [0.30, 0.40]}, // inferred
  "impact_measures": ["net proceeds after tax and fees", "RemainCo net leverage", "EBITDA given up", "collateral coverage after release", "sweep amount versus reinvestment window"], // inferred; reinvestment window 12 months in sample clauses (findlaw URL, search summary)
  "escalation": {"consent_vote": "Required Lenders for sweep waiver, all lenders if substantially all collateral", "act_without_asking_confidence": 0.9, "always_human": ["sale of substantially all assets", "RemainCo leverage over covenant after sale"]} // vote rules sourced (Section 10.1); rest inferred
}
```

### 6. Bankruptcy

```jsonc
{
  "type": "bankruptcy",
  "mode": "detect_stop_escalate", // sourced to ../README.md decision (Cayden, 2026-10-23); the agents do not run this type
  "scope": {"documents": ["petition or draft petition", "DIP term sheet", "13-week budget", "first-day declarations"], "clauses": ["automatic default on filing", "DIP priority and priming", "milestones", "roll-up"], "out_of_bounds": ["everything else"]}, // inferred; items sourced (Stout URL)
  "information_needed": ["confirm whether a petition is filed or planned", "who the debtor counsel is"], // inferred
  "allowed_instruments": [], // sourced to README decision
  "objectives": "not applied", // reference ranges if a future build covers it: cost 0.05-0.15, risk 0.20-0.30, dilution 0.00-0.05, control 0.15-0.25, speed_certainty 0.35-0.45 (inferred)
  "impact_measures": ["weekly liquidity", "milestone dates", "recovery by class"], // inferred
  "escalation": {"always_human": ["any filing signal", "any request to price a DIP"], "act_without_asking_confidence": 1.0} // inferred; court approval requirement sourced (Stout URL)
}
```

### 7. Borrowing against assets

```jsonc
{
  "type": "asset_based_borrowing",
  "scope": {
    "documents": ["borrowing base certificate", "AR aging", "inventory report", "appraisals", "field exam", "perfection certificate", "existing lien searches"],
    "clauses": ["lien baskets", "borrowing base definitions", "eligibility", "reserves", "sale-leaseback limit", "cash dominion"],
    "out_of_bounds": ["valuation of collateral by the agents (use appraisals only)"]
  }, // sourced (SFNet URL, Vorys URL); sale-leaseback limit seen in Organogenesis Section 7.12
  "information_needed": ["eligible receivables and inventory by aging", "dilution rate", "customer concentration", "NOLV appraisal"], // sourced (SFNet URL)
  "allowed_instruments": ["ABL revolver", "receivables facility", "equipment loan", "FILO tranche", "sale-leaseback only if permitted"], // inferred; FILO example in file 07
  "objectives": {"cost": [0.25, 0.35], "risk": [0.25, 0.35], "dilution": [0.00, 0.05], "control": [0.10, 0.20], "speed_certainty": [0.15, 0.25]}, // inferred
  "impact_measures": ["excess availability", "borrowing base trend", "dilution", "concentration", "DSO and DIO", "advance rate versus 70 to 90 percent AR and 20 to 75 percent of NOLV"], // sourced (SFNet URL)
  "escalation": {"act_without_asking_confidence": 0.9, "min_excess_availability_flag": "set by reviewer", "always_human": ["advance rate above the sourced range", "collateral with no appraisal", "fast-depreciating collateral such as GPUs"]} // ranges sourced (SFNet URL); rest inferred
}
```

### 8. Ownership changes

```jsonc
{
  "type": "ownership_change",
  "scope": {
    "documents": ["credit agreement", "certificate of designations or charter", "shareholder agreements", "stock repurchase or purchase agreements", "cap table"],
    "clauses": ["Change of Control definition", "mandatory prepayment on change of control", "affiliate transactions", "equity transfer restrictions", "board and consent rights"],
    "out_of_bounds": ["tax structuring beyond a Section 382 flag"]
  }, // inferred; Change of Control definition present in Organogenesis agreement (verified)
  "information_needed": ["pre and post ownership by holder", "voting power", "NOL balance", "related-party identities"], // Section 382 test sourced (Cornell URL); rest inferred
  "allowed_instruments": ["redefine Change of Control", "waiver", "stock purchase", "preferred with governance rights", "voting agreements"], // inferred
  "objectives": {"cost": [0.10, 0.20], "risk": [0.15, 0.25], "dilution": [0.10, 0.20], "control": [0.25, 0.35], "speed_certainty": [0.15, 0.25]}, // inferred
  "impact_measures": ["ownership and voting by holder", "triggers hit in each document", "Section 382 owner shift versus 50 points", "board composition"], // 50-point test sourced (Cornell URL)
  "escalation": {"consent_vote": "Required Lenders for waiver", "always_human": ["any related-party transaction", "any shift near 50 points", "any trigger in a document the system could not read"], "act_without_asking_confidence": 0.9} // vote rule sourced; rest inferred
}
```

### Multi-label rule (inferred)

When a deal has several labels, merge profiles this way.
- scope and information_needed: union.
- allowed_instruments: intersection of the primary label with any hard limits from the second label, then union for options (so Organogenesis keeps preferred and also runs the ownership triggers).
- objectives: use the primary label's ranges, and take the wider range for control when ownership_change is a secondary label.
- impact_measures: union.
- escalation: the strictest value per field.

## Part 3 - Organogenesis, "raising money" profile from pre-deal public information only

### Information cut-off

- Replay cut-off: before the 8-K filed 2024-11-13 (event date 2024-11-12).
  verified (https://data.sec.gov/submissions/CIK0001661181.json)
- The Q3 2024 10-Q was filed 2024-11-12, the same day as the deal.
  Exclude it, so the last periodic report is the Q2 10-Q filed 2024-08-08.
  verified (same submissions JSON)
- Allowed inputs:
  - Credit Agreement dated August 6, 2021 (Exhibit 10.1 to the 8-K filed 2021-08-09): https://www.sec.gov/Archives/edgar/data/1661181/000119312521240438/d184440dex101.htm
  - First Amendment, December 8, 2022: https://www.sec.gov/Archives/edgar/data/1661181/000095017023005585/orgo-ex10_33.htm
  - Second Amendment, April 17, 2023: https://www.sec.gov/Archives/edgar/data/1661181/000095017023020627/orgo-ex10_1.htm
  - FY2023 10-K: https://www.sec.gov/Archives/edgar/data/1661181/000095017024023150/orgo-20231231.htm
  - Q2 2024 10-Q: https://www.sec.gov/Archives/edgar/data/1661181/000095017024094009/orgo-20240630.htm
- Not allowed as inputs: the Third Amendment, the 8-K, the term sheet circulated about November 7, 2024, the Avista subscription agreement.
  I read the Third Amendment and the 8-K only to check the file 08 facts and to build the answer-key comparison.
- The plan the system is handed (a convertible preferred of up to $130M, 8 percent dividend, holder redemption after seven years, about $23.5M buyback) comes from the announcement, so it is a plan input and not pre-deal public information.
  This repeats the caveat in file 08.

### Facts the system would have (all verified)

| Fact | Value | Source |
| --- | --- | --- |
| Facility | $200M total: $75M term loan plus $125M revolver, with a $75M incremental limit | credit agreement URL |
| Maturity | Both revolver and term loan, August 6, 2026 | credit agreement URL, Q2 10-Q URL |
| Pricing | Term SOFR plus 2.00 to 3.25 percent by net leverage; commitment fee 0.25 to 0.45 percent | Q2 10-Q URL |
| Balances at 2024-06-30 | Term loan $63.75M, revolver undrawn, $125.0M available | Q2 10-Q URL |
| Cash at 2024-06-30 | $89.9M cash and equivalents | Q2 10-Q URL |
| Compliance | In compliance with covenants at 2024-06-30 | Q2 10-Q URL |
| Covenant 7.1(a) | Fixed charge coverage at least 1.25x | credit agreement URL |
| Covenant 7.1(b) | Total net leverage at most 3.00x from the quarter ending Dec 31, 2023; cash netting capped at $25M of Qualified Cash | credit agreement URL |
| Revenue and EBITDA | FY2023 revenue $433.1M and Adjusted EBITDA $42.6M; H1 2024 revenue $240.2M (H1 2023 $225.0M), H1 2024 Adjusted EBITDA $18.2M (H1 2023 $19.2M) | 10-K URL, Q2 10-Q URL |
| Prior amendments | First: SOFR conversion. Second: operating accounts clause. Neither touches equity or debt baskets | amendment URLs |
| Lender voting | Required Lenders: at least two unaffiliated lenders holding over 50 percent | credit agreement URL |

Derived (inferred) figure.
LTM Adjusted EBITDA at June 30, 2024 is about $41.6M (42.616 minus 19.171 plus 18.200, in $M).
This uses the company's Adjusted EBITDA and not the agreement's "Consolidated EBITDA", so the true covenant figure may differ.

### Profile (filled in)

```jsonc
{
  "type": "raising_money",
  "secondary_labels": [{"type": "ownership_change", "confidence": "inferred, because of a board seat, class votes, and 19.99 percent cap"}], // inferred; consistent with ../README.md
  "scope": {
    "documents": [
      "Credit Agreement 2021-08-06 (conformed copy missing, see escalation E1)",   // verified (credit agreement URL)
      "First Amendment 2022-12-08, Second Amendment 2023-04-17",                  // verified (amendment URLs)
      "FY2023 10-K and Q2 2024 10-Q",                                             // verified (10-K and 10-Q URLs)
      "term sheet and certificate of designations draft (supplied by user)"       // inferred; not public before the deal
    ],
    "clauses": ["1.1 Disqualified Stock", "1.1 Indebtedness (clause g)", "1.1 Consolidated Total Indebtedness", "1.1 Liquidity and Qualified Cash", "2.12 mandatory prepayments", "7.1 financial covenants", "7.2 indebtedness baskets", "7.6 restricted payments (e), (f), (g)", "7.11 affiliate transactions", "10.1 amendments and waivers"], // verified (credit agreement URL)
    "out_of_bounds": ["Nasdaq 20 percent rule and stockholder vote", "Reg D exemption", "director conflict analysis for the buyback"] // inferred
  },
  "information_needed": ["lender register and each lender's share of term loan and commitments (Schedule 1.1A)", "Guarantee and Collateral Agreement", "Q3 2024 results (not available at cut-off)", "preferred term sheet incl. cash-pay option and redemption date", "list of repurchase counterparties and whether affiliates"], // inferred; Schedule 1.1A and agreements exist in the credit agreement (verified)
  "allowed_instruments": ["convertible preferred (PIK or cash dividend)", "prepay term loan", "straight preferred", "second lien (blocked by 7.2 baskets of $5M general)", "common equity PIPE"], // inferred; basket size sourced (credit agreement Section 7.2(h), $5,000,000)
  "objectives": {"cost": [0.20, 0.25], "risk": [0.20, 0.30], "dilution": [0.20, 0.30], "control": [0.15, 0.20], "speed_certainty": [0.05, 0.15]}, // inferred, healthy-company end: cash $89.9M and covenant compliance (Q2 10-Q URL)
  "impact_measures": ["total net leverage under reading A (preferred excluded) and reading B (preferred counted as Indebtedness)", "EBITDA headroom against 3.00x", "fixed charge coverage against 1.25x", "Liquidity", "as-converted ownership", "cash dividend capacity under 7.6(f)"], // inferred; covenant levels verified
  "escalation": "see E1 to E10 below"
}
```

Why these weights.
- Healthy company: $89.9M cash, undrawn $125M revolver, in compliance (Q2 10-Q URL).
  That supports low speed_certainty and higher dilution and control.
- Maturity is August 2026, about 21 months from the deal date (inferred arithmetic).
  That keeps speed_certainty at 0.05 to 0.15 and not lower.

### Illustrative blocking test (inferred, depends on E2)

Reading B counts the preferred at its full amount as Indebtedness through clause (g), which covers payments on Disqualified Stock.
verified (credit agreement URL, definition of Indebtedness)
The amount counted is the maximum payable plus accrued dividends.
verified (credit agreement URL, definition of Disqualified Stock)
Rough numbers (inferred): term loan $63.75M plus $130M preferred equals $193.75M.
Less the $25M cash netting cap gives $168.75M.
Divided by about $41.6M LTM Adjusted EBITDA gives about 4.1x against a 3.00x covenant.
Reading A (preferred excluded) leaves about $38.75M net of the cap, or under 1.0x.
The $130M preferred alone is about 3.1x.
This is the core "plan passes or fails depending on a definition" demo number, with the EBITDA caveat above.

### Escalations the system would raise (with evidence)

| ID | Escalation | Type | Evidence | Verified or inferred |
| --- | --- | --- | --- | --- |
| E1 | Missing document: no conformed credit agreement. Only the base agreement and two amendments are available, and the system cannot prove there are no other amendments, waivers, or side letters. | missing document | amendments exist as separate exhibits (amendment URLs) | verified that gap exists; need is inferred |
| E2 | Ambiguous definition: is the preferred "Disqualified Stock"? The definition covers stock redeemable at the holder's option on or before 91 days after the loans mature. Loans mature Aug 6, 2026, so the window ends Nov 5, 2026. A holder redemption right in 2031 falls outside the window. The announced cash-in-lieu payment date of Nov 5, 2026 falls exactly on the boundary, but that term was not public before the deal. The conversion feature at the holder's option also needs reading. | ambiguity | Disqualified Stock definition (credit agreement URL); the 8-K cash-in-lieu date (8-K URL) is used only to confirm the arithmetic | verified for text and date arithmetic; the legal outcome is inferred |
| E3 | Plan blocked by 7.6(g): dividends are allowed only if payable in Capital Stock other than Disqualified Stock. A PIK dividend on a preferred that is Disqualified Stock is not allowed. | blocked plan | 7.6(g) text (credit agreement URL) | verified text; outcome depends on E2 |
| E4 | Plan blocked by 7.6(e): a buyback is allowed only with proceeds of a substantially concurrent issue of Capital Stock other than Disqualified Stock. The $23.5M buyback has no other basket, because the general restricted-payments basket 7.6(f) is $7.5M per fiscal year. | blocked plan | 7.6(e) and (f) text (credit agreement URL) | verified |
| E5 | Plan blocked by 7.2: if the preferred is Disqualified Stock it is Indebtedness (clause g), and no basket fits. The general basket is $5.0M. | blocked plan | Indebtedness definition and 7.2(h) (credit agreement URL) | verified text; outcome depends on E2 |
| E6 | Covenant flip: leverage covenant 7.1(b) at 3.00x passes or fails depending on whether the preferred is in Consolidated Total Indebtedness. Run both readings and show both. Also flag that the covenant uses "Consolidated EBITDA", not the company's Adjusted EBITDA. | ambiguity and numeric | 7.1(b) and definitions (credit agreement URL); illustrative test above | verified text; numbers inferred |
| E7 | Cash-pay option: the plan lets the company pay the 8 percent dividend in cash. Cash dividends on preferred are not permitted outside the $7.5M per year basket (7.6(f)), and the later amendment still withholds consent for any dividend not permitted by 7.6. Block the cash-pay option and route it. | blocked plan | 7.6 text (credit agreement URL); Third Amendment clause (b) and clause 4(f) (https://www.sec.gov/Archives/edgar/data/1661181/000119312524256699/d885519dex102.htm) | verified |
| E8 | Affiliate transactions: 7.11 requires an affiliate transaction to be permitted elsewhere, in the ordinary course, and on arm's-length terms, all three. A buyback from directors and their affiliates is not ordinary course. | blocked plan | 7.11 text (credit agreement URL); the later amendment rewrote 7.11(b) | verified text; reading inferred |
| E9 | Lender consent path: the amendment needs Required Lenders (two unaffiliated lenders over 50 percent). Without the lender register the system cannot say who must sign. Also, the term loan and revolver both mature Aug 2026, so lenders have leverage in the negotiation. Ask the user for the register and propose what to offer lenders (inferred; the real deal prepaid the term loan). | consent and strategy | Required Lenders definition and 10.1 (credit agreement URL) | verified text; the offer idea is inferred |
| E10 | Out-of-scope items to hand to counsel and the board: Nasdaq stockholder-vote rule and the 19.99 percent cap, related-party approval, securities exemption. | out of scope | not in the credit agreement | inferred (the 8-K confirms such terms existed but they were not public before) |

Outcome check against the real amendment (post-deal, used as an answer key only).
- The Third Amendment fixed E3 by adding preferred PIK dividends to 7.6(g), fixed E4 by deeming up to $50M of buyback concurrent if within two weeks, fixed E5 by a new 7.2 clause "to the extent constituting Disqualified Stock", fixed E6 by excluding the preferred from Consolidated Total Indebtedness, and fixed E8 by editing 7.11(b).
  verified (https://www.sec.gov/Archives/edgar/data/1661181/000119312524256699/d885519dex102.htm)
- It also required the term loan to be prepaid within one business day of the first preferred issuance, and set a lenders' price for cash settlement: no default, pro forma leverage 0.25x inside the covenant, and Liquidity of at least $100M.
  verified (same URL and the 8-K URL)
- The amendment defines the preferred as issued in an initial installment of at least $65M by Nov 15, 2024 and total installments up to $150M.
  verified (same URL)
  That is a structure feature (a staged raise) the pre-deal profile would not have predicted.

### Correction to file 08 (inferred, for the team to check)

File 08's blocking-clause table says holder redemption rights make the preferred Disqualified Stock.
The text of the definition is narrower: only redemption at the holder's option on or before 91 days after loan maturity counts, and a 2031 redemption date is outside that window.
The amendment's wording "to the extent constituting Disqualified Stock" supports reading it as an open question that the lenders chose to settle by contract.
Treat E2 as the real ambiguity in the demo, not as a clear block.

## Part 4 - What a practitioner must confirm, and what can be a user setting

### Practitioner must confirm (all are "inferred" or weakly sourced)

1. The objective weight ranges for all eight types.
   No source gives numbers.
2. The extra dimensions "control" and "speed_certainty" as the right additions to cost, risk, dilution, and whether tax should be a sixth.
3. The treatment of redeemable or convertible preferred as Indebtedness or as equity in each document, because it flips covenant tests (already an open conflict in files 01 and 02).
4. The mapping of leverage bands to "risk" scores.
   The only band table I verified is S&P's 2009 matrix, and current criteria differ.
5. Headroom flag at 25 percent.
   The sourced norm is 30 percent or more for new deals, but existing credits can be tighter.
6. Escalation confidence thresholds (0.85 to 1.0 above) and the 13-week runway flag.
7. The consent vote rules.
   They must be extracted per deal, not fixed in the profile.
   Practitioners should confirm the rule that maturity extension needs each affected lender holds in the document family used.
8. The decision to stop at "detect and escalate" for bankruptcy, and whether DIP reference weights belong in any later build.
9. Which instruments are allowed per type, in particular whether a rescue deal may use super-senior bridge paper.
10. Whether the Organogenesis reading of Disqualified Stock (E2) is correct.
11. Multi-label merge rule (strictest escalation, union of scope).

### Safe as reviewer console settings (user knobs)

These are preferences or risk appetite, not facts, so a senior reviewer can set them per deal.
- A single risk-appetite slider that shifts weight between risk and cost within the sourced range for that type.
- A dilution-versus-cost slider (the board's preference).
- A control sensitivity slider (founder or sponsor preference).
- Minimum acceptable EBITDA headroom (start at 25 percent, allow 15 to 40 percent).
- Minimum liquidity floor or runway in weeks.
- Maximum pro forma leverage for the plan.
- Agent-confidence threshold for acting without asking.
- Which scenarios the Monte Carlo emphasizes (recession severity), with defaults labeled as assumptions.
- Lock lists: instruments the company will never use (for example no cash-pay preferred).

### Not to be a user setting (must come from documents or counsel)

- Covenant levels, basket sizes, definitions, voting thresholds, maturity dates.
- Whether an instrument counts as debt under a given agreement.
- Legal conclusions on enforceability, exchange rules, and tax.

## Source list (all URLs used)

- https://www.sec.gov/Archives/edgar/data/1661181/000119312524256699/d885519d8k.htm (Organogenesis 8-K, fetched)
- https://www.sec.gov/Archives/edgar/data/1661181/000119312524256699/d885519dex102.htm (Third Amendment, fetched, used as answer key only)
- https://www.sec.gov/Archives/edgar/data/1661181/000119312521240438/d184440dex101.htm (Credit Agreement 2021, fetched)
- https://www.sec.gov/Archives/edgar/data/1661181/000095017023005585/orgo-ex10_33.htm (First Amendment, fetched)
- https://www.sec.gov/Archives/edgar/data/1661181/000095017023020627/orgo-ex10_1.htm (Second Amendment, fetched)
- https://www.sec.gov/Archives/edgar/data/1661181/000095017024094009/orgo-20240630.htm (Q2 2024 10-Q, fetched)
- https://www.sec.gov/Archives/edgar/data/1661181/000095017024023150/orgo-20231231.htm (FY2023 10-K, fetched)
- https://data.sec.gov/submissions/CIK0001661181.json (filing dates, fetched)
- https://www.mayerbrown.com/en/insights/publications/2026/10/the-rise-of-private-capital-capital-solutions-and-the-new-architecture-of-credit (fetched)
- https://www.macfarlanes.com/insights/102mqsg/capitalising-on-dislocation-and-complexity-opportunistic-credit-in-2026 (fetched)
- https://www.proskauer.com/alert/private-credit-deep-dives-leverage-covenants-and-auto-resets (fetched)
- https://www.taftlaw.com/news-events/law-bulletins/distressed-companies-q-and-a/ (fetched)
- https://www.stout.com/en/insights/article/recent-trends-and-developments-dip-financing (fetched, 2014 article)
- https://www.cliffordchance.com/content/dam/cliffordchance/briefings/2016/04/how-soft-is-your-soft-call.pdf (fetched, 2016 briefing)
- https://www.sfnet.com/home/industry-data-publications/the-secured-lender/magazine/tsl-article-detail/abl-primer-for-students--interns-and-industry-newcomers (fetched)
- https://www.law.cornell.edu/uscode/text/26/382 (fetched, first 100,000 characters)
- https://www.creditgpt.com/content/asset-sale-sweeps-and-reinvestment-rights (fetched, no numbers)
- https://www.efis.psc.mo.gov/Document/Display/44676 (S&P 2009 matrix copy, fetched)
- Search-summary only: Barings (Moody's recoveries), Proskauer private credit report, GF Data via ACG, Mercer Capital, SFNet SunGard glossary, Box and Four Springs consents, Bausch soft call exhibit, findlaw and lawinsider sweep clauses, cfo.com DIP article, Stretto SDTX dossier, Bondoro EEW terms, Vorys ABL article, Debevoise note on Moody's equity credit (https://debevoise.com/insights/publications/2024/08/in-the-moodys-for-subordinated-debt-securities), 2007 and 2026 change-of-control exhibits.
