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
