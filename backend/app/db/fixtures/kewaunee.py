"""The demo deal: Kewaunee Scientific buys Nu Aire. Every figure is from a public filing.

Sources (all read on 2026-10-24 from SEC EDGAR, links in docs/research/real-deal-candidates.md):
- 10-Q: Kewaunee balance sheet at 2024-10-31 and the sale-leaseback note.
- 10-K FY2024: Kewaunee depreciation ($3,125K) and the Statesville rent obligation ($1,970K next year).
- 8-K/A Ex 99.1: Nu Aire audited statements for the year ended 2024-09-30 (whole dollars).
- 8-K/A Ex 99.2: Kewaunee FY2024 income statement (Kewaunee historical column) and Note 4(h), the closing financing.
- 8-K Ex 10.1: the PNC Loan Agreement, Section 4.8(a) and the definitions.
Owner of the data: Eric (data/, scripts/, evals/). Cayden loaded this first copy so the pipeline could run.
Figures marked inferred=True are our estimates and must be said out loud.
"""
from __future__ import annotations

from pathlib import Path

from app.core.models import CONTROLLER, Adjustment, Brief, Deal, Financing, SourceLine
from app.db.memory import MemoryStore
from app.gateway.gateway import Gateway

DEAL_ID = "d_kequ_nuaire"
NOTE = ("The live demo deal: closed 2024-11-01 for $55M, funded by a PNC term loan and revolver and 8% seller notes; "
        "PNC's Senior Funded Bank Debt to EBITDA must stay below 2.50x.")
PLATFORM = "Kewaunee"
TARGET = "Nu Aire"

TENQ = "10-Q for the quarter ended 2024-10-31, condensed consolidated balance sheet"
TENK = "10-K FY2024 (year ended 2024-04-30)"
EX991 = "8-K/A Ex 99.1, Nu Aire audited statements, year ended 2024-09-30"
EX992_IS = "8-K/A Ex 99.2, pro forma statement of operations, Kewaunee historical column, year ended 2024-04-30"
EX992_FIN = "8-K/A Ex 99.2 Note 4(h), closing financing"
EX101 = "8-K Ex 10.1, PNC Loan Agreement dated 2024-11-01"

BRIEF = Brief(
    lender="PNC Bank, National Association",
    agreement_ref=EX101,
    limit=2.50,
    limit_section="Section 4.8(a)",
    limit_wording="ratio of Senior Funded Bank Debt to EBITDA of less than 2.50 to 1.00",
    debt_term="Senior Funded Bank Debt",
    debt_definition="Secured borrowed money, including finance leases and letters of credit.",
    debt_excludes=[
        "Subordinated Debt, which includes the 8% seller notes",
        "Capitalized lease obligations relating to the real property at 2700 West Front Street (the Statesville sale-leaseback)",
    ],
    ebitda_definition="Net income plus interest, taxes, depreciation, and amortization, plus the add-backs below, "
                      "less cash rent on the Statesville property.",
    ebitda_addbacks=[
        Adjustment(name="Noncash pension termination expense", amount=4019.0,
                   source_ref=f"{TENK}, MD&A: one-time pension termination expense $4,019K; add-back named in {EX101}",
                   note="The income statement line is Pension expense 4,177. The agreement adds back only the termination expense, "
                        "which the 10-K puts at $4,019K; the other $158K is ordinary pension expense. Decided 2026-10-24."),
        Adjustment(name="Stock-based compensation", amount=1018.0,
                   source_ref=f"{TENK}, stock plan note: stock-based compensation expense $1,018K; add-back named in {EX101}",
                   note="The agreement adds back any stock-based compensation. Kewaunee's fiscal 2024 figure, the same period as its "
                        "other inputs. Nu Aire's statements show none. Decided 2026-10-24."),
        Adjustment(name="Transaction costs (capped)", amount=0.0, cap=4000.0, source_ref=EX101,
                   note="Not quantified separately in the filings read, so 0 is applied. Cap is $4,000K.", inferred=True),
        Adjustment(name="Integration costs (capped)", amount=0.0, cap=1000.0, source_ref=EX101,
                   note="Not quantified in the filings read, so 0 is applied. Cap is $1,000K.", inferred=True),
    ],
    ebitda_deductions=[
        Adjustment(name="Cash rent on the Statesville property", amount=1970.0, source_ref=f"{TENK}, contractual obligations: Sale-Leaseback Financing Transaction, due within one year $1,970K",
                   note="The agreement subtracts cash rent. The 10-K gives the next-year obligation, which we use for the year. Initial basic rent is about $158K per month per the 10-Q.", inferred=True),
    ],
    closing_financing=[
        Financing(name="PNC Term Loan", amount=15000.0, kind="senior_secured", source_ref=EX992_FIN),
        Financing(name="PNC Revolving Credit Facility draw", amount=5563.0, kind="senior_secured", source_ref=EX992_FIN),
        Financing(name="8% subordinated Seller Notes", amount=22540.0, kind="subordinated", source_ref=f"{EX992_FIN} ($22,540K in the table; $23,000K in the narrative)"),
    ],
    test_period_note="Kewaunee's fiscal year ends April 30 and Nu Aire's ends September 30. The combined income "
                     "statement adds the two filed years. It is not the filed pro forma and does not match it to the dollar.",
)

# (line, section, amount, is_total) in USD thousands unless stated
KEWAUNEE_BS = [
    ("Cash and cash equivalents", 25963, False), ("Restricted cash", 3701, False),
    ("Receivables, less allowance", 41885, False), ("Inventories", 18659, False),
    ("Prepaid expenses and other current assets", 6228, False), ("Total Current Assets", 96436, True),
    ("Property, plant and equipment, at cost", 65098, False), ("Accumulated depreciation", -48108, False),
    ("Net Property, Plant and Equipment", 16990, True), ("Right of use assets", 6941, False),
    ("Deferred income taxes", 8305, False), ("Other assets", 5806, False), ("Total Assets", 134478, True),
    ("Short-term borrowings", 805, False), ("Current portion of financing liability", 750, False),
    ("Current portion of financing lease liabilities", 109, False),
    ("Current portion of operating lease liabilities", 2112, False), ("Accounts payable", 21458, False),
    ("Employee compensation and amounts withheld", 3708, False), ("Deferred revenue", 6239, False),
    ("Other accrued expenses", 1290, False), ("Total Current Liabilities", 36471, True),
    ("Long-term portion of financing liability", 27032, False),
    ("Long-term portion of financing lease liabilities", 156, False),
    ("Long-term portion of operating lease liabilities", 5035, False),
    ("Accrued pension and deferred compensation costs", 3625, False), ("Deferred income taxes (liability)", 1042, False),
    ("Other non-current liabilities", 460, False), ("Total Liabilities", 73821, True),
    ("Common stock", 7353, False), ("Additional paid-in-capital", 4885, False), ("Retained earnings", 52715, False),
    ("Accumulated other comprehensive loss", -3574, False), ("Common stock in treasury, at cost", -2051, False),
    ("Non-controlling interest", 1329, False), ("Total Stockholders' Equity", 60657, True),
    ("Total Liabilities and Stockholders' Equity", 134478, True),
]
# The closing financing, which the pro forma adds to the financing liability line (Ex 99.2 Note 4(h)).
KEWAUNEE_CLOSE = [
    ("Financing liability: PNC Revolving Credit Facility", 5563),
    ("Financing liability: PNC Term Loan", 15000),
    ("Financing liability: 8% Seller Notes (subordinated)", 22540),
]
KEWAUNEE_IS = [
    ("Net sales", 203755, False), ("Cost of products sold", 151704, False), ("Gross profit", 52051, True),
    ("Operating expenses", 33770, False), ("Operating profit", 18281, True), ("Pension expense", 4177, False),
    ("Other income, net", 814, False), ("Interest expense", 1799, False),
    ("Profit before income taxes", 13119, True), ("Income tax (benefit) expense", -5938, False),
    ("Net earnings", 19057, True), ("Net earnings attributable to the non-controlling interest", 304, False),
    ("Net earnings attributable to Kewaunee Scientific Corporation", 18753, True),
]
KEWAUNEE_CF = [("Depreciation", 3125, False)]

# Nu Aire, whole dollars, year ended / as of 2024-09-30 (Ex 99.1)
NUAIRE_BS = [
    ("Cash and Cash Equivalents", 13455974, False), ("Certificates of Deposit", 991082, False),
    ("Accounts Receivable, Net", 10560193, False), ("Inventories, Net", 12559018, False),
    ("Prepaid Expenses", 817527, False), ("Income Taxes Receivable", 154818, False),
    ("Total Current Assets", 38538612, True),
    ("Leasehold Improvements", 709565, False), ("Machinery and Equipment", 13375505, False),
    ("Office Furniture and Equipment", 3240349, False), ("Vehicles", 262490, False), ("Software", 3240597, False),
    ("Construction in Process", 420332, False), ("Total Property and Equipment, at Cost", 21248838, True),
    ("Less: Accumulated Depreciation", -18856875, False),
    ("Total Property and Equipment (at Depreciated Cost)", 2391963, True),
    ("Noncompete Agreement, Net", 20833, False), ("Operating Right-of-Use Asset, Net", 6413855, False),
    ("Deferred Tax Asset", 606057, False), ("Deposits", 6861, False), ("Total Other Assets", 7047606, True),
    ("Total Assets", 47978181, True),
    ("Accounts Payable", 3650249, False), ("Current Portion of Lease Liability - Operating", 1315402, False),
    ("Income Taxes Payable", 180539, False), ("Accrued Compensation", 2127269, False),
    ("Accrued Commissions", 1064020, False), ("Other Accrued Expenses", 2181943, False),
    ("Total Current Liabilities", 10519422, True),
    ("Reserve for Uncertain Tax Positions", 0, False),
    ("Long-Term Lease Liability - Operating (Less Current Portion)", 5376568, False),
    ("Total Long-Term Liabilities", 5376568, True), ("Total Liabilities", 15895990, True),
    ("Common Stock", 30030, False), ("Additional Paid-In Capital", 12359, False),
    ("Retained Earnings", 32039802, False), ("Total Stockholders' Equity", 32082191, True),
    ("Total Liabilities and Stockholders' Equity", 47978181, True),
]
NUAIRE_IS = [
    ("Net Revenues", 74850302, False), ("Cost of Revenues", 51168691, False), ("Gross Profit", 23681611, True),
    ("Selling Expense", 11738103, False), ("General and Administrative", 6162806, False),
    ("Research and Development", 532092, False), ("Total Operating Expense", 18433001, True),
    ("Income from Operations", 5248610, True), ("Interest Income - Net", 513770, False),
    ("Other Income", 189840, False), ("Total Other Income", 703610, True),
    ("Income Before Income Taxes", 5952220, True), ("Provision for Income Taxes", 513949, False),
    ("Net Income", 5438271, True),
]
NUAIRE_CF = [("Depreciation and Amortization", 1830395, False)]


# What the filings say about particular lines. Loaded onto SourceLine.note so every backend sees it.
LINE_NOTES = {
    "Current portion of financing liability": "10-Q: arises from the sale-leaseback of the headquarters and manufacturing facility at 2700 West Front Street, Statesville, accounted for as a financing; carrying value $27,782K at 2024-10-31.",
    "Long-term portion of financing liability": "10-Q: arises from the sale-leaseback of the headquarters and manufacturing facility at 2700 West Front Street, Statesville, accounted for as a financing; carrying value $27,782K at 2024-10-31.",
    "Financing liability: PNC Revolving Credit Facility": "Ex 99.2 Note 4(h): drawn at close on the $20M senior secured revolving credit facility with PNC; added to the financing liability line.",
    "Financing liability: PNC Term Loan": "Ex 99.2 Note 4(h): $15M senior secured term loan from PNC; added to the financing liability line.",
    "Financing liability: 8% Seller Notes (subordinated)": "Ex 99.2 Note 4(h) and Note 3: 8% subordinated notes issued to the sellers, maturing 2027; added to the financing liability line.",
    "Short-term borrowings": "10-Q: overdraft protection and short-term loan arrangements at the international subsidiaries.",
    "Current portion of financing lease liabilities": "10-Q: finance leases of equipment, not the Statesville property.",
    "Long-term portion of financing lease liabilities": "10-Q: finance leases of equipment, not the Statesville property.",
    "Certificates of Deposit": "Ex 99.1: short-term investments; maturities are not disclosed in the pages read.",
    "Noncompete Agreement, Net": "Ex 99.1: an intangible asset being amortized; $20,833 left at 2024-09-30.",
    "Reserve for Uncertain Tax Positions": "Ex 99.1: nil at 2024-09-30 ($2,336,000 at 2023-09-30).",
}


def build_lines(store: MemoryStore) -> list[SourceLine]:
    lines: list[SourceLine] = []

    def add(company, section, period, unit, source_ref, rows):
        for line, amount, is_total in rows:
            lines.append(SourceLine(id=store.next_id("sl"), deal_id=DEAL_ID, company=company, line=line,
                                    section=section, period=period, amount=float(amount), unit=unit,
                                    source_ref=source_ref, is_total=is_total, note=LINE_NOTES.get(line)))

    cut = next(i for i, r in enumerate(KEWAUNEE_BS) if r[0] == "Long-term portion of financing liability") + 1
    add(PLATFORM, "balance_sheet", "2024-10-31", "USD thousands", TENQ, KEWAUNEE_BS[:cut])
    add(PLATFORM, "balance_sheet", "2024-11-01 (closing)", "USD thousands", EX992_FIN,
        [(l, a, False) for l, a in KEWAUNEE_CLOSE])
    add(PLATFORM, "balance_sheet", "2024-10-31", "USD thousands", TENQ, KEWAUNEE_BS[cut:])
    add(PLATFORM, "income_statement", "FY ended 2024-04-30", "USD thousands", EX992_IS, KEWAUNEE_IS)
    add(PLATFORM, "cash_flow", "FY ended 2024-04-30", "USD thousands", f"{TENK}, statement of cash flows", KEWAUNEE_CF)
    add(TARGET, "balance_sheet", "2024-09-30", "USD", EX991, NUAIRE_BS)
    add(TARGET, "income_statement", "FY ended 2024-09-30", "USD", EX991, NUAIRE_IS)
    add(TARGET, "cash_flow", "FY ended 2024-09-30", "USD", f"{EX991}, statement of cash flows", NUAIRE_CF)
    return lines


# The agreement text the live demo deal starts from (D23): verbatim extracts of Ex 10.1 (the opening, Section 4.8, and
# the EBITDA, Senior Funded Bank Debt, and Subordinated Debt definitions), committed so the demo runs on any machine
# with the repo. The full 115K-character exhibit stays out of git (data/raw/, scripts/fetch_filings.py).
AGREEMENT_PATH = Path(__file__).resolve().parents[4] / "data" / "brief" / "kewaunee_ex101_extract.txt"
AGREEMENT_SOURCE = f"{EX101} (verbatim extracts)"
# The amounts the books give for the agreement's adjustments, each with its source outside the agreement. The verifier
# fills the reader's draft from them, so the controller is asked for none of them (D23).
BOOK_AMOUNTS = [*BRIEF.ebitda_addbacks, *BRIEF.ebitda_deductions]


def agreement_text() -> str:
    return AGREEMENT_PATH.read_text()


def seed(store: MemoryStore, gw: Gateway, from_agreement: bool = False) -> Deal:
    """The demo deal. With `from_agreement` (the app's live demo deal, D23) it starts from the agreement text: the
    Brief Reader drafts the Brief, the verifier checks it, fills the amounts from the books, and approves it when every
    check passes. Without it (most tests) the deal carries the hand-written Brief, approved."""
    deal = Deal(id=DEAL_ID, name="Kewaunee Scientific acquires Nu Aire", platform=PLATFORM, target=TARGET,
                stage="new", brief=BRIEF, data_source="filings", note=NOTE)
    if not from_agreement:
        gw.create_deal(CONTROLLER, deal, build_lines(store))
        return deal
    deal = deal.model_copy(update={"brief": None, "brief_status": "none", "brief_auto_approve": True,
                                   "book_amounts": [a.model_copy(deep=True) for a in BOOK_AMOUNTS]})
    return gw.create_deal_from_agreement(CONTROLLER, deal, build_lines(store), agreement_text(), AGREEMENT_SOURCE)


def is_demo_twin(lines: list[SourceLine], platform: str, text: str) -> bool:
    """An upload of the demo deal itself: the committed agreement extract and the same statements (by the replay's
    content hash). Its adjustments then have the same sourced book amounts, so the upload gets them, and the
    verifier's auto-approval, like the demo deal (D23). Any other upload is asked and approved by the controller."""
    from app.agents import demo_replay
    from app.core.agreement import agreement_sha256
    if agreement_sha256(text) != agreement_sha256(agreement_text()):
        return False
    return demo_replay.content_digest(lines, platform) == demo_replay.content_digest(build_lines(MemoryStore()),
                                                                                    PLATFORM)


def seed_demo(store: MemoryStore, gw: Gateway) -> Deal:
    """The live demo deal as the app seeds it: from the agreement (D23)."""
    return seed(store, gw, from_agreement=True)
