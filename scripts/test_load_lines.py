"""Tests for scripts/load_lines.py.

    backend/.venv/bin/python -m pytest -q scripts/test_load_lines.py

The QuickBooks expectations come from the QuickBooks Online test-drive company's own Balance Sheet
report, as of 2026-10-24, read on screen on the same day as the exports in samples/qbo/.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "backend")]

from app.db.memory import MemoryStore  # noqa: E402
from load_lines import FILES, load_lines, load_trial_balance  # noqa: E402

QBO = HERE / "samples" / "qbo"


def _by_name(lines):
    return {sl.line: sl for sl in lines}


def _write(path: Path, rows: list[list[str]]) -> Path:
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    return path


def test_real_quickbooks_export_matches_its_own_balance_sheet():
    pytest.importorskip("openpyxl")
    lines, warns = load_trial_balance(QBO / "trial_balance.xlsx", "d", MemoryStore(), QBO / "account_list.xlsx")
    got = _by_name(lines)
    assert got["Total Assets"].amount == 23436.29
    assert got["Total Liabilities"].amount == 31131.33
    assert got["Net Income"].amount == 1642.46
    assert got["Total Stockholders' Equity"].amount == -7695.04
    assert got["Total Liabilities and Stockholders' Equity"].amount == 23436.29
    assert lines[0].company == "Craig's Design and Landscaping Services"
    assert lines[0].period == "2026-10-24"
    assert "accrual basis" in lines[0].source_ref
    assert got["Truck:Original Cost"].section == "balance_sheet"
    assert got["Discounts given"].amount == -89.5  # a debit on an income account is a contra revenue
    assert any("depreciation" in w for w in warns)


def test_real_quickbooks_export_without_account_list_is_refused():
    pytest.importorskip("openpyxl")
    with pytest.raises(ValueError, match="Account List"):
        load_trial_balance(QBO / "trial_balance.xlsx", "d", MemoryStore())


def test_account_missing_from_the_list_is_named(tmp_path):
    rows = list(csv.reader(open(QBO / "nuaire_account_list.csv")))
    short = _write(tmp_path / "list.csv", [r for r in rows if r[0] != "Vehicles"])
    with pytest.raises(ValueError, match="Vehicles"):
        load_trial_balance(QBO / "nuaire_trial_balance.csv", "d", MemoryStore(), short)


def test_nuaire_sample_ties_to_the_audited_statements():
    lines, _ = load_trial_balance(QBO / "nuaire_trial_balance.csv", "d", MemoryStore(), QBO / "nuaire_account_list.csv")
    got = _by_name(lines)
    # Ex 99.1, Nu Aire audited statements, year ended 2024-09-30
    assert got["Net Income"].amount == 5438271
    assert got["Total Assets"].amount == 47978181
    assert got["Total Liabilities"].amount == 15895990
    assert got["Total Stockholders' Equity"].amount == 32082191
    assert got["Less: Accumulated Depreciation"].amount == -18856875
    assert got["Interest Income - Net"].amount == 513770


def test_unbalanced_file_is_refused(tmp_path):
    rows = list(csv.reader(open(QBO / "nuaire_trial_balance.csv")))
    rows = [[r[0], "13455975.00", r[2]] if r and r[0] == "Cash and Cash Equivalents" else r for r in rows]
    bad = _write(tmp_path / "tb.csv", [r for r in rows if not r or r[0] != "TOTAL"])
    with pytest.raises(ValueError, match="do not balance"):
        load_trial_balance(bad, "d", MemoryStore(), QBO / "nuaire_account_list.csv")


def test_numbered_accounts_load_without_a_list_and_derive_interest_tax_and_da(tmp_path):
    tb = _write(tmp_path / "tb.csv", [
        ["Acme Co"], ["Trial Balance"], ["As of December 31, 2025"], [],
        ["Account Name", "Debit", "Credit"],
        ["1000 Checking", "500.00", ""], ["2000 Bank Loan", "", "300.00"], ["3000 Retained Earnings", "", "100.00"],
        ["4000 Sales", "", "1,000.00"], ["6000 Wages", "700.00", ""], ["6100 Depreciation", "50.00", ""],
        ["8000 Interest Expense", "100.00", ""], ["9000 Income Tax Expense", "50.00", ""],
        ["TOTAL", "$1,400.00", "$1,400.00"], [], ["Cash Basis Monday"],
    ])
    lines, warns = load_trial_balance(tb, "d", MemoryStore())
    got = _by_name(lines)
    assert got["Net Income"].amount == 100.0
    assert got["Depreciation and Amortization"].amount == 50.0 and got["Depreciation and Amortization"].section == "cash_flow"
    assert got["Interest Expense"].amount == 100.0  # the account's own name already matches, so nothing is derived
    assert "Interest expense" not in got
    assert got["Total Assets"].amount == got["Total Liabilities and Stockholders' Equity"].amount == 500.0
    assert any("cash basis" in w for w in warns)


def test_total_row_that_disagrees_is_refused(tmp_path):
    tb = _write(tmp_path / "tb.csv", [
        ["Acme Co"], ["Trial Balance"], ["As of Dec 31, 2025"], [], ["Account Name", "Debit", "Credit"],
        ["1000 Checking", "100.00", ""], ["3000 Equity", "", "100.00"], ["TOTAL", "100.00", "999.00"],
    ])
    with pytest.raises(ValueError, match="TOTAL row"):
        load_trial_balance(tb, "d", MemoryStore())


# Unverified layouts. Each file below is our own guess at the system's export, built for this test with the
# same tiny books (net income 100, total assets 500). Passing shows the code path runs, not that real exports load.
BOOKS = [("1000", "Cash", "Asset", 500), ("2000", "Bank Loan", "Liability", -300), ("3000", "Retained Earnings", "Equity", -100),
         ("4000", "Sales", "Income", -1000), ("6000", "Wages", "Expense", 700), ("6100", "Depreciation Expense", "Expense", 200)]


def _dc(v):
    return (f"{v:.2f}", "") if v >= 0 else ("", f"{-v:.2f}")


UNVERIFIED = {
    "NetSuite": [["Acme Co"], ["Trial Balance"], ["As of Sep 30, 2024"], [], ["Account", "Debit", "Credit"]]
    + [[f"{n} {a}", *_dc(v)] for n, a, t, v in BOOKS] + [["Total", "1400.00", "1400.00"]],
    "Sage Intacct": [["Acme Co"], ["Trial Balance"], ["Period ending 09/30/2024"], ["Accrual basis"],
                     ["Account No.", "Account Title", "Beginning Balance", "Debits", "Credits", "Ending Balance"]]
    + [[n, a, "0", "0", "0", f"{v:.2f}"] for n, a, t, v in BOOKS],
    "Microsoft Dynamics 365 Business Central": [["Acme Co"], ["Trial Balance"], ["Period: 9/30/2024"],
                                                ["No.", "Name", "Net Change Debit", "Net Change Credit", "Balance Debit", "Balance Credit"]]
    + [[n, a, "", "", *_dc(v)] for n, a, t, v in BOOKS],
    "Microsoft Dynamics 365 Finance": [["Acme Co"], ["Trial balance"], ["As of 2024-09-30"],
                                       ["Main account", "Name", "Main account type", "Opening balance", "Debit", "Credit", "Closing balance"]]
    + [[n, a, t, "0", "0", "0", f"{v:.2f}"] for n, a, t, v in BOOKS],
    "Epicor": [["Acme Co"], ["GL Trial Balance"], ["Fiscal period ending Sep 2024"],
               ["GL Account", "Description", "Beginning Balance", "Debit", "Credit", "Ending Balance"]]
    + [[f"{n}-00", a, "0", "0", "0", f"{v:.2f}" if v >= 0 else f"{-v:.2f}-"] for n, a, t, v in BOOKS],
    "Infor": [["Acme Co"], ["Trial Balance"], ["As of 30 Sep 2024"],
              ["Account", "Description", "Account Type", "Beginning Balance", "Debits", "Credits", "Ending Balance"]]
    + [[n, a, t, "0", "0", "0", f"({-v:.2f})" if v < 0 else f"{v:.2f}"] for n, a, t, v in BOOKS],
}


@pytest.mark.parametrize("system", list(UNVERIFIED))
def test_unverified_layouts_run_on_our_own_sample(system, tmp_path):
    lines, warns = load_trial_balance(_write(tmp_path / "tb.csv", UNVERIFIED[system]), "d", MemoryStore())
    got = _by_name(lines)
    assert lines[0].source_ref.startswith(system) and "(layout unverified)" in lines[0].source_ref
    assert any("unverified" in w for w in warns)
    assert lines[0].company == "Acme Co" and lines[0].period == "2024-09-30"
    assert got["Net Income"].amount == 100.0
    assert got["Total Assets"].amount == got["Total Liabilities and Stockholders' Equity"].amount == 500.0
    assert got["Depreciation and Amortization"].amount == 200.0


@pytest.mark.skipif(not all(p.exists() for p in FILES.values()), reason="run `load_lines.py export` first; data/ is git-ignored")
def test_statement_line_csvs_round_trip_with_the_fixture():
    from app.db.fixtures.kewaunee import build_lines
    store = MemoryStore()
    loaded = [sl for p in FILES.values() for sl in load_lines(p, "d_kequ_nuaire", store)]
    fixture = build_lines(MemoryStore())
    assert [s.model_dump(exclude={"id"}) for s in loaded] == [s.model_dump(exclude={"id"}) for s in fixture]
