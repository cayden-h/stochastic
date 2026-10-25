"""DLH Holdings acquires Grove Resource Solutions (GRSi). Every figure is from a public filing.

Sources (all read on 2026-10-24 from SEC EDGAR):
- TENK: DLH 10-K for the fiscal year ended 2022-09-30: balance sheet, statement of operations, cash flow statement
  (depreciation and amortization, stock-based compensation), Note 7 (debt obligations).
  https://www.sec.gov/Archives/edgar/data/785557/000078555722000046/dlhc-20220930.htm
- EIGHTK: 8-K filed 2022-12-14, Items 1.01 and 2.01: the price and the closing draws ($190M term loans, $25.2M revolver).
  https://www.sec.gov/Archives/edgar/data/785557/000078555722000052/dlhc-20221208.htm
- EX101: 8-K Ex 10.1, Second Amended and Restated Credit Agreement dated 2022-12-08: Section 8.2.16 and the definitions
  (Total Funded Debt, Indebtedness, Total Leverage Ratio, Consolidated EBITDA, Consolidated Net Income, Transaction Expenses).
  https://www.sec.gov/Archives/edgar/data/785557/000078555722000052/aomega12082022exh101comp.htm
- EX991: 8-K/A Ex 99.1, GRSi audited statements for 2021 and 2020 (Note 9: the shareholder redemption notes).
  https://www.sec.gov/Archives/edgar/data/785557/000078555723000034/pdfissuedfinancialstatem.htm
- EX992: 8-K/A Ex 99.2, GRSi unaudited statements as of and for the nine months ended 2022-09-30 (whole dollars).
  https://www.sec.gov/Archives/edgar/data/785557/000078555723000034/unauditedproformagrsi9-3.htm
- EX993: 8-K/A Ex 99.3, unaudited pro forma condensed combined statements (notes 3b and 3c conform GRSi to DLH).
  https://www.sec.gov/Archives/edgar/data/785557/000078555723000034/exhibit993unauditedproform.htm
- EX994: 8-K/A Ex 99.4, unaudited pro forma EBITDA reconciliation, year ended 2022-09-30 (a cross-check only).
  https://www.sec.gov/Archives/edgar/data/785557/000078555723000034/exhibit994proformaebitdagr.htm
Figures marked inferred are our estimates and must be said out loud.
"""
from __future__ import annotations

from app.core.models import Adjustment, Brief, Financing

DEAL_ID = "d_dlh_grsi"
NAME = "DLH Holdings Corp. acquires Grove Resource Solutions (GRSi)"
PLATFORM = "DLH"
TARGET = "GRSi"
NOTE = ("DLH Holdings bought Grove Resource Solutions (GRSi) on 2022-12-08 for $185 million ($178 million cash, "
        "funded by $215.2 million of new FNB-led bank debt, plus $7 million of stock), under a Total Leverage Ratio "
        "covenant of at most 4.50 to 1.00.")
SOURCES = {
    "10-K FY2022": "https://www.sec.gov/Archives/edgar/data/785557/000078555722000046/dlhc-20220930.htm",
    "8-K": "https://www.sec.gov/Archives/edgar/data/785557/000078555722000052/dlhc-20221208.htm",
    "8-K Ex 10.1": "https://www.sec.gov/Archives/edgar/data/785557/000078555722000052/aomega12082022exh101comp.htm",
    "8-K/A Ex 99.1": "https://www.sec.gov/Archives/edgar/data/785557/000078555723000034/pdfissuedfinancialstatem.htm",
    "8-K/A Ex 99.2": "https://www.sec.gov/Archives/edgar/data/785557/000078555723000034/unauditedproformagrsi9-3.htm",
    "8-K/A Ex 99.3": "https://www.sec.gov/Archives/edgar/data/785557/000078555723000034/exhibit993unauditedproform.htm",
    "8-K/A Ex 99.4": "https://www.sec.gov/Archives/edgar/data/785557/000078555723000034/exhibit994proformaebitdagr.htm",
}

TENK_BS = "DLH 10-K FY2022, consolidated balance sheet at 2022-09-30"
TENK_IS = "DLH 10-K FY2022, consolidated statement of operations, year ended 2022-09-30"
TENK_CF = "DLH 10-K FY2022, consolidated statement of cash flows, year ended 2022-09-30"
TENK_DEBT = "DLH 10-K FY2022, Note 7 Debt obligations"
EIGHTK = "8-K filed 2022-12-14, Item 1.01, closing draws under the Second Amended and Restated Credit Agreement"
EX101 = "8-K Ex 10.1, Second Amended and Restated Credit Agreement dated 2022-12-08"
EX991 = "8-K/A Ex 99.1, GRSi audited statements, years ended 2021-12-31 and 2020-12-31"
EX992_BS = "8-K/A Ex 99.2, GRSi unaudited balance sheet at 2022-09-30"
EX992_IS = "8-K/A Ex 99.2, GRSi unaudited statement of income, nine months ended 2022-09-30"
EX992_CF = "8-K/A Ex 99.2, GRSi unaudited statement of cash flow, nine months ended 2022-09-30"
EX993 = "8-K/A Ex 99.3, unaudited pro forma condensed combined statements, year ended / at 2022-09-30"
EX994 = "8-K/A Ex 99.4, unaudited pro forma EBITDA reconciliation, year ended 2022-09-30"

BRIEF = Brief(
    lender="First National Bank of Pennsylvania, as Administrative Agent, and the other Lenders",
    agreement_ref=EX101,
    limit=4.50,
    limit_section="Section 8.2.16",
    limit_wording="The Borrowers shall not permit the Total Leverage Ratio as of the end of any fiscal quarter during "
                  "the term of this Agreement (commencing with the fiscal quarter ending December 31, 2022) to exceed "
                  "the ratio set forth below for the periods specified below: Period Total Leverage Ratio From "
                  "December 31, 2022, through and including fiscal quarter ending December 31, 2023 4.50 to 1.00",
    debt_term="Total Funded Debt",
    debt_definition="As of any date of determination, without duplication, the sum of all Indebtedness representing "
                    "borrowed money, including both the current and long-term portion thereof, capitalized lease "
                    "obligations, reimbursement obligations under Letters of Credit, and guaranty obligations in "
                    "respect of any of the foregoing, for the Borrowers and their subsidiaries under GAAP.",
    debt_excludes=[
        "Trade payables and accrued expenses incurred in the ordinary course of business which are not represented "
        "by a promissory note or other evidence of indebtedness and which are not more than thirty (30) days past due "
        "(the Indebtedness definition)",
        "Operating lease liabilities: the definition counts capitalized lease obligations only (our reading)",
    ],
    ebitda_definition="Consolidated Net Income plus, to the extent deducted: all interest expense, taxes, depreciation, "
                      "amortization, other non-cash charges including stock-based compensation, and non-recurring "
                      "charges outside the ordinary course including Transaction Expenses (capped at $10,250,000 in "
                      "aggregate, subject to the Administrative Agent's reasonable approval). Interest income is not "
                      "deducted.",
    ebitda_addbacks=[
        Adjustment(name="Stock-based compensation (DLH)", amount=2608.0,
                   source_ref=f"{TENK_CF}: stock-based compensation expense $2,608K; add-back (iv) in {EX101}, "
                              "Consolidated EBITDA",
                   note="The agreement adds back other non-cash charges, including stock-based compensation. "
                        "GRSi's statements show none."),
        Adjustment(name="Interest income (GRSi), which this agreement does not deduct", amount=16.637,
                   source_ref=f"{EX992_IS}: interest income $16,637; {EX101}, Consolidated EBITDA",
                   note="Consolidated EBITDA adds back interest expense only, so interest income stays in. The "
                        "ebitda tool always subtracts interest income, so this restores it. Drop this add-back if "
                        "the tool stops subtracting interest income for this agreement."),
        Adjustment(name="Transaction Expenses: GRSi acquisition expenses", amount=800.0, cap=10250.0,
                   source_ref=f"{EX993}, note 3c: 'Eliminate GRSi incurred acquisition expenses' $(800)K; "
                              f"Transaction Expenses in {EX101}",
                   note="The pro forma gives $800K for the twelve months to 2022-09-30; we assume it falls in GRSi's "
                        "nine months to 2022-09-30. The $10,250K cap is on all Transaction Expenses together, and "
                        "the add-back is subject to the Administrative Agent's reasonable approval.",
                   inferred=True),
        Adjustment(name="Transaction Expenses: DLH corporate development costs", amount=614.0, cap=10250.0,
                   source_ref=f"{TENK_IS}: corporate development costs $614K; Transaction Expenses and "
                              f"non-recurring charges in {EX101}",
                   note="The 10-K calls these 'incremental due diligence costs, such as legal and accounting fees' "
                        "but does not say they were for GRSi. We treat them as non-recurring Transaction Expenses. "
                        "Same $10,250K aggregate cap.",
                   inferred=True),
    ],
    ebitda_deductions=[],
    closing_financing=[
        Financing(name="Term Loans", amount=190000.0, kind="senior_secured",
                  source_ref=f"{EIGHTK}: 'DLH received $190 million of funds under the Term Loans'"),
        Financing(name="Revolving Credit Facility draw", amount=25200.0, kind="senior_secured",
                  source_ref=f"{EIGHTK}: '$25.2 million of funds under the Revolving Credit Facility'"),
    ],
    test_period_note="DLH: fiscal year ended 2022-09-30 (10-K). GRSi: balance sheet at 2022-09-30 and income statement "
                     "for the NINE months ended 2022-09-30 (Ex 99.2), the filed GRSi period closest to DLH's year; "
                     "GRSi's last full filed year is calendar 2021 (Ex 99.1, net income $8,895K). Nine months "
                     "understate a twelve-month EBITDA: the pro forma (Ex 99.3, Ex 99.4) shows GRSi at $15,509K of "
                     "EBITDA for the twelve months to 2022-09-30, but only in DLH's captions, so it is not used. "
                     "The agreement deems Consolidated EBITDA for the four quarters to 2022-09-30 at $16,335,925, "
                     "$15,964,761, $14,360,238 and $11,172,834 ($57,833,758 in all), a lender cross-check the "
                     "schema cannot hold. The limit steps down from 4.50 (to the quarter ending 2023-12-31) to "
                     "4.25, 3.75, 3.25, 2.75, 2.50 and 2.00 (from the quarter ending 2026-09-30). The covenant reads "
                     "'not to exceed', so 4.50 itself passes. Not held: the step-downs, the deemed EBITDA, the "
                     "Fixed Charge Coverage Ratio of at least 1.25 (Section 8.2.15), and about $2.0M of undrawn "
                     "letters of credit (inferred from the 10-K: $25.0M revolver, $23.0M unused 'net of outstanding "
                     "letters of credit', no borrowings), which are not counted.",
)

# Blocks of lines: (section, period, unit, source_ref, rows); rows are (line name as filed, amount, is_total).
DLH_BS_ASSETS_TO_DEBT = [
    ("Cash", 228, False), ("Accounts receivable", 40496, False), ("Other current assets", 2878, False),
    ("Total current assets", 43602, True),
    ("Equipment and improvements, net", 1704, False), ("Operating lease right-of-use-assets", 16851, False),
    ("Goodwill", 65643, False), ("Intangible assets, net", 40884, False), ("Other long-term assets", 328, False),
    ("Total assets", 169012, True),
    ("Operating lease liabilities - current", 2235, False), ("Accrued payroll", 9444, False),
    ("Deferred revenue", 0, False), ("Accounts payable and accrued liabilities", 26862, False),
    ("Total current liabilities", 38541, True),
    ("Deferred taxes, net", 1534, False), ("Operating lease liabilities - long-term", 16461, False),
    ("Debt obligations - long-term, net of deferred financing costs", 20416, False),
]
# The closing financing (8-K Item 1.01), placed next to the debt line. It does not change DLH's filed totals.
DLH_CLOSE = [
    ("Term loans: Second Amended and Restated Credit Agreement", 190000, False),
    ("Revolving credit facility: draw at close", 25200, False),
]
DLH_BS_REST = [
    ("Total long-term liabilities", 38411, True), ("Total liabilities", 76952, True),
    ("Common stock", 13, False), ("Additional paid-in capital", 91057, False),
    ("Retained earnings (accumulated deficit)", 990, False), ("Total shareholders' equity", 92060, True),
    ("Total liabilities and shareholders' equity", 169012, True),
]
DLH_IS = [
    ("Revenue", 395173, False), ("Contract costs", 322886, False), ("General and administrative costs", 30730, False),
    ("Corporate development costs", 614, False), ("Depreciation and amortization", 7665, False),
    ("Total operating costs", 361895, True), ("Income from operations", 33278, True), ("Interest expense", 2215, False),
    ("Income before provision for income taxes", 31063, True), ("Provision for income taxes", 7775, False),
    ("Net income", 23288, True),
]
DLH_CF = [("Depreciation and amortization", 7665, False)]

# GRSi, whole dollars (Ex 99.2)
GRSI_BS = [
    ("Cash", 3606313, False), ("Accounts receivable", 21404561, False), ("Other current assets", 256791, False),
    ("Total current assets", 25267665, True),
    ("Property and equipment, net", 549550, False), ("Other long-term assets", 144857, False),
    ("Total assets", 25962072, True),
    ("Accounts payable and accrued expenses", 1686635, False),
    ("Accrued payroll and related liabilities", 5699254, False), ("Other current liabilities", 209, False),
    ("Total current liabilities", 7386098, True),
    ("Deferred rent", 769308, False), ("Note payable, shareholder", 30246414, False),
    ("Total liabilities", 38401820, True),
    ("Common stock", 1740, False), ("Additional paid-in capital", 0, False),
    ("Treasury stock, at cost", -29310696, False), ("Retained earnings", 16869208, False),
    ("Total stockholders' equity", -12439748, True),
    ("Total liabilities and stockholders' equity", 25962072, True),
]
GRSI_IS = [
    ("Revenue", 88197944, False), ("Direct costs", 53085780, False), ("Indirect costs", 22734962, False),
    ("Total operating costs", 75820742, True), ("Income from operations", 12377202, True),
    ("Interest income", 16637, False), ("Interest expense", 4673, False),
    ("Total other income (expense)", 11964, True), ("Net income", 12389166, True),
]
GRSI_CF = [("Depreciation and amortization", 164824, False)]

PLATFORM_BLOCKS = [
    ("balance_sheet", "2022-09-30", "USD thousands", TENK_BS, DLH_BS_ASSETS_TO_DEBT),
    ("balance_sheet", "2022-12-08 (closing)", "USD thousands", EIGHTK, DLH_CLOSE),
    ("balance_sheet", "2022-09-30", "USD thousands", TENK_BS, DLH_BS_REST),
    ("income_statement", "FY ended 2022-09-30", "USD thousands", TENK_IS, DLH_IS),
    ("cash_flow", "FY ended 2022-09-30", "USD thousands", TENK_CF, DLH_CF),
]
TARGET_BLOCKS = [
    ("balance_sheet", "2022-09-30", "USD", EX992_BS, GRSI_BS),
    ("income_statement", "Nine months ended 2022-09-30", "USD", EX992_IS, GRSI_IS),
    ("cash_flow", "Nine months ended 2022-09-30", "USD", EX992_CF, GRSI_CF),
]

LINE_NOTES = {
    "Debt obligations - long-term, net of deferred financing costs":
        "10-K Note 7: secured term loan $22,000K less unamortized deferred financing costs $1,584K; no revolver "
        "balance at 2022-09-30. 8-K Item 1.01: the closing draws paid 'the repayment of indebtedness outstanding "
        "under the Prior Credit Agreement'.",
    "Term loans: Second Amended and Restated Credit Agreement":
        "8-K Item 1.01: 'On the Closing Date, DLH received $190 million of funds under the Term Loans'. Matures "
        "2027-12-08; quarterly principal of $3,562,500 from December 2022.",
    "Revolving credit facility: draw at close":
        "8-K Item 1.01: '$25.2 million of funds under the Revolving Credit Facility'; outstanding borrowings were "
        "$215.2 million after the close. The revolver allows up to $70 million.",
    "Deferred revenue": "10-K: nil at 2022-09-30 ($22,273K at 2021-09-30).",
    "Note payable, shareholder":
        "Ex 99.1 Note 9: on 2022-04-15 GRSi redeemed 1,337 shares for $30,246,414 of promissory notes at the prime "
        "rate, maturing at the earlier of 2029-04-15 or a liquidation event. Ex 99.2 Note 10: 'In connection with the "
        "acquisition the notes payable, shareholder for $30,246,414 including interest was paid in full.' Ex 99.3 "
        "carries no GRSi debt.",
    "Treasury stock, at cost":
        "Ex 99.2 equity statement: the 2022 redemption charged $934,381 to paid-in capital and $29,310,696 to "
        "treasury stock. DLH's 10-K: DLH holds repurchased stock as treasury stock at cost but held none at "
        "2022-09-30.",
    "Deferred rent":
        "Ex 99.2 Note 1: straight-line rent expense less payments (ASC 840; GRSi had not adopted ASC 842). Ex 99.3 "
        "shows this balance in DLH's operating lease captions ($356K current, $413K long-term) and notes 4g and 4h "
        "replace it under ASC 842.",
    "Indirect costs":
        "Ex 99.3 note 3b: 'This adjustment conforms GRSi's income statement presentation with that of DLH': "
        "'Reclassify certain infrastructure and operational management costs from G&A to contract costs' $3,070K "
        "and 'Reclassify certain fringe costs from G&A to contract costs' $14,404K (twelve months to 2022-09-30). "
        "Ex 99.2: advertising costs are included in indirect costs.",
    "Other current liabilities": "Ex 99.2 Note 1: contract liabilities included in other current liabilities, $209.",
    "Accounts receivable": "Ex 99.2 Note 3: billed $17,966,645 and unbilled $3,437,916; no allowance.",
    "Other long-term assets": "Ex 99.2 Note 1: includes two equity-method joint ventures, not material.",
    "Interest income": "Ex 99.2: interest income. DLH reports no interest income line; Ex 99.3 nets GRSi's interest "
                       "into 'Interest and other income (expense), net'.",
}

MAPPING = {
    # balance sheet
    "Cash": ("Cash", 0.98, "Same line"),
    "Accounts receivable": ("Accounts receivable", 0.97, "Same line, billed and unbilled; Ex 99.3 adds them"),
    "Other current assets": ("Other current assets", 0.95, "Same line; Ex 99.3 adds them"),
    "Total current assets": ("Total current assets", 1.0, "Same subtotal"),
    "Property and equipment, net": ("Equipment and improvements, net", 0.93,
                                    "Net fixed assets; Ex 99.3 puts GRSi's $549K on this line"),
    "Other long-term assets": ("Other long-term assets", 0.95, "Same line; Ex 99.3 adds them"),
    "Total assets": ("Total assets", 1.0, "Same subtotal"),
    "Accounts payable and accrued expenses": ("Accounts payable and accrued liabilities", 0.95,
                                              "Same line, different wording"),
    "Accrued payroll and related liabilities": ("Accrued payroll", 0.95, "Same line; Ex 99.3 adds them"),
    "Other current liabilities": ("Accounts payable and accrued liabilities", 0.75,
                                  "$209 of contract liabilities; DLH has no other current liabilities line, and Ex 99.3 "
                                  "shows none for GRSi (its GRSi accounts payable and accrued liabilities, $1,991K, "
                                  "is larger than GRSi's own $1,687K, so it appears to hold it)"),
    "Total current liabilities": ("Total current liabilities", 1.0, "Same subtotal"),
    "Deferred rent": ("Operating lease liabilities - long-term", 0.7,
                      "Straight-line rent liability under ASC 840; Ex 99.3 shows it in DLH's operating lease "
                      "captions"),
    "Note payable, shareholder": ("Debt obligations - long-term, net of deferred financing costs", 0.8,
                                  "DLH's only debt line; the note matures in 2029, so it is long-term"),
    "Total liabilities": ("Total liabilities", 1.0, "Same subtotal"),
    "Common stock": ("Common stock", 0.97, "Same line"),
    "Additional paid-in capital": ("Additional paid-in capital", 0.98, "Same line"),
    "Treasury stock, at cost": ("Retained earnings (accumulated deficit)", 0.6,
                                "DLH has no treasury stock line at 2022-09-30; the redemption already used up "
                                "paid-in capital, so the rest sits against retained earnings, and purchase "
                                "accounting eliminates GRSi's equity (Ex 99.3 note 4l)"),
    "Retained earnings": ("Retained earnings (accumulated deficit)", 0.97, "Same line"),
    "Total stockholders' equity": ("Total shareholders' equity", 1.0, "Same subtotal"),
    "Total liabilities and stockholders' equity": ("Total liabilities and shareholders' equity", 1.0,
                                                   "Same subtotal"),
    # income statement
    "Revenue": ("Revenue", 0.98, "Same line"),
    "Direct costs": ("Contract costs", 0.9, "Direct contract costs; Ex 99.3 carries GRSi's direct costs as contract "
                                             "costs"),
    "Indirect costs": ("General and administrative costs", 0.7,
                       "Overhead outside direct contract cost; Ex 99.3's GRSi column carries GRSi's non-direct costs "
                       "as G&A before note 3b"),
    "Total operating costs": ("Total operating costs", 1.0, "Same subtotal"),
    "Income from operations": ("Income from operations", 1.0, "Same subtotal"),
    "Interest income": (None, 0.9,
                        "DLH has no interest income or other income line, and an income line never maps to an "
                        "expense line; left unmapped and reported ($16.6K)"),
    "Interest expense": ("Interest expense", 0.97, "Same line"),
    "Total other income (expense)": (None, 1.0, "subtotal; its parts are mapped"),
    "Net income": ("Net income", 1.0, "Same subtotal"),
    # cash flow
    "Depreciation and amortization": ("Depreciation and amortization", 0.98, "Same cash flow line"),
}

TAGS = {
    # DLH
    "Cash": ("na", "Cash, not a liability"),
    "Accounts receivable": ("na", "Asset"),
    "Other current assets": ("na", "Asset"),
    "Total current assets": ("na", "Subtotal of assets"),
    "Equipment and improvements, net": ("na", "Asset"),
    "Operating lease right-of-use-assets": ("na", "Asset"),
    "Goodwill": ("na", "Asset"),
    "Intangible assets, net": ("na", "Asset"),
    "Other long-term assets": ("na", "Asset"),
    "Total assets": ("na", "Subtotal of assets"),
    "Operating lease liabilities - current": ("na", "Operating lease, not a capitalized lease obligation"),
    "Accrued payroll": ("na", "Accrued expense in the ordinary course"),
    "Deferred revenue": ("na", "Contract liability, not borrowed money"),
    "Accounts payable and accrued liabilities": ("na", "Trade payables and accruals, excluded from Indebtedness"),
    "Total current liabilities": ("na", "Subtotal; its debt parts are tagged on their own lines"),
    "Deferred taxes, net": ("na", "Deferred tax, not borrowed money"),
    "Operating lease liabilities - long-term": ("na", "Operating lease, not a capitalized lease obligation"),
    "Debt obligations - long-term, net of deferred financing costs": (
        "unclear", "Borrowed money at 2022-09-30 ($22,000K principal), but the closing draws repaid the Prior Credit "
                   "Agreement on 2022-12-08 (8-K Item 1.01)"),
    "Term loans: Second Amended and Restated Credit Agreement": ("debt", "Term loans drawn at close, borrowed money"),
    "Revolving credit facility: draw at close": ("debt", "Revolver drawn at close, borrowed money"),
    "Total long-term liabilities": ("na", "Subtotal; its debt parts are tagged on their own lines"),
    "Total liabilities": ("na", "Subtotal; its debt parts are tagged on their own lines"),
    "Common stock": ("na", "Equity"),
    "Additional paid-in capital": ("na", "Equity"),
    "Retained earnings (accumulated deficit)": ("na", "Equity"),
    "Total shareholders' equity": ("na", "Equity subtotal"),
    "Total liabilities and shareholders' equity": ("na", "Balance sheet total"),
    # GRSi
    "Property and equipment, net": ("na", "Asset"),
    "Accounts payable and accrued expenses": ("na", "Trade payables and accruals, excluded from Indebtedness"),
    "Accrued payroll and related liabilities": ("na", "Accrued expense in the ordinary course"),
    "Other current liabilities": ("na", "Contract liabilities, $209 (Ex 99.2)"),
    "Deferred rent": ("na", "Straight-line rent accrual on operating leases, not borrowed money"),
    "Note payable, shareholder": (
        "unclear", "Redemption notes to GRSi shareholders at 2022-09-30, paid in full at the acquisition "
                   "(Ex 99.2 Note 10)"),
    "Treasury stock, at cost": ("na", "Equity"),
    "Retained earnings": ("na", "Equity"),
    "Total stockholders' equity": ("na", "Equity subtotal"),
    "Total liabilities and stockholders' equity": ("na", "Balance sheet total"),
}

COVENANT_FLAG = {
    "lines": ["Debt obligations - long-term, net of deferred financing costs", "Note payable, shareholder"],
    "question": "Two debts on the 2022-09-30 balance sheets were paid off at the 2022-12-08 close: DLH's prior FNB "
                "term loan ($20,416K net) and GRSi's shareholder notes ($30,246K). The $215,200K drawn at close paid "
                "for that. Total Funded Debt is measured 'without duplication'. Do the old debts count on top of the "
                "new borrowings?",
    "options": [
        ("a", "Count both, as the balance sheets show",
         {"Debt obligations - long-term, net of deferred financing costs": "debt",
          "Note payable, shareholder": "debt"}),
        ("b", "Both were repaid at close; only the new borrowings count",
         {"Debt obligations - long-term, net of deferred financing costs": "not_debt",
          "Note payable, shareholder": "not_debt"}),
        ("c", "DLH's loan was refinanced; GRSi's notes still count",
         {"Debt obligations - long-term, net of deferred financing costs": "not_debt",
          "Note payable, shareholder": "debt"}),
    ],
    "default": "b",
    "evidence": [
        ("On the Closing Date, DLH received $190 million of funds under the Term Loans and $25.2 million of funds "
         "under the Revolving Credit Facility to pay the cash purchase price of Grove, certain transaction expenses "
         "and the repayment of indebtedness outstanding under the Prior Credit Agreement.",
         "8-K filed 2022-12-14, Item 1.01"),
        ("In connection with the acquisition the notes payable, shareholder for $30,246,414 including interest was "
         "paid in full.", "8-K/A Ex 99.2, Note 10 Subsequent Events"),
        ("Total Funded Debt shall mean, as of any date of determination, without duplication, the sum of all "
         "Indebtedness representing borrowed money",
         "8-K Ex 10.1, Section 1.1 Certain Definitions"),
    ],
}

MAPPING_FLAGS: dict = {}
