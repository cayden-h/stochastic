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

Covenant EBITDA today is $27,519K, with interest income subtracted (item 1, done 2026-10-24). The option debt figures are unchanged.

| Case | EBITDA | a. Whole line | b. PNC only | c. PNC plus seller notes |
| --- | --- | --- | --- | --- |
| Before the interest income fix | $28,033K | 2.57x | 0.77x | 1.58x |
| Today (interest income subtracted) | $27,519K | 2.61x | 0.79x | 1.61x |
| Today plus stock compensation and pension (all three) | $28,379K | 2.54x | 0.76x | 1.56x |
| Today plus stock compensation | $28,537K | 2.52x | 0.76x | 1.55x |
| Today plus stock compensation and $698K transaction costs | $29,235K | 2.46x | 0.74x | 1.51x |
| Today plus pension | $27,361K | 2.63x | 0.79x | 1.61x |

Option a stays over the 2.50x limit only while covenant EBITDA is below $28,782K. [verified: arithmetic]
With all three changes, option a is still over the limit, with about $400K of EBITDA to spare. [inferred: depends on the readings above]
Stock compensation alone leaves option a over the limit at 2.52x. Stock compensation plus the $698K of transaction costs would put it under, and the verdict would no longer change with the controller's answer. [verified: arithmetic]

## Asks

- Cayden and Tri: decide the stock compensation add-back, the pension figure, and the $698K of transaction costs. Stock compensation plus the transaction costs breaks the moment.
- Done 2026-10-24: the EBITDA tool subtracts interest income (`test_ebitda_subtracts_interest_income`).
- Everyone: the moment now rests on a thinner margin. Say the inferred inputs out loud, as `demo-script.md` already plans.
