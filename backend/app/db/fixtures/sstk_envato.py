"""Shutterstock acquires Envato. Every figure is from a public filing.

Sources (all read on 2026-10-24 from SEC EDGAR):
- EIGHTK: Shutterstock 8-K filed 2024-07-22 (Item 1.01 and 2.03, the A&R Credit Agreement and the $280 million borrowing):
  https://www.sec.gov/Archives/edgar/data/1549346/000114036124033759/ef20032751_8k.htm
- EX101: 8-K Ex 10.1, Amended and Restated Credit Agreement dated 2024-07-22, Bank of America, N.A. as Administrative Agent
  (Section 7.11(b); definitions of Consolidated Funded Indebtedness, Consolidated Net Leverage Ratio, Consolidated EBITDA,
  Consolidated Net Income, Capital Lease, Attributable Indebtedness, Unrestricted Cash, Specified Acquisition,
  Effective Date Target EBITDA; Section 1.03):
  https://www.sec.gov/Archives/edgar/data/1549346/000114036124033759/ef20032751_ex10-1.htm
- EIGHTK_ACQ: Shutterstock 8-K filed 2024-07-22 (Item 2.01, completion of the Envato acquisition):
  https://www.sec.gov/Archives/edgar/data/1549346/000154934624000027/sstk-20240722.htm
- EIGHTKA: Shutterstock 8-K/A (Item 9.01 financial statements of Envato and pro forma information):
  https://www.sec.gov/Archives/edgar/data/1549346/000154934624000039/sstk-20240726.htm
- EX991: 8-K/A Ex 99.1, Envato audited IFRS statements for the year ended 2023-06-30, presented in USD'000 (scanned pages):
  https://www.sec.gov/Archives/edgar/data/1549346/000154934624000039/annualfinal-envatofinanc.htm
- EX992: 8-K/A Ex 99.2, Envato unaudited condensed IFRS interim statements at 2023-12-31 and for the six months then ended,
  presented in USD'000 (scanned pages; the balance sheet and Notes 9 to 17 are read from the page images):
  https://www.sec.gov/Archives/edgar/data/1549346/000154934624000039/interimfinal-withnoopini.htm
- EX993: 8-K/A Ex 99.3, unaudited pro forma condensed combined information (Note 1 IFRS to GAAP statement, Note 4 Envato
  twelve months to 2023-12-31 in Envato's own captions, Note 5 reclassifications, Note 6A closing financing):
  https://www.sec.gov/Archives/edgar/data/1549346/000154934624000039/a2024-8xka_exx993xproforma.htm
- TENK: Shutterstock 10-K for the year ended 2023-12-31 (statement of operations, cash flows, Note 11, adjusted EBITDA):
  https://www.sec.gov/Archives/edgar/data/1549346/000154934624000007/sstk-20231231.htm
- TENQ: Shutterstock 10-Q for the quarter ended 2024-06-30 (the last balance sheet before the 2024-07-22 close):
  https://www.sec.gov/Archives/edgar/data/1549346/000154934624000034/sstk-20240630.htm
- TENQ3: Shutterstock 10-Q for the quarter ended 2024-09-30 (the first covenant test date: debt split, cash, compliance):
  https://www.sec.gov/Archives/edgar/data/1549346/000154934624000045/sstk-20240930.htm
Figures marked inferred are our estimates and must be said out loud.
"""
from __future__ import annotations

from app.core.models import Adjustment, Brief, Financing

DEAL_ID = "d_sstk_envato"
NAME = "Shutterstock, Inc. acquires Envato Pty Ltd"
PLATFORM = "Shutterstock"
TARGET = "Envato"
NOTE = ("Shutterstock bought Envato on 2024-07-22 for $250 million in cash, funded with $280 million borrowed under its "
        "Bank of America A&R Credit Agreement, whose covenant caps the Consolidated Net Leverage Ratio at 3.50 to 1.00.")
SOURCES = {
    "8-K": "https://www.sec.gov/Archives/edgar/data/1549346/000114036124033759/ef20032751_8k.htm",
    "8-K Ex 10.1": "https://www.sec.gov/Archives/edgar/data/1549346/000114036124033759/ef20032751_ex10-1.htm",
    "8-K (acquisition)": "https://www.sec.gov/Archives/edgar/data/1549346/000154934624000027/sstk-20240722.htm",
    "8-K/A": "https://www.sec.gov/Archives/edgar/data/1549346/000154934624000039/sstk-20240726.htm",
    "8-K/A Ex 99.1": "https://www.sec.gov/Archives/edgar/data/1549346/000154934624000039/annualfinal-envatofinanc.htm",
    "8-K/A Ex 99.2": "https://www.sec.gov/Archives/edgar/data/1549346/000154934624000039/interimfinal-withnoopini.htm",
    "8-K/A Ex 99.3": "https://www.sec.gov/Archives/edgar/data/1549346/000154934624000039/a2024-8xka_exx993xproforma.htm",
    "10-K FY2023": "https://www.sec.gov/Archives/edgar/data/1549346/000154934624000007/sstk-20231231.htm",
    "10-Q 2024-06-30": "https://www.sec.gov/Archives/edgar/data/1549346/000154934624000034/sstk-20240630.htm",
    "10-Q 2024-09-30": "https://www.sec.gov/Archives/edgar/data/1549346/000154934624000045/sstk-20240930.htm",
}

EIGHTK = "8-K filed 2024-07-22, Item 1.01 (A&R Credit Agreement)"
EX101 = "8-K Ex 10.1, Amended and Restated Credit Agreement dated 2024-07-22 (Bank of America, N.A., Administrative Agent)"
TENQ = "10-Q for the quarter ended 2024-06-30, consolidated balance sheet"
TENQ3 = "10-Q for the quarter ended 2024-09-30"
TENK_IS = "10-K FY2023 (year ended 2023-12-31), consolidated statement of operations"
TENK_N11 = "10-K FY2023, Note 11 Other Income / (Expense), net"
TENK_CF = "10-K FY2023, consolidated statement of cash flows"
TENK_ADJ = "10-K FY2023, MD&A reconciliation of net income to adjusted EBITDA and adjusted net income"
EX992_BS = "8-K/A Ex 99.2, Envato condensed consolidated statement of financial position at 2023-12-31 (IFRS, USD'000)"
EX992 = "8-K/A Ex 99.2, Envato interim statements (IFRS, USD'000)"
EX993_N4 = ("8-K/A Ex 99.3 Note 4, Envato statement of profit or loss, twelve months ended 2023-12-31 (column A - B + C, "
            "Envato's own captions, IFRS, USD thousands)")
EX993_6A = "8-K/A Ex 99.3 Note 6A, closing financing under the A&R Credit Agreement"
EX993 = "8-K/A Ex 99.3, unaudited pro forma condensed combined information"

BRIEF = Brief(
    lender="Bank of America, N.A., as Administrative Agent, and the lenders under the A&R Credit Agreement",
    agreement_ref=EX101,
    limit=3.50,
    limit_section="Section 7.11(b)",
    limit_wording="Permit the Consolidated Net Leverage Ratio as of the end of any Measurement Period of the Borrower "
                  "(commencing with the fiscal quarter ending September 30, 2024) to be greater than 3.50:1.00",
    debt_term="Consolidated Funded Indebtedness",
    debt_definition="The outstanding principal of all obligations for borrowed money (including the loans under this "
                    "agreement), bonds, notes and loan agreements, purchase money debt, drawn and unreimbursed letters of credit "
                    "and guaranties, deferred purchase price (other than ordinary trade payables), and Attributable Indebtedness "
                    "of Capital Leases (leases classified as capital or financing leases under GAAP). Section 1.03(a) carries it "
                    "at 100% of principal, so debt issuance costs are not netted. The ratio itself is NET: it subtracts "
                    "Unrestricted Cash, capped at the greater of $100,000K and 25% of Consolidated EBITDA. The Brief cannot net "
                    "cash, so the figure computed here is GROSS debt over EBITDA. That is a conservative reading: gross debt is "
                    "never below net debt, so a pass on the gross figure is a pass on the agreement's figure.",
    debt_excludes=[
        "Operating leases: Section 1.03(b) keeps every lease that is or would have been an operating lease under GAAP before "
        "ASC 842 as an operating lease for all financial definitions, so it is not a Capital Lease and not Attributable "
        "Indebtedness.",
        "Trade accounts payable in the ordinary course of business (clause (d) of the definition).",
        "Unamortized debt issuance costs: Section 1.03(a) carries Indebtedness at 100% of the outstanding principal amount.",
    ],
    ebitda_definition="Consolidated EBITDA: Consolidated Net Income plus, to the extent deducted, Consolidated Interest Charges, "
                      "income taxes, depreciation and amortization, non-cash charges (including impairment and purchase "
                      "accounting), extraordinary or non-recurring charges, non-recurring cash charges (including severance and "
                      "restructuring), costs of cost-saving, restructuring, integration and retention or completion bonuses, and "
                      "run-rate synergies (capped at 10%); less non-cash gains and extraordinary or non-recurring gains. The cash "
                      "add-backs under clauses (b)(v), (b)(vi) and (b)(viii) together may not exceed 20% of Consolidated EBITDA. "
                      "Consolidated Net Income excludes unusual and infrequent gains and losses and the income or loss of any "
                      "Person that is not a Subsidiary. The definition does NOT subtract interest income, so no line here is "
                      "named as interest income: Shutterstock's 'Interest income / (expense) and other' and Envato's 'Finance "
                      "income' stay in net income. Envato's 'Finance costs' ($4,644K) are not added back: Envato had no "
                      "borrowed money, and Ex 99.2 shows interest paid of only $46K in the six months to 2023-12-31 against "
                      "finance costs of $4,592K, so they are not shown to be Consolidated Interest Charges (conservative).",
    ebitda_addbacks=[
        Adjustment(name="Non-cash equity-based compensation", amount=48577.0,
                   source_ref=f"{TENK_CF}: Non-cash equity-based compensation 48,577; {EX101}, Consolidated EBITDA (b)(iv)",
                   note="Clause (b)(iv) adds back non-cash charges. Shutterstock's FY2023 figure; Envato's statements show no "
                        "separate share-based payment expense."),
        Adjustment(name="Giphy Retention Compensation Expense - non-recurring", amount=31577.0,
                   source_ref=f"{TENK_ADJ}: Giphy Retention Compensation Expense - non-recurring 31,577; {EX101}, "
                              f"Consolidated EBITDA (b)(vii) \"any retention or completion bonus\"",
                   note="One-time employment inducement bonuses and the cash value of unvested Meta equity awards for Giphy "
                        "employees, which Meta funded into escrow. Read as a retention bonus under (b)(vii), which has no cap. "
                        "Read under (b)(v) instead, it falls in the 20% cap, which it fits (see the severance note)."),
        Adjustment(name="Severance from workforce optimizations (within the 20% cap)", amount=12493.0,
                   source_ref=f"{TENK_ADJ}: adjusted net income 'Other' 12,493; 10-K accrued expenses note: $12.5 million of "
                              f"severance costs associated with workforce optimizations in 2023; {EX101}, Consolidated EBITDA (b)(vi)",
                   note="The 10-K names severance as the only 'Other' item in adjusted net income, and the adjusted EBITDA line "
                        "'Other adjustments, net' 8,686 equals 12,493 + interest expense 1,856 - interest income 4,784 - FX gain "
                        "879. A cash add-back under (b)(vi), so it counts toward the 20% cap on (b)(v), (b)(vi) and (b)(viii): "
                        "20% of EBITDA before those add-backs is about $47,500K, so it fits even with the Giphy figure added."),
        Adjustment(name="Envato share of losses of associates (excluded from Consolidated Net Income)", amount=2046.0,
                   source_ref=f"{EX993_N4}: Share of profits/(losses) of associates (2,046); {EX101}, Consolidated Net Income "
                              f"proviso (c)",
                   note="Consolidated Net Income excludes the income or loss of any Person that is not a Subsidiary. The loss is "
                        "Envato's 29.9% stake in Music Vine Limited, including a $1,638K impairment (Ex 99.2 Note 6); the stake "
                        "was sold on 2024-06-28 (Ex 99.2 Note 18). The pro forma removes the same amount (Ex 99.3 Note 5 (i))."),
    ],
    ebitda_deductions=[
        Adjustment(name="Bargain purchase gain (Giphy)", amount=50261.0,
                   source_ref=f"{TENK_IS}: Bargain purchase gain 50,261; {EX101}, Consolidated EBITDA (c) and Consolidated Net "
                              f"Income proviso (a)",
                   note="A non-cash, non-recurring gain from the 2023 Giphy acquisition. Clause (c) subtracts non-cash and "
                        "non-recurring gains."),
        Adjustment(name="Unrealized foreign currency gain (Shutterstock)", amount=879.0,
                   source_ref=f"{TENK_N11}: Foreign currency gain / (loss) 879; 10-K MD&A: $0.9 million of favorable unrealized "
                              f"foreign currency fluctuations; {EX101}, Consolidated EBITDA (c)(i)",
                   note="Clause (c)(i) subtracts non-cash gains. The 10-K calls the 2023 FX gain unrealized. Envato's $130K FX "
                        "gain for the same period is not split into realized and unrealized, so it is left in."),
    ],
    closing_financing=[
        Financing(name="Term Loan, A&R Credit Agreement (senior unsecured)", amount=125000.0, kind="senior_secured",
                  source_ref=f"{EX993_6A}: Term Loan Credit Facility 125,000; {TENQ3}, Note 7"),
        Financing(name="Revolver draw, A&R Credit Agreement (senior unsecured)", amount=155000.0, kind="senior_secured",
                  source_ref=f"{EX993_6A}: Revolver loan facility 155,000; {TENQ3}, Note 7"),
    ],
    test_period_note="Shutterstock: balance sheet at 2024-06-30 (10-Q), income statement and D&A for calendar 2023 (10-K). "
                     "Envato: balance sheet at 2023-12-31 (Ex 99.2, its last filed balance sheet), income statement for the "
                     "twelve months to 2023-12-31 (Ex 99.3 Note 4, which the filer built from the audited year to 2023-06-30 "
                     "and the two six-month periods). Both reported in USD; Envato's statements are IFRS and the pro forma says "
                     "no material adjustments were needed to convert them to US GAAP. The agreement tests the four quarters to "
                     "2024-09-30 first, with Envato included on a Pro Forma Basis (Section 1.03(d)), and it replaces Envato's "
                     "EBITDA for the quarters ended 2023-12-31, 2024-03-31 and 2024-06-30 with fixed amounts in Schedule 2.01E "
                     "('Effective Date Target EBITDA'), which was not filed. So the EBITDA here is a stand-in from the filed "
                     "statements, not the lender's figure. Limit: 3.50x at the first test. Section 7.11(b) lets the borrower "
                     "elect 4.00x by writing to the agent after a Specified Acquisition (price over $50,000,000), but only 'for "
                     "the first three full fiscal quarters occurring after the date of such Specified Acquisition'. The close "
                     "on 2024-07-22 falls inside the quarter ending 2024-09-30, so that quarter is not a full quarter after it "
                     "and 3.50x applies; the 4.00x step-up, if elected, would cover the quarters ending 2024-12-31 to "
                     "2025-06-30. No filing read shows an election, and the 2024-09-30 10-Q says the company was in compliance. "
                     "The breach test is 'greater than', so exactly 3.50x passes. Debt is the $280,000K borrowed at close; the "
                     "prior $30,000K revolver on the 2024-06-30 balance sheet was repaid from it (shown as a negative closing "
                     "line). The $250,213K cash paid for Envato is not taken out of cash, which does not matter to a gross "
                     "figure. Not held by the schema: the cash netting (by hand at 2024-09-30: $280,000K principal less "
                     "Unrestricted Cash capped at $100,000K of the $131,393K reported = $180,000K net), the interest coverage "
                     "covenant in Section 7.11(a) (at least 3.00x), and the 4.00x step-up.",
)

# Blocks of lines: (section, period, unit, source_ref, rows); rows are (line name as filed, amount, is_total).
# Shutterstock, USD thousands. Captions as filed; the curly apostrophe in the equity total is a straight one here.
_SSTK_BS_TO_DEBT = [
    ("Cash and cash equivalents", 74871, False),
    ("Accounts receivable, net", 97442, False),
    ("Prepaid expenses and other current assets", 68534, False),
    ("Total current assets", 240847, True),
    ("Property and equipment, net", 63069, False),
    ("Right-of-use assets", 15392, False),
    ("Intangible assets, net", 164508, False),
    ("Goodwill", 402774, False),
    ("Deferred tax assets, net", 23779, False),
    ("Other assets", 93497, False),
    ("Total assets", 1003866, True),
    ("Accounts payable", 10545, False),
    ("Accrued expenses", 96910, False),
    ("Contributor royalties payable", 65705, False),
    ("Deferred revenue", 186522, False),
    ("Debt", 30000, False),
]
# The closing financing (Ex 99.3 Note 6A; the 2024-09-30 10-Q confirms $125M term loan and $155M revolver).
_SSTK_CLOSE = [
    ("Term loan, A&R Credit Agreement", 125000, False),
    ("Revolving credit facility, A&R Credit Agreement", 155000, False),
    ("Repayment of prior revolving credit facility", -30000, False),
]
_SSTK_BS_REST = [
    ("Other current liabilities", 42649, False),
    ("Total current liabilities", 432331, True),
    ("Deferred tax liability, net", 3744, False),
    ("Lease liabilities", 26433, False),
    ("Other non-current liabilities", 20946, False),
    ("Total liabilities", 483454, True),
    ("Common stock", 402, False),
    ("Treasury stock", -248805, False),
    ("Additional paid-in capital", 441497, False),
    ("Accumulated other comprehensive loss", -13754, False),
    ("Retained earnings", 341072, False),
    ("Total stockholders' equity", 520412, True),
    ("Total liabilities and stockholders' equity", 1003866, True),
]
# Statement of operations face, with Other income / (expense), net shown in its Note 11 parts (expenses positive).
_SSTK_IS = [
    ("Revenue", 874587, False),
    ("Cost of revenue", 352630, False),
    ("Sales and marketing", 214749, False),
    ("Product development", 96162, False),
    ("General and administrative", 142646, False),
    ("Total operating expenses", 806187, True),
    ("Income from operations", 68400, True),
    ("Bargain purchase gain", 50261, False),
    ("Foreign currency gain / (loss)", 879, False),
    ("Interest expense", 1856, False),
    ("Interest income / (expense) and other", 4784, False),
    ("Other income / (expense), net", 3807, True),
    ("Income before income taxes", 122468, True),
    ("Provision for income taxes", 12199, False),
    ("Net income", 110269, True),
]
_SSTK_CF = [("Depreciation and amortization", 79729, False)]

PLATFORM_BLOCKS = [
    ("balance_sheet", "2024-06-30", "USD thousands", TENQ, _SSTK_BS_TO_DEBT),
    ("balance_sheet", "2024-07-22 (closing)", "USD thousands",
     f"{EX993_6A}: $125,000K Term Loan and $155,000K Revolver borrowed, $30,000K of it repaying the prior revolving loan "
     f"facility; {EIGHTK}", _SSTK_CLOSE),
    ("balance_sheet", "2024-06-30", "USD thousands", TENQ, _SSTK_BS_REST),
    ("income_statement", "FY ended 2023-12-31", "USD thousands", f"{TENK_IS}; Other income parts from {TENK_N11}", _SSTK_IS),
    ("cash_flow", "FY ended 2023-12-31", "USD thousands", TENK_CF, _SSTK_CF),
]

# Envato, USD thousands, IFRS, its own captions. Duplicate captions get "(current)" / "(non-current)" from their section.
_ENVATO_BS = [
    ("Cash and cash equivalent", 100940, False),
    ("Trade and other receivables", 5801, False),
    ("Current tax receivable", 0, False),
    ("Derivative financial instruments", 393, False),
    ("Total Current Assets", 107134, True),
    ("Property, plant and equipment", 1112, False),
    ("Intangible assets", 7924, False),
    ("Right-of-use assets (IFRS 16)", 621, False),
    ("Non-current prepayments", 1478, False),
    ("Financial assets at fair value through other comprehensive income", 1894, False),
    ("Investments accounted for using the equity method", 4123, False),
    ("Deferred tax asset", 11838, False),
    ("Total Non-Current Assets", 28990, True),
    ("Total assets", 136124, True),
    ("Trade and other payables", 25732, False),
    ("Lease liabilities (current)", 496, False),
    ("Provisions (current)", 28104, False),
    ("Deferred revenue", 45457, False),
    ("Current tax payable", 5868, False),
    ("Total Current Liabilities", 105657, True),
    ("Provisions (non-current)", 863, False),
    ("Lease liabilities (non-current)", 73, False),
    ("Total Non-Current Liabilities", 936, True),
    ("Total Liabilities", 106593, True),
    ("Net Assets", 29531, True),
    ("Contributed equity", 14, False),
    ("Retained earnings", 27684, False),
    ("Other reserves", 1833, False),
    ("Total Equity", 29531, True),
    ("Total liabilities and equity", 136124, True),
]
_ENVATO_IS = [
    ("Revenue from ordinary activities", 197809, False),
    ("Direct costs", 55772, False),
    ("Employee costs", 55032, False),
    ("Service provider expenses", 4234, False),
    ("Depreciation, amortization and impairment", 3633, False),
    ("Data and software expenses", 13345, False),
    ("Marketing expenses", 24004, False),
    ("Travel expenses", 555, False),
    ("Rental expenses", 40, False),
    ("Professional fees", 4634, False),
    ("Foreign exchange loss", -130, False),
    ("Other expenses", 1413, False),
    ("Operating profit", 35277, True),
    ("Finance income", 1749, False),
    ("Finance costs", 4644, False),
    ("Share of profits/(losses) of associates accounted for using the equity method", -2046, False),
    ("Profit before income tax", 30336, True),
    ("Income tax expense", 9524, False),
    ("Net income", 20812, True),
]
_ENVATO_CF = [("Depreciation and amortization", 3633, False)]

TARGET_BLOCKS = [
    ("balance_sheet", "2023-12-31", "USD thousands", EX992_BS, _ENVATO_BS),
    ("income_statement", "Twelve months ended 2023-12-31", "USD thousands", EX993_N4, _ENVATO_IS),
    ("cash_flow", "Twelve months ended 2023-12-31", "USD thousands",
     f"{EX993_N4}: the 'Depreciation, amortization and impairment' line (no cash flow statement covers this period)",
     _ENVATO_CF),
]

LINE_NOTES = {
    "Debt": "10-Q 2024-06-30: $30 million outstanding on the 2022 Bank of America revolving Credit Facility. The A&R Credit "
            "Agreement replaced it; it was repaid and terminated at the 2024-07-22 close (10-Q 2024-09-30, Note 7).",
    "Term loan, A&R Credit Agreement": "Ex 99.3 Note 6A: $125 million five-year senior unsecured Term Loan drawn at close. "
                                       "10-Q 2024-09-30: carrying value $3,834K current plus $120,392K non-current, with "
                                       "$0.8 million unamortized issuance cost (principal $125,000K).",
    "Revolving credit facility, A&R Credit Agreement": "Ex 99.3 Note 6A: $155 million drawn on the $250 million senior "
                                                       "unsecured Revolver at close. 10-Q 2024-09-30: $155,000K outstanding.",
    "Repayment of prior revolving credit facility": "Ex 99.3 Note 6A: $30 million of the $280 million borrowed repaid the "
                                                    "extinguished unsecured revolving loan facility (the 'Debt' line). Shown "
                                                    "as a negative closing line so that debt at close is $280,000K, not "
                                                    "$310,000K.",
    "Lease liabilities": "Shutterstock's non-current operating lease liabilities under ASC 842 (10-K: operating leases are in "
                         "ROU assets, other current liabilities and lease liabilities). Section 1.03(b) keeps them as "
                         "operating leases, so they are not debt.",
    "Other current liabilities": "Includes the current portion of Shutterstock's operating lease liabilities (10-K leases "
                                 "note) and the chargeback and refund allowance (10-Q).",
    "Interest expense": "10-K Note 11: interest expense on the credit facility, $1,856K, a part of Other income / "
                        "(expense), net.",
    "Interest income / (expense) and other": "10-K Note 11. The MD&A puts 2023 interest income at $4.8 million. Not "
                                             "subtracted: this agreement's Consolidated EBITDA does not deduct interest "
                                             "income.",
    "Foreign currency gain / (loss)": "10-K Note 11: a gain of $879K; the MD&A calls it favorable unrealized foreign "
                                      "currency fluctuations.",
    "Bargain purchase gain": "10-K: the gain on the June 2023 Giphy acquisition, where the fair value of net assets "
                             "exceeded the net consideration.",
    "Trade and other receivables": "Ex 99.2 Note 9 at 2023-12-31: trade receivables $76K, prepayments $2,684K, accrued income "
                                   "$1,540K, other receivables $1,501K. The pro forma moved $3,507K of the 2024-03-31 balance "
                                   "to prepaid expenses and other current assets (Ex 99.3 Note 5 (ii)).",
    "Derivative financial instruments": "Ex 99.2 cash flow reconciliation: gains on forward exchange contracts. An asset, "
                                        "not a swap obligation.",
    "Right-of-use assets (IFRS 16)": "Ex 99.2 Note 11: buildings only, cost $1,926K less accumulated depreciation $1,305K. "
                                     "Filed caption 'Right-of-use assets'; '(IFRS 16)' added to tell it from Shutterstock's "
                                     "line of the same name.",
    "Lease liabilities (current)": "Ex 99.2 Note 14: IFRS 16 lease liabilities, $496K current and $73K non-current, all "
                                   "payable within five years, for premises (Note 11 buildings; Note 17 bank guarantee 'as "
                                   "part of the lease of premises'). IFRS 16 puts every lease on the balance sheet and has no "
                                   "operating or finance lease split for lessees.",
    "Lease liabilities (non-current)": "Ex 99.2 Note 14: IFRS 16 lease liabilities, $496K current and $73K non-current, for "
                                       "premises. IFRS 16 has no operating or finance lease split for lessees.",
    "Provisions (current)": "Ex 99.2 Note 15: employee benefits $3,021K and global sales tax $25,083K. The sales tax provision "
                            "is a weighted-probability estimate of indirect tax exposures (Note 3). Not borrowed money.",
    "Provisions (non-current)": "Ex 99.2 Note 15: employee benefits $808K and make good provision $55K.",
    "Trade and other payables": "Ex 99.2 Note 13: trade payables $16,495K and other payables $9,237K (general accruals "
                                "$5,362K, sales tax liabilities $2,552K, payroll related $1,308K, other $14K); non-interest "
                                "bearing.",
    "Financial assets at fair value through other comprehensive income": "Sold on 2024-06-28, before the close (Ex 99.2 "
                                                                         "Note 18).",
    "Investments accounted for using the equity method": "29.9% of Music Vine Limited (Ex 99.2 Note 6); sold on 2024-06-28, "
                                                         "before the close (Note 18).",
    "Total liabilities and equity": "Not a filed caption: Envato presents Net Assets and Total Equity. Total Liabilities "
                                    "$106,593K plus Total Equity $29,531K, added so the balance sheet has the total the "
                                    "tie-out needs.",
    "Total assets": "Shutterstock files 'Total assets'; Envato files 'TOTAL ASSETS' (case changed only).",
    "Net income": "Shutterstock files 'Net income'. Envato files 'Profit for the period' (renamed so the ebitda tool finds it).",
    "Depreciation, amortization and impairment": "Ex 99.3 Note 4 spelling; Envato's own statements spell it 'amortisation'.",
    "Finance costs": "Ex 99.3 Note 4: $4,644K for the twelve months, of which $4,592K in the six months to 2023-12-31, when "
                     "Ex 99.2 shows interest paid of only $46K and Envato had no borrowings. What the cost is, is not "
                     "disclosed. Not added back to covenant EBITDA (conservative).",
    "Finance income": "Ex 99.2 cash flow: interest received $1,019K in the six months to 2023-12-31.",
    "Share of profits/(losses) of associates accounted for using the equity method":
        "Music Vine Limited, including a $1,638K impairment in the six months to 2023-12-31 (Ex 99.2 Note 6).",
    "Foreign exchange loss": "Ex 99.3 Note 4: (130), a net gain for the twelve months; stored as a negative expense.",
}

# The scripted Mapper's reference answer: every Envato line -> (Shutterstock line or None, confidence, reason).
MAPPING = {
    # balance sheet
    "Cash and cash equivalent": ("Cash and cash equivalents", 0.98, "Same meaning; the pro forma maps it the same way."),
    "Trade and other receivables": ("Prepaid expenses and other current assets", 0.45,
                                    "Mostly prepayments and other receivables (Note 9); the pro forma split it between "
                                    "receivables and prepaid expenses."),
    "Current tax receivable": ("Prepaid expenses and other current assets", 0.85,
                               "Shutterstock has no tax receivable line; a current non-trade asset. Nil at 2023-12-31."),
    "Derivative financial instruments": ("Prepaid expenses and other current assets", 0.75,
                                         "Forward exchange contracts in an asset position; Shutterstock has no derivative "
                                         "line."),
    "Total Current Assets": ("Total current assets", 0.98, "Same subtotal."),
    "Property, plant and equipment": ("Property and equipment, net", 0.95, "Same meaning, net of depreciation."),
    "Intangible assets": ("Intangible assets, net", 0.95, "Same meaning, net of amortization."),
    "Right-of-use assets (IFRS 16)": ("Right-of-use assets", 0.92, "Lease assets; the pro forma maps it to Right-of-use asset."),
    "Non-current prepayments": ("Other assets", 0.85, "Long-term prepaid content; the pro forma puts it in Other assets."),
    "Financial assets at fair value through other comprehensive income": ("Other assets", 0.8,
                                                                         "A non-current investment; Shutterstock has no "
                                                                         "investment line."),
    "Investments accounted for using the equity method": ("Other assets", 0.8,
                                                          "A non-current investment; Shutterstock has no investment line."),
    "Deferred tax asset": ("Deferred tax assets, net", 0.95, "Same meaning."),
    "Total Non-Current Assets": (None, 0.9, "Shutterstock has no non-current assets subtotal; the parts are mapped."),
    "Total assets": ("Total assets", 0.99, "Same total."),
    "Trade and other payables": ("Contributor royalties payable", 0.45,
                                 "Holds author payouts, trade payables and accruals (Note 13); the pro forma split it across "
                                 "four Shutterstock lines, mostly contributor royalties."),
    "Lease liabilities (current)": ("Other current liabilities", 0.8,
                                    "Shutterstock carries current lease liabilities in Other current liabilities; the pro "
                                    "forma maps it there (Note 5 (iv))."),
    "Provisions (current)": ("Other current liabilities", 0.8,
                             "Sales tax and employee provisions; the pro forma maps them to Other current liabilities."),
    "Deferred revenue": ("Deferred revenue", 0.97, "Same meaning."),
    "Current tax payable": ("Other current liabilities", 0.8,
                            "Shutterstock has no tax payable line; the pro forma maps it to Other current liabilities."),
    "Total Current Liabilities": ("Total current liabilities", 0.98, "Same subtotal."),
    "Provisions (non-current)": ("Other non-current liabilities", 0.85, "The pro forma maps it there (Note 5 (v))."),
    "Lease liabilities (non-current)": ("Lease liabilities", 0.85,
                                        "Shutterstock's non-current lease liabilities line; the lease's classification under "
                                        "the covenant is a separate question."),
    "Total Non-Current Liabilities": (None, 0.9, "Shutterstock has no non-current liabilities subtotal; the parts are mapped."),
    "Total Liabilities": ("Total liabilities", 0.98, "Same total."),
    "Net Assets": (None, 0.9, "An IFRS presentation subtotal equal to Total Equity; Shutterstock has none."),
    "Contributed equity": ("Additional paid-in capital", 0.85, "Paid-in capital; the pro forma maps Issued Capital there."),
    "Retained earnings": ("Retained earnings", 0.97, "Same meaning."),
    "Other reserves": ("Accumulated other comprehensive loss", 0.7,
                       "Translation and fair value reserves, which US GAAP holds in other comprehensive income."),
    "Total Equity": ("Total stockholders' equity", 0.97, "Same total."),
    "Total liabilities and equity": ("Total liabilities and stockholders' equity", 0.99, "Same total."),
    # income statement
    "Revenue from ordinary activities": ("Revenue", 0.98, "Same meaning."),
    "Direct costs": ("Cost of revenue", 0.8, "The pro forma puts 50,429 of 55,772 in cost of revenue (Note 5 (ii))."),
    "Employee costs": ("Product development", 0.4,
                       "Expensed by nature under IFRS; Shutterstock reports by function. The pro forma spread it over four "
                       "lines."),
    "Service provider expenses": ("Cost of revenue", 0.65, "The pro forma puts 2,451 of 4,234 in cost of revenue."),
    "Depreciation, amortization and impairment": ("Cost of revenue", 0.85,
                                                  "The pro forma puts 3,507 of 3,633 in cost of revenue."),
    "Data and software expenses": ("Cost of revenue", 0.7, "The pro forma puts 8,824 of 13,345 in cost of revenue."),
    "Marketing expenses": ("Sales and marketing", 0.95, "The pro forma maps it the same way."),
    "Travel expenses": ("General and administrative", 0.9, "The pro forma maps it the same way."),
    "Rental expenses": ("General and administrative", 0.9, "The pro forma maps it the same way."),
    "Professional fees": ("General and administrative", 0.9, "The pro forma maps it the same way."),
    "Foreign exchange loss": ("General and administrative", 0.65,
                              "An operating expense line with the expense sign; Shutterstock reports realized FX losses in "
                              "G&A. The pro forma moves it to other income instead."),
    "Other expenses": ("General and administrative", 0.85, "The pro forma maps it the same way."),
    "Operating profit": ("Income from operations", 0.95, "Same subtotal."),
    "Finance income": ("Interest income / (expense) and other", 0.8, "Interest received; Shutterstock's interest income line."),
    "Finance costs": ("Interest expense", 0.7, "Finance costs; what they consist of is not disclosed."),
    "Share of profits/(losses) of associates accounted for using the equity method":
        ("Interest income / (expense) and other", 0.6, "Non-operating; Shutterstock's catch-all other line in Note 11."),
    "Profit before income tax": ("Income before income taxes", 0.97, "Same subtotal."),
    "Income tax expense": ("Provision for income taxes", 0.97, "Same meaning."),
    "Net income": ("Net income", 0.99, "Same total."),
    # cash flow
    "Depreciation and amortization": ("Depreciation and amortization", 0.95,
                                      "Same meaning; Envato's figure includes impairment."),
}

# Covenant tags for balance sheet lines of both companies, by line name.
TAGS = {
    # Shutterstock
    "Cash and cash equivalents": ("na", "Cash. The agreement nets Unrestricted Cash (capped), which the schema cannot do."),
    "Accounts receivable, net": ("na", "An asset."),
    "Prepaid expenses and other current assets": ("na", "An asset."),
    "Total current assets": ("na", "A subtotal of assets."),
    "Property and equipment, net": ("na", "An asset."),
    "Right-of-use assets": ("na", "An asset."),
    "Intangible assets, net": ("na", "An asset."),
    "Goodwill": ("na", "An asset."),
    "Deferred tax assets, net": ("na", "An asset."),
    "Other assets": ("na", "An asset."),
    "Total assets": ("na", "A total."),
    "Accounts payable": ("na", "Trade payables, excluded by clause (d)."),
    "Accrued expenses": ("na", "Accruals, not borrowed money."),
    "Contributor royalties payable": ("na", "Royalties owed to contributors, an ordinary-course payable."),
    "Deferred revenue": ("na", "Customer prepayments, not borrowed money."),
    "Debt": ("debt", "The $30,000K drawn on the prior revolving Credit Facility, borrowed money; repaid at close."),
    "Term loan, A&R Credit Agreement": ("debt", "Borrowed money under this agreement (Obligations hereunder)."),
    "Revolving credit facility, A&R Credit Agreement": ("debt", "Borrowed money under this agreement."),
    "Repayment of prior revolving credit facility": ("debt", "Takes the repaid $30,000K out of debt at close."),
    "Other current liabilities": ("na", "Current operating lease liabilities and allowances, not borrowed money."),
    "Total current liabilities": ("na", "A subtotal."),
    "Deferred tax liability, net": ("na", "A tax balance."),
    "Lease liabilities": ("na", "Operating leases under ASC 842; Section 1.03(b) keeps them out of every financial definition."),
    "Other non-current liabilities": ("na", "Not borrowed money."),
    "Total liabilities": ("na", "A total."),
    "Common stock": ("na", "Equity."),
    "Treasury stock": ("na", "Equity."),
    "Additional paid-in capital": ("na", "Equity."),
    "Accumulated other comprehensive loss": ("na", "Equity."),
    "Retained earnings": ("na", "Equity."),
    "Total stockholders' equity": ("na", "Equity."),
    "Total liabilities and stockholders' equity": ("na", "A total."),
    # Envato
    "Cash and cash equivalent": ("na", "Cash."),
    "Trade and other receivables": ("na", "An asset."),
    "Current tax receivable": ("na", "An asset."),
    "Derivative financial instruments": ("na", "An asset (forward exchange contracts in a gain position)."),
    "Total Current Assets": ("na", "A subtotal of assets."),
    "Property, plant and equipment": ("na", "An asset."),
    "Intangible assets": ("na", "An asset."),
    "Right-of-use assets (IFRS 16)": ("na", "An asset."),
    "Non-current prepayments": ("na", "An asset."),
    "Financial assets at fair value through other comprehensive income": ("na", "An asset."),
    "Investments accounted for using the equity method": ("na", "An asset."),
    "Deferred tax asset": ("na", "An asset."),
    "Total Non-Current Assets": ("na", "A subtotal of assets."),
    "Trade and other payables": ("na", "Non-interest-bearing trade and other payables (Ex 99.2 Note 13), clause (d)."),
    "Lease liabilities (current)": ("unclear", "IFRS 16 lease liability for premises. Debt only if it is a Capital Lease under "
                                               "GAAP; Section 1.03(b) keeps pre-ASC 842 operating leases out."),
    "Provisions (current)": ("na", "Sales tax and employee provisions (Note 15), not borrowed money."),
    "Current tax payable": ("na", "A tax balance."),
    "Total Current Liabilities": ("na", "A subtotal."),
    "Provisions (non-current)": ("na", "Employee benefits and make good provisions (Note 15), not borrowed money."),
    "Lease liabilities (non-current)": ("unclear", "IFRS 16 lease liability for premises; same question as the current part."),
    "Total Non-Current Liabilities": ("na", "A subtotal."),
    "Total Liabilities": ("na", "A total."),
    "Net Assets": ("na", "Equity subtotal."),
    "Contributed equity": ("na", "Equity."),
    "Other reserves": ("na", "Equity."),
    "Total Equity": ("na", "Equity."),
    "Total liabilities and equity": ("na", "A total."),
}

COVENANT_FLAG = {
    "lines": ["Lease liabilities (current)", "Lease liabilities (non-current)"],
    "question": "Do Envato's IFRS 16 lease liabilities ($569K: $496K current, $73K non-current, its office premises) "
                "count as Consolidated Funded Indebtedness? IFRS puts every lease on the balance sheet; the agreement "
                "counts only GAAP capital or financing leases, and Section 1.03(b) keeps pre-ASC 842 operating leases "
                "operating. Envato's statements do not say how US GAAP would classify this lease.",
    "options": [
        ("a", "Count them, as IFRS shows them",
         {"Lease liabilities (current)": "debt", "Lease liabilities (non-current)": "debt"}),
        ("b", "Do not count them: an operating lease under US GAAP",
         {"Lease liabilities (current)": "not_debt", "Lease liabilities (non-current)": "not_debt"}),
    ],
    "default": "b",
    "evidence": [
        ("means each lease that has been or is required to be, in accordance with GAAP, classified and accounted for as a "
         "capital lease or financing lease.", "8-K Ex 10.1, Section 1.01, definition of Capital Lease"),
        ("all obligations of any Person that are or would have been treated as operating leases for purposes of GAAP prior to "
         "the effectiveness of FASB ASC 842 shall continue to be accounted for as operating leases for purposes of all "
         "financial definitions and calculations for purposes of this Agreement.", "8-K Ex 10.1, Section 1.03(b)"),
        ("all Attributable Indebtedness", "8-K Ex 10.1, definition of Consolidated Funded Indebtedness, clause (e)"),
        ("There were no material adjustments required to convert these financial statements to United States generally "
         "accepted accounting principles", "8-K/A Ex 99.3, Note 1"),
        ("Represents the reclassification of \"Lease liabilities\", \"Provisions\" and \"Current tax payable\" on Envato's "
         "statement of financial position into \"Other current liabilities\"", "8-K/A Ex 99.3, Note 5 (iv)"),
        ("An unsecured bank guarantee has been provided to the value of USD 189 thousand as part of the lease of premises.",
         "8-K/A Ex 99.2, Note 17 (transcribed from the scanned page)"),
    ],
}

MAPPING_FLAGS = {
    "Trade and other receivables": {
        "question": "Envato's 'Trade and other receivables' ($5,801K) is mostly not trade receivables: Ex 99.2 Note 9 shows "
                    "trade receivables $76K, prepayments $2,684K, accrued income $1,540K and other receivables $1,501K. The "
                    "pro forma split the 2024-03-31 balance about evenly between Accounts receivable, net and Prepaid "
                    "expenses and other current assets (Ex 99.3 Note 5 (ii)). Which Shutterstock line takes it?",
        "options": [
            ("a", "Prepaid expenses and other current assets (prepayments and other receivables are 72% of it)",
             "Prepaid expenses and other current assets"),
            ("b", "Accounts receivable, net (the filed caption says receivables)", "Accounts receivable, net"),
        ],
        "default": "a",
    },
    "Trade and other payables": {
        "question": "Envato's 'Trade and other payables' ($25,732K) mixes trade payables $16,495K with general accruals, "
                    "sales tax and payroll liabilities $9,237K (Ex 99.2 Note 13). Envato's trade payables include what it owes "
                    "authors. At 2024-03-31 the pro forma split the line into Contributor royalties payable $15,269K, "
                    "Accrued expenses $10,126K, Accounts payable $2,439K and Other current liabilities (Ex 99.3 Note 5 (iii)). "
                    "Which Shutterstock line takes it?",
        "options": [
            ("a", "Contributor royalties payable (the largest part in the pro forma split)", "Contributor royalties payable"),
            ("b", "Accounts payable (the filed caption)", "Accounts payable"),
            ("c", "Accrued expenses", "Accrued expenses"),
        ],
        "default": "a",
    },
    "Employee costs": {
        "question": "Envato reports expenses by nature, and 'Employee costs' ($55,032K for the twelve months) has no single "
                    "home in Shutterstock's statement by function. The pro forma spread it as Product development $23,606K, "
                    "General and administrative $15,831K, Sales and marketing $8,022K and Cost of revenue $7,573K (Ex 99.3 "
                    "Note 5 (iii)). Which line takes it in the combined book?",
        "options": [
            ("a", "Product development (the largest share, 43%)", "Product development"),
            ("b", "General and administrative", "General and administrative"),
            ("c", "Cost of revenue", "Cost of revenue"),
        ],
        "default": "a",
    },
}
