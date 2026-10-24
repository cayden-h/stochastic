"""The CSV loader is strict: a bad file raises with the row and column, and never half-loads."""
import itertools

import pytest

from app.db.loader import MAX_ROWS, LoaderError, parse_statement_csv

HEADER = "line,section,period,amount,unit,source_ref,is_total"


def ids():
    c = itertools.count(1)
    return lambda prefix: f"{prefix}_{next(c):03d}"


def load(text, company="Acme"):
    return parse_statement_csv(text, company, "d_x", ids())


def test_good_file_parses_amounts_and_totals():
    text = f"{HEADER}\nNet sales,income_statement,FY2025,\"1,500\",USD thousands,10-K p5,false\nTotal revenue,income_statement,FY2025,1500,USD thousands,,yes\n"
    lines = load(text)
    assert [l.amount for l in lines] == [1500.0, 1500.0]
    assert [l.is_total for l in lines] == [False, True]
    assert lines[0].company == "Acme" and lines[0].deal_id == "d_x"
    assert lines[0].source_ref == "10-K p5" and lines[1].source_ref == ""
    assert lines[0].covenant_tag == "na"


def test_parentheses_mean_negative():
    lines = load(f"{HEADER}\nLoss,income_statement,FY2025,\"(1,234)\",USD,,\n")
    assert lines[0].amount == -1234.0
    assert lines[0].is_total is False


def test_missing_column_names_it():
    with pytest.raises(LoaderError, match="amount"):
        load("line,section,period,unit,source_ref,is_total\nx,income_statement,FY,USD,,\n")


def test_bad_section_names_row_3():
    text = f"{HEADER}\na,income_statement,FY,1,USD,,\nb,ledger,FY,1,USD,,\n"
    with pytest.raises(LoaderError, match=r"row 3.*section"):
        load(text)


def test_unknown_unit_raises():
    with pytest.raises(LoaderError, match=r"row 2.*unit"):
        load(f"{HEADER}\na,income_statement,FY,1,furlongs,,\n")


def test_is_total_maybe_raises():
    with pytest.raises(LoaderError, match=r"row 2.*is_total"):
        load(f"{HEADER}\na,income_statement,FY,1,USD,,maybe\n")


@pytest.mark.parametrize("bad", ["NaN", "inf", "-inf", "abc", ""])
def test_bad_amount_raises(bad):
    with pytest.raises(LoaderError, match=r"row 2.*amount"):
        load(f"{HEADER}\na,income_statement,FY,{bad},USD,,\n")


def test_too_many_rows_raises():
    rows = "\n".join("a,income_statement,FY,1,USD,," for _ in range(MAX_ROWS + 1))
    with pytest.raises(LoaderError, match="2000"):
        load(f"{HEADER}\n{rows}\n")


def test_exactly_max_rows_loads():
    rows = "\n".join("a,income_statement,FY,1,USD,," for _ in range(MAX_ROWS))
    assert len(load(f"{HEADER}\n{rows}\n")) == MAX_ROWS


def test_zero_rows_raises():
    with pytest.raises(LoaderError, match="no data rows"):
        load(f"{HEADER}\n")


def test_covenant_tag_loan_raises_and_debt_accepted():
    with pytest.raises(LoaderError, match=r"row 2.*covenant_tag"):
        load(f"{HEADER},covenant_tag\na,balance_sheet,FY,1,USD,,,loan\n")
    assert load(f"{HEADER},covenant_tag\na,balance_sheet,FY,1,USD,,,debt\n")[0].covenant_tag == "debt"


def test_long_line_and_empty_line_raise():
    with pytest.raises(LoaderError, match=r"row 2.*line"):
        load(f"{HEADER}\n{'x' * 201},income_statement,FY,1,USD,,\n")
    with pytest.raises(LoaderError, match=r"row 2.*line"):
        load(f"{HEADER}\n  ,income_statement,FY,1,USD,,\n")


def test_bad_file_assigns_no_ids():
    nxt = ids()
    text = f"{HEADER}\na,income_statement,FY,1,USD,,\nb,income_statement,FY,oops,USD,,\n"
    with pytest.raises(LoaderError):
        parse_statement_csv(text, "Acme", "d_x", nxt)
    assert nxt("sl") == "sl_001"


def test_extra_columns_ignored_and_short_row_raises():
    assert len(load(f"{HEADER},notes\na,income_statement,FY,1,USD,,,hello\n")) == 1
    with pytest.raises(LoaderError, match="row 2"):
        load(f"{HEADER}\na,income_statement\n")
