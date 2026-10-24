# Fixture check against the filings (2026-10-24)

Checked by Eric against `backend/app/db/fixtures/kewaunee.py` at commit d6a909e.
Filings pulled with `scripts/fetch_filings.py` into `data/raw/` (git-ignored).
Tags: [verified] means the filing text shows it. [inferred] means judgment.

## Result

Every amount in the fixture matches its filing. [verified]
- Kewaunee balance sheet, 38 lines: matches the 10-Q at 2024-10-31 line for line.
- Kewaunee income statement: matches the Kewaunee historical column of Ex 99.2.
- Kewaunee depreciation $3,125K and the Statesville obligation due within one year $1,970K: match the 10-K.
- Closing financing: revolver $5,563K, term loan $15,000K, seller notes $22,540K match the Ex 99.2 Note 4(h) table.
- Nu Aire balance sheet, income statement, and D&A $1,830,395: match Ex 99.1.
- Brief: the 2.50x limit, Section 4.8(a), and both debt exclusions match Ex 10.1.

The fixture leaves out one subtotal, "Total Kewaunee Scientific Corporation Stockholders' Equity" ($59,328K). It does not change any figure. [verified]

## Differences in how the EBITDA definition is applied

The Ex 10.1 definition of EBITDA reads, in part, "net income plus interest expense less interest income". [verified: Ex 10.1, definitions]
It also adds back "any stock-based compensation" and "noncash pension termination expense". [verified: Ex 10.1, definitions]
Three items differ from the fixture.

1. Nu Aire interest income is not subtracted.
   Nu Aire reports "Interest Income - Net" of $513,770 and no interest expense line. [verified: Ex 99.1]
   The definition subtracts interest income, so Nu Aire EBITDA would be about $514K lower. [inferred]
   Kewaunee's interest income sits inside "Other income, net" ($814K) and is not quantified in the 10-K. [verified that it is not broken out]
2. The stock-based compensation add-back is missing.
   Kewaunee recorded $1,018K of stock-based compensation expense in fiscal 2024. [verified: 10-K, stock plan note]
   Nu Aire's statements do not mention stock-based compensation. [verified: Ex 99.1]
3. The pension add-back may be too large.
   The fixture adds back the whole pension expense of $4,177K.
   The 10-K says terminating the pension caused a one-time expense of $4,019K, and the rest is ordinary pension expense. [verified: 10-K, MD&A]
   The definition names only the termination expense, so the add-back may be $4,019K, which is $158K lower. [inferred]

## Effect on leverage

Covenant EBITDA today is $28,379K. All three items were applied on 2026-10-24: interest income is subtracted, the pension add-back is the $4,019K termination expense, and stock-based compensation of $1,018K is added back. The option debt figures are unchanged.

| Case | EBITDA | a. Whole line | b. PNC only | c. PNC plus seller notes |
| --- | --- | --- | --- | --- |
| Before any change | $28,033K | 2.57x | 0.77x | 1.58x |
| Interest income subtracted only (2026-10-24, morning) | $27,519K | 2.61x | 0.79x | 1.61x |
| Today (all three applied) | $28,379K | 2.54x | 0.76x | 1.56x |
| Today plus the $698K of expected transaction costs | $29,077K | 2.47x | 0.74x | 1.52x |

Option a stays over the 2.50x limit only while covenant EBITDA is below $28,782K. [verified: arithmetic]
With all three changes, option a is still over the limit, with $403K of EBITDA to spare. [verified: arithmetic]
Adding the $698K of expected transaction costs would put option a under the limit, and the verdict would no longer change with the controller's answer. We keep them at zero because Ex 99.2 Note 5(b) describes costs expected after 2024-10-31, outside the period of the statements in the fixture. [verified: Ex 99.2, Note 5(b); timing inferred]

## Asks

- Decided 2026-10-24 by Cayden: apply the stock compensation add-back and the $4,019K pension figure; keep transaction costs at zero. The brief in `backend/app/db/fixtures/kewaunee.py` carries both with their sources.
- Done 2026-10-24: the EBITDA tool subtracts interest income (`test_ebitda_subtracts_interest_income`).
- Everyone: the moment now rests on a thinner margin. Say the inferred inputs out loud, as `demo-script.md` already plans.

## Sensitivity recheck (2026-10-24, Tri)

This section rechecks the two inferred inputs the verdict is most sensitive to: the Statesville cash rent deduction and the transaction cost add-back.
The fixture was not changed.
Sources were read with WebFetch on 2026-10-24: the Kewaunee 10-K for fiscal 2024 (`kequ-20240430.htm`) and the PNC credit agreement, Ex 10.1 (`d886750dex101.htm`).

### What the new verdict keys say

The `/case` verdict now carries `naive_flip_addback` 403.155 and `naive_flip_rent` 1,566.845, from a gateway `limit_test` run. [verified: `test_verdict_sensitivity_from_limit_test_run`]
The whole-line reading (71,955) reaches the 2.50x limit when covenant EBITDA is 71,955 / 2.5 = 28,782. [verified: arithmetic]
So the controller's answer changes the verdict only while the add-backs stay below 403.155 more and the rent deduction stays above 1,566.845; together, the extra add-backs plus the cut in rent must stay below 403.155. [verified: arithmetic]

### Statesville cash rent (fixture deduction 1,970)

Ex 10.1 subtracts "cash rental expense relating to the real property located at 2700 West Front Street". [verified: Ex 10.1, Addendum I, EBITDA]
The 10-K future minimum payments table for the sale-leaseback gives 1,970 for fiscal 2025, then 2,009, 2,049, 2,090, 2,132, and 31,736 thereafter, total 41,986. [verified: 10-K, Note 5]
The 10-K says initial basic rent is about $158K per month, with increases of about 2% a year over a 20-year term. [verified: 10-K, Note 5]
The sale-leaseback is accounted for as a financing liability, so the 10-K reports interest and principal, not rent expense. [verified: 10-K, Note 5]
Fiscal 2024 interest on the arrangement was 1,287 and repayments on the financing liability were 642. [verified: 10-K, Note 5 and cash flow statement]
Their sum, 1,929, is our best reading of the cash rent actually paid in fiscal 2024, the same period as Kewaunee's other inputs. [inferred: that the interest was paid in cash and that the 642 repayment is all on this liability]
A rent of 1,929 instead of 1,970 raises EBITDA by 41, which leaves the whole-line reading over the limit by 362. [verified: arithmetic]
Rent would have to fall to 1,566.845 to flip the verdict; no figure in the 10-K is near that. [verified: arithmetic and the table above]
Better figure: 1,929 is closer to the test period than 1,970, but it is itself inferred, and either figure gives the same verdict. [inferred]
Side note for Cayden: the 10-K carries the financing liability at 28,133 at 2024-04-30 (current 713, long-term 27,420, net of 648 of issuance costs), while the fixture uses 27,782 with a current portion of 750. [verified: 10-K, Note 5]
The fixture figures likely come from the later 10-Q balance sheet; this does not change covenant debt, because the line is excluded. [inferred]

### Transaction costs of the Closing Date Acquisition (fixture add-back 0, cap 4,000)

Ex 10.1 adds back "transaction costs related to the Closing Date Acquisition, but not exceeding $4,000,000 in the aggregate". [verified: Ex 10.1, Addendum I, EBITDA]
The cap is "in the aggregate", which we read as one cap across all test periods, not a cap per period. [inferred]
The definition sets no time window for transaction costs. [verified: Ex 10.1, as read by WebFetch]
Integration costs have a separate window: those incurred within 18 months of the Closing Date Acquisition, capped at $1,000,000 in the aggregate. [verified: Ex 10.1, Addendum I, EBITDA]
The add-back only applies to costs inside the EBITDA of the tested period, since it adds back expense that was deducted in arriving at net income. [inferred]
Ex 10.1 tests the ratio "as of the end of each fiscal quarter of the Borrower" in Section 4.8(a); the "rolling four quarter basis" wording appears in 4.8(b), for the fixed charge coverage ratio. [verified: Ex 10.1, Sections 4.8(a) and 4.8(b)]
Nu Aire's pro forma EBITDA counts for the four quarters from 2023-11-01 to 2024-10-31, "solely to the extent included in the tested period". [verified: Ex 10.1, Addendum I, EBITDA]
Our income statement is Kewaunee's fiscal year ended 2024-04-30. [verified: 10-K]
It ends before the deal closed on the Effective Date. [inferred: the closing date is from the deal papers, not the 10-K]
So no transaction cost for this deal is likely to sit in that period, and 0 is the right add-back for it. [inferred]
The $698K of expected costs in Ex 99.2 Note 5(b) would fall in the first test period that includes the close, and would be added back there in full (under the 4,000 cap). [inferred]
That 698 is above the 403.155 flip, so in that period the whole-line reading would also pass, and the controller's answer would no longer change the verdict. [verified: arithmetic]
Better figure: none for the fixture's period. [inferred]

### What Cayden would need to know

- Keep the transaction costs at 0 for this test period; the cap reading in the brief (4,000 aggregate) matches Ex 10.1. [verified]
- The rent deduction could be 1,929 (fiscal 2024 interest plus principal) instead of 1,970 (fiscal 2025 scheduled payment); the verdict is the same either way, and the brief's note already marks it inferred. [inferred]
- The demo claim "the controller's answer flips the verdict" rests on 403.155 of EBITDA; say it out loud with the two inferred inputs. [verified: arithmetic]
