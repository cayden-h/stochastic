# The brief

Owner: Eric.
Written 2026-10-24.
The brief is the third input to Stochastic, next to the two statement files.
It states the lender's limit and the agreement's own definitions of debt and EBITDA, so the tools test the limit the way the lender does.
This file holds it as short prose for the Devpost, and as text for one slide.
Tags: [verified] means a filing or a test shows it. [inferred] means our judgment.
Quotes are under 15 words and name the exhibit and section.

## Devpost prose

The lender's limit comes from the PNC Loan Agreement that Kewaunee signed at the close, filed as Exhibit 10.1 to its 8-K. [verified]
Section 4.8(a) requires a "ratio of Senior Funded Bank Debt to EBITDA of less than 2.50 to 1.00". [verified: Ex 10.1, Section 4.8(a)]
It is tested on a consolidated basis at the end of each fiscal quarter, so it applies to the combined company. [verified: Ex 10.1, Section 4.8(a)]

Both sides of the ratio are defined terms, and they are not the numbers on the face of the statements.
Senior Funded Bank Debt is "all secured indebtedness for borrowed money", including finance leases and letters of credit. [verified: Ex 10.1, definitions]
It excludes two things: Subordinated Debt, which names the seller notes, and the capitalized lease on 2700 West Front Street, the Statesville headquarters. [verified: Ex 10.1, definitions]
EBITDA starts from "net income plus interest expense less interest income", then adds taxes, depreciation, and amortization. [verified: Ex 10.1, definitions]
It also adds back the noncash pension termination expense, stock-based compensation, and acquisition costs capped at $4,000,000 for transaction costs and $1,000,000 for integration costs. [verified: Ex 10.1, definitions]
It includes Nu Aire's EBITDA for the four quarters from November 1, 2023, and it deducts the cash rent on the Statesville property. [verified: Ex 10.1, definitions]

The brief puts these terms in front of the tools, so the debt figure and the EBITDA figure follow the agreement and not a generic formula. [verified: `backend/app/db/fixtures/kewaunee.py`, `BRIEF`]
That is why one balance sheet line can read as 2.57x or 0.77x: the face of the statements and the agreement disagree about what counts. [verified: tool runs on the fixture]
Today's covenant EBITDA is $28,033K. [verified: tool run `ebitda`]
It is not final: three items in how we apply the EBITDA definition are still open with the team, and the filings do not give every input for the tested period. [verified: `evals/fixture_check.md`]

## Slide text

Title: The lender's own rules

- Limit: Senior Funded Bank Debt to EBITDA below 2.50x, tested each quarter on the combined company. (PNC Loan Agreement, Ex 10.1, Section 4.8(a))
- Debt: all secured borrowed money, including finance leases.
- Not debt: subordinated seller notes, and the Statesville sale-leaseback.
- EBITDA: net income, plus interest, taxes, depreciation, and amortization, less interest income.
- Add back: pension termination, stock compensation, deal costs up to $4M, integration costs up to $1M.
- Also: Nu Aire's four quarters to October 31, 2024, less Statesville cash rent.
- Footer: Figures from public SEC filings. Covenant EBITDA is preliminary.

Speaker line: "The tools use the agreement's definitions, not the balance sheet's labels. That is where the flag comes from."

## What the brief does not settle

- Whether the failed sale-leaseback counts as a "capitalized lease obligation" under the exclusion. We read it as yes. [inferred]
- The Statesville cash rent for the tested period. We use $1,970K, the 10-K's obligation due within one year. [inferred]
- Transaction and integration costs. The demo applies $0. Ex 99.2 Note 5(b) estimates $698K of expected transaction expenses after 2024-10-31, which may or may not fall in the tested period. [verified: Ex 99.2, Note 5(b); timing inferred]
- Nu Aire's EBITDA for the exact four quarters the agreement names. We use its audited year to 2024-09-30, one month off. [inferred]
