"""Edit-aware math tools (docs/tasks/tri.md T1) on the real Kewaunee and Nu Aire figures.

Edits are SimpleNamespace objects with the shape of Cayden's C1 Edit model, read by attribute.
Expected values are worked out by hand in the comments from the fixture (app/db/fixtures/kewaunee.py).
"""
import os
from types import SimpleNamespace

import pytest

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

from app.agents.jobs import advance  # noqa: E402
from app.core.models import CONTROLLER, SourceLine  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402
from app.tools import edits as edit_tools  # noqa: E402
from app.tools import finance  # noqa: E402


@pytest.fixture(scope="module")
def inputs():
    """Fixture lines and the scripted Mapper's mappings, after the controller answers every flag."""
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    advance(gw, DEAL_ID)
    for flag in gw.open_flags(DEAL_ID):
        gw.answer(CONTROLLER, flag.id, flag.default or flag.options[0].id)
    deal = gw._deal(DEAL_ID)
    return (gw._platform_lines(deal), gw._target_lines(deal), gw._usable_mappings(DEAL_ID), deal.brief)


def edit(eid, kind="amount", status="reasoned", **kw):
    base = dict(id=eid, deal_id=DEAL_ID, kind=kind, company=None, line=None, section=None, old_value=None,
                new_value=None, old_platform_line=None, new_platform_line=None, status=status, reason_chip=None,
                reason_text="test", remember=False, policy_id=None, adjustment_id=None, actor="controller",
                at=None, run_ids=[])
    base.update(kw)
    return SimpleNamespace(**base)


def rows_by_line(out):
    return {(r["section"], r["line"]): r for r in out["rows"]}


def run_all(inputs, edits=None):
    p, t, m, brief = inputs
    c = finance.consolidate(p, t, m, edits=edits)
    return {"consolidate": c, "tie_out": finance.tie_out(c["rows"], edits=edits),
            "ebitda": finance.ebitda(p, t, brief, edits=edits),
            "covenant_debt": finance.covenant_debt(p, t, brief, edits=edits)}


def strip(out):
    return {k: v for k, v in out.items() if k != "edits_applied"}


def test_no_edits_gives_todays_figures_and_an_empty_edits_applied(inputs):
    p, t, m, brief = inputs
    for edits in (None, []):
        out = run_all(inputs, edits)
        for name in ("consolidate", "tie_out", "ebitda", "covenant_debt"):
            assert out[name]["edits_applied"] == []
    assert out["ebitda"]["ebitda"] == 28378.845  # base 25,311.845 + add-backs 5,037 - rent 1,970
    assert out["covenant_debt"]["debt"] == 21633.0
    assert out["tie_out"]["ok"] is True
    assert rows_by_line(out["consolidate"])[("balance_sheet", "Total Assets")]["combined"] == 182456.181
    # the call without the argument gives the same dicts
    assert finance.consolidate(p, t, m) == out["consolidate"]
    assert finance.ebitda(p, t, brief) == out["ebitda"]
    assert finance.covenant_debt(p, t, brief) == out["covenant_debt"]


def test_amount_edit_on_nu_aire_net_income_moves_ebitda_and_leverage(inputs):
    p, t, m, brief = inputs
    e = edit("ed_1", company="Nu Aire", line="Net Income", section="income_statement",
             old_value=5438.271, new_value=6438.271)  # Nu Aire files dollars; the edit is in thousands
    out = run_all(inputs, [e])
    # 28,378.845 + 1,000 = 29,378.845
    assert out["ebitda"]["ebitda"] == 29378.845
    assert out["ebitda"]["edits_applied"] == ["ed_1"]
    assert out["ebitda"]["parts"][1]["net_income"] == 6438.271
    # 21,633 / 29,378.845 = 0.73636 -> 0.736
    assert finance.leverage(out["covenant_debt"]["debt"], out["ebitda"]["ebitda"])["leverage"] == 0.736
    row = rows_by_line(out["consolidate"])[("income_statement", "Net earnings")]
    # before: target 5,438.271, combined 19,057 + 5,438.271 = 24,495.271; after: both up 1,000
    assert (row["target"], row["combined"]) == (6438.271, 25495.271)
    assert out["consolidate"]["edits_applied"] == ["ed_1"]
    assert out["covenant_debt"]["edits_applied"] == ["ed_1"]
    # the input lines were not changed
    assert next(x for x in t if x.line == "Net Income").amount == 5438271.0


def test_remap_of_certificates_of_deposit_moves_the_amount_and_still_ties_out(inputs):
    e = edit("ed_2", kind="remap", company="Nu Aire", line="Certificates of Deposit",
             old_platform_line="Cash and cash equivalents",
             new_platform_line="Prepaid expenses and other current assets")
    before = rows_by_line(run_all(inputs)["consolidate"])
    out = run_all(inputs, [e])
    rows = rows_by_line(out["consolidate"])
    cash = rows[("balance_sheet", "Cash and cash equivalents")]
    prepaid = rows[("balance_sheet", "Prepaid expenses and other current assets")]
    # Certificates of Deposit: 991,082 dollars = 991.082. Cash target 14,447.056 - 991.082 = 13,455.974,
    # combined 25,963 + 13,455.974 = 39,418.974. Prepaid target 972.345 + 991.082 = 1,963.427,
    # combined 6,228 + 1,963.427 = 8,191.427.
    assert (cash["target"], cash["combined"]) == (13455.974, 39418.974)
    assert (prepaid["target"], prepaid["combined"]) == (1963.427, 8191.427)
    assert "Certificates of Deposit" in prepaid["target_lines"]
    assert "Certificates of Deposit" not in cash["target_lines"]
    for key in (("balance_sheet", "Total Assets"), ("balance_sheet", "Total Current Assets")):
        assert rows[key]["combined"] == before[key]["combined"]  # the totals are unchanged
    assert out["tie_out"]["ok"] is True and out["tie_out"]["balance_sheet_balances"] is True
    assert out["consolidate"]["edits_applied"] == ["ed_2"]
    assert out["ebitda"]["edits_applied"] == []  # a remap does not touch the lines


def test_remap_lands_on_the_platform_lines_own_section(inputs):
    p, t, m, brief = inputs
    e = edit("ed_x", kind="remap", company="Nu Aire", line="Certificates of Deposit",
             new_platform_line="Net sales")  # a balance sheet line remapped onto an income statement line
    rows = rows_by_line(finance.consolidate(p, t, m, edits=[e]))
    assert ("balance_sheet", "Net sales") not in rows
    assert "Certificates of Deposit" in rows[("income_statement", "Net sales")]["target_lines"]
    new_m, applied = edit_tools.apply_remap_edits(m, t, p, [e])
    moved = next(x for x in new_m if x.target_line == "Certificates of Deposit")
    assert moved.platform_line_id == next(x.id for x in p if x.line == "Net sales")
    assert applied == ["ed_x"]


def test_remap_onto_a_platform_total_or_a_missing_line_is_refused(inputs):
    p, t, m, brief = inputs
    onto_total = edit("ed_y1", kind="remap", company="Nu Aire", line="Deposits", new_platform_line="Total Current Assets")
    with pytest.raises(ValueError, match="remap edit ed_y1: Total Current Assets is a platform total"):
        edit_tools.apply_remap_edits(m, t, p, [onto_total])
    with pytest.raises(ValueError, match="platform total"):
        finance.consolidate(p, t, m, edits=[onto_total])
    ghost = edit("ed_y2", kind="remap", company="Nu Aire", line="Deposits", new_platform_line="Nowhere")
    with pytest.raises(ValueError, match="remap edit ed_y2: the platform has no line Nowhere"):
        edit_tools.apply_remap_edits(m, t, p, [ghost])
    stale = edit("ed_y3", kind="remap", company="Nu Aire", line="Certificates of Deposit",
                 old_platform_line="Restricted cash", new_platform_line="Prepaid expenses and other current assets")
    with pytest.raises(ValueError, match="remap edit ed_y3 is stale: it expects Restricted cash"):
        edit_tools.apply_remap_edits(m, t, p, [stale])


def test_amount_edit_on_kewaunee_total_assets_breaks_the_tie_out(inputs):
    # 134,478 + 500 = 134,978; combined total assets 182,956.181 against 182,456.181 of liabilities and equity.
    # Refusing approval of a result whose tie-out fails is the gateway's job, not this tool's.
    e = edit("ed_3", company="Kewaunee", line="Total Assets", section="balance_sheet",
             old_value=134478, new_value=134978)
    out = run_all(inputs, [e])
    tie = out["tie_out"]
    assert tie["ok"] is False and tie["balance_sheet_balances"] is False
    assert tie["balance"] == {"total_assets": 182956.181, "total_liabilities_and_equity": 182456.181}
    assert tie["edits_applied"] == ["ed_3"]
    assert rows_by_line(out["consolidate"])[("balance_sheet", "Total Assets")]["platform"] == 134978.0


def test_reverted_edit_changes_nothing(inputs):
    plain = run_all(inputs)
    e = edit("ed_3", status="reverted", company="Kewaunee", line="Total Assets", section="balance_sheet",
             old_value=134478, new_value=134978)
    out = run_all(inputs, [e, None])
    for name in plain:
        assert strip(out[name]) == strip(plain[name])
        assert out[name]["edits_applied"] == []
    assert edit_tools.active([e, None]) == []


def test_unmatched_edits_are_refused(inputs):
    p, t, m, brief = inputs
    with pytest.raises(ValueError, match=r"No Such Line \(Nu Aire\)"):
        finance.ebitda(p, t, brief, edits=[edit("ed_4", company="Nu Aire", line="No Such Line", new_value=1.0)])
    with pytest.raises(ValueError, match=r"Phantom Line \(Nu Aire\)"):
        finance.consolidate(p, t, m, edits=[edit("ed_5", kind="remap", company="Nu Aire", line="Phantom Line",
                                                 new_platform_line="Net sales")])
    # a Kewaunee line name under the wrong company does not match either
    with pytest.raises(ValueError, match="matches no line"):
        edit_tools.apply_amount_edits(p + t, [edit("ed_6", company="Nu Aire", line="Net earnings", new_value=1.0)])


def test_amount_edit_section_is_optional_and_case_is_ignored(inputs):
    p, t, m, brief = inputs
    e = edit("ed_7", company="nu aire", line="  net income ", new_value=6438.271)
    lines, applied = edit_tools.apply_amount_edits(t, [e])
    hit = [x for x in lines if x.line == "Net Income"]
    assert hit and all(x.amount == 6438.271 and x.unit == "USD thousands" for x in hit)
    assert applied == ["ed_7"]


ROLLUP = "the roll-up for that section is not defined, so code cannot recompute the totals"


def is_amounts(lines, company):
    return {x.line: round(finance.to_thousands(x.amount, x.unit), 3) for x in lines
            if x.company == company and x.section == "income_statement"}


def test_line_sign_on_the_fixture_income_statements():
    plus = ("Net sales", "Other income, net", "Net Revenues", "Interest Income - Net", "Other Income")
    minus = ("Cost of products sold", "Operating expenses", "Pension expense", "Interest expense",
             "Income tax (benefit) expense", "Net earnings attributable to the non-controlling interest",
             "Cost of Revenues", "Selling Expense", "General and Administrative", "Research and Development",
             "Provision for Income Taxes")
    assert [edit_tools.line_sign(n) for n in plus] == [1] * len(plus)
    assert [edit_tools.line_sign(n) for n in minus] == [-1] * len(minus)


def test_a_cost_cut_on_nu_aire_general_and_administrative_carries_to_net_income(inputs):
    p, t, m, brief = inputs
    # 6,162,806 dollars = 6,162.806; cut 500 to 5,662.806 (delta -500). Total Operating Expense is the first
    # total after it and starts with "Total": 18,433.001 - 500 = 17,933.001. The running totals move by
    # -1 * -500 = +500: Income from Operations 5,248.610 -> 5,748.610, Income Before Income Taxes
    # 5,952.220 -> 6,452.220, Net Income 5,438.271 -> 5,938.271. Gross Profit (before) and Total Other Income
    # (a group total after a running total) do not move.
    ga = edit("ed_8", company="Nu Aire", line="General and Administrative", section="income_statement",
              old_value=6162.806, new_value=5662.806)
    lines, applied, rollup, notes = edit_tools.carry_amount_edits(t, [ga])
    got = is_amounts(lines, "Nu Aire")
    assert (got["General and Administrative"], got["Total Operating Expense"], got["Income from Operations"],
            got["Income Before Income Taxes"], got["Net Income"]) == (5662.806, 17933.001, 5748.61, 6452.22, 5938.271)
    assert (got["Gross Profit"], got["Total Other Income"]) == (23681.611, 703.61)
    assert rollup == [{"edit_id": "ed_8", "company": "Nu Aire", "line": n, "delta": d} for n, d in (
        ("Total Operating Expense", -500.0), ("Income from Operations", 500.0),
        ("Income Before Income Taxes", 500.0), ("Net Income", 500.0))]
    assert applied == ["ed_8"]
    assert notes == ["General and Administrative (Nu Aire) has no revenue or cost word in its name; "
                     "the roll-up treated it as a cost"]
    out = run_all(inputs, [ga])
    # covenant EBITDA 28,378.845 + 500 = 28,878.845; 21,633 / 28,878.845 = 0.74909 -> 0.749
    assert out["ebitda"]["ebitda"] == 28878.845 and out["ebitda"]["rollup"] == rollup
    assert out["ebitda"]["rollup_notes"] == notes
    assert finance.leverage(out["covenant_debt"]["debt"], out["ebitda"]["ebitda"])["leverage"] == 0.749
    assert out["consolidate"]["rollup"] == rollup and out["covenant_debt"]["debt"] == 21633.0
    net = rows_by_line(out["consolidate"])[("income_statement", "Net earnings")]
    assert (net["target"], net["combined"]) == (5938.271, 24995.271)  # 19,057 + 5,938.271
    assert out["tie_out"]["ok"] is True
    # the input lines were not changed
    assert next(x for x in t if x.line == "Total Operating Expense").amount == 18433001.0


def test_a_cost_rise_on_kewaunee_operating_expenses_carries_to_every_running_total(inputs):
    p, t, m, brief = inputs
    # 33,770 + 1,000. The first total after it is Operating profit, a running total, so no group total moves.
    # Running totals move by -1 * 1,000: Operating profit 18,281 -> 17,281, Profit before income taxes
    # 13,119 -> 12,119, Net earnings 19,057 -> 18,057, Net earnings attributable to Kewaunee 18,753 -> 17,753.
    ox = edit("ed_13", company="Kewaunee", line="Operating expenses", section="income_statement",
              old_value=33770, new_value=34770)
    lines, applied, rollup, notes = edit_tools.carry_amount_edits(p, [ox])
    got = is_amounts(lines, "Kewaunee")
    assert (got["Operating profit"], got["Profit before income taxes"], got["Net earnings"],
            got["Net earnings attributable to Kewaunee Scientific Corporation"], got["Gross profit"]) == (
        17281.0, 12119.0, 18057.0, 17753.0, 52051.0)
    assert [r["line"] for r in rollup] == ["Operating profit", "Profit before income taxes", "Net earnings",
                                           "Net earnings attributable to Kewaunee Scientific Corporation"]
    assert {r["delta"] for r in rollup} == {-1000.0} and notes == []
    # covenant EBITDA 28,378.845 - 1,000 = 27,378.845
    assert finance.ebitda(p, t, brief, edits=[ox])["ebitda"] == 27378.845


def test_more_interest_income_at_nu_aire_leaves_covenant_ebitda_unchanged(inputs):
    p, t, m, brief = inputs
    # 513.770 + 100 = 613.770. Total Other Income 703.610 + 100 = 803.610; Income Before Income Taxes
    # 6,052.220; Net Income 5,538.271. The EBITDA build subtracts interest income, so net income +100 and
    # interest income +100 cancel: covenant EBITDA stays 28,378.845.
    ii = edit("ed_14", company="Nu Aire", line="Interest Income - Net", section="income_statement",
              old_value=513.77, new_value=613.77)
    lines, applied, rollup, notes = edit_tools.carry_amount_edits(t, [ii])
    got = is_amounts(lines, "Nu Aire")
    assert (got["Total Other Income"], got["Income Before Income Taxes"], got["Net Income"]) == (
        803.61, 6052.22, 5538.271)
    assert (got["Income from Operations"], got["Total Operating Expense"]) == (5248.61, 18433.001)
    assert [(r["line"], r["delta"]) for r in rollup] == [("Total Other Income", 100.0),
                                                         ("Income Before Income Taxes", 100.0), ("Net Income", 100.0)]
    out = finance.ebitda(p, t, brief, edits=[ii])
    assert out["ebitda"] == 28378.845
    assert (out["parts"][1]["net_income"], out["parts"][1]["interest_income"]) == (5538.271, 613.77)


def test_reverting_the_carried_edits_restores_every_figure(inputs):
    plain = run_all(inputs)
    edits = [edit("ed_8", status="reverted", company="Nu Aire", line="General and Administrative",
                  section="income_statement", old_value=6162.806, new_value=5662.806),
             edit("ed_13", status="reverted", company="Kewaunee", line="Operating expenses",
                  section="income_statement", old_value=33770, new_value=34770)]
    out = run_all(inputs, edits)
    for name in plain:
        assert out[name] == plain[name]
    assert out["ebitda"]["ebitda"] == 28378.845 and out["consolidate"]["rollup"] == []


def test_amount_edit_on_a_balance_sheet_detail_line_is_refused(inputs):
    p, t, m, brief = inputs
    # Cash and Cash Equivalents: 13,455.974 + 500 would not reach Total Assets, and the tie-out would still pass.
    cash = edit("ed_9", company="Nu Aire", line="Cash and Cash Equivalents", section="balance_sheet",
                old_value=13455.974, new_value=13955.974)
    with pytest.raises(ValueError, match=r"amount edit ed_9 on Cash and Cash Equivalents \(Nu Aire, balance_sheet\) "
                                         r"is refused: " + ROLLUP):
        finance.consolidate(p, t, m, edits=[cash])
    with pytest.raises(ValueError, match="ed_9"):
        finance.covenant_debt(p, t, brief, edits=[cash])
    with pytest.raises(ValueError, match="ed_9"):
        finance.ebitda(p, t, brief, edits=[cash])


def _synthetic(lid, section, amount):
    return SourceLine(id=lid, deal_id="d_x", company="Nu Aire", line="Other", section=section, period="FY",
                      amount=amount, source_ref="test")


def test_amount_edit_matching_two_lines_is_refused():
    lines = [_synthetic("sl_a", "cash_flow", 100.0), _synthetic("sl_b", "cash_flow", 200.0)]
    e = edit("ed_10", company="Nu Aire", line="Other", section="cash_flow", new_value=300.0)
    with pytest.raises(ValueError, match=r"amount edit ed_10 matches 2 lines: sl_a Other \(cash_flow\); "
                                         r"sl_b Other \(cash_flow\)"):
        edit_tools.apply_amount_edits(lines, [e])
    # no section given and the name is on two statements: also refused
    lines = [_synthetic("sl_a", "cash_flow", 100.0), _synthetic("sl_c", "income_statement", 200.0)]
    with pytest.raises(ValueError, match="matches 2 lines"):
        edit_tools.apply_amount_edits(lines, [edit("ed_11", company="Nu Aire", line="Other", new_value=1.0)])
    # with the section it applies to the one line
    out, applied = edit_tools.apply_amount_edits(lines, [edit("ed_12", company="Nu Aire", line="Other",
                                                              section="cash_flow", new_value=1.0)])
    assert [x.amount for x in out] == [1.0, 200.0] and applied == ["ed_12"]
