# Flag card: "Financing liability"

Owner: Eric.
Checked 2026-10-24 against the filings in `data/raw/`.
This file holds the facts behind the one covenant flag in the demo, so the card, the slide, and the Devpost say the same thing.
Tags: [verified] means a filing or a test shows it.
[inferred] means our judgment.
Every quote is under 15 words and names its exhibit and section.
The figures are today's tool runs on the fixture.
They are not final: EBITDA items are still open with Cayden and Tri (see "How firm the figures are" below).

## The question on the card

Kewaunee's "Financing liability" line holds three different debts.
Which of them count as Senior Funded Bank Debt?

## The three parts of the line

| Part | Amount | What it is | Source |
| --- | --- | --- | --- |
| Statesville sale-leaseback | $27,782K | Kewaunee sold and leased back its headquarters and plant at 2700 West Front Street, Statesville. The books carry it as a financing, not a sale. | 10-Q at 2024-10-31, Note G [verified] |
| PNC term loan and revolver | $20,563K | $15,000K term loan plus $5,563K drawn on the $20M revolver, both from PNC at close. | Ex 99.2, Note 4(h) [verified] |
| 8% seller notes | $22,540K | Notes issued to the Nu Aire sellers as part of the price. | Ex 99.2, Note 4(h) [verified] |
| Whole line | $70,885K | The sum of the three. | Arithmetic [verified] |

Detail on each part:
- Statesville: $750K current plus $27,032K long-term, net of $618K of issuance costs. [verified: 10-Q, Note G]
- The 10-Q says the lease "was determined to be a finance lease". [verified: 10-Q, Note G]
- So the transaction was "deemed a failed sale-leaseback and accounted for as a financing arrangement". [verified: 10-Q, Note G]
- PNC: the revolver and term loan "mature on the 5-year anniversary of the Closing". [verified: Ex 99.2, Description of the Financing]
- Seller notes: they "will accrue interest at 8% per annum". [verified: Ex 99.2, Description of the Financing]
- Seller notes: the sellers' payment rights are "subordinate to the rights of PNC under the Loan Agreement". [verified: Ex 99.2, Description of the Financing]
- Seller notes: the Note 4(h) table shows $22,540K, while the narrative says $23 million. We use the table figure. [verified: Ex 99.2; the gap is likely a fair value or discount, inferred]
- The pro forma puts all of the closing financing on the financing liability lines, which is why one line holds all three. [verified: Ex 99.2, Note 4(h) table headers]

## What the agreement says

The test, from the PNC Loan Agreement (8-K Ex 10.1):
- Section 4.8(a): the borrower keeps a "ratio of Senior Funded Bank Debt to EBITDA of less than 2.50 to 1.00". [verified: Ex 10.1, Section 4.8(a)]
- It is tested "as of the end of each fiscal quarter". [verified: Ex 10.1, Section 4.8(a)]

The debt definition, from the definitions in Ex 10.1:
- Senior Funded Bank Debt means "all secured indebtedness for borrowed money". [verified: Ex 10.1, definitions]
- It includes "capital or finance lease obligations". [verified: Ex 10.1, definitions]
- It then excludes two things.

Exclusion 1, Subordinated Debt:
- The definition excludes "(i) Subordinated Debt". [verified: Ex 10.1, definitions, Senior Funded Bank Debt]
- Subordinated Debt names the seller notes: "including, without limitation, the Subordinated Seller Notes". [verified: Ex 10.1, definitions, Subordinated Debt]

Exclusion 2, the Statesville lease:
- The definition excludes "capitalized lease obligations relating to the real property located at 2700 West Front Street". [verified: Ex 10.1, definitions, Senior Funded Bank Debt]
- 2700 West Front Street is the Statesville sale-leaseback property. [verified: 10-Q, Note G]
- Reading the failed sale-leaseback as a "capitalized lease obligation" is our reading. The 10-Q calls the lease a finance lease but books a financing liability. A practitioner should confirm it. [inferred]

## The three options and their effect

Senior Funded Bank Debt below includes $1,070K that is not on the flagged line and counts in every option: $805K of short-term borrowings at the international subsidiaries and $265K of finance leases for vehicles and IT equipment. [verified: fixture and 10-Q, Notes F and H]
Covenant EBITDA in every option is $28,379K, today's figure, with the agreement's add-backs applied. [verified: `test_naive_and_covenant_leverage_differ_on_real_figures`]
The gateway computes each effect with the tools.
No model writes these numbers. [verified: `test_mapper_flags_the_financing_liability_and_effects_are_computed`]

| Option | What counts from the line | Senior Funded Bank Debt | Leverage | Verdict |
| --- | --- | --- | --- | --- |
| a. Whole line | All $70,885K | $71,955K | 2.54x | Over the 2.50x limit |
| b. PNC only (the agreement's reading, the default) | $20,563K | $21,633K | 0.76x | OK, 1.74x of room, about $49M of debt capacity |
| c. PNC plus the seller notes | $43,103K | $44,173K | 1.56x | OK |

Why b is the default: it applies both exclusions as written. [inferred: our reading of Ex 10.1; not checked by a practitioner]
Why a matters: it is what a reader gets who counts the balance sheet line as it stands.
It is the naive figure. [verified: `covenant_debt` with `naive=True`]
The gap between a and b is 1.78x on the same books. [verified: arithmetic]

The table above is the flag the scripted backend raises. [verified: scripted run of the fixture]
The recorded Droid runs raised the same flag, but neither offered option c. Their figures below were computed before the EBITDA definition items were applied, so each is about 0.01x to 0.03x lower today:
- Sonnet 5.5, 2026-10-24, 03:30: 0.77x (the agreement), 1.76x, and 2.57x (all counted). [verified: `docs/agents.md`, run log]
  The 1.76x matches PNC plus the Statesville lease, without the seller notes. [inferred: arithmetic]
- Haiku 5.5, 2026-10-24, 04:30: 0.77x (the agreement), 0.74x (short-term borrowings also excluded), and 2.57x (all counted). [verified: `docs/agents.md`, run log]

So the middle option on screen depends on which run is shown.
Read the card on screen before the pitch.

## How firm the figures are

Every amount in the fixture matches its filing. [verified: `evals/fixture_check.md`]
The debt figures in options a, b, and c do not change with the open items below.
Covenant EBITDA can change, and with it the leverage in every option.

Open with Cayden and Tri, from `evals/fixture_check.md`:
1. Done 2026-10-24: Nu Aire interest income ($514K) is subtracted, as the definition says "less interest income". [verified: `test_ebitda_subtracts_interest_income`]
2. Done 2026-10-24: Kewaunee's stock-based compensation ($1,018K) is added back, as the definition adds "any stock-based compensation". [verified: Ex 10.1, definitions; 10-K, stock plan note; the brief in `kewaunee.py`]
3. Done 2026-10-24: the pension add-back is the $4,019K termination expense the 10-K names, not the whole $4,177K line. [verified: 10-K, MD&A; the brief in `kewaunee.py`]

New item found while writing this card:
4. Transaction costs are applied as $0, but Ex 99.2 Note 5(b) lists $698K of "Expected transaction expenses", item (i). [verified: Ex 99.2, Note 5(b)]
   The agreement adds back transaction costs "not exceeding $4,000,000 in the aggregate". [verified: Ex 10.1, definitions, EBITDA]
   Item (i) describes costs incurred after 2024-10-31, so whether they fall in the tested period is a judgment. [inferred]
   Adding $698K gives EBITDA $29,077K and option a at 2.47x, under the limit. We keep it at zero: the costs fall after the period of the statements in the fixture. [verified: arithmetic; timing inferred]
5. The definition takes Nu Aire EBITDA "for the four quarter period commencing on November 1, 2023". The fixture uses Nu Aire's year to 2024-09-30, one month off. [verified: Ex 10.1, definitions; inferred that the gap is small]

The thin margin:
- Option a stays over the limit only while covenant EBITDA is below $28,782K. Today's figure is $28,379K, so the margin is $403K. [verified: arithmetic]
- Items 1 to 3 are applied, so that margin is today's. The one add-back that would close it is the $698K of expected transaction costs, which would put option a at 2.47x, and the verdict would then no longer change with the controller's answer. [verified: arithmetic]
- The Statesville cash rent ($1,970K) is inferred. If the period's cash rent were $403K lower, option a would also drop under the limit. [verified: arithmetic]
- Options b and c stay far under the limit in every case above. [verified: arithmetic]

So the card and the pitch must not present today's leverage figures as final.
Say the inferred inputs out loud, as `docs/demo-script.md` section 6 plans.
