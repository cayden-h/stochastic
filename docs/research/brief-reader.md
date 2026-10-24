# Research: reading a credit agreement into a Brief

Date: 2026-10-24, evening.
Why: the Brief is hand-written for one agreement (PNC and Kewaunee), so Stochastic is tested on one loan.
This file holds the research behind the Brief Reader (D20).
The design is in `architecture/brief-reader.md`.
Tags: [verified: URL or file] means we read the source.
[inferred] means our judgment.
Vendor and author numbers are self-reported.
Quotes are 15 words or fewer.

## 1. Bottom line

- The covenant and the definitions it uses are a small part of an agreement.
  The agent needs about 8K to 30K characters out of 240K to 690K. [verified: character offsets in the four agreements below]
- Our `Brief` schema fits a simple bank covenant, like PNC's or Noble Roman's.
  It does not fit sponsor-style agreements: step-downs, cash netting, percent-of-EBITDA caps, pro forma acquisitions, and several covenants at once. [verified: section 3]
- Our `ebitda()` hard-codes a base that subtracts interest income.
  Two of the four agreements below do not subtract it, and one is unclear. [verified: section 3]
- Adjustment amounts mostly do not come from the agreement.
  The agreement gives the name and the cap. The amount comes from the books. [verified: `backend/app/db/fixtures/kewaunee.py`, where pension 4,019 and stock compensation 1,018 come from the 10-K]
- Products that read credit agreements extract terms and link to the source.
  We found none that says the model is barred from producing numbers. [inferred: absence of evidence, not proof]
- Model accuracy on long contracts is far from perfect, so code must check every quote and a person must approve. [verified: CUAD and ContractEval, section 4]

## 2. Four real agreements

The text copies were fetched from EDGAR on 2026-10-24 and are not in git (the SEC redistribution question is open, `STOCHASTIC.md` section 18).

### 2.1 Mayville Engineering (MEC): bank-style, with an answer key

- Amended and Restated Credit Agreement, 2023-06-28, $250M revolver, Wells Fargo as agent. [verified: https://www.sec.gov/Archives/edgar/data/1766368/000155837023011571/tmb-20230628xex10.htm]
  The First Amendment (2025-06-26) raised it to $350M; the 10-Q says the other material terms "remained unchanged". [verified: 10-Q below]
- Covenant, Section 9.15(a): "permit the Consolidated Total Leverage Ratio to be greater than 3.50 to 1.00". [verified]
  No step-down. After an acquisition over $25M the limit steps up 0.50x for four quarters, at most 4.00x, at most twice. [verified]
- Debt: all Indebtedness, excluding net hedge obligations. It includes earn-outs, capital leases, and letters of credit drawn or not. No cash netting. [verified]
- EBITDA base: net income plus interest, taxes, and D&A. Interest income is not subtracted. [verified]
- Add-backs include non-cash charges, restructuring, transaction costs "not to exceed $2,500,000 per Acquisition", and a fixed CEO transition amount. Several cash add-backs share a cap of 15% of EBITDA, measured before the add-backs. [verified]
- Acquired EBITDA counts as if the acquisition happened on the first day of the period. [verified]
- Other covenants: interest coverage and a capex limit. [verified]
- Answer key: the 10-Qs report the ratio before and after a real add-on. [verified: we read the 3.47 figure in the September 10-Q text]
  - 2025-06-30: 1.36x against 3.50x. [verified: https://www.sec.gov/Archives/edgar/data/1766368/000155837025010445/tmb-20250630x10q.htm]
  - 2025-07-01: Accu-Fab acquired for $140.5M with revolver borrowings.
  - 2025-09-30: 3.47x against 4.00x (stepped up after the deal). [verified: https://www.sec.gov/Archives/edgar/data/1766368/000110465925106973/tmb-20250930x10q.htm]

### 2.2 Noble Roman's: the closest to PNC

- Credit Agreement, 2026-06-10, $6.9M term loan, Lake Forest Bank and Trust as sole lender, EX-10.3 to the Q2 2026 10-Q. [verified: https://www.sec.gov/Archives/edgar/data/709005/000165495426007523/nrom_ex103.htm]
- Covenant, Section 7.10(b): "Permit the Senior Leverage Ratio at any time to exceed 2.30:1.00". No step-down. [verified]
- Debt: Consolidated Funded Indebtedness minus Subordinated Indebtedness (none at closing). [verified]
- EBITDA base: net income plus interest, taxes, and D&A. Interest income is not subtracted. [verified]
- Add-backs: non-cash items, non-recurring expenses as the lender allows, closing costs "not to exceed $250,000", and GAAP rent over cash rent. Deductions mirror them. [verified]
- Test period: the last four fiscal quarters, first tested Q3 2026. [verified]
- Annex A is a compliance-certificate worksheet that lists every line in order. It is a ready template for what a Brief should hold. [verified]
- Answer key: none yet. The 10-Q says only "in compliance". [verified]

### 2.3 Portillo's: sponsor-style, a hard case

- Credit Agreement, 2023-02-02, Fifth Third as agent, $300M and $100M facilities. [verified: https://www.sec.gov/Archives/edgar/data/1871509/000187150923000005/form8-k2223exhibit101.htm]
  A First Amendment exists; we did not read it. [verified that it exists]
- Covenant, Section 7.11(a): a rent-adjusted net leverage ratio, 5.50x stepping down to 5.25x and then 5.00x. [verified]
- Debt is net of all unrestricted cash, plus eight times cash rent. The denominator is EBITDAR. [verified]
- About 13 add-backs, with per-restaurant caps, a life-of-agreement cap of $10M on transaction costs, run-rate synergies, and one shared cap of 5.0% of EBITDA. [verified]
- Answer key: none. The 10-Qs say only "in compliance". [verified]

### 2.4 Potbelly: private credit, now superseded

- Credit and Guaranty Agreement, 2023-02-07, Sagard as agent, $25M term loan, repaid 2024-02-07. [verified: https://www.sec.gov/Archives/edgar/data/1195734/000119312523031475/d390319dex101.htm]
- Covenant, Section 8.01(d): total net leverage, stepping down quarterly from 1.60x to 1.00x. [verified]
- Debt is net of cash up to $3,000,000. [verified]
- EBITDA base subtracts interest income, like our `ebitda()`. [verified]
- A 50% add-back of pre-opening costs, capped at $250,000 per period. An equity cure in 8.01(e). [verified]
- Answer key: none found. [verified for Q1 2024]

## 3. What the Brief schema cannot express

Counted over the four agreements above. [verified: section 2]

| Gap | Seen in | Today |
| --- | --- | --- |
| More than one financial covenant | 4 of 4 | One limit per Brief |
| Test period as data (last four quarters, first test date) | 4 of 4 | Free text `test_period_note` |
| Strict or inclusive limit as an enum | 4 of 4 | Free text `limit_wording` |
| Pro forma acquired EBITDA | 3 of 4 | Not modeled |
| A limit that changes over time (step-down or step-up) | 3 of 4 | One float |
| Cap scope (per period, per deal, per unit, life of agreement) | 3 of 4 | A bare `cap` |
| A different EBITDA base (interest income subtracted or not) | 3 of 4 differ or are unclear | Hard-coded in `finance.ebitda` |
| Percent-of-EBITDA caps shared across add-backs, before or after | 2 of 4 | Not modeled |
| Cash netting, with or without a cap | 2 of 4 | Not modeled |
| Rent-adjusted leverage (EBITDAR) | 1 of 4 | Not modeled |
| Partial add-backs (50% of a cost) | 1 of 4 | Not modeled |
| Equity cure | 1 of 4 | Not modeled |

The fixture `Brief` also mixes two kinds of fields. [verified: `backend/app/db/fixtures/kewaunee.py`]
`limit_wording` is a verbatim quote, but `debt_definition`, `debt_excludes`, and `ebitda_definition` are paraphrases.
So the quotes must be separate fields; "the field value appears in the agreement" does not work.

## 4. Prior art

### 4.1 Products

All vendor claims are self-reported.

- **Hebbia** extracts covenants and terms into structured data with "sentence-level citation". No review step is described. [verified: https://www.hebbia.com/resources/credit-agreement-software]
- **9fin** tracks debt, lien, payment, and investment capacity, and caps on EBITDA adjustments, with "AI-powered covenant detection" and a trace to the source. [verified: search excerpt of https://9fin.com/insights/9fin-announces-launch-of-latest-enhancements-to-covenant-capacity-tool]
- **Octus** (formerly Reorg) extracts "170+ data fields per instrument", "augmented by Octus' legal analysts". [verified: https://octus.com/company/news/octus-launches-deal-lens-and-covenantai/]
- **Ontra Insight**: abstractions "created by AI and reviewed by Ontra trained specialists". [search snippet only]
- **V7 Go** links each basket to its location and claims 15 to 20 minutes per agreement versus 3 to 5 days by hand. [search snippet: https://www.v7labs.com/automations/loan-and-credit-agreement-analysis]
- Others named in Hebbia's list: Cardo AI, CovenantIQ, Finley (compliance certificates, acquired by Concord in February 2026), Sirion, Moody's Lending Suite. [verified: Hebbia page]

The pattern: extract terms, link to the source, and sometimes have analysts review. [inferred]
Where a ratio is monitored, the vendor computes it from extracted fields.

### 4.2 Benchmarks

- CUAD: 510 contracts, 41 clause types. The best model reached 44.0% precision at 80% recall. [verified: https://arxiv.org/abs/2103.06268]
- ContractEval (2025, on CUAD): the best F1 was about 0.64. Failure modes: answering "no related clause" when one exists, and selecting too much text. [verified: https://arxiv.org/abs/2508.03080]
- ContractNLI: exceptions and negation are a main difficulty. [verified: https://arxiv.org/abs/2110.01799]
- Lost in the Middle: accuracy drops when the relevant text sits mid-context. [verified: https://arxiv.org/abs/2307.03172]
- A citation-checking study: models catch 93% to 100% of wrong-case citations but only 37% to 61% of wrong pinpoints. [verified abstract: https://consensus.app/papers/details/45e292b7502f58f4a6596e661207c2c0/]
  So a model should not check its own quotes. Code should.
- CDMizer: an LLM fills a fixed schema for derivatives collateral agreements. It is the closest precedent for "fill a fixed formalism". [verified abstract: https://arxiv.org/abs/2510.23990]
- We found no peer-reviewed benchmark for covenant extraction from credit agreements. [verified: absence in our searches]

### 4.3 Pitfalls named by practitioners

- Similar terms ("Consolidated", "Adjusted", "Pro Forma" EBITDA) get swapped. [verified: https://www.kore1.com/ai-read-credit-agreement-test/]
- "Greater of" caps come back as the dollar floor only. Step-down tables come back as one row. Caps measured before or after the add-back get mixed. [verified: Kore1]
- Amendments override the base agreement without saying so in the base text. [verified: Kore1]
- Leverage debt is often narrower than the general debt definition: undrawn letters of credit, preferred equity, and earn-outs are often excluded. [verified: https://www.sidley.com/en/insights/newsupdates/2026/03/financial-covenants-in-private-credit-transactions]
- Pro forma synergies and covenant holidays after acquisitions matter for add-on deals. [verified: Sidley]

### 4.4 A tooling constraint

Anthropic's Citations API returns quotes that point into the document, but it cannot be combined with structured outputs. [verified: https://platform.claude.com/docs/en/build-with-claude/citations]
Our backends include Droid and scripted, which do not have that API.
So we keep our own quote check in the gateway, which works on every backend. [inferred]

## 5. What a controller checks

- The compliance certificate: an officer certifies that no default exists and attaches the covenant computations by section. [verified: https://sec.gov/Archives/edgar/data/799292/000079929213000027/exhibit101-exhibitbformofc.htm]
- The schedules show debt by component, any cash netted, an EBITDA bridge from net income with each add-back and its cap, the ratio against the required level for the period, and yes or no. [inferred from search snippets of EDGAR certificate exhibits]
- Noble Roman's Annex A follows that order. [verified: section 2.2]
- So the Brief Reader should present its draft in certificate order, so the controller can check it line by line. [inferred]

## 6. How this differs from existing products (for judges)

Commercial tools extract covenant terms and link each one to its source, and some add analyst review.
Our Brief Reader is narrower and stricter.
The model only points at exact quotes and fills a fixed schema.
Code checks every quote character for character and checks that every number appears in its quote.
A person approves the Brief before any deal is tested against it, and the math is the same deterministic code as today.
We do not claim better extraction accuracy than these vendors, because we have not measured it against them.
