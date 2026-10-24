# Real public deal candidates for the Stochastic demo

Research date: 2026-10-23.
Method: SEC EDGAR filing indexes, EDGAR submissions API, and the filed exhibits themselves (fetched and read).
Labels: VERIFIED means I opened the exact URL given and read the text or numbers cited.
INFERRED means my own reasoning, or something I could not confirm in the filings.
The ranking in section 2 is INFERRED (my judgment, not a measured score).
This report does not repeat `ma-workflow-research.md` or `post-close-deliverables.md`.

---

## 1. Honest limits first

- Public filings give statement line items (about 25 to 40 lines per balance sheet), not trial balances or general ledgers.
- A mapping demo from real data is therefore a statement-line-to-statement-line mapping, not an account-level mapping.
- Account-level detail (for example "6120 Freight-in", "6130 Freight-out") must be synthetic.
- The best real data we found even includes a filed answer key for the line mapping (the Kewaunee Note 2 reclassification table).
- Pro forma statements are preliminary and "for illustrative purposes only" (their own words), so they are an answer key for the shape of the result, not an audited truth.
- Covenant EBITDA in a credit agreement is a defined term with add-backs, so it will not equal the simple pro forma EBITDA you compute from statements.
- That gap is a feature for the demo, but the demo should say it out loud.
- Every candidate below has an 8-K/A with the target's audited statements plus an Article 11 pro forma exhibit.
- Only some candidates have an explicit acquisition basket or "Permitted Acquisition" term in the credit agreement.
- I could not use the EDGAR full-text search reliably for discovery (long queries returned errors), so this is a hand-checked shortlist, not an exhaustive scan.
- Several 8-K/A filings I opened were dead ends (earnings-release corrections, officer changes, auditor changes), so do not trust a form-type filter alone when you search for more.

---

## 2. Ranked shortlist (ranking is INFERRED)

| Rank | Acquirer | Target | Close | Price | Leverage covenant | Acquisition term | Pro forma exhibit |
|---|---|---|---|---|---|---|---|
| 1 | Kewaunee Scientific (KEQU) | Nu Aire, Inc. | 2024-11-01 | $55M | Senior Funded Bank Debt to EBITDA below 2.50x | Yes, $5M basket with pro forma compliance | Yes, Ex 99.2 with a reclass column |
| 2 | DLH Holdings (DLHC) | Grove Resource Solutions (GRSi) | 2022-12-08 | $185M | Max Total Leverage Ratio 4.50x, stepping down | Not found in the agreement text | Yes, Ex 99.3 plus Ex 99.4 pro forma EBITDA |
| 3 | Mama's Creations (MAMA) | Crown I carve-out (from Sysco) | 2025-09-02 | $17.5M cash | Total Funded Debt to EBITDA 3.75x, Senior 2.75x | Yes, "Permitted Acquisition" and a $20M PA Line | Yes, Ex 99.3 |
| 4 | Shutterstock (SSTK) | Envato Pty Ltd | 2024-07-22 | about $250M | Consolidated Net Leverage Ratio 3.50x, 4.00x after a Specified Acquisition | Yes, Acquisition conditions with pro forma compliance | Yes, Ex 99.3 |
| 5 | Standex (SXI) | Amran and Narayan group | 2024-10-28 | about $415M cash | Not retrieved | Not retrieved | Yes, Ex 99.3 |

Why this order (INFERRED):
Rank 1 is the only one where all five criteria are met, the deal is small relative to the acquirer, the covenant is real, and the filing itself contains a mapping table.
Rank 2 has the strongest "combined EBITDA" answer key but is a larger deal and lacks a clean acquisition-basket clause.
Rank 3 is the smallest and has the cleanest acquisition term, but the leverage story is weak because the combined company carries very little debt.
Rank 4 has the cleanest credit agreement language, but it is about $250M and the target reports under IFRS, which adds a second mapping problem.
Rank 5 fails the size test and I did not retrieve its credit agreement.

---

## 3. Candidate 1 (best pick): Kewaunee Scientific buys Nu Aire

### Facts

- Acquirer: Kewaunee Scientific Corporation (Nasdaq KEQU, fiscal year ends April 30), CIK 55529.
- Target: Nu Aire, Inc. (private, Minnesota, fiscal year ends September 30).
- Close date: 2024-11-01.
- Price: $55,000,000, subject to adjustments for debt, cash, transaction expenses, and working capital.
- Funding: a $15M PNC term loan, a $20M PNC revolver (undrawn amount at close not stated in the pages I read), and $23M of 8% subordinated seller notes.
- VERIFIED: https://www.sec.gov/Archives/edgar/data/55529/000119312525007212/d915304dex992.htm (price, funding, and the PNC loan terms).
- Size context, VERIFIED: Kewaunee fiscal 2024 net sales were $203,755K and Nu Aire's reclassed fiscal-2024 net sales were $80,875K (same exhibit, year-ended-April-30 pro forma table).
- Nu Aire audited fiscal 2024 (year to September 30, 2024) net revenues were $74,850,302 (Ex 99.1 below).
- Both statements of operations are public, and Nu Aire's own line items differ from Kewaunee's.

### Exact EDGAR links

- Original 8-K (closing, 2024-11-01), VERIFIED: https://www.sec.gov/Archives/edgar/data/55529/000119312524249232/d886750d8k.htm
- Original 8-K filing index, VERIFIED: https://www.sec.gov/Archives/edgar/data/55529/000119312524249232/0001193125-24-249232-index.htm
- 8-K/A with financials (filed 2025-01-16), VERIFIED: https://www.sec.gov/Archives/edgar/data/55529/000119312525007212/d915304d8ka.htm
- Ex 99.1, Nu Aire audited statements for the year ended 2024-09-30 (auditor consent is Ex 23.1), VERIFIED: https://www.sec.gov/Archives/edgar/data/55529/000119312525007212/d915304dex991.htm
- Ex 99.2, unaudited pro forma condensed combined financial information (Article 11), VERIFIED: https://www.sec.gov/Archives/edgar/data/55529/000119312525007212/d915304dex992.htm
- Credit agreement, Ex 10.1 to the original 8-K (PNC Loan Agreement, dated 2024-11-01), VERIFIED: https://www.sec.gov/Archives/edgar/data/55529/000119312524249232/d886750dex101.htm
- Purchase agreement, Ex 2.1 to the original 8-K, exists in the filing folder (file `d886750dex21.htm`), VERIFIED by directory listing only, not read: https://www.sec.gov/Archives/edgar/data/55529/000119312524249232/d886750dex21.htm
- Kewaunee 10-Q for the quarter ended 2024-10-31 (historical balance sheet and the sale-leaseback note), VERIFIED: https://www.sec.gov/Archives/edgar/data/55529/000005552924000040/kequ-20241031.htm

### Covenant wording

- Leverage covenant, Ex 10.1 Section 4.8(a), VERIFIED: "ratio of Senior Funded Bank Debt to EBITDA of less than 2.50 to 1.00".
- A second covenant, Section 4.8(b), is a Fixed Charge Coverage Ratio of at least 1.20 to 1, VERIFIED (same exhibit).
- Acquisition basket, Ex 10.1 Section 5.8(ii), VERIFIED: "each such Acquisition does not exceed $5,000,000".
- That basket also requires pro forma compliance with the Section 4.8 financial covenants.
- The Closing Date Acquisition itself is carved out of the basket, and Ex 10.1 requires an acquisition compliance certificate showing pro forma covenant compliance (VERIFIED, same exhibit).
- The 8-K summary also states the 2.50x and 1.20x tests, VERIFIED in the original 8-K Item 1.01.

### Covenant definitions that matter for the demo (all VERIFIED in Ex 10.1)

- "Senior Funded Bank Debt" is secured borrowed money including finance leases and letters of credit, excluding Subordinated Debt (the seller notes) and "any capitalized lease obligations relating to the real property located at 2700 West Front Street".
- "EBITDA" is net income plus interest, taxes, depreciation, and amortization, plus add-backs.
- The add-backs include capped transaction costs (up to $4,000,000), capped integration costs (up to $1,000,000), stock compensation, a noncash pension termination expense, and Nu Aire's pro forma EBITDA for the four quarters ended 2024-10-31.
- The definition then subtracts cash rent on the Statesville property.
- So the covenant EBITDA is a negotiated number, not the pro forma operating profit.

### Do the two companies' accounts differ enough to make mapping credible?

Yes.
VERIFIED from Ex 99.1 and Ex 99.2:
- Nu Aire's income statement has Selling Expense, General and Administrative, and Research and Development.
- Kewaunee shows one "Operating expenses" line.
- Nu Aire's balance sheet has Accrued Compensation, Accrued Commissions, Other Accrued Expenses, Income Taxes Payable, and Income Taxes Receivable.
- Kewaunee's has Employee compensation and amounts withheld, Deferred revenue, and Other accrued expenses.
- Nu Aire carries "Certificates of Deposit" and a "Noncompete Agreement, Net" line, which have no direct Kewaunee line.
- Kewaunee's Note 2 (Ex 99.2) is a filed reclassification table from Nu Aire line items to Kewaunee line items.
- Example reclasses in that note: Accrued Commissions to Employee compensation and amounts withheld ($0.9M), Accrued Compensation to Other accrued expenses ($0.2M), Interest Income - Net to Other income, net ($0.3M).
- Note 2 also says Kewaunee is "conducting a more detailed review of reclassifications", so even the filed key is preliminary.

### A natural "one unclear account for a human"

- Kewaunee carries a "Financing liability" ($750K current plus $27,032K long-term at 2024-10-31).
- The 10-Q says it arises from a Sale-Leaseback Arrangement accounted for as a financing, with a carrying value of $27,782,000 (VERIFIED in the 10-Q URL above).
- The credit agreement excludes the capital lease on the Statesville real property from Senior Funded Bank Debt and subtracts the cash rent from EBITDA (VERIFIED in Ex 10.1).
- Whether that line counts as debt for the leverage test is exactly the kind of judgment that needs a human sign-off.
- The pro forma balance sheet adds $3,000K current and $40,103K long-term to "financing liability" for the new debt (VERIFIED in Ex 99.2), so the same line holds both the sale-leaseback and the acquisition financing.
- That is a strong demo moment: the model sees one line called "financing liability" and has to ask which part is covenant debt.
- Pro forma total financing liability is $3,750K plus $67,135K (VERIFIED).
- What part of the $43,103K increase is the revolver draw is not stated in the lines I read (INFERRED that it is the $15M term loan, the $23M seller notes, and a revolver draw net of costs).

### Rough check that combined EBITDA and leverage can be computed

- Pro forma operating profit for the year ended 2024-04-30 is $20,817K (Kewaunee $18,281K plus Nu Aire $5,652K plus transaction accounting adjustments of $(3,105)K plus financing adjustments of $(11)K), VERIFIED in Ex 99.2.
- Pro forma operating profit for the six months ended 2024-10-31 is $7,304K, VERIFIED (Ex 99.2).
- Kewaunee shows a separate "Pension expense" of $(4,177)K in fiscal 2024, which the covenant EBITDA adds back as a noncash pension termination (VERIFIED for both facts).
- Nu Aire's depreciation and amortization for the year to 2024-09-30 was $1,830,395 (VERIFIED in Ex 99.1 cash flow statement).
- Kewaunee's own depreciation and amortization is not in the pro forma exhibit, so it must come from Kewaunee's 10-K cash flow statement (INFERRED that it is there, not fetched).
- So a simple EBITDA is: operating profit plus D&A for both companies plus the new intangible amortization (Note 3 says a 10 percent change in intangible values moves annual amortization by about $154K, VERIFIED, so total new amortization is roughly ten times that, INFERRED).
- Leverage numerator under the covenant: term loan plus any revolver draw plus finance leases plus short-term borrowings, excluding the seller notes and the Statesville lease.
- A deliberately naive numerator would add all of "financing liability" ($70,885K pro forma), which shows why the covenant definition matters.
- I did not compute a final leverage ratio because the Kewaunee D&A and the revolver draw were not in what I read.
- My expectation, INFERRED and not computed: the covenant ratio is well under the 2.50x limit and the naive all-in ratio is much closer to or above it, which makes the "limit next to result" picture interesting.

### Risks specific to this pick

- Nu Aire's fiscal year ends in September and Kewaunee's in April, so the pro forma "Nu Aire reclassed" column for the April-2024 year ($80,875K sales) does not match the audited September-2024 year ($74,850K).
- You cannot reproduce the April-aligned Nu Aire column from Ex 99.1 alone (INFERRED, because the interim Nu Aire statements are not in this 8-K/A).
- Use the audited September statements as the "raw target" input and treat the pro forma column as the answer key for shape, not to the dollar.
- The covenant is senior bank debt to EBITDA, not "total net leverage".
- The covenant is a bilateral PNC loan agreement, not a syndicated sponsor-style credit agreement, so there is no "total net leverage" or "permitted acquisition" language.
- Cash and EBITDA add-backs are simpler than a private-equity credit agreement.

---

## 4. Candidate 2: DLH Holdings buys Grove Resource Solutions (GRSi)

### Facts

- Acquirer: DLH Holdings Corp. (Nasdaq DLHC, fiscal year ends September 30), CIK 785557.
- Target: Grove Resource Solutions, LLC (GRSi), private.
- Close date: 2022-12-08.
- Price: $185M, being $178M cash plus 526,898 shares valued at $7M, funded from the amended credit facility.
- VERIFIED: https://www.sec.gov/Archives/edgar/data/785557/000078555722000052/dlhc-20221208.htm
- Size context, VERIFIED: DLH fiscal 2022 revenue $395,173K and GRSi revenue $114,251K (Ex 99.4 below).
- This is a large add-on, about 29 percent of acquirer revenue, so it is less "easy to explain" than rank 1.

### Exact EDGAR links

- Original 8-K (Items 1.01, 2.01, 2.03), filed 2022-12-14, VERIFIED: https://www.sec.gov/Archives/edgar/data/785557/000078555722000052/dlhc-20221208.htm
- Credit agreement, Ex 10.1 (Second Amended and Restated Credit Agreement), VERIFIED: https://www.sec.gov/Archives/edgar/data/785557/000078555722000052/aomega12082022exh101comp.htm
- 8-K/A filed 2023-02-23, VERIFIED: https://www.sec.gov/Archives/edgar/data/785557/000078555723000034/dlhc-20221208.htm
- Ex 99.1, GRSi audited statements for 2021 and 2020, VERIFIED: https://www.sec.gov/Archives/edgar/data/785557/000078555723000034/pdfissuedfinancialstatem.htm
- Ex 99.2, GRSi unaudited statements for the nine months to 2022-09-30, VERIFIED: https://www.sec.gov/Archives/edgar/data/785557/000078555723000034/unauditedproformagrsi9-3.htm
- Ex 99.3, unaudited pro forma condensed combined statements, VERIFIED: https://www.sec.gov/Archives/edgar/data/785557/000078555723000034/exhibit993unauditedproform.htm
- Ex 99.4, unaudited pro forma EBITDA reconciliation (furnished), VERIFIED: https://www.sec.gov/Archives/edgar/data/785557/000078555723000034/exhibit994proformaebitdagr.htm

### Covenant wording

- Original 8-K Item 1.01, VERIFIED: "maximum total leverage ratio of 4.5 to 1.0".
- Credit agreement Section 8.2.16 "Maximum Total Leverage Ratio", VERIFIED: 4.50 to 1.00 through the quarter ending 2023-12-31, then stepping down to 2.00 to 1.00 from the quarter ending 2026-09-30.
- Section 8.2.15 sets a minimum Fixed Charge Coverage Ratio of 1.25 to 1.00 (VERIFIED).
- I searched the exhibit text for "Permitted Acquisition" and found zero matches, and I did not find a dollar acquisition basket (VERIFIED absence in the exhibit text I fetched, so criterion 1 is only partly met).

### Do the accounts differ enough?

Yes, moderately.
VERIFIED in Ex 99.3: note 3b says "This adjustment conforms GRSi's income statement presentation with that of DLH."
It reclassifies certain infrastructure and operational management costs, and certain fringe costs, from G&A to contract costs ($3,070K for the first item).
Note 3a also removes non-recurring revenue and moves an administrative fee from revenue to contract costs.
This is a government-services contractor (cost-reimbursable contracts), so the cost-of-revenue versus G&A line is a real mapping judgment.

### Rough check of combined EBITDA

- Ex 99.4 gives a filed pro forma EBITDA reconciliation, VERIFIED: DLH $40,943K, GRSi $15,509K, completed FEMA contracts $(12,479)K, pro forma adjustments $538K, pro forma combined $44,511K (in thousands, year ended 2022-09-30).
- The same table shows net income, interest, taxes, and D&A by column (for example D&A of $7,665K for DLH and $290K for GRSi, VERIFIED).
- That is a direct answer key for "combined EBITDA" and it includes a removal of non-recurring FEMA task orders, which is a good "adjustment" story.
- Leverage: the facility funded $178M of cash price (VERIFIED), but DLH's existing debt balance before the deal is not in what I read, so a leverage ratio would need the 10-K balance sheet (INFERRED).
- Covenant "Total Leverage Ratio" is Total Funded Debt over a defined EBITDA (VERIFIED partial: the definition begins "the ratio of (A) Total Funded Debt"), and the full EBITDA definition was not read.

### Risks specific to this pick

- Larger deal and a lender-defined EBITDA I did not read in full.
- The FEMA carve-out makes the pro forma EBITDA harder to explain in one sentence.

---

## 5. Candidate 3: Mama's Creations buys the Crown I carve-out business

### Facts

- Acquirer: Mama's Creations, Inc. (Nasdaq MAMA, fiscal year ends January 31), CIK 1520358.
- Target: substantially all assets of Crown I Enterprises Inc., an indirect subsidiary of Sysco, called the "Crown 1 Carve Out Business".
- Close date: 2025-09-02.
- Price: $17.5 million in cash, subject to a working capital adjustment, VERIFIED in the pro forma exhibit below.
- Funding: a $19,000,000 draw on a new $20,000,000 M&T Bank "PA Line" (a non-revolving line for acquisitions), VERIFIED in the original 8-K.
- A $20.0 million private placement closed 2025-09-03 and about $16.9 million of proceeds repaid term loan and PA Line amounts, VERIFIED in the pro forma exhibit.
- Size context, VERIFIED: Mama's net sales for the year to 2025-01-31 were $123,328K and Crown 1's were $56,091K (twelve months to 2024-12-31).

### Exact EDGAR links

- Original 8-K filed 2025-09-02, VERIFIED: https://www.sec.gov/Archives/edgar/data/1520358/000149315225012528/form8-k.htm
- Credit agreement, Ex 10.1 (A&R Loan and Security Agreement with M&T Bank, dated 2025-08-28), VERIFIED: https://www.sec.gov/Archives/edgar/data/1520358/000149315225012528/ex10-1.htm
- 8-K/A filed 2025-11-07, VERIFIED: https://www.sec.gov/Archives/edgar/data/1520358/000149315225021306/form8-ka.htm
- Ex 99.2, Crown I carve-out audited statements for the year to 2025-06-28 (named in the 8-K/A body), VERIFIED to exist: https://www.sec.gov/Archives/edgar/data/1520358/000149315225021306/ex99-2.htm
- Ex 99.3, unaudited pro forma condensed combined information, VERIFIED: https://www.sec.gov/Archives/edgar/data/1520358/000149315225021306/ex99-3.htm

### Covenant wording

- Ex 10.1 Section 5.31 (Financial Covenants), item B, VERIFIED: "Total Funded Debt to EBITDA to be greater than 3.75 to 1.00".
- Item C is Senior Funded Debt to EBITDA of no more than 2.75 to 1.00, and item A is Fixed Charge Coverage of at least 1.25 to 1.00 (VERIFIED).
- Acquisition term, VERIFIED: "Permitted Acquisition" is defined with conditions, and PA Line advances are "utilized exclusively for any Permitted Acquisition".
- The EBITDA definition says calculations are made "on a pro forma basis to reflect any Permitted Acquisition" as if it occurred on the first day of the four-quarter period (VERIFIED, my paraphrase of the Ex 10.1 text, and the exact sentence is in that exhibit).

### Do the accounts differ enough?

Moderately.
VERIFIED in Ex 99.3: the carve-out balance sheet has "Due from parent", "Parent net investment", and operating lease lines that are eliminated or replaced in the adjustments, while Mama's has "Term loan", "Promissory notes - related parties", and "Line of credit".
Mama's income statement has a Research and development line that Crown 1 does not.
The filing says "An initial review of the accounting policies was completed to determine no material differences", so there is no filed reclass table (VERIFIED).
The target's operating margin is very different from the acquirer's, which is a good explain-it-simply contrast.

### Rough check of combined EBITDA and leverage

- Pro forma income from operations for the year to 2025-01-31 is $4,414K (Mama's $4,877K plus Crown 1 $1,764K plus adjustments $(2,227)K), VERIFIED in Ex 99.3.
- The six months to 2025-07-31 pro forma income from operations is $2,859K, and Crown 1 alone was $(313)K, VERIFIED.
- D&A is not on the pro forma face, so EBITDA needs the cash flow statements (INFERRED that they are in Ex 99.2 and Mama's 10-K/10-Q).
- Pro forma debt after the private placement paydown is small (term loan $1,536K current plus $3,627K non-current, finance leases about $1.35M, promissory notes $750K, VERIFIED).
- So leverage is likely far below the limits (INFERRED, not computed), which makes it a weak "near the limit" story.

### Risks specific to this pick

- Weak leverage drama, and the lender is a single bank, so the document is a loan and security agreement, not a sponsor-style credit agreement.
- The deal is a carve-out (asset purchase), with parent-allocation lines, which is realistic but a little unusual.

---

## 6. Candidate 4: Shutterstock buys Envato

### Facts

- Acquirer: Shutterstock, Inc. (NYSE SSTK), CIK 1549346.
- Target: Envato Pty Ltd (Australia), reporting under IFRS (VERIFIED: "prepared in accordance with International Financial Reporting Standards").
- Close date: 2024-07-22.
- Price: about $250 million after adjustments (VERIFIED in the 8-K/A Item 2.01).
- Funding: $280 million borrowed on the A&R Credit Agreement, which has a $125.0M senior unsecured term loan and a $250.0M revolver (VERIFIED in the original 8-K).
- Larger than a "small add-on", so it misses criterion 4.

### Exact EDGAR links

- Original 8-K with the credit agreement, filed 2024-07-22, VERIFIED: https://www.sec.gov/Archives/edgar/data/1549346/000114036124033759/ef20032751_8k.htm
- Credit agreement, Ex 10.1, VERIFIED: https://www.sec.gov/Archives/edgar/data/1549346/000114036124033759/ef20032751_ex10-1.htm
- Separate acquisition 8-K by the company, filed 2024-07-22, exists (accession 0001549346-24-000027), VERIFIED by listing only: https://www.sec.gov/Archives/edgar/data/1549346/000154934624000027/sstk-20240722.htm
- 8-K/A (financials), VERIFIED: https://www.sec.gov/Archives/edgar/data/1549346/000154934624000039/sstk-20240726.htm
- Ex 99.1, Envato audited statements for the year to 2023-06-30 (file `annualfinal-envatofinanc.htm`), VERIFIED to exist: https://www.sec.gov/Archives/edgar/data/1549346/000154934624000039/annualfinal-envatofinanc.htm
- Ex 99.2, Envato unaudited interim statements (file `interimfinal-withnoopini.htm`), VERIFIED to exist: https://www.sec.gov/Archives/edgar/data/1549346/000154934624000039/interimfinal-withnoopini.htm
- Ex 99.3, unaudited pro forma (file `a2024-8xka_exx993xproforma.htm`), VERIFIED to exist: https://www.sec.gov/Archives/edgar/data/1549346/000154934624000039/a2024-8xka_exx993xproforma.htm

### Covenant wording

- Ex 10.1 Section 7.11(b), VERIFIED: "to be greater than 3.50:1.00" for the Consolidated Net Leverage Ratio.
- The same section lets the borrower raise the maximum to 4.00:1.00 for three full fiscal quarters after a "Specified Acquisition" (VERIFIED).
- Section 7.11(a) sets a Consolidated Interest Coverage Ratio floor of 3.00:1.00 (VERIFIED).
- Ratios are computed on a pro forma basis for any acquisition over $5,000,000 (VERIFIED, Ex 10.1 Section 1.03).
- Acquisitions must have "Pro Forma Compliance" with Section 7.11, and need audited target statements at $15,000,000 or more (VERIFIED, Ex 10.1 acquisition definition).
- This is the closest wording to "maximum total net leverage" plus a permitted-acquisition term, of all five candidates.

### Do the accounts differ enough?

Yes, probably very much (INFERRED).
The target is on IFRS with Australian fiscal years, and the acquirer is on US GAAP.
I did not read the Ex 99.3 line items, so I cannot say how the filing maps them.

### Rough check

- Computable from Ex 99.3 in principle, but I did not extract the numbers (INFERRED).
- I did not verify the Shutterstock pro forma EBITDA or net debt.

### Risks specific to this pick

- Not small, IFRS adds a second mapping problem, and the Ex 99.3 file is 589 KB, so it is a heavy document to parse in a hackathon.

---

## 7. Candidate 5: Standex buys Amran and Narayan (reject on size)

- Acquirer: Standex International Corporation (NYSE SXI), CIK 310354.
- Targets: Amran, LLC (Texas) and 90.1 percent of Narayan Powertech Private Limited (India).
- Close date: 2024-10-28.
- Price: $153.3 million cash plus 152,299 shares for Amran, and $261.6 million cash for Narayan, VERIFIED in Ex 99.3.
- That is about $415M of cash, so it misses the small-add-on test.
- 8-K/A filed 2025-01-13, VERIFIED: https://www.sec.gov/Archives/edgar/data/310354/000143774925000976/sxi20250107_8ka.htm
- Ex 99.1 audited combined statements for 2023, VERIFIED to exist: https://www.sec.gov/Archives/edgar/data/310354/000143774925000976/ex_764349.htm
- Ex 99.2 unaudited six-month statements, VERIFIED to exist: https://www.sec.gov/Archives/edgar/data/310354/000143774925000976/ex_764498.htm
- Ex 99.3 pro forma, with a column "The Amran/Narayan Group Operations (Adjusted Historical)", VERIFIED: https://www.sec.gov/Archives/edgar/data/310354/000143774925000976/ex_764554.htm
- Credit agreement and covenant: not retrieved, so criterion 1 is unverified (INFERRED that Standex has a public credit agreement, because it is a large accelerated filer, but I did not read it).

---

## 8. Which criteria each candidate misses

| Criterion | Kewaunee | DLH | Mama's | Shutterstock | Standex |
|---|---|---|---|---|---|
| 1 Public credit agreement with leverage covenant and acquisition term | Met (4.8(a), 5.8) | Partly (leverage yes, acquisition term not found) | Met (5.31, Permitted Acquisition) | Met (7.11(b), acquisition conditions) | Unverified |
| 2 Target statements public | Met (audited, 8-K/A) | Met | Met (carve-out) | Met (IFRS) | Met |
| 3 Article 11 pro forma with acquirer, target, adjustments columns | Met | Met | Met | Met (not read in detail) | Met |
| 4 Small add-on, 2022 to 2026 | Met ($55M, 2024) | Partly ($185M, 2022) | Met ($17.5M, 2025) | Missed (about $250M) | Missed (about $415M) |
| 5 Free EDGAR documents with exact URLs | Met | Met | Met | Met | Partly (no credit agreement) |

All dates fall inside 2022 to 2026.

---

## 9. What the demo can do with real data versus synthetic data

### Real data (statement-line level)

- Load Kewaunee's historical balance sheet and income statement lines and Nu Aire's audited lines from the filings.
- Map Nu Aire's roughly 30 balance sheet and income lines to Kewaunee's lines, and check the result against the filed Note 2 reclassification table.
- Show the transaction accounting adjustments as separate columns, as the pro forma does.
- Compute a simple combined operating profit and compare it to the filed pro forma figure ($20,817K for the year to 2024-04-30).
- Flag the "Financing liability" line for a human, with the sale-leaseback evidence and the credit agreement exclusion as the cited reasons.
- Show covenant headroom against the 2.50x limit using the covenant's own definitions.

### Synthetic data (account level)

- A trial balance for each company with account numbers, names, and monthly balances that roll up into the real statement lines.
- Duplicate or ambiguous account names that do not appear in public statements (for example two "Freight" accounts or a vague "Misc accrued" account).
- Monthly or quarterly periods, because filings give annual and half-year figures only.
- Any ERP-specific fields (department, entity, currency).

If we generate synthetic accounts, the totals should be built to tie exactly to the real statement lines.
That keeps the real filing as the answer key while giving the mapping step something realistic to work on.

---

## 10. Recommendation (INFERRED)

Use Kewaunee Scientific and Nu Aire.
It is the smallest deal that has a real leverage covenant, a real acquisition basket, a filed reclassification table, and an unclear account that needs a human.
Keep DLH and GRSi as a backup because its Ex 99.4 gives a ready-made combined EBITDA answer key.
Use Shutterstock and Envato only if the team wants to show IFRS to US GAAP mapping and a "total net leverage" wording match.

Before the pitch, someone should open the Kewaunee 10-K for fiscal 2025 (period ending 2025-04-30) and the Q3 and Q4 10-Qs to see whether a covenant compliance figure was ever disclosed, because I did not check that (INFERRED that it may exist).
Someone should also pull Kewaunee's depreciation and amortization from its fiscal 2024 10-K cash flow statement to finish the EBITDA check.
