"""Per-tool tests for app/tools/finance.py. Inputs are hand-built; expected values are worked out in comments."""
from __future__ import annotations

import pytest

from app.core.models import Adjustment, Brief, Mapping, SourceLine
from app.tools import finance

_n = 0


def line(company, section, name, amount, unit="USD thousands", is_total=False, tag="na"):
    global _n
    _n += 1
    return SourceLine(id=f"L{_n}", deal_id="d", company=company, line=name, section=section, period="FY",
                      amount=amount, unit=unit, source_ref="test", is_total=is_total, covenant_tag=tag)


def mapping(target, platform_line, flagged=False, approved_by=None, mid=None):
    return Mapping(id=mid or f"M{target.id}", deal_id="d", target_line_id=target.id, target_line=target.line,
                   platform_line=platform_line, confidence=0.9, reason="test", flagged=flagged,
                   approved_by=approved_by)


def brief(addbacks=(), deductions=()):
    return Brief(lender="L", agreement_ref="x", limit=2.5, limit_section="4.8", limit_wording="less than",
                 debt_term="Senior Funded Bank Debt", debt_definition="d", debt_excludes=[],
                 ebitda_definition="e", ebitda_addbacks=list(addbacks), ebitda_deductions=list(deductions))


def test_to_thousands():
    assert finance.to_thousands(5000, "USD") == 5.0  # 5000 dollars / 1000
    assert finance.to_thousands(5000, "USD thousands") == 5000.0
    assert finance.to_thousands(2, "USD millions") == 2000.0  # 2 * 1000
    with pytest.raises(ValueError):
        finance.to_thousands(1, "euros")


def _consol_inputs():
    p = [line("P", "income_statement", "Revenue", 1_000_000, "USD"),
         line("P", "income_statement", "Cost of sales", 600_000, "USD"),
         line("P", "income_statement", "Gross profit", 400_000, "USD", is_total=True)]
    t = [line("T", "income_statement", "Sales", 200_000, "USD"),
         line("T", "income_statement", "Cost of goods", 120_000, "USD")]
    return p, t


def test_consolidate_hand_values():
    p, t = _consol_inputs()
    out = finance.consolidate(p, t, [mapping(t[0], "Revenue"), mapping(t[1], "Cost of sales")])
    rows = {r["line"]: r for r in out["rows"]}
    # Revenue: platform 1000K, target 200K, combined 1200K. Cost: 600K + 120K = 720K. Gross profit: 400K + 0.
    assert (rows["Revenue"]["platform"], rows["Revenue"]["target"], rows["Revenue"]["combined"]) == (1000.0, 200.0, 1200.0)
    assert (rows["Cost of sales"]["platform"], rows["Cost of sales"]["target"], rows["Cost of sales"]["combined"]) == (600.0, 120.0, 720.0)
    assert rows["Gross profit"]["combined"] == 400.0
    assert out["unmapped_target_lines"] == [] and out["skipped_target_totals"] == []


def test_consolidate_target_subtotal_on_detail_line_is_skipped():
    p, t = _consol_inputs()
    sub = line("T", "income_statement", "Gross profit", 80_000, "USD", is_total=True)
    out = finance.consolidate(p, t + [sub], [mapping(sub, "Revenue")])
    rows = {r["line"]: r for r in out["rows"]}
    assert out["skipped_target_totals"] == ["Gross profit"]
    assert rows["Revenue"]["target"] == 0.0  # the 80K subtotal was not added onto the 1000K detail line


def test_consolidate_unmapped_detail_line_reported():
    p, t = _consol_inputs()
    out = finance.consolidate(p, t, [mapping(t[0], "Revenue")])
    # t[1] (120,000 dollars = 120K) has no mapping
    assert out["unmapped_target_lines"] == [{"line": "Cost of goods", "amount": 120.0}]


def test_consolidate_flagged_unapproved_raises():
    p, t = _consol_inputs()
    with pytest.raises(ValueError, match="flagged"):
        finance.consolidate(p, t, [mapping(t[0], "Revenue", flagged=True, approved_by=None)])


def test_consolidate_flagged_approved_ok():
    p, t = _consol_inputs()
    out = finance.consolidate(p, t, [mapping(t[0], "Revenue", flagged=True, approved_by="controller")])
    assert {r["line"]: r for r in out["rows"]}["Revenue"]["combined"] == 1200.0


def test_consolidate_target_line_mapped_twice_raises():
    p, t = _consol_inputs()
    ms = [mapping(t[0], "Revenue", mid="M1"), mapping(t[0], "Cost of sales", mid="M2", flagged=True)]
    with pytest.raises(ValueError, match=r"target line Sales is mapped twice \(M1, M2\)"):
        finance.consolidate(p, t, ms)


def _bs(name, amount):
    return {"line": name, "section": "balance_sheet", "platform": amount, "target": 0.0, "combined": amount}


def test_tie_out_balanced_passes():
    out = finance.tie_out([_bs("Total Assets", 500.0), _bs("Total liabilities and equity", 500.0)])
    assert out["ok"] is True and out["balance_sheet_balances"] is True


def test_tie_out_off_by_one_fails():
    out = finance.tie_out([_bs("Total Assets", 500.0), _bs("Total liabilities and equity", 499.0)])
    assert out["ok"] is False and out["balance_sheet_balances"] is False  # |500 - 499| = 1.0 > 0.5


def test_tie_out_curly_shareholders_variant_accepted():
    out = finance.tie_out([_bs("Total Assets", 10.0), _bs("Total liabilities and shareholders’ equity", 10.0)])
    assert out["ok"] is True and out["balance_sheet_balances"] is True


def test_tie_out_missing_equity_total_fails():
    out = finance.tie_out([_bs("Total Assets", 500.0), _bs("Total Liabilities and Net Worth", 500.0)])
    assert out["ok"] is False
    assert out["missing_totals"] == ["total liabilities and equity"]


def test_tie_out_income_statement_only_passes():
    rows = [{"line": "Revenue", "section": "income_statement", "platform": 10.0, "target": 5.0, "combined": 15.0}]
    out = finance.tie_out(rows)
    assert out["ok"] is True and out["balance_sheet_balances"] is None


def _is(c, name, amt):
    return line(c, "income_statement", name, amt)


def _cf(c, name, amt):
    return line(c, "cash_flow", name, amt)


def test_ebitda_hand_case():
    plat = [_is("P", "Net income", 100), _is("P", "Interest expense", 10), _is("P", "Interest income", 4),
            _is("P", "Income tax expense", 20), _cf("P", "Depreciation and amortization", 30)]
    targ = [_is("T", "Net income", 40), _is("T", "Income tax expense", 10), _cf("T", "Depreciation", 5)]
    b = brief([Adjustment(name="a", amount=50, cap=40, source_ref="s")], [Adjustment(name="d", amount=5, source_ref="s")])
    out = finance.ebitda(plat, targ, b)
    # platform: 100 + 10 - 4 + 20 + 30 = 156. target: 40 + 0 - 0 + 10 + 5 = 55. base 211.
    # add-back min(50, 40) = 40. deduction 5. total 211 + 40 - 5 = 246.
    assert [p["subtotal"] for p in out["parts"]] == [156.0, 55.0]
    assert out["base"] == 211.0 and out["addbacks"][0]["applied"] == 40.0
    assert out["ebitda"] == 246.0
    assert out["parts"][0]["lines_used"] == ["Net income", "Interest expense", "Interest income",
                                             "Income tax expense", "Depreciation and amortization"]
    assert out["parts"][1]["lines_used"] == ["Net income", "Income tax expense", "Depreciation"]


def test_ebitda_unknown_net_income_name_raises():
    plat = [_is("P", "Net profit", 100), _cf("P", "Depreciation", 1)]
    targ = [_is("T", "Net income", 1), _cf("T", "Depreciation", 1)]
    with pytest.raises(ValueError, match="platform: no net income line found"):
        finance.ebitda(plat, targ, brief())


def test_ebitda_missing_da_raises():
    plat = [_is("P", "Net income", 100), _cf("P", "Depreciation", 1)]
    targ = [_is("T", "Net income", 1)]
    with pytest.raises(ValueError, match="target: no depreciation and amortization line found"):
        finance.ebitda(plat, targ, brief())


def _bsl(name, amt, tag, note=None):
    l = line("P", "balance_sheet", name, amt, tag=tag)
    l.covenant_note = note
    return l


def test_covenant_debt_sums_and_excludes():
    ls = [_bsl("Term loan", 100, "debt"), _bsl("Revolver", 50, "debt"), _bsl("Seller notes", 30, "not_debt", "subordinated")]
    out = finance.covenant_debt(ls, [], brief())
    assert out["debt"] == 150.0  # 100 + 50
    assert out["excluded"] == [{"line": "Seller notes", "company": "P", "amount": 30.0, "note": "subordinated"}]


def test_covenant_debt_unclear_raises_unless_naive():
    ls = [_bsl("Term loan", 100, "debt"), _bsl("Financing liability", 40, "unclear")]
    with pytest.raises(ValueError, match="unclear"):
        finance.covenant_debt(ls, [], brief())
    out = finance.covenant_debt(ls, [], brief(), naive=True)
    assert out["debt"] == 140.0  # 100 + 40 counted
    assert out["included"][1]["note"] == "naive: unclear line counted as debt"


def test_covenant_debt_na_on_borrowing_line_raises():
    with pytest.raises(ValueError, match=r"covenant tag is 'na' on a borrowing-like line: Term loan payable \(P\)"):
        finance.covenant_debt([_bsl("Term loan payable", 10, "na")], [], brief())


def test_covenant_debt_na_on_loans_receivable_ok():
    assert finance.covenant_debt([_bsl("Loans receivable", 10, "na")], [], brief())["debt"] == 0.0


def test_covenant_debt_na_on_accounts_payable_ok():
    assert finance.covenant_debt([_bsl("Accounts payable", 10, "na")], [], brief())["debt"] == 0.0


def test_leverage():
    assert finance.leverage(150, 60)["leverage"] == 2.5  # 150 / 60
    for bad in (0, -5):
        with pytest.raises(ValueError):
            finance.leverage(150, bad)


def test_leverage_rejects_non_finite():
    for bad in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite"):
            finance.leverage(bad, 60)
        with pytest.raises(ValueError, match="finite"):
            finance.leverage(150, bad)


def test_limit_test():
    assert finance.limit_test(2.499, 2.5)["ok"] is True
    assert finance.limit_test(2.5, 2.5, wording="less than")["ok"] is False  # strict
    at = finance.limit_test(2.5, 2.5, wording="less than or equal")
    assert at["ok"] is True and at["headroom_turns"] == 0.0
    cap = finance.limit_test(2.0, 2.5, ebitda_value=60, debt=120)
    assert cap["debt_capacity"] == 30.0  # 2.5 * 60 - 120


def test_limit_test_sensitivity_on_fixture_figures():
    # Whole-line debt 71,955 over covenant EBITDA 28,378.845 = 2.5355, rounds to 2.536: over 2.50.
    # Flip add-back: 71,955 / 2.5 = 28,782; 28,782 - 28,378.845 = 403.155 more EBITDA reaches the limit.
    # Flip rent: the 1,970 rent deduction would have to fall to 1,970 - 403.155 = 1,566.845.
    out = finance.limit_test(0.762, 2.5, ebitda_value=28378.845, debt=21633.0, naive_debt=71955.0,
                             rent_deduction=1970.0)
    assert out["naive_debt"] == 71955.0
    assert out["naive_leverage"] == 2.536
    assert out["naive_ok"] is False
    assert out["naive_flip_addback"] == pytest.approx(403.155, abs=1e-9)
    assert out["naive_flip_rent"] == pytest.approx(1566.845, abs=1e-9)
    assert out["ok"] is True and out["debt_capacity"] == pytest.approx(49314.113, abs=0.001)  # unchanged keys


def test_limit_test_sensitivity_already_passing():
    # 120 / 60 = 2.0 passes 2.5; flip add-back 120 / 2.5 - 60 = 48 - 60 = -12 (negative: already passes).
    out = finance.limit_test(2.0, 2.5, ebitda_value=60, debt=120, naive_debt=120, rent_deduction=5)
    assert out["naive_leverage"] == 2.0 and out["naive_ok"] is True
    assert out["naive_flip_addback"] == -12.0
    assert out["naive_flip_rent"] == 17.0  # 5 - (-12)


def test_limit_test_sensitivity_without_rent_or_naive():
    # 150 / 50 = 3.0 fails 2.5; flip add-back 150 / 2.5 - 50 = 60 - 50 = 10. No rent: no rent flip.
    out = finance.limit_test(1.0, 2.5, ebitda_value=50, debt=50, naive_debt=150)
    assert out["naive_leverage"] == 3.0 and out["naive_ok"] is False
    assert out["naive_flip_addback"] == 10.0
    assert "naive_flip_rent" not in out
    plain = finance.limit_test(1.0, 2.5, ebitda_value=50, debt=50, rent_deduction=5)
    assert not any(k.startswith("naive") for k in plain)


def test_limit_test_rejects_non_finite():
    for bad in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite"):
            finance.limit_test(1.0, 2.5, ebitda_value=50, debt=50, naive_debt=bad)
        with pytest.raises(ValueError, match="finite"):
            finance.limit_test(1.0, 2.5, ebitda_value=50, debt=50, naive_debt=150, rent_deduction=bad)
        with pytest.raises(ValueError, match="finite"):
            finance.limit_test(bad, 2.5)
