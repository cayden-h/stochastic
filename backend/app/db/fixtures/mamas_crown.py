"""Mama's Creations acquires the Crown I carve-out business from Sysco. Every figure is from a public filing.

Sources (all read on 2026-10-24 from SEC EDGAR):
- EIGHTK: Mama's 8-K filed 2025-09-02 (the acquisition, the A&R Loan Agreement, the $19,000,000 PA Line draw, the private placement):
  https://www.sec.gov/Archives/edgar/data/1520358/000149315225012528/form8-k.htm
- EX101: 8-K Ex 10.1, Amended and Restated Loan and Security Agreement with M&T Bank dated 2025-08-28
  (Section 5.31 Financial Covenants; definitions 1.9, 1.12, 1.32, 1.35; Section 2.4 PA Line; Section 5.19 H Indebtedness):
  https://www.sec.gov/Archives/edgar/data/1520358/000149315225012528/ex10-1.htm
- EIGHTKA: Mama's 8-K/A filed 2025-11-07 (names the exhibits below):
  https://www.sec.gov/Archives/edgar/data/1520358/000149315225021306/form8-ka.htm
- EX992: 8-K/A Ex 99.2, Crown I Carve Out Business audited statements as of and for the year ended 2025-06-28 (USD thousands):
  https://www.sec.gov/Archives/edgar/data/1520358/000149315225021306/ex99-2.htm
- EX993: 8-K/A Ex 99.3, unaudited pro forma condensed combined information (price, financing, and the Crown 1 balance sheet column):
  https://www.sec.gov/Archives/edgar/data/1520358/000149315225021306/ex99-3.htm
- TENK: Mama's 10-K for the year ended 2025-01-31 (statement of operations, cash flows, director settlement note):
  https://www.sec.gov/Archives/edgar/data/1520358/000162828025017063/mmmb-20250131.htm
- TENQ: Mama's 10-Q for the quarter ended 2025-07-31 (condensed consolidated balance sheet, debt and lease notes):
  https://www.sec.gov/Archives/edgar/data/1520358/000152035825000004/mama-20250731.htm
Figures marked inferred are our estimates and must be said out loud.
"""
from __future__ import annotations

from app.core.models import Adjustment, Brief, Financing

DEAL_ID = "d_mama_crown"
NAME = "Mama's Creations, Inc. acquires the Crown I Carve Out Business (Crown I Enterprises, Inc., a Sysco subsidiary)"
PLATFORM = "Mama's Creations"
TARGET = "Crown I"
NOTE = ("Mama's Creations bought substantially all assets of Sysco's Crown I Enterprises on 2025-09-02 for $17.5 million in cash, "
        "funded by a $19.0 million draw on its M&T Bank PA Line, under an M&T covenant of Total Funded Debt to EBITDA "
        "not greater than 3.75 to 1.00.")
SOURCES = {
    "8-K": "https://www.sec.gov/Archives/edgar/data/1520358/000149315225012528/form8-k.htm",
    "8-K Ex 10.1": "https://www.sec.gov/Archives/edgar/data/1520358/000149315225012528/ex10-1.htm",
    "8-K/A": "https://www.sec.gov/Archives/edgar/data/1520358/000149315225021306/form8-ka.htm",
    "8-K/A Ex 99.2": "https://www.sec.gov/Archives/edgar/data/1520358/000149315225021306/ex99-2.htm",
    "8-K/A Ex 99.3": "https://www.sec.gov/Archives/edgar/data/1520358/000149315225021306/ex99-3.htm",
    "10-K FY2025": "https://www.sec.gov/Archives/edgar/data/1520358/000162828025017063/mmmb-20250131.htm",
    "10-Q 2025-07-31": "https://www.sec.gov/Archives/edgar/data/1520358/000152035825000004/mama-20250731.htm",
}

EIGHTK = "8-K filed 2025-09-02, Item 1.01 Credit Facility"
EX101 = "8-K Ex 10.1, M&T Bank Amended and Restated Loan and Security Agreement dated 2025-08-28"
TENQ = "10-Q for the quarter ended 2025-07-31, condensed consolidated balance sheet"
TENK_IS = "10-K for the year ended 2025-01-31, consolidated statement of operations"
TENK_CF = "10-K for the year ended 2025-01-31, consolidated statement of cash flows"
TENK = "10-K for the year ended 2025-01-31"
EX992_BS = "8-K/A Ex 99.2, Crown I Carve Out Business audited balance sheet as of 2025-06-28"
EX992_IS = "8-K/A Ex 99.2, Crown I Carve Out Business audited statement of operations, year ended 2025-06-28"
EX992_CF = "8-K/A Ex 99.2, Crown I Carve Out Business audited statement of cash flows, year ended 2025-06-28"
EX993 = "8-K/A Ex 99.3, unaudited pro forma condensed combined balance sheet as of 2025-07-31"

BRIEF = Brief(
    lender="M&T Bank",
    agreement_ref=EX101,
    limit=3.75,
    limit_section="Section 5.31 B",
    limit_wording="Borrower shall not permit the ratio of its Total Funded Debt to EBITDA to be greater than 3.75 to 1.00 "
                  "measured quarterly on a rolling four quarter basis as of each quarter end.",
    debt_term="Total Funded Debt",
    debt_definition="Section 1.35: \"all borrowed money as reflected in the most recent financial statements.\" "
                    "That takes in the M&T term loan and PA Line and the related-party promissory notes. "
                    "The agreement does not say whether finance lease obligations are borrowed money (the covenant question).",
    debt_excludes=[
        "Operating lease liabilities: lease obligations, not borrowed money (the agreement treats operating lease payments as a "
        "fixed charge in Section 1.17, not as debt).",
        "Trade payables and accrued expenses: Section 5.19 H(iii) separates ordinary-course current liabilities from "
        "liabilities incurred through the borrowing of money.",
    ],
    ebitda_definition="Section 1.12: earnings from continuing operations, including interest income and excluding non-cash "
                      "compensation items, before income taxes, plus interest expense, depreciation and amortization, non-cash "
                      "charges (including stock compensation expense), and one-time charges related to the refinance or to "
                      "Project Jubilee or any other Permitted Acquisition not to exceed $1,500,000 in each case for the period, "
                      "calculated on a pro forma basis to reflect any Permitted Acquisition as if it had occurred on the first "
                      "day of the four-quarter period. The pro forma rule is why Crown I's earnings are added in.",
    ebitda_addbacks=[
        Adjustment(name="Interest income (the definition keeps it in EBITDA)", amount=218.0,
                   source_ref=f"{TENK_IS}: Interest income 218; {EX101} Section 1.12 \"including interest income\"",
                   note="Section 1.12 builds EBITDA from earnings including interest income. The base EBITDA formula subtracts "
                        "interest income, so this add-back puts Mama's $218K back. Crown I has no interest income. "
                        "Remove this add-back if the ebitda tool stops subtracting interest income for this agreement."),
        Adjustment(name="Stock-based compensation", amount=1099.0,
                   source_ref=f"{TENK_CF}: Stock-based compensation 1,099; add-back named in {EX101} Section 1.12",
                   note="Section 1.12 adds back non-cash charges including stock compensation expense. Mama's fiscal 2025 "
                        "figure. Crown I's statements show none."),
        Adjustment(name="Amortization of debt discount", amount=16.0,
                   source_ref=f"{TENK_IS}: Amortization of debt discount 16; {EX101} Section 1.12 (amortization, non-cash charges)",
                   note="A non-cash charge on its own line below operating income, outside the Interest expense line the base "
                        "formula uses."),
        Adjustment(name="Non-cash portion of the director settlement", amount=450.0,
                   source_ref=f"{TENK}, Note on the 2024-05-15 Settlement Agreement with Directors and the supplemental "
                              f"non-cash disclosure 'Issuance of stock for director settlement $450'; {EX101} Section 1.12",
                   note="The 10-K records a one-time charge of about $900K in SG&A: about $113K cash per director (four "
                        "directors) plus shares valued at $450K. We add back only the $450K paid in shares as a non-cash "
                        "charge. The cash part is a one-time expense the bank may allow at its discretion, so it is not added. "
                        "Reading the share part as a Section 1.12 non-cash charge is our reading.", inferred=True),
        Adjustment(name="Permitted Acquisition and refinance charges (capped)", amount=0.0, cap=1500.0,
                   source_ref=f"{EX101} Section 1.12; {EX993} Note 2 BB (estimated transaction costs $1,244K)",
                   note="The historical years used here end before the deal, so they hold no Crown I deal costs; 0 is applied. "
                        "The pro forma books estimated transaction costs of $1,244K as if incurred on 2024-02-01, which "
                        "the historical statements do not contain. Cap is $1,500K.", inferred=True),
    ],
    ebitda_deductions=[],
    closing_financing=[
        Financing(name="M&T PA Line draw (non-revolving acquisition line)", amount=19000.0, kind="senior_secured",
                  source_ref=f"{EIGHTK}: initial draw on the PA Line on 2025-08-28 of $19,000,000 to finance the Acquisition; "
                             f"{EX101} Section 2.4"),
    ],
    test_period_note="Mama's figures are its fiscal year ended 2025-01-31 (income statement, 10-K) and its balance sheet at "
                     "2025-07-31 (10-Q). Crown I's are its audited fiscal year and balance sheet at 2025-06-28 (Ex 99.2). "
                     "The combined income statement adds the two filed years; the agreement tests the rolling four quarters "
                     "to each quarter end (first test 2025-07-31; the first test after the close is 2025-10-31), with Crown I "
                     "included pro forma from the first day of the period. There are no step-downs: 3.75x applies at every test. "
                     "The closing line is the $19,000,000 PA Line draw made on 2025-08-28 for the 2025-09-02 close. The "
                     "$20.0 million private placement closed on 2025-09-03, after the close, and about $16.9 million of it "
                     "repaid term loan and PA Line amounts (Ex 99.3 Note 2 D); that paydown is not in these figures. "
                     "The existing term loan is shown at its 2025-07-31 carrying value ($1,987K); the 8-K gives $1,873,276 of "
                     "principal at 2025-08-28. Section 5.31 C, Senior Funded Debt (indebtedness owing to the Bank) to EBITDA "
                     "not greater than 2.75 to 1.00, is a second covenant the schema cannot hold: on these figures its debt is "
                     "the term loan plus the PA Line draw, $20,987K, or 1.72x. Section 5.31 A, fixed charge coverage of at "
                     "least 1.25 to 1.00, is also not modeled. The pro forma also reverses $1,777K of Crown I intercompany "
                     "sales to Sysco ($771K of gross profit) for calendar 2024 (Ex 99.3 Note 2 AA); the fiscal year used here "
                     "is a different period and its share is not disclosed, so no deduction is made.",
)

# Blocks of lines: (section, period, unit, source_ref, rows); rows are (line name as filed, amount, is_total).
_MAMAS_BS_CURRENT = [
    ("Cash and cash equivalents", 9384, False),
    ("Accounts receivable, net", 6740, False),
    ("Inventories, net", 6433, False),
    ("Prepaid expenses and other current assets", 881, False),
    ("Total Current Assets", 23438, True),
    ("Property, plant, and equipment, net", 9377, False),
    ("Intangible assets, net", 2685, False),
    ("Goodwill", 8633, False),
    ("Operating lease right of use assets, net", 6492, False),
    ("Deferred tax asset", 516, False),
    ("Deposits", 95, False),
    ("Total Assets", 51236, True),
    ("Accounts payable and accrued expenses", 11128, False),
    ("Term loan, net of unamortized debt discount", 1536, False),
    ("Operating lease liabilities", 1113, False),
    ("Finance leases payable", 309, False),
    ("Promissory notes - related parties", 750, False),
    ("Total Current Liabilities", 14836, True),
    ("Term loan - net of current", 451, False),
]
# The closing financing: the PA Line draw that paid for the deal (8-K). Placed next to the term loan lines.
_MAMAS_CLOSE = [
    ("Term loan - M&T PA Line draw", 19000, False),
]
_MAMAS_BS_REST = [
    ("Operating lease liabilities - net of current", 5321, False),
    ("Finance leases payable - net of current", 1041, False),
    ("Total long-term liabilities", 6813, True),
    ("Total Liabilities", 21649, True),
    ("Series A Preferred stock", 0, False),
    ("Series B Preferred stock", 0, False),
    ("Preferred stock", 0, False),
    ("Common stock", 0, False),
    ("Additional paid-in capital", 27059, False),
    ("Retained earnings", 2678, False),
    ("Less: Treasury stock, 230,000 shares at cost", -150, False),
    ("Total Stockholders' Equity", 29587, True),
    ("Total Liabilities and Stockholders' Equity", 51236, True),
]
_MAMAS_IS = [
    ("Net sales", 123328, False),
    ("Costs of sales", 92795, False),
    ("Gross profit", 30533, True),
    ("Research and development", 455, False),
    ("Selling, general and administrative", 25201, False),
    ("Total operating expenses", 25656, True),
    ("Income from operations", 4877, True),
    ("Interest expense", 477, False),
    ("Interest income", 218, False),
    ("Amortization of debt discount", 16, False),
    ("Other income", 104, False),
    ("Total other expenses", 171, True),
    ("Income before income tax provision and income from equity method investment", 4706, True),
    ("Income from equity method investment", 0, False),
    ("Income tax provision", 995, False),
    ("Net income", 3711, True),
    ("Less: series B preferred dividends", 0, False),
    ("Net income available to common stockholders", 3711, True),
]
_MAMAS_CF = [
    ("Depreciation and amortization", 3135, False),
]

PLATFORM_BLOCKS = [
    ("balance_sheet", "2025-07-31", "USD thousands", TENQ, _MAMAS_BS_CURRENT),
    ("balance_sheet", "2025-09-02 (closing)", "USD thousands", f"{EIGHTK}: $19,000,000 initial PA Line draw on 2025-08-28",
     _MAMAS_CLOSE),
    ("balance_sheet", "2025-07-31", "USD thousands", TENQ, _MAMAS_BS_REST),
    ("income_statement", "FY ended 2025-01-31", "USD thousands", TENK_IS, _MAMAS_IS),
    ("cash_flow", "FY ended 2025-01-31", "USD thousands",
     f"{TENK_CF}: Depreciation 1,592 plus Amortization of intangibles 1,543", _MAMAS_CF),
]

_CROWN_BS = [
    ("Accounts receivable, net", 3307, False),
    ("Due from parent", 544, False),
    ("Inventories, net", 1635, False),
    ("Prepaid expenses and other current assets", 44, False),
    ("Total Current Assets", 5530, True),
    ("Property, plant, and equipment, net", 10153, False),
    ("Operating lease right of use assets, net", 6598, False),
    ("Deferred tax asset", 384, False),
    ("Security deposits", 6, False),
    ("Total Assets", 22671, True),
    ("Accounts payable and accrued expenses", 3542, False),
    ("Operating leases liabilities", 267, False),
    ("Finance leases payable", 11, False),
    ("Total Current Liabilities", 3820, True),
    ("Operating leases liability - net of current", 6427, False),
    ("Finance leases payable - net of current", 2, False),
    ("Total Long-Term Liabilities", 6429, True),
    ("Total Liabilities", 10249, True),
    ("Parent's net investment", 12422, False),
    ("Total liabilities and equity", 22671, True),
]
_CROWN_IS = [
    ("Net sales", 56779, False),
    ("Costs of sales", 51883, False),  # inferred: filed as 51,833, which does not tie (see LINE_NOTES)
    ("Gross profit", 4896, True),
    ("Selling, general and administrative", 4377, False),
    ("Total operating expenses", 4377, True),
    ("Income from operations", 519, True),
    ("Interest expense", 1, False),
    ("Other income", 65, False),
    ("Total other expenses", -64, True),
    ("Income before income tax provision", 583, True),
    ("Income tax provision", 159, False),
    ("Net income", 424, True),
]
_CROWN_CF = [
    ("Depreciation", 1706, False),
]

TARGET_BLOCKS = [
    ("balance_sheet", "2025-06-28", "USD thousands",
     f"{EX992_BS}; Total Liabilities from the Crown 1 column of {EX993}", _CROWN_BS),
    ("income_statement", "FY ended 2025-06-28", "USD thousands",
     f"{EX992_IS}; Costs of sales inferred as Net sales less Gross profit", _CROWN_IS),
    ("cash_flow", "FY ended 2025-06-28", "USD thousands", EX992_CF, _CROWN_CF),
]

LINE_NOTES = {
    "Term loan, net of unamortized debt discount": "10-Q: the M&T T&L Note ($7.5M in 2021, matures 2027-01-17), balance about $2.0M "
        "and unamortized discount $16K at 2025-07-31. Filed caption: 'Term loan, net of unamortized debt discount of $16 and $22, "
        "respectively'. Restated as the Term Loan Facility in the A&R Loan Agreement (principal $1,873,276 at 2025-08-28).",
    "Term loan - net of current": "10-Q: the non-current part of the M&T T&L Note. Owed to M&T, so it is Senior Funded Debt too.",
    "Term loan - M&T PA Line draw": "8-K: initial draw on the $20,000,000 non-revolving PA Line on 2025-08-28 of $19,000,000 to "
        "finance the Acquisition and related expenses. Ex 10.1 Section 2.4: PA Line advances convert to a five-year term loan "
        "within 60 days. Part of it was repaid from the private placement on or after 2025-09-03, after the close.",
    "Promissory notes - related parties": "10-Q: a $3M promissory note to the sellers of T&L Creative Salads (including Anthony "
        "Morello, Jr., President of Creative Salads and Olive Branch), 3.5% interest, $750K annual principal; $750K outstanding "
        "at 2025-07-31. Ex 10.1 Section 5.19 H(ix) permits these notes as indebtedness, due 2025-12-29. The agreement does not "
        "subordinate them. They are borrowed money, so Total Funded Debt; they are not owed to M&T, so not Senior Funded Debt.",
    "Finance leases payable": "Mama's (10-Q): finance leases relating primarily to machinery and equipment, weighted average "
        "rate 7.95%. Crown I (Ex 99.2 Note 7): $13K total finance lease liabilities; Ex 99.3 Note 2 F says Crown I's leases were "
        "not assumed in the asset purchase.",
    "Finance leases payable - net of current": "Mama's (10-Q): finance leases relating primarily to machinery and equipment. "
        "Crown I (Ex 99.2 Note 7): $2K non-current; not assumed in the asset purchase (Ex 99.3 Note 2 F).",
    "Due from parent": "Ex 99.2: a receivable from Sysco Holdings, LLC, the carve-out's parent; the cash flow statement shows "
        "Due to/from parent of $(2,374)K. Ex 99.3 Note 2 F eliminates it as not assumed in the transaction.",
    "Parent's net investment": "Ex 99.2 Note 2: the Parent's contribution to and distribution from the Business and the "
        "allocation of shared costs; $11,998K at 2024-06-30 plus net income $424K. Ex 99.3 eliminates it in purchase accounting.",
    "Total Liabilities": "Crown I: Ex 99.2 prints Total Liabilities as 10,429, but its parts add to 10,249 (3,820 + 6,429), "
        "10,249 plus Parent's net investment 12,422 equals Total Assets 22,671, and the Crown 1 column of Ex 99.3 prints 10,249. "
        "We load 10,249; the 10,429 in Ex 99.2 is a transposition in the filing.",
    "Costs of sales": "Crown I: Ex 99.2 prints Costs of sales as 51,833, but Net sales 56,779 (also in its revenue note: gross "
        "sales 56,884 less 105) less Gross profit 4,896 is 51,883, and Gross profit 4,896 carries through Income from operations "
        "519 to Net income 424 and the net investment roll-forward. We load 51,883, inferred; the filed 51,833 looks like a "
        "typo. Mama's Costs of sales (92,795) is as filed.",
    "Total liabilities and equity": "Crown I: filed as 'Total Liabilities and Parent's Net Investment', renamed so the tie-out "
        "finds the side total.",
    "Total other expenses": "Crown I files 64 with no parentheses: net other income (Other income 65 less Interest expense 1). "
        "Stored as -64 because expenses are positive. Mama's 171 is a net expense, filed as (171).",
    "Operating leases liabilities": "Ex 99.2 Note 7: current operating lease liabilities, $6,694K total with the non-current "
        "part; not assumed in the asset purchase (Ex 99.3 Note 2 F).",
    "Depreciation and amortization": "Mama's 10-K cash flow statement shows Depreciation 1,592 and Amortization of intangibles "
        "1,543 on two lines; this line is their sum, 3,135.",
}

# The scripted Mapper's reference answer: every target line name -> (platform line name or None, confidence, reason).
MAPPING = {
    # balance sheet
    "Accounts receivable, net": ("Accounts receivable, net", 0.98, "Same caption."),
    "Due from parent": ("Prepaid expenses and other current assets", 0.45,
                        "A receivable from Sysco, the seller; Mama's has no related-party receivable line."),
    "Inventories, net": ("Inventories, net", 0.98, "Same caption."),
    "Prepaid expenses and other current assets": ("Prepaid expenses and other current assets", 0.98, "Same caption."),
    "Total Current Assets": ("Total Current Assets", 0.98, "Same subtotal."),
    "Property, plant, and equipment, net": ("Property, plant, and equipment, net", 0.98, "Same caption."),
    "Operating lease right of use assets, net": ("Operating lease right of use assets, net", 0.98, "Same caption."),
    "Deferred tax asset": ("Deferred tax asset", 0.97, "Same caption."),
    "Security deposits": ("Deposits", 0.9, "Mama's 'Deposits' holds its security deposits (10-K cash flow: Security deposits)."),
    "Total Assets": ("Total Assets", 0.99, "Same side total."),
    "Accounts payable and accrued expenses": ("Accounts payable and accrued expenses", 0.98, "Same caption."),
    "Operating leases liabilities": ("Operating lease liabilities", 0.95, "Current operating lease liabilities, same meaning."),
    "Finance leases payable": ("Finance leases payable", 0.97, "Same caption."),
    "Total Current Liabilities": ("Total Current Liabilities", 0.98, "Same subtotal."),
    "Operating leases liability - net of current": ("Operating lease liabilities - net of current", 0.95,
                                                    "Non-current operating lease liabilities, same meaning."),
    "Finance leases payable - net of current": ("Finance leases payable - net of current", 0.97, "Same caption."),
    "Total Long-Term Liabilities": ("Total long-term liabilities", 0.97, "Same subtotal."),
    "Total Liabilities": ("Total Liabilities", 0.98, "Same subtotal."),
    "Parent's net investment": ("Additional paid-in capital", 0.4,
                                "Carve-out equity: Sysco's contributions and the business's earnings in one figure; Mama's has "
                                "no such line."),
    "Total liabilities and equity": ("Total Liabilities and Stockholders' Equity", 0.95, "Same side total."),
    # income statement
    "Net sales": ("Net sales", 0.99, "Same caption."),
    "Costs of sales": ("Costs of sales", 0.99, "Same caption."),
    "Gross profit": ("Gross profit", 0.99, "Same subtotal."),
    "Selling, general and administrative": ("Selling, general and administrative", 0.98, "Same caption."),
    "Total operating expenses": ("Total operating expenses", 0.98, "Same subtotal."),
    "Income from operations": ("Income from operations", 0.98, "Same subtotal."),
    "Interest expense": ("Interest expense", 0.98, "Same caption."),
    "Other income": ("Other income", 0.95, "Same caption."),
    "Total other expenses": ("Total other expenses", 0.9, "Same subtotal; Crown I's is net other income, stored negative."),
    "Income before income tax provision": ("Income before income tax provision and income from equity method investment", 0.9,
                                           "Pre-tax income; Crown I has no equity method investment."),
    "Income tax provision": ("Income tax provision", 0.98, "Same caption."),
    "Net income": ("Net income", 0.99, "Same caption."),
    # cash flow
    "Depreciation": ("Depreciation and amortization", 0.9, "Crown I's only D&A line; it shows no amortization."),
}

# Covenant tags for balance sheet lines of both companies, by line name.
TAGS = {
    "Cash and cash equivalents": ("na", "Cash. Section 1.35 has no cash netting."),
    "Accounts receivable, net": ("na", "An asset."),
    "Due from parent": ("na", "An asset: a receivable from Sysco."),
    "Inventories, net": ("na", "An asset."),
    "Prepaid expenses and other current assets": ("na", "An asset."),
    "Total Current Assets": ("na", "A subtotal of assets."),
    "Property, plant, and equipment, net": ("na", "An asset."),
    "Intangible assets, net": ("na", "An asset."),
    "Goodwill": ("na", "An asset."),
    "Operating lease right of use assets, net": ("na", "An asset."),
    "Deferred tax asset": ("na", "An asset."),
    "Deposits": ("na", "An asset."),
    "Security deposits": ("na", "An asset."),
    "Total Assets": ("na", "A side total."),
    "Accounts payable and accrued expenses": ("na", "Trade payables and accruals, not borrowed money (Section 5.19 H(iii))."),
    "Term loan, net of unamortized debt discount": ("debt", "M&T term loan: borrowed money (Section 1.35), owed to the Bank."),
    "Term loan - net of current": ("debt", "M&T term loan: borrowed money (Section 1.35), owed to the Bank."),
    "Term loan - M&T PA Line draw": ("debt", "The $19,000,000 PA Line advance that paid for the deal: borrowed money owed to the Bank."),
    "Promissory notes - related parties": ("debt", "Interest-bearing notes to the T&L sellers: borrowed money under Section 1.35. "
                                                   "Not owed to M&T, so outside Senior Funded Debt only."),
    "Operating lease liabilities": ("na", "Operating lease obligations; Section 1.17 treats operating lease payments as fixed charges, not debt."),
    "Operating lease liabilities - net of current": ("na", "Operating lease obligations, not borrowed money."),
    "Operating leases liabilities": ("na", "Operating lease obligations, not borrowed money; not assumed (Ex 99.3 Note 2 F)."),
    "Operating leases liability - net of current": ("na", "Operating lease obligations, not borrowed money; not assumed (Ex 99.3 Note 2 F)."),
    "Finance leases payable": ("unclear", "Section 1.35 counts 'all borrowed money' and does not name finance leases."),
    "Finance leases payable - net of current": ("unclear", "Section 1.35 counts 'all borrowed money' and does not name finance leases."),
    "Total Current Liabilities": ("na", "A subtotal; its debt parts are tagged on their own lines."),
    "Total long-term liabilities": ("na", "A subtotal; its debt parts are tagged on their own lines."),
    "Total Long-Term Liabilities": ("na", "A subtotal; its parts are tagged on their own lines."),
    "Total Liabilities": ("na", "A subtotal; its debt parts are tagged on their own lines."),
    "Series A Preferred stock": ("na", "Equity, none outstanding."),
    "Series B Preferred stock": ("na", "Equity, none outstanding."),
    "Preferred stock": ("na", "Equity, none outstanding."),
    "Common stock": ("na", "Equity."),
    "Additional paid-in capital": ("na", "Equity."),
    "Retained earnings": ("na", "Equity."),
    "Less: Treasury stock, 230,000 shares at cost": ("na", "Equity."),
    "Total Stockholders' Equity": ("na", "Equity subtotal."),
    "Parent's net investment": ("na", "Carve-out equity: Sysco's net investment, not borrowed money."),
    "Total Liabilities and Stockholders' Equity": ("na", "A side total."),
    "Total liabilities and equity": ("na", "A side total."),
}

COVENANT_FLAG = {
    "lines": ["Finance leases payable", "Finance leases payable - net of current"],
    "question": "Do finance lease obligations count as Total Funded Debt? Section 1.35 defines it as \"all borrowed money as "
                "reflected in the most recent financial statements\" and does not mention leases. On the books: Mama's "
                "Finance leases payable $309K and Finance leases payable - net of current $1,041K ($1,350K, machinery and "
                "equipment), and Crown I $11K and $2K ($13K, not assumed in the asset purchase). Together $1,363K.",
    "options": [
        ("a", "Finance leases count as borrowed money (equipment financing)",
         {"Finance leases payable": "debt", "Finance leases payable - net of current": "debt"}),
        ("b", "Finance leases are not borrowed money, so only loans and notes count",
         {"Finance leases payable": "not_debt", "Finance leases payable - net of current": "not_debt"}),
    ],
    "default": "a",
    "evidence": [
        ("“TOTAL FUNDED DEBT” means , at any time, all borrowed money as reflected in the most recent financial statements.",
         "8-K Ex 10.1, Section 1.35"),
        ("indebtedness incurred to finance the acquisition, construction, repair, replacement or improvement of any fixed or "
         "capital assets, including equipment (whether or not constituting purchase money financing), including finance lease "
         "obligations", "8-K Ex 10.1, Section 5.19 H(viii)"),
        ("the scheduled principal loan or capital lease payments paid or required to be paid during the applicable period",
         "8-K Ex 10.1, Section 1.9 (Current Maturity of Long-Term Debt)"),
        ("We also have finance leases relating primarily to machinery and equipment.",
         "10-Q for the quarter ended 2025-07-31, Leases note"),
        ("Reflects the elimination of asset and liabilities not assumed in the transaction, including receivables, certain "
         "payables, deposits and operating and financing leases.", "8-K/A Ex 99.3, Note 2 F"),
    ],
}

MAPPING_FLAGS = {
    "Due from parent": {
        "question": "Crown I's 'Due from parent' ($544K) is a receivable from Sysco Holdings, LLC, the seller. Mama's has no "
                    "related-party receivable line. It is not a trade receivable, and the pro forma eliminates it as not "
                    "assumed (Ex 99.3 Note 2 F). Where does it go in the combined book?",
        "options": [
            ("a", "Prepaid expenses and other current assets (a non-trade current receivable)",
             "Prepaid expenses and other current assets"),
            ("b", "Accounts receivable, net (treat it like a customer balance)", "Accounts receivable, net"),
        ],
        "default": "a",
    },
    "Parent's net investment": {
        "question": "Crown I's 'Parent's net investment' ($12,422K) is carve-out equity: Sysco's contributions and "
                    "distributions plus the business's earnings, in one figure ($11,998K at 2024-06-30 plus net income $424K). "
                    "Mama's equity splits paid-in capital from retained earnings. Which line takes it?",
        "options": [
            ("a", "Additional paid-in capital (the parent's contributed capital)", "Additional paid-in capital"),
            ("b", "Retained earnings (the business's accumulated earnings)", "Retained earnings"),
        ],
        "default": "a",
    },
}
