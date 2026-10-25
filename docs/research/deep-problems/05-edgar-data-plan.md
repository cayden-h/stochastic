# 05 - EDGAR data plan for Stochastic

Written 2026-10-23.
Every claim is labeled "verified (URL)" or "inferred".
Verified means I fetched that URL from the shell today with curl.
Scratch downloads (about 20 MB) are under `/private/tmp/claude-501/-Users-cayden-Documents-GitHub-hackathons-CalHacks/0bb3df36-df56-4ddb-b811-b4ae74bfaf4b/scratchpad/edgar/` and not in the repo.

## Short answer

Use EDGAR as the base.
The best demo bases are Red Robin (Fortress private-credit term loan and a covenant-amendment trail) and Carrols (nine credit-agreement amendments plus a preferred stock exchange).
Build a fictional company on top, plant traps, and keep a private answer key.
Say out loud that the company is fictional and the filings are only the structural base.
Do not use Bright Data or Apify for the core.

## 1. How to get data from EDGAR

### Rules that matter

- Declare a User-Agent with a company or project name and a contact email, for example `CalHacks research contact@example.com`.
  Replace the example address with a real team inbox before the demo.
  verified (https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
- Fair-access limit is 10 requests per second across all machines.
  The SEC may block IPs that exceed it.
  verified (https://www.sec.gov/about/developer-resources)
- Without a declared User-Agent the SEC returns HTTP 403 with an "Undeclared Automated Tool" page.
  verified (my test: `curl https://data.sec.gov/submissions/CIK0000001750.json` with no -A returned 403, 4819 bytes)
- Practical plan: stay at or under 5 requests per second, send `Accept-Encoding: gzip`, and cache everything on disk.
  inferred (a safety margin below the stated limit)

### Endpoints tested

All tested with `curl -A "CalHacks research contact@example.com"` on 2026-10-23.

| Purpose | URL | Result |
| --- | --- | --- |
| Ticker to CIK map | `https://www.sec.gov/files/company_tickers.json` | 200, 798 KB, 10,425 entries |
| Filing list per company | `https://data.sec.gov/submissions/CIK##########.json` (CIK zero padded to 10 digits) | 200, about 150 KB |
| Older filings for the same company | `https://data.sec.gov/submissions/CIK##########-submissions-001.json` (named in the `filings.files` array) | listed, not fetched |
| All XBRL facts for one company | `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` | 200, 1 to 4 MB each (Carrols, Red Robin, Papa John's, BurgerFi, Apple) |
| One concept for one company | `https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/LongTermDebt.json` | 200, 7.6 KB |
| One concept across all companies | `https://data.sec.gov/api/xbrl/frames/us-gaap/LongTermDebt/USD/CY2023Q4I.json` | 200, 305 KB |
| Full-text search | `https://efts.sec.gov/LATEST/search-index?q=...&forms=8-K&dateRange=custom&startdt=...&enddt=...&ciks=...` | 200, JSON with hits and filing ids |
| Filing folder listing | `https://www.sec.gov/Archives/edgar/data/<CIK>/<accession-no-dashes>/index.json` | 200, lists every document with sizes |
| Filing document | `https://www.sec.gov/Archives/edgar/data/<CIK>/<accession-no-dashes>/<file>` | 200 for every 8-K and exhibit I tried |

Sources: verified (https://www.sec.gov/about/developer-resources) for the host list, and my tests above for the results.

### What did not work

- `https://efts.sec.gov/LatestSearch/rest/search-index` returned 403 `{"message":"Forbidden"}`.
  The working path is `/LATEST/search-index`.
  The full-text search API is not documented on the developer page I read, so treat it as unofficial and possibly unstable.
  verified (my test) for the behavior, inferred for the "unofficial" part.
- Full-text search is noisy.
  A query like "restaurant second lien" returned business development companies and casinos.
  Filter by `ciks=` for a known company instead of searching broadly.
  verified (my test)
- Search results include metadata only (form, items, filer, file date, accession id and file name), so you still fetch the document separately.
  verified (my test)

### Financial statements

- Fastest path: `companyfacts` for the CIK, then read `facts["us-gaap"][<tag>]["units"]["USD"]`.
  Each point has `end`, `val`, `form`, `fy`, `fp`, and `accn`, so each number links back to a filing.
  verified (my test)
- Tags that exist for these companies include `LongTermDebt`, `LongTermDebtNoncurrent`, `Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax`, `OperatingIncomeLoss`, `InterestExpense`, `PreferredStockValue`, and for Papa John's `TemporaryEquityCarryingAmountAttributableToParent` (the Series B preferred).
  Not every company has every tag (BurgerFi has no `PreferredStockValue`, Red Robin has few `InterestExpense` points).
  Latest values seen: Carrols `LongTermDebt` 431.5M at 2024-03-31, Papa John's `LongTermDebt` 722.3M at 2025-12-28, Red Robin `LongTermDebt` 170.2M at 2025-12-28.
  verified (my test)
- EBITDA is not a standard tag.
  Compute it from operating income plus depreciation and amortization, and expect to adjust it by hand.
  inferred
- Use `frames` only for peer comparison (for example the same tag for all restaurant SIC 5812 companies).
  Frames returns every filer, so filter by CIK list afterward.
  inferred
- Each filing folder also holds `R*.htm` pages and `Financial_Report.xlsx` for XBRL filings, and `FilingSummary.xml`.
  verified (https://www.sec.gov/Archives/edgar/data/1171759/000117175921000061/index.json)

### Credit agreements and amendments

- They are exhibits (usually EX-10.x) to an 8-K (Item 1.01 or 2.03), a 10-Q, or a 10-K.
  Use the `submissions` JSON: the `items` array lists 8-K item numbers, and `primaryDocument` plus `accessionNumber` give the URL.
  verified (my test)
- A filter that worked: 8-K rows whose items include 1.01, 2.03, 3.02, or 3.03.
  verified (my test, script in the scratchpad)
- Exhibits are large HTML files (0.2 to 1.3 MB each).
  Credit agreement text strips to roughly 550 to 720 KB of text, which is a long-context job, so chunk by Article and Section.
  verified (my test)
- Some "amendment" exhibits are really conformed copies of the whole agreement.
  The Carrols Ninth Amendment exhibit is 705 KB, which matches a full conformed credit agreement.
  verified (https://www.sec.gov/Archives/edgar/data/809248/000080924822000123/carrols-ninthamendmentto.htm) for the size and title, inferred for "conformed copy".
- Exhibit schedules are often missing from the filed version.
  inferred (common practice, not checked here)

### 8-K announcements of new financing

- Item 1.01 (material agreement), 2.03 (new direct financial obligation), 3.02 (unregistered equity sales), 3.03 (change in security-holder rights), 8.01 and 7.01 (press release in EX-99.1).
  verified (item lists in the submissions JSON for Red Robin, Papa John's, Carrols, BurgerFi)
- The 8-K body summarizes the deal in plain English, and the EX-10 holds the full text.
  That gives a ready-made pair for the "sources disagree" check (summary versus agreement).
  verified (e.g. https://www.sec.gov/Archives/edgar/data/1171759/000095014222000996/eh220231699_8k.htm and its ex10.1)

## 2. Candidate real companies

All URLs below returned HTTP 200 and I downloaded each one.
Company descriptions come from the 8-K text I read.

### A. Red Robin Gourmet Burgers (CIK 1171759) - best overall base

Why: a full life cycle of a mid-size casual-dining borrower, from bank covenant waivers to a private-credit term loan and back to a bank refinancing.
Revenue is about 1.3 billion dollars (2019), which scales down well.

- Covenant waiver and amendment trail with a bank group (Wells Fargo agent):
  - First Amendment and Waiver, 2020-05-29: waives existing events of default, suspends leverage and fixed charge tests, raises pricing.
    https://www.sec.gov/Archives/edgar/data/1171759/000110465920067757/tm2020982-4_8kseq1.htm
  - Second Amendment, 2021-03-03.
    https://www.sec.gov/Archives/edgar/data/1171759/000117175921000017/rrgb-20210225.htm
  - Third Amendment, 2021-11-10 (waiver of the leverage covenant, changed definitions, liquidity covenant tested at all times).
    https://www.sec.gov/Archives/edgar/data/1171759/000117175921000061/rrgb-20211109.htm
    Exhibit: https://www.sec.gov/Archives/edgar/data/1171759/000117175921000061/exhibit101thirdamendmentto.htm
- Non-bank financing: 5-year, 225M dollar Credit Agreement of 2022-03-04 with Fortress Credit Corp. as administrative agent (25M revolver, 200M term loan, 1.0 percent annual amortization, secured by substantially all assets, accordion up to 40M).
  8-K: https://www.sec.gov/Archives/edgar/data/1171759/000095014222000996/eh220231699_8k.htm
  Agreement: https://www.sec.gov/Archives/edgar/data/1171759/000095014222000996/eh220231699_ex1001.htm (1.2 MB, 14 mentions of "Prepayment Premium", 319 of "Indebtedness", 25 of "Restricted Payments")
- Amendment No. 1, 2023-07-19: removes the 50M dollar cap on sale-leasebacks, adds a reinvestment right and a reduced prepayment premium on excess proceeds.
  https://www.sec.gov/Archives/edgar/data/1171759/000117175923000035/rrgb-20230717.htm
  This is a ready-made example of an amendment that quietly changes a basket.
- 2025-11-10: 40M dollar at-the-market equity program with Evercore.
  https://www.sec.gov/Archives/edgar/data/1171759/000095014225002930/eh250702594_8k.htm
- 2026-10-02 (8-K filed 2026-10-05): refinancing into a 5-year, 115M dollar Credit Agreement with JPMorgan as agent (25M revolver, 90M term loan, 5 percent amortization stepping up).
  8-K: https://www.sec.gov/Archives/edgar/data/1171759/000110465926113514/tm2626832d1_8k.htm
  Agreement: https://www.sec.gov/Archives/edgar/data/1171759/000110465926113514/tm2626832d1_ex10-1.htm
- Gap: I did not find a preferred, PIPE, or convertible deal in what I read.
  The unusual piece here is the private-credit term loan with prepayment premium and the covenant history.
  The 2024-12-03 8-K (cooperation agreement with activists, Item 3.02 present) was read only for the cooperation terms.
  https://www.sec.gov/Archives/edgar/data/1171759/000095014224002872/eh240546757_8k.htm
- Caution: the 2026 refinancing is a very recent real event, so use it as structure only, and do not present it as our scenario.

### B. Carrols Restaurant Group (CIK 809248) - best for the "missing amendment" trap

Why: one credit agreement dated 2019-04-30 with nine numbered amendments in about three years, plus preferred stock.
That is the natural setting for "which version of the covenant is in force".

- First Amendment, 2019-12-13, loosens the Total Net Leverage Ratio test (4.75 to 1.00 earlier) for the revolver.
  https://www.sec.gov/Archives/edgar/data/809248/000121390019026462/f8k121319_carrolsrestaurant.htm
- Sixth Amendment, 2021-04-06, which lists the First to Fifth Amendments by date (2019-12-13, 2020-03-25, 2020-04-08, 2020-04-16, 2020-06-23).
  https://www.sec.gov/Archives/edgar/data/809248/000080924821000075/tast-20210406.htm
- Ninth Amendment, 2022-12-15, with a 705 KB exhibit.
  8-K: https://www.sec.gov/Archives/edgar/data/809248/000080924822000123/tast-20221215.htm
  Exhibit: https://www.sec.gov/Archives/edgar/data/809248/000080924822000123/carrols-ninthamendmentto.htm (8 mentions of "Total Net Leverage Ratio")
- Preferred exchange, 2022-12-20 (8-K filed 2022-12-27): Series B shares exchanged for Series D Preferred, with a Certificate of Designation.
  https://www.sec.gov/Archives/edgar/data/809248/000080924822000129/tast-20221220.htm
  Exhibit: https://www.sec.gov/Archives/edgar/data/809248/000080924822000129/carrols-preferredstockex.htm
- Context: an 8-K on 2024-05-16 reports the merger closing (items 1.02, 2.01, 3.01, 5.01), so Carrols no longer trades.
  inferred from the item numbers only; I did not read that filing.
  https://www.sec.gov/Archives/edgar/data/809248/000114036124026400/ny20029141x10_8k.htm
- Gap: I did not read the preferred terms beyond the exchange summary.

### C. Papa John's International (CIK 901491) - best for a clean activist preferred deal

Why: a well-documented 200M dollar convertible preferred investment placed beside an existing bank credit agreement that had just been loosened.
Revenue is larger (about 2 billion dollars), so scale it down heavily.

- Starboard Value funds bought 200,000 shares of Series B Convertible Preferred Stock at 1,000 dollars per share (200M dollars), with an option for 50,000 more, convertible at the holder's option and redeemable for cash from the eighth anniversary, equal to 11.2 to 15.4 percent of common as-converted.
  https://www.sec.gov/Archives/edgar/data/901491/000110465919005561/a19-3945_18k.htm
  The folder also holds EX-10.1, 10.2, 10.3, EX-3.1 and EX-4.1 (what each exhibit is: not checked).
  https://www.sec.gov/Archives/edgar/data/901491/000110465919005561/index.json
- Credit Agreement Amendment No. 3, 2018-10-09: cut the revolver from 600M to 400M dollars, raised pricing when leverage is 3.50x or more, changed financial covenants.
  8-K: https://www.sec.gov/Archives/edgar/data/901491/000115752318002037/a51880006.htm
  Exhibit (553 KB of text): https://www.sec.gov/Archives/edgar/data/901491/000115752318002037/a51880006ex10_1.htm
- XBRL: `TemporaryEquityCarryingAmountAttributableToParent` holds the Series B balance, so the preferred appears in the statements.
  verified (companyfacts test above)
- Gap: it was not a distressed borrower, so the answer key would be a stretch case, not a rescue.
  The Series B was a strategic investment, not a covenant-driven one (inferred).

### D. BurgerFi International (CIK 1723580) - best for distress and the extreme amendment count

Why: a small company (revenue about 161M dollars for FY2023 per XBRL) with a bank credit agreement amended seventeen times, then a forbearance with a private-credit lender.

- Fifteenth Amendment, 2023-02-24, with Regions Bank as agent and a non-bank lender (CP7 Warming Bag, LP) in the group.
  https://www.sec.gov/Archives/edgar/data/1723580/000119312523049781/d268213d8k.htm
- Forbearance Agreement and Seventeenth Amendment, 2024-05-30, with TREW Capital Management Private Credit 2 LLC as lender, covering existing and anticipated Events of Default.
  https://www.sec.gov/Archives/edgar/data/1723580/000172358024000027/bfi-20240523.htm
- Acquisition of Anthony's Coal Fired Pizza and Wings (2021-10-08) paid partly in newly issued shares (86.6M dollars consideration, subject to adjustment).
  https://www.sec.gov/Archives/edgar/data/1723580/000156459021050876/bfi-8k_20211008.htm
- Settlement with an investor (Lion Point) over registration rights, 2024-07-23.
  https://www.sec.gov/Archives/edgar/data/1723580/000172358024000039/bfi-20240723.htm
- Later 8-Ks carry Item 1.03 (bankruptcy) on 2024-12-02 and 2025-03-18 in the submissions JSON.
  verified (https://data.sec.gov/submissions/CIK0001723580.json) for the item numbers, inferred for the meaning.
- Gap: I did not locate the preferred or convertible instrument itself, and a real outcome (restructuring) would leak the "answer".
  Use it for amendment-chain structure, not for a happy-path deal.

### Recommendation

Primary base: Red Robin (credit agreement text, amendments, private-credit lender, prepayment premium, sale-leaseback basket).
Secondary base for the preferred instrument: Papa John's Series B terms and Carrols Series D exchange.
Use BurgerFi only if the team wants a distressed scenario.
Buyers Edge (the case in `research.md`) is private, so its filings are not on EDGAR (inferred, I did not check EDGAR for it).

## 3. Synthetic layer design

### Disclosure rule

The demo company is fictional.
Show a banner on the intake screen and in the deck: "Fictional company. Real SEC filings are used only as a structural template."
Never present a real company's name, real lenders' names, or real dates as our scenario.
Do not claim the traps are in the real filings.
This is a labeling and fairness rule, not a legal conclusion (inferred).

### Build recipe (a fictional company from a real filing)

1. Pick the base: Red Robin 2022 credit agreement (text) plus the 2021 to 2023 amendments (structure) plus its 10-K XBRL facts (numbers).
2. Rename.
   Company, borrower, guarantors, brands, lenders, agents, and people get invented names ("Harbor Grill Holdings", "Northgate Credit Partners").
   Keep a private mapping file for provenance, and keep it out of the demo.
3. Rescale.
   Divide every dollar amount by one factor (for example revenue to about 200M dollars to match the pitch example).
   Keep ratios identical so covenant tests still behave like the original.
   Round to realistic figures and re-derive totals so the statements still add up.
4. Shift dates.
   Move all dates by a fixed offset so the deal "happens" in a recent quarter, and keep the order and gaps between events.
5. Keep structure.
   Keep the Articles, Section numbering, defined terms, amendment sequence, and instrument types.
   Rewrite only names, amounts, and dates.
6. Use an LLM only to rewrite text during the build, then freeze the output as files.
   All deal math at demo time is deterministic code, per `CalHacks/ideation/Stochastic/README.md`.
7. Produce a document pack: a synthetic 10-K style financial table set, the credit agreement with amendments, a term sheet for the new money, and a few emails or 8-K style notices that arrive during the demo (for the time dimension).

### Traps to plant (7 to 8, pick 5 to 7 for the demo)

Each trap is invented by us, and its location in the document is known to us.

| # | Trap | Where it hides | Why it matters |
| --- | --- | --- | --- |
| 1 | Debt cap lower than the plan | A basket in the negative-covenant article (for example general debt basket of a fixed dollar amount, or the greater of a dollar figure and a percent of EBITDA) | Hero case: $80M debt plan is blocked, agents must replan |
| 2 | Lease-inclusive leverage | Defined term "Indebtedness" or "Consolidated Total Debt" includes capital and finance leases (and the sale-leaseback basket) | Ratio passes on the statements but fails on the contract definition |
| 3 | Missing amendment | The amendment index shows First, Second, Fourth, but the Third is not in the folder | Agents must notice the gap, request the document, and not rely on the old covenant |
| 4 | Conflicting numbers | Amended covenant level (for example 4.50x) differs from the number in the financial model (4.75x) or the latest compliance certificate | Sources that disagree |
| 5 | Preferred equity blocked | Restricted payments clause treats preferred dividends as restricted, or requires lender consent for any preferred issuance with a mandatory redemption date inside the loan maturity | Instrument-level restriction, not just a debt cap |
| 6 | Springing or hidden covenant | A minimum liquidity test that applies only when revolver usage passes a threshold, buried in the definitions | Looks absent in a summary and appears only in the full text |
| 7 | Prepayment premium or call protection | A premium on early repayment (step-down schedule) that changes the true cost of refinancing the old loan | Changes the best mix; mirrors the Red Robin premium structure (inferred, premium schedule not read) |
| 8 | Cross-default / MFN | A most-favored-nation yield clause or cross-default to the new junior debt | Second-order effect on the junior tranche |

Keep traps believable: each one should mimic language that exists in real credit agreements.
Real clause language can be read from the Red Robin and Carrols exhibits and paraphrased, not copied word for word, to avoid presenting real contract text as ours (inferred good practice).

### Answer key format

One JSON file per scenario, stored privately and not shown to the agents.
Suggested fields:

```json
{
  "scenario_id": "harbor-grill-01",
  "fictional_notice": "Fictional company; real filings used as structural template only",
  "source_provenance": [{"base_company": "Red Robin", "accession": "0000950142-22-000996", "use": "credit agreement structure"}],
  "traps": [
    {
      "id": "T1",
      "type": "debt_cap",
      "location": {"doc": "credit_agreement.md", "section": "7.01(x)", "quote": "..."},
      "expected_finding": "Plan A adds $80M debt but basket allows $55M",
      "expected_action": "Reject Plan A, generate plan within $55M, re-run simulation, escalate",
      "severity": "blocking",
      "evidence_required": ["clause quote", "computed headroom"]
    }
  ],
  "ground_truth_numbers": {"ebitda": 0, "total_debt": 0, "headroom_by_covenant": {}},
  "acceptable_final_structures": [{"senior": 0, "junior": 0, "preferred": 0}],
  "forbidden_actions": ["approve own proposal", "state a number without citing a source"]
}
```

Score = traps found, correct action taken, evidence cited, no forbidden action.
This matches the Hyphenate request for an answer key (see `../../hyphenate-workshop.md`).

## 4. Bright Data and Apify

Recommendation: no for the core, and optional only for one narrow, real input.

- Bright Data disqualifies mocked or hardcoded demo data.
  verified (`CalHacks/ideation/tracks.md` line 36, which quotes the email)
- The Stochastic core is a seeded fictional company, which is by design not "public web data", so it cannot qualify for that prize.
  inferred
- A real, live input that does not need scraping exists: the NY Fed SOFR API returned 200 with `percentRate` 3.90 for 2026-10-22.
  verified (https://markets.newyorkfed.org/api/rates/secured/sofr/last/1.json)
  This can feed the simulation's rate path as a labeled live input, with no sponsor tool.
- If the team still wants a sponsor, the only honest use is a live feed that really drives a decision, for example pulling a day's deal press releases and showing the agent react to a new lender-term event.
  That requires the demo to truly depend on it, which adds failure risk in 36 hours, and the Hyphenate judges want the seeded company (inferred).
- Apify: a Store Actor could fetch rate or news pages, but the same logic applies, and the free plan hard-blocks when the $5 monthly usage is used up.
  verified (`CalHacks/ideation/sponsors/apify.md`, citing https://apify.com/pricing)
- Verdict: no Bright Data or Apify for the core.
  If a spare person has time, add the SOFR feed (free) and decide later whether to route it through a sponsor tool.

## 5. Legal and terms risks, and what to cache

### Risks

- EDGAR content is publicly available, but the SEC says it does not allow unclassified bots, may block IPs above 10 requests per second, and gives no technical support.
  verified (https://www.sec.gov/about/developer-resources)
- A real contact email in the User-Agent is expected; a fake address risks being blocked, and it is the team's responsibility (inferred).
- I could not confirm the SEC's wording on redistribution or copyright in this session.
  The `/privacy` page fetched (200) but my text search for "public domain" and "Copyright" found nothing, so I make no claim.
  Treat as unresolved: read https://www.sec.gov/privacy before publishing any raw filing text.
- Filings may embed third-party material (logos, quotes, exhibits from other parties), and the SEC's own disclaimers are the usual caveat (inferred, not verified).
- Using real lender and borrower names in a fake scenario could mislead judges or the named parties.
  Rename everything, and keep the fictional banner (inferred).
- Do not claim the real companies' outcomes in the answer key (for example BurgerFi's restructuring or Red Robin's 2026 refinancing).
  The real events are historical facts, but the demo must stand without them (inferred).
- Redistribution plan: publish only the synthetic documents and our code, and keep raw downloaded filings in a private cache.
  Link to the SEC URLs in the README instead of re-hosting (inferred).
- A public repo with the answer key lets later teams game it, so keep the key private or in a separate private file (inferred).
- Note from the sponsor file: Hyphenate welcomes simulated data (in the task brief), and the workshop notes say answer keys matter.
  Nobody has asked Hyphenate whether data derived from real filings has extra rules (inferred, open question).

### Cache locally

Cache these under a gitignored data folder, with the SEC accession number in each file name:

1. `company_tickers.json` (one file).
2. `submissions` JSON for the 3 to 4 chosen CIKs.
3. `companyfacts` JSON for the same CIKs (1 to 4 MB each).
4. The 8-K main documents listed in section 2 (20 to 90 KB each).
5. The credit agreement and amendment exhibits listed in section 2 (about 0.2 to 1.3 MB each).
6. `index.json` for each accession folder.
7. The extracted text version of each exhibit, chunked by Section, so the LLM never needs a second fetch.
8. The NY Fed SOFR reading with a timestamp.

At demo time make zero SEC requests.
The fetch script should skip files already on disk, send the User-Agent, sleep at least 200 ms between requests, and stop on any 403 or 429 (inferred best practice).
The whole set is under 50 MB (the scratchpad set I downloaded is 20 MB including extras).

## Open questions

- Is the contact address real, and who owns it?
- Does Hyphenate accept data derived from public filings as "simulated data" (ask at the booth)?
- Can a practitioner check at least the covenant definitions (nobody on the team has)?
- Does the team want a rescue case (Red Robin, BurgerFi) or a growth case (Papa John's)?
