# Draft compliance certificate: what the agreement asks for

Owner: Tri.
Checked 2026-10-24 against the PNC Loan Agreement, 8-K Ex 10.1 (https://www.sec.gov/Archives/edgar/data/55529/000119312524249232/d886750dex101.htm), read with WebFetch.
This file says which clause each section of our draft certificate comes from, and what the draft leaves out.
Tags: [verified] means the exhibit text says it.
[inferred] means our reading or judgment.
Every quote is under 15 words and names its section.
The route is `GET /deals/{id}/certificate?format=md|html|json`.
The output is a draft built from the approved result, not advice and not a signed certificate.

## What the agreement requires

- The borrower delivers a certificate "certifying compliance with all applicable financial covenants". [verified: Ex 10.1, Section 4.2(g)]
- It comes with each set of interim and annual financial statements. [verified: Ex 10.1, Section 4.2(g)]
- It contains "detailed calculations of such financial covenants". [verified: Ex 10.1, Section 4.2(g)]
- It says, for the period then ended, whether any Event of Default exists, and if so the borrower's corrective measures. [verified: Ex 10.1, Section 4.2(g)]
- It "shall be duly executed by, either the Chief Financial Officer," or another responsible senior financial officer or an authorized officer of the borrower. [verified: Ex 10.1, Section 4.2(g)]
- Quarterly statements are due "within forty-five (45) days after the end of each quarter". [verified: Ex 10.1, Section 4.2(a)]
- Annual statements are due "within ninety (90) days after the end of each fiscal year". [verified: Ex 10.1, Section 4.2(b)]
- The annual date can move to the Form 10-K deadline while the borrower reports to the SEC. [verified: Ex 10.1, Section 4.2(b)]
- So the certificate is due on the same dates as the statements it goes with. [inferred: Section 4.2(g) ties it to those statements]
- We did not find a form of compliance certificate as an exhibit in the text we read. [inferred: not found, so the lender's form, if any, is not in Ex 10.1]

## The leverage test and its period

- Section 4.8(a) requires a "ratio of Senior Funded Bank Debt to EBITDA of less than 2.50 to 1.00". [verified: Ex 10.1, Section 4.8(a)]
- It is "measured as of the end of each fiscal quarter of the Borrower". [verified: Ex 10.1, Section 4.8(a)]
- Section 4.8(a) does not itself say trailing four quarters. [verified: not in the Section 4.8(a) text]
- Section 4.8(b), the fixed charge test, says "on a rolling four quarter basis". [verified: Ex 10.1, Section 4.8(b)]
- The EBITDA definition adds Nu Aire's EBITDA "calculated on a pro forma basis for the four quarter period" from November 1, 2023 to October 31, 2024. [verified: Ex 10.1, Addendum I, EBITDA]
- So the EBITDA in the leverage test is a four-quarter figure. [inferred: from the Nu Aire clause and Section 4.8(b), not from Section 4.8(a)]
- The draft says "less than" and tests strictly below 2.50. [verified: `limit_test` with wording "less than"]

## The definitions

- EBITDA starts from "net income plus interest expense less interest income plus income tax expense". [verified: Ex 10.1, Addendum I, EBITDA]
- It then adds depreciation and amortization. [verified: Ex 10.1, Addendum I, EBITDA]
- It adds noncash pension termination expense for the fiscal year ending April 30, 2024. [verified: Ex 10.1, Addendum I, EBITDA]
- It adds transaction costs of the Closing Date Acquisition, "not exceeding $4,000,000 in the aggregate". [verified: Ex 10.1, Addendum I, EBITDA]
- It adds integration costs within 18 months of that acquisition, "not exceeding $1,000,000 in the aggregate". [verified: Ex 10.1, Addendum I, EBITDA]
- It adds "any stock-based compensation". [verified: Ex 10.1, Addendum I, EBITDA]
- It subtracts "extraordinary gains". [verified: Ex 10.1, Addendum I, EBITDA]
- It subtracts "cash rental expense relating to the real property located at 2700 West Front Street". [verified: Ex 10.1, Addendum I, EBITDA]
- Senior Funded Bank Debt means "all secured indebtedness for borrowed money", including finance leases, letter of credit reimbursement obligations, and guarantees. [verified: Ex 10.1, definition of Senior Funded Bank Debt]
- It excludes Subordinated Debt. [verified: Ex 10.1, definition of Senior Funded Bank Debt]
- It excludes "capitalized lease obligations relating to the real property located at 2700 West Front Street". [verified: Ex 10.1, definition of Senior Funded Bank Debt]
- Subordinated Debt includes, "without limitation, the Subordinated Seller Notes". [verified: Ex 10.1, definition of Subordinated Debt]
- The Senior Funded Bank Debt definition sits in the alphabetical definitions with EBITDA, which we take to be Addendum I. [inferred: the text we read gave no section number for it]

## Our draft, section by section

| Draft section | What it shows | Clause it comes from |
| --- | --- | --- |
| Header | Lender, agreement, Section 4.8(a) wording, debt term, unit, backend, "Draft" | Section 4.8(a) [verified] |
| Test period | Each company's income statement periods and balance sheet dates, from its source lines, and the brief's note | Section 4.8(a) and the Nu Aire clause in EBITDA [verified]; our periods differ, see below [verified] |
| EBITDA | Per-company net income, interest, taxes, D&A, each add-back with cap and applied amount, the rent deduction, the total | Addendum I, EBITDA [verified] |
| Debt | Lines counted as Senior Funded Bank Debt and lines excluded with the reason | Definition of Senior Funded Bank Debt and Subordinated Debt [verified] |
| Leverage | Debt divided by EBITDA | Section 4.8(a) [verified] |
| Limit test | Leverage against 2.50, "less than", headroom, and room for more debt | Section 4.8(a) [verified]; debt capacity is our addition [inferred: not a term of the agreement] |
| Tie-out | The combined books add up and the balance sheet balances | Not in the agreement; our check on the "detailed calculations" of Section 4.2(g) [inferred] |
| Decisions | Each flag the controller answered, the option, and its computed effect | Not in the agreement; the audit trail behind the calculation [inferred] |
| Approval | The approval item, audit row count, chain check, denied attempts | Not in the agreement [inferred] |
| Mappings | How many lines were mapped and how many came from a learned policy | Not in the agreement [inferred] |

Every figure in the draft is followed by the run id of the tool run that produced it, for example `28,378.845 [run_014]`. [verified: `backend/tests/test_certificate.py`]

## What the draft leaves out

- The signature and the officer's name and title that Section 4.2(g) requires. [verified: the draft says "Draft. Not signed."]
- The statement on whether any Event of Default exists, and any corrective measures. [verified: Section 4.2(g) asks for it; the draft does not say it]
- The other financial covenants, such as the fixed charge coverage ratio in Section 4.8(b). [verified: the draft tests only Section 4.8(a)]
- The lender's own form, if it has one. [inferred: we found none in Ex 10.1]
- Extraordinary gains: the draft has no line for them, so none are subtracted. [inferred: none appear in the source lines]
- The agreement's test period: our combined income statement adds Kewaunee's year to April 30, 2024 and Nu Aire's year to September 30, 2024. [verified: the source line periods]
- The agreement uses Nu Aire's four quarters to October 31, 2024 and a quarter-end test date. [verified: Ex 10.1, Addendum I and Section 4.8(a)]
- So the draft figure is not the figure a quarter-end certificate would carry. [inferred]
- The transaction and integration cost add-backs are applied at 0, because the filings we read do not quantify them. [verified: the brief marks both inferred]
