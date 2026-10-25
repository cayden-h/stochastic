"""The Dashboard's four seeded cases, besides the live demo deal (Kewaunee and Nu Aire, kewaunee.py).

Three are real public deals, each built from its filings like the Kewaunee fixture (sources in each module's header):
- DLH Holdings acquires GRSi (dlh_grsi.py): posted, after one covenant answer and two reasoned remap edits.
- Mama's Creations acquires Crown I (mamas_crown.py): awaiting the controller's approval.
- Shutterstock acquires Envato (sstk_envato.py): waiting on the controller, with the IFRS 16 lease question open.
The fourth is a sample, not a real deal: DLH's next add-on, the QuickBooks Online sample company (Craig's Design and
Landscaping Services, scripts/samples/qbo/). Its platform lines are the posted combined DLH and GRSi books of the
first case, read from that case's consolidate run, and the Mapper reuses the controller's answer on DLH's prior term
loan from that case (policy:apply), so it asks only about the sample company's own credit card. It is posted, after two reasoned remap edits.
Four reasoned edits in all, each citing its source line in the reason.

Every case runs through the real pipeline on the scripted backend with no pace: the scripted Mapper reads the deal's
reference mapping (`DealPlan`), the Preparer and the Reviewer call the tools through the gateway, and the controller's
steps go through the same gateway calls the console makes. So every figure is a tool run and every case has its
mappings, conversation, audit log, and review.

`seed_cases` is idempotent: a case whose deal id is already in the store (a Postgres ledger that loaded it) is left as
it is. The app runs it in a background thread after startup (`DEMO_CASES`, on by default; off under pytest unless a
test calls it). No case teaches a policy that covers Kewaunee or Nu Aire, so the live demo deal still asks its two
questions on a fresh run (checked by `assert_demo_deal_untouched` and the tests).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.agents.backends.scripted import DEAL_PLANS, DealPlan, register_plan
from app.agents.jobs import advance
from app.core.models import CONTROLLER, Brief, Deal, ReasonChip, SourceLine, State
from app.db.fixtures import dlh_grsi, mamas_crown, sstk_envato
from app.db.fixtures import kewaunee
from app.gateway.gateway import Gateway

log = logging.getLogger("stochastic.cases")

FILED = (dlh_grsi, mamas_crown, sstk_envato)

# The reasons the edit bubble offers on each seeded deal, hardcoded per deal like the demo deal's.
DLH_REMAP_REASON = ("Ex 99.3 note 3b conforms GRSi to DLH's presentation: its indirect costs are contract costs")
CHIPS = {
    dlh_grsi.DEAL_ID: {
        "amount": [ReasonChip(id=0, label="One-time acquisition cost, an allowed add-back"),
                   ReasonChip(id=1, label="Auditor's late adjustment"),
                   ReasonChip(id=2, label="Correcting a typo in the source")],
        "remap": [ReasonChip(id=0, label=DLH_REMAP_REASON),
                  ReasonChip(id=1, label="Matches how the platform reports it"),
                  ReasonChip(id=2, label="Auditor's reclassification")],
    },
}

# The controller's reasoned edits on the seeded cases (D19), each sourced in the filing or the sample's own export and
# made through the same gateway calls as the console's edit bubble (apply_edit, then reason_edit). With the DLH remap
# above (remembered, a platform policy) there are four across the cases, two on DLH and GRSi and two on the sample:
# GET /memory/counts reads 4 after seeding. These three are not remembered, so none becomes memory a later deal is
# offered. Mama's and Crown I has none: the gateway refuses amount edits on subtotals and on balance sheet detail
# lines, and no Crown I line has a filing-sourced correction or remap that fits those rules.
DLH_CONTRACT_LIABILITIES_REASON = (
    "Ex 99.2 Note 1: GRSi's other current liabilities ($209) are its contract liabilities, which DLH reports as "
    "Deferred revenue")
SAMPLE_UNDEPOSITED_FUNDS_REASON = (
    "QuickBooks account list (scripts/samples/qbo/account_list.xlsx): Undeposited Funds is an Other Current Assets "
    "account, not a Bank account: customer payments received but not yet in the bank")
SAMPLE_EQUIPMENT_RENTAL_REASON = (
    "QuickBooks account list (scripts/samples/qbo/account_list.xlsx): Equipment Rental is its own Expenses account, "
    "not the Job Expenses:Equipment Rental job cost, so it is overhead")


def _reasoned_edit(gw: Gateway, deal_id: str, kind: str, company: str, line: str, reason: str, **change) -> None:
    out = gw.apply_edit(CONTROLLER, deal_id, kind, company, line, **change)
    gw.reason_edit(CONTROLLER, out["edit"].id, text=reason, remember=False)


for _m in FILED:
    register_plan(_m.DEAL_ID, DealPlan(mapping=_m.MAPPING, tags=_m.TAGS, covenant_flag=_m.COVENANT_FLAG,
                                       mapping_flags=_m.MAPPING_FLAGS,
                                       note="scripted backend: this deal's reference mapping from its filings; "
                                            "policies applied first"),
                  chips=CHIPS.get(_m.DEAL_ID))


# ---------------------------------------------------------------------------------------------------- the sample case
SAMPLE_ID = "d_dlh_craigs"
SAMPLE_PLATFORM = dlh_grsi.PLATFORM  # the same company name, so DLH's learned answers apply to its lines
SAMPLE_TARGET = "Craig's Design and Landscaping"
SAMPLE_NAME = "DLH acquires Craig's Design and Landscaping (QuickBooks sample, not a real deal)"
SAMPLE_NOTE = ("A sample, not a real deal: the QuickBooks Online sample company as DLH's next add-on after GRSi. The "
               "platform is the posted DLH and GRSi combined books, and the Mapper reuses the controller's answer on "
               "DLH's prior term loan.")
QBO = Path(__file__).resolve().parents[4] / "scripts" / "samples" / "qbo"
QBO_REF = ("QuickBooks Online test-drive company trial balance and account list (scripts/samples/qbo/), "
           "exported 2026-10-24")

# The scripted Mapper's reference mapping of the sample company's trial balance lines onto DLH's lines.
_REVENUE = ("Revenue", 0.9, "An income account; DLH reports one revenue line")
_DIRECT = ("Contract costs", 0.85, "A job cost; DLH's contract costs include direct costs identifiable with a contract")
_OVERHEAD = ("General and administrative costs", 0.85, "An overhead expense; DLH reports one G&A line")
SAMPLE_MAPPING: dict[str, tuple[str | None, float, str]] = {
    "Checking": ("Cash", 0.95, "A bank account"), "Savings": ("Cash", 0.95, "A bank account"),
    "Undeposited Funds": ("Cash", 0.8, "Customer payments received, not yet deposited"),
    "Accounts Receivable (A/R)": ("Accounts receivable", 0.95, "Trade receivables"),
    "Inventory Asset": ("Other current assets", 0.75, "DLH carries no inventory line; a small current asset"),
    "Truck:Original Cost": ("Equipment and improvements, net", 0.8, "A vehicle at cost; no depreciation is booked"),
    "Accounts Payable (A/P)": ("Accounts payable and accrued liabilities", 0.95, "Trade payables"),
    "Mastercard": ("Accounts payable and accrued liabilities", 0.7, "A credit card balance, payable monthly"),
    "Arizona Dept. of Revenue Payable": ("Accounts payable and accrued liabilities", 0.85, "Sales tax payable"),
    "Board of Equalization Payable": ("Accounts payable and accrued liabilities", 0.85, "Sales tax payable"),
    "Loan Payable": ("Debt obligations - long-term, net of deferred financing costs", 0.8, "Borrowed money"),
    "Notes Payable": ("Debt obligations - long-term, net of deferred financing costs", 0.8, "Borrowed money"),
    "Opening Balance Equity": ("Additional paid-in capital", 0.7,
                               "QuickBooks' opening balance plug, the owner's starting equity"),
    "Current year earnings": ("Retained earnings (accumulated deficit)", 0.9, "This year's earnings, not yet closed"),
    "Total Assets": ("Total assets", 1.0, "Same subtotal"),
    "Total Liabilities": ("Total liabilities", 1.0, "Same subtotal"),
    "Total Stockholders' Equity": ("Total shareholders' equity", 1.0, "Same subtotal"),
    "Total Liabilities and Stockholders' Equity": ("Total liabilities and shareholders' equity", 1.0, "Same subtotal"),
    "Design income": _REVENUE, "Discounts given": _REVENUE, "Landscaping Services": _REVENUE,
    "Landscaping Services:Job Materials:Fountains and Garden Lighting": _REVENUE,
    "Landscaping Services:Job Materials:Plants and Soil": _REVENUE,
    "Landscaping Services:Job Materials:Sprinklers and Drip Systems": _REVENUE,
    "Landscaping Services:Labor:Installation": _REVENUE, "Landscaping Services:Labor:Maintenance and Repair": _REVENUE,
    "Pest Control Services": _REVENUE, "Sales of Product Income": _REVENUE, "Services": _REVENUE,
    "Cost of Goods Sold": _DIRECT, "Job Expenses": _DIRECT, "Job Expenses:Job Materials:Decks and Patios": _DIRECT,
    "Job Expenses:Job Materials:Plants and Soil": _DIRECT,
    "Job Expenses:Job Materials:Sprinklers and Drip Systems": _DIRECT, "Equipment Rental": _DIRECT,
    "Advertising": _OVERHEAD, "Automobile": _OVERHEAD, "Automobile:Fuel": _OVERHEAD, "Insurance": _OVERHEAD,
    "Legal & Professional Fees": _OVERHEAD, "Legal & Professional Fees:Accounting": _OVERHEAD,
    "Legal & Professional Fees:Bookkeeper": _OVERHEAD, "Legal & Professional Fees:Lawyer": _OVERHEAD,
    "Maintenance and Repair": _OVERHEAD, "Maintenance and Repair:Equipment Repairs": _OVERHEAD,
    "Meals and Entertainment": _OVERHEAD, "Office Expenses": _OVERHEAD, "Rent or Lease": _OVERHEAD,
    "Utilities:Gas and Electric": _OVERHEAD, "Utilities:Telephone": _OVERHEAD, "Miscellaneous": _OVERHEAD,
    "Net Income": ("Net income", 1.0, "Same total"),
    "Depreciation and amortization": ("Depreciation and amortization", 1.0, "Same cash flow line (zero here)"),
}
SAMPLE_TAGS = {
    **dlh_grsi.TAGS,  # DLH's lines as in its own case; the prior term loan is settled by the learned policy
    "Loan Payable": ("debt", "Borrowed money"),
    "Notes Payable": ("debt", "Borrowed money ($25,000 of unknown lender)"),
    "Mastercard": ("unclear", "A credit card balance: borrowed from the card issuer, or a trade payable?"),
}
SAMPLE_COVENANT_FLAG = {
    "lines": ["Mastercard"],
    "question": "Is Craig's Mastercard balance ($158) part of Total Funded Debt? The agreement counts 'all "
                "Indebtedness representing borrowed money' and leaves out trade payables not more than 30 days past "
                "due; a card balance is money the card issuer lent. DLH's prior term loan is not asked again: the "
                "controller answered it on the GRSi deal (the learned policy is applied).",
    "options": [
        ("a", "Count it: a card balance is borrowed from the card issuer", {"Mastercard": "debt"}),
        ("b", "Leave it out: it is paid monthly like a trade payable", {"Mastercard": "not_debt"}),
    ],
    "default": "a",
    "evidence": [("Total Funded Debt shall mean, as of any date of determination, without duplication, the sum of all "
                  "Indebtedness representing borrowed money", "8-K Ex 10.1, Section 1.1 Certain Definitions")],
}
register_plan(SAMPLE_ID, DealPlan(mapping=SAMPLE_MAPPING, tags=SAMPLE_TAGS, covenant_flag=SAMPLE_COVENANT_FLAG,
                                  note="scripted backend: the sample deal's reference mapping; policies applied first"))


# ---------------------------------------------------------------------------------------------------- building
def build_lines(store, deal_id: str, company: str, blocks, notes: dict[str, str]) -> list[SourceLine]:
    """SourceLine rows from a fixture module's blocks: (section, period, unit, source_ref, [(line, amount, is_total)])."""
    out = []
    for section, period, unit, source_ref, rows in blocks:
        for line, amount, is_total in rows:
            out.append(SourceLine(id=store.next_id("sl"), deal_id=deal_id, company=company, line=line, section=section,
                                  period=period, amount=float(amount), unit=unit, source_ref=source_ref,
                                  is_total=is_total, note=notes.get(line)))
    return out


def create_filed_case(gw: Gateway, m) -> Deal:
    store = gw.store
    deal = Deal(id=m.DEAL_ID, name=m.NAME, platform=m.PLATFORM, target=m.TARGET, brief=m.BRIEF,
                data_source="filings", note=m.NOTE)
    lines = (build_lines(store, m.DEAL_ID, m.PLATFORM, m.PLATFORM_BLOCKS, m.LINE_NOTES)
             + build_lines(store, m.DEAL_ID, m.TARGET, m.TARGET_BLOCKS, m.LINE_NOTES))
    gw.create_deal(CONTROLLER, deal, lines)
    return deal


def _run(gw: Gateway, deal_id: str) -> None:
    advance(gw, deal_id, backend="scripted", pace_name="off")


def _answer(gw: Gateway, deal_id: str, kinds=("covenant_tag", "mapping")) -> None:
    """The controller takes the default reading (the agreement's, or the filing's) on each open question."""
    for flag in gw.open_flags(deal_id):
        if flag.payload.get("kind") in kinds:
            gw.answer(CONTROLLER, flag.id, flag.default or flag.options[0].id)


def _approval(gw: Gateway, deal_id: str):
    items = [i for i in gw.store.deal_items(deal_id, "approve_result") if i.state == State.PROPOSED]
    return items[-1] if items else None


def _stage(gw: Gateway, deal_id: str, want: str) -> None:
    got = gw.store.deals[deal_id].stage
    if got != want:
        raise RuntimeError(f"seeded case {deal_id} stopped at {got}, expected {want}")


def scenario_dlh(gw: Gateway) -> None:
    """Posted: the covenant answer (the prior loans were repaid at close), two reasoned remap edits, approval."""
    m = dlh_grsi
    _run(gw, m.DEAL_ID)
    _answer(gw, m.DEAL_ID)
    _run(gw, m.DEAL_ID)
    _stage(gw, m.DEAL_ID, "awaiting_approval")
    out = gw.apply_edit(CONTROLLER, m.DEAL_ID, "remap", m.TARGET, "Indirect costs", platform_line="Contract costs")
    gw.reason_edit(CONTROLLER, out["edit"].id, chip=0, remember=True)
    _reasoned_edit(gw, m.DEAL_ID, "remap", m.TARGET, "Other current liabilities", DLH_CONTRACT_LIABILITIES_REASON,
                   platform_line="Deferred revenue")
    gw.approve(CONTROLLER, _approval(gw, m.DEAL_ID).id)
    _stage(gw, m.DEAL_ID, "posted")


def scenario_mamas(gw: Gateway) -> None:
    """Awaiting approval: the three questions answered with the filings' reading; the Reviewer passed."""
    m = mamas_crown
    _run(gw, m.DEAL_ID)
    _answer(gw, m.DEAL_ID)
    _run(gw, m.DEAL_ID)
    _stage(gw, m.DEAL_ID, "awaiting_approval")


def scenario_sstk(gw: Gateway) -> None:
    """Waiting on the controller: the mapping questions answered, the IFRS 16 lease question still open."""
    m = sstk_envato
    _run(gw, m.DEAL_ID)
    _answer(gw, m.DEAL_ID, kinds=("mapping",))
    _stage(gw, m.DEAL_ID, "awaiting_flag")


def _sample_lines(gw: Gateway) -> list[SourceLine] | None:
    """The sample deal's lines: DLH's side is the posted DLH and GRSi combined books, one line per row of that case's
    consolidate run (the post-close platform for the next add-on); the target is the QuickBooks sample company."""
    sys.path.insert(0, str(QBO.parents[1]))  # scripts/, for load_lines
    from load_lines import load_trial_balance  # noqa: PLC0415 - a script module, loaded only for the sample

    store = gw.store
    result = store.latest_result(dlh_grsi.DEAL_ID)
    if result is None or store.deals[dlh_grsi.DEAL_ID].stage != "posted":
        return None
    cons = store.tool_runs[result.run_ids_by_tool["consolidate"]]
    ref = (f"Posted combined books of {dlh_grsi.NAME} ({dlh_grsi.DEAL_ID}), result {result.id}, consolidate run "
           f"{cons.run_id}")
    platform = [SourceLine(id=store.next_id("sl"), deal_id=SAMPLE_ID, company=SAMPLE_PLATFORM, line=r["line"],
                           section=r["section"], period="DLH FY2022 and GRSi nine months to 2022-09-30, combined",
                           amount=r["combined"], unit="USD thousands", source_ref=ref, is_total=r["is_total"],
                           note=dlh_grsi.LINE_NOTES.get(r["line"]))
                for r in cons.outputs["rows"]]
    target, _ = load_trial_balance(QBO / "trial_balance.xlsx", SAMPLE_ID, store, QBO / "account_list.xlsx")
    target = [t.model_copy(update={"company": SAMPLE_TARGET, "source_ref": f"{QBO_REF}; {t.source_ref}".strip("; ")})
              for t in target]
    target.append(target[0].model_copy(update={
        "id": store.next_id("sl"), "line": "Depreciation and amortization", "section": "cash_flow", "amount": 0.0,
        "is_total": False, "source_ref": "None in the trial balance (no depreciation is booked); added at 0",
        "note": None}))
    return platform + target


def _sample_brief() -> Brief:
    """DLH's Brief, without the add-back that restores GRSi's interest income: the combined books carry no interest
    income line (GRSi's was left unmapped), so the ebitda tool subtracts none and there is nothing to restore."""
    b = dlh_grsi.BRIEF
    return b.model_copy(update={
        "ebitda_addbacks": [a for a in b.ebitda_addbacks if not a.name.startswith("Interest income")],
        "closing_financing": [],
        "test_period_note": "A sample: DLH's agreement and limit over the combined DLH and GRSi books (DLH FY2022, "
                            "GRSi nine months to 2022-09-30, with the GRSi closing draws) plus the QuickBooks sample "
                            "company's trial balance. " + b.test_period_note})


def scenario_sample(gw: Gateway) -> None:
    """Posted: the Mapper reuses the DLH policy, the controller answers the one new question, makes two reasoned remap
    edits from the QuickBooks account list, and approves."""
    lines = _sample_lines(gw)
    if lines is None:
        log.warning("sample case skipped: %s is not posted", dlh_grsi.DEAL_ID)
        return
    deal = Deal(id=SAMPLE_ID, name=SAMPLE_NAME, platform=SAMPLE_PLATFORM, target=SAMPLE_TARGET, brief=_sample_brief(),
                data_source="sample", note=SAMPLE_NOTE)
    gw.create_deal(CONTROLLER, deal, lines)
    _run(gw, SAMPLE_ID)
    _answer(gw, SAMPLE_ID)
    _run(gw, SAMPLE_ID)
    _stage(gw, SAMPLE_ID, "awaiting_approval")
    _reasoned_edit(gw, SAMPLE_ID, "remap", SAMPLE_TARGET, "Equipment Rental", SAMPLE_EQUIPMENT_RENTAL_REASON,
                   platform_line="General and administrative costs")
    _reasoned_edit(gw, SAMPLE_ID, "remap", SAMPLE_TARGET, "Undeposited Funds", SAMPLE_UNDEPOSITED_FUNDS_REASON,
                   platform_line="Other current assets")
    gw.approve(CONTROLLER, _approval(gw, SAMPLE_ID).id)
    _stage(gw, SAMPLE_ID, "posted")


# The order matters: the sample reads the posted DLH case.
CASES = [(dlh_grsi.DEAL_ID, lambda gw: (create_filed_case(gw, dlh_grsi), scenario_dlh(gw))),
         (mamas_crown.DEAL_ID, lambda gw: (create_filed_case(gw, mamas_crown), scenario_mamas(gw))),
         (sstk_envato.DEAL_ID, lambda gw: (create_filed_case(gw, sstk_envato), scenario_sstk(gw))),
         (SAMPLE_ID, scenario_sample)]
CASE_IDS = tuple(i for i, _ in CASES)


def seed_cases(gw: Gateway) -> list[str]:
    """Seed every case not in the store yet, in order. Each runs as a job for its deal (`gw.running`), so a Run
    click on it meanwhile gets 409 and a reset of the demo deal is not held up. A case that fails is logged and
    left at the stage it reached; the others still run. Returns the ids seeded now."""
    done = []
    for deal_id, build in CASES:
        if deal_id in gw.store.deals:
            continue
        with gw.running_lock:
            if deal_id in gw.running:
                continue
            gw.running.add(deal_id)
        try:
            build(gw)
            if deal_id in gw.store.deals:
                done.append(deal_id)
        except Exception:  # noqa: BLE001 - one case must not stop the others or the app
            log.exception("seeding case %s failed", deal_id)
        finally:
            with gw.running_lock:
                gw.running.discard(deal_id)
    assert_demo_deal_untouched(gw)
    return done


def assert_demo_deal_untouched(gw: Gateway) -> None:
    """No policy or adjustment learned on a seeded case may cover the live demo deal's companies, so its fresh run
    always asks. Raises if one does (a fixture change that would quietly skip the demo's escalation)."""
    demo = {kewaunee.PLATFORM.casefold(), kewaunee.TARGET.casefold()}
    for p in gw.store.policies.values():
        if p.deal_id in CASE_IDS and ((p.company or "").casefold() in demo or (p.platform or "").casefold() in demo):
            raise RuntimeError(f"policy {p.id} from seeded case {p.deal_id} covers the demo deal")
    for a in gw.store.adjustments.values():
        if a.deal_id in CASE_IDS and ((a.company or "").casefold() in demo
                                      or (getattr(a, "platform", None) or "").casefold() in demo):
            raise RuntimeError(f"adjustment {a.id} from seeded case {a.deal_id} covers the demo deal")


__all__ = ["CASES", "CASE_IDS", "DEAL_PLANS", "SAMPLE_ID", "seed_cases"]
