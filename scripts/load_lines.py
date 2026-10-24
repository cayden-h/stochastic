"""Read and write the input files: one file of statement lines per company.

    backend/.venv/bin/python scripts/load_lines.py export   # fixture -> data/kewaunee_lines.csv, data/nuaire_lines.csv
    backend/.venv/bin/python scripts/load_lines.py check    # reload both CSVs and compare them with the fixture
    backend/.venv/bin/python scripts/load_lines.py tb <trial balance> [<account list>]

Statement-line CSV columns: company, line, section, period, amount, unit, source_ref, is_total, note (note may be blank).
Row order is kept, because the Mapper and the console show lines in filing order.
`load_lines(path, deal_id, store)` is what the fixture and `POST /deals` call to turn a file into SourceLine rows.

`load_lines` also reads a trial balance exported from an accounting system, the input for a private company
with no filings. Each system's layout is a profile in PROFILES, matched by the file's header row.
Only the QuickBooks Online profile was checked against real exports (the QuickBooks Online test-drive company,
2026-10-24, samples in `scripts/samples/qbo/`). The NetSuite, Sage Intacct, Microsoft Dynamics 365, Epicor,
and Infor profiles are written from how those reports are usually laid out and were never run on a real export.
Every line loaded through an unverified profile says so in its source_ref.
"""
from __future__ import annotations

import calendar
import csv
import re
import sys
import warnings
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.models import SourceLine  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402

COLUMNS = ["company", "line", "section", "period", "amount", "unit", "source_ref", "is_total", "note"]
FILES = {"Kewaunee": ROOT / "data" / "kewaunee_lines.csv", "Nu Aire": ROOT / "data" / "nuaire_lines.csv"}


def load_lines(path: Path, deal_id: str, store: MemoryStore, account_list: Path | None = None) -> list[SourceLine]:
    """Turn one file into SourceLine rows. Raises ValueError with the row number on a bad row."""
    path = Path(path)
    if path.suffix.lower() == ".xlsx" or is_trial_balance(path):
        lines, notes = load_trial_balance(path, deal_id, store, account_list)
        for n in notes:
            warnings.warn(f"{path.name}: {n}", stacklevel=2)
        return lines
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        missing = set(COLUMNS[:-1]) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
        lines = []
        for n, row in enumerate(reader, start=2):
            try:
                lines.append(SourceLine(
                    id=store.next_id("sl"), deal_id=deal_id, company=row["company"], line=row["line"],
                    section=row["section"], period=row["period"], amount=float(row["amount"]),
                    unit=row["unit"], source_ref=row["source_ref"],
                    is_total=row["is_total"].strip().lower() in ("true", "1", "yes"),
                    note=(row.get("note") or "").strip() or None))
            except Exception as exc:
                raise ValueError(f"{path.name} row {n}: {exc}") from exc
    return lines


# ---- trial balance exports ----

@dataclass(frozen=True)
class Profile:
    """Where one system's trial balance export puts each field. Header names are matched lowercased,
    with dots and extra spaces removed. Amounts come from the first group present: an ending balance split
    into debit and credit, a signed ending balance (debit positive), or plain Debit and Credit columns."""
    name: str
    verified: bool
    number: tuple[str, ...] = ()
    account: tuple[str, ...] = ()
    type: tuple[str, ...] = ()
    debit: tuple[str, ...] = ()
    credit: tuple[str, ...] = ()
    balance: tuple[str, ...] = ()
    balance_debit: tuple[str, ...] = ()
    balance_credit: tuple[str, ...] = ()


# Checked in order; the first profile whose required headers are all present wins.
PROFILES = [
    Profile("QuickBooks Online", True, account=("account name",), debit=("debit",), credit=("credit",)),
    Profile("Microsoft Dynamics 365 Business Central", False, number=("no",), account=("name",),
            type=("account type", "income/balance"), balance_debit=("balance debit", "balance at date debit"),
            balance_credit=("balance credit", "balance at date credit")),
    Profile("Microsoft Dynamics 365 Finance", False, number=("main account",), account=("name",),
            type=("main account type", "account type"), balance=("closing balance", "ending balance")),
    Profile("Sage Intacct", False, number=("account no", "account number"), account=("account title",),
            type=("account type", "normal balance"), balance=("ending balance",),
            debit=("debits", "debit"), credit=("credits", "credit")),
    Profile("Epicor", False, number=("gl account",), account=("description", "account description"),
            type=("account type", "category"), balance=("ending balance", "end balance")),
    Profile("Infor", False, number=("account",), account=("description", "account description"),
            type=("account type",), balance=("ending balance", "closing balance")),
    Profile("NetSuite", False, account=("account",), type=("account type", "type"),
            debit=("debit", "amount (debit)"), credit=("credit", "amount (credit)")),
]

# kind -> (section, sign). sign=+1 means the normal balance is a debit, -1 a credit.
# Amounts are stored the way statements show them: expenses and liabilities positive, contra accounts negative.
KINDS = {
    "asset": ("balance_sheet", +1), "liability": ("balance_sheet", -1), "equity": ("balance_sheet", -1),
    "revenue": ("income_statement", -1), "expense": ("income_statement", +1),
    "other income": ("income_statement", -1), "other expense": ("income_statement", +1),
}
# Account type words, checked in this order. The QuickBooks Online spellings are verified from its Account List
# export; the NetSuite, Dynamics, Epicor, and Infor spellings are inferred.
TYPE_WORDS = [
    ("bank", "asset"), ("cash", "asset"), ("accounts receivable", "asset"), ("unbilled receivable", "asset"),
    ("other current asset", "asset"), ("fixed asset", "asset"), ("other asset", "asset"), ("asset", "asset"),
    ("accounts payable", "liability"), ("credit card", "liability"), ("deferred revenue", "liability"),
    ("other current liabilit", "liability"), ("long term liabilit", "liability"), ("liabilit", "liability"),
    ("equity", "equity"), ("capital", "equity"),
    ("other income", "other income"), ("income", "revenue"), ("revenue", "revenue"), ("sales", "revenue"),
    ("cost of goods sold", "expense"), ("cost of sales", "expense"),
    ("other expense", "other expense"), ("expense", "expense"),
]
# First digit of an account number, the usual chart-of-accounts convention, when no type is given.
NUMBER_KINDS = {"1": "asset", "2": "liability", "3": "equity", "4": "revenue", "5": "expense",
                "6": "expense", "7": "other income", "8": "other expense", "9": "other expense"}
ACCOUNT_NUMBER = re.compile(r"^\s*(\d[\d\-.]{2,})[\s\-:.]+(.+?)\s*$")
NUMBER_ONLY = re.compile(r"^\s*\d[\d\-.]*\s*$")
# Detail types (or account names) that the EBITDA tool needs as named lines.
DA_DETAIL = re.compile(r"depreciation|amortization", re.I)
INTEREST_DETAIL = re.compile(r"interest paid|interest expense", re.I)
TAX_DETAIL = re.compile(r"income tax", re.I)
DATE_FORMATS = ("%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d/%m/%Y")
MONTH_FORMATS = ("%b %Y", "%B %Y", "%m/%Y")
DATE_TOKEN = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|[A-Za-z]{3,9}\.? \d{1,2},? \d{4}|\d{1,2} [A-Za-z]{3,9} \d{4}|"
                        r"[A-Za-z]{3,9} \d{4}|\d{1,2}/\d{4})")
REPORT_TITLES = ("trial balance", "detailed trial balance", "gl trial balance", "general ledger trial balance")
BLANK_KINDS = {"asset": 0.0, "liability": 0.0, "equity": 0.0}


def _rows(path: Path) -> list[list]:
    """All rows of a CSV or the first sheet of an .xlsx, as lists of cells (str, float, or None)."""
    if path.suffix.lower() == ".xlsx":
        try:
            import openpyxl
        except ImportError as exc:
            raise ValueError(f"{path.name}: .xlsx needs openpyxl, which the backend does not install; "
                             "save the export as CSV and load that instead") from exc
        ws = openpyxl.load_workbook(path, read_only=True).worksheets[0]
        return [list(r) for r in ws.iter_rows(values_only=True)]
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.reader(f))


def _cell(v) -> str:
    return "" if v is None else str(v).strip()


def _norm(v) -> str:
    return re.sub(r"\s+", " ", _cell(v).lower().replace(".", "")).strip()


def _money(v) -> float | None:
    """An amount cell as a number. None for an Excel formula, which exports leave uncomputed."""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("$", "").replace(",", "")
    if not s:
        return 0.0
    if s.startswith("="):
        return None
    if s.endswith("-"):  # some ERPs print a trailing minus
        s = "-" + s[:-1]
    neg = s.startswith("(") and s.endswith(")")
    return -float(s.strip("()")) if neg else float(s)


def _col(header: list[str], names: tuple[str, ...]) -> int | None:
    return next((header.index(n) for n in names if n in header), None)


def _match(header: list[str]) -> tuple[Profile, dict[str, int | None]] | None:
    for p in PROFILES:
        cols = {f: _col(header, getattr(p, f)) for f in
                ("number", "account", "type", "debit", "credit", "balance", "balance_debit", "balance_credit")}
        if p.number and cols["number"] is None:
            continue  # the number column is what tells look-alike layouts apart
        has_name = cols["account"] is not None or cols["number"] is not None
        has_amount = (cols["balance_debit"] is not None and cols["balance_credit"] is not None) \
            or cols["balance"] is not None or (cols["debit"] is not None and cols["credit"] is not None)
        if has_name and has_amount:
            return p, cols
    return None


def _header(rows: list[list]) -> tuple[int, Profile, dict[str, int | None]] | None:
    for i, r in enumerate(rows[:20]):
        found = _match([_norm(c) for c in r])
        if found:
            return (i, *found)
    return None


def is_trial_balance(path: Path) -> bool:
    try:
        return _header(_rows(Path(path))) is not None
    except (OSError, UnicodeDecodeError, ValueError):
        return False


def _parse_date(text: str) -> str | None:
    """The last date in a title such as 'As of Oct 24, 2026' or 'Period: Sep 2024' (month end), as ISO."""
    for token in reversed(DATE_TOKEN.findall(text)):
        token = token.replace(".", "").replace(" ,", ",")
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(token, fmt).date().isoformat()
            except ValueError:
                pass
        for fmt in MONTH_FORMATS:
            try:
                d = datetime.strptime(token, fmt).date()
                return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1]).isoformat()
            except ValueError:
                pass
    return None


def _account_types(path: Path) -> dict[str, tuple[str, str]]:
    """Account name -> (type, detail type), from a QuickBooks Online Account List export."""
    rows = _rows(path)
    hdr = next((i for i, r in enumerate(rows[:15]) if [_norm(c) for c in r[:2]] == ["account name", "type"]), None)
    if hdr is None:
        raise ValueError(f"{path.name}: no 'Account Name, Type' header, so this is not a QuickBooks Account List export")
    cols = [_norm(c) for c in rows[hdr]]
    detail = cols.index("detail type") if "detail type" in cols else None
    out = {}
    for r in rows[hdr + 1:]:
        name = _cell(r[0]) if r else ""
        if not name or name.upper() == "TOTAL":
            continue
        out[name] = (_cell(r[1]), _cell(r[detail]) if detail is not None and detail < len(r) else "")
    return out


def _kind_of_type(type_text: str) -> str | None:
    t = type_text.lower()
    return next((kind for word, kind in TYPE_WORDS if word in t), None)


def load_trial_balance(path: Path, deal_id: str, store: MemoryStore, account_list: Path | None = None,
                       period: str | None = None) -> tuple[list[SourceLine], list[str]]:
    """Turn a trial balance export into SourceLine rows, plus the derived lines the math tools need.

    Returns the lines and a list of warnings. Raises ValueError when the file does not balance,
    an account cannot be placed, or a numeric TOTAL row disagrees with the accounts.
    `period` (ISO date) is used when the title rows carry no date.
    """
    path = Path(path)
    rows = _rows(path)
    found = _header(rows)
    if found is None:
        raise ValueError(f"{path.name}: no header row this loader knows (see PROFILES)")
    hdr, profile, cols = found
    titles = [_cell(c) for r in rows[:hdr] for c in r if _cell(c)]
    dated = [t for t in titles if _parse_date(t)]
    period = (_parse_date(dated[0]) if dated else None) or period
    if period is None:
        raise ValueError(f"{path.name}: no date in the title rows; pass period=")
    others = [t for t in titles if t not in dated and _norm(t) not in REPORT_TITLES and ":" not in t]
    company = others[0] if others else path.stem
    types = _account_types(Path(account_list)) if account_list else {}

    warn: list[str] = []
    if not profile.verified:
        warn.append(f"the {profile.name} layout is unverified: it was written without a real export to check against")
    accounts, unknown = [], []
    debits = credits = 0.0
    total_row = None
    footer = []

    def get(r, field):
        i = cols[field]
        return r[i] if i is not None and i < len(r) else None

    for n, r in enumerate(rows[hdr + 1:], start=hdr + 2):
        first = _cell(get(r, "number")) if cols["number"] is not None else ""
        label_cell = _cell(get(r, "account"))
        name = f"{first} {label_cell}".strip()
        amount_cells = [_cell(get(r, f)) for f in ("debit", "credit", "balance", "balance_debit", "balance_credit")]
        if not name and not any(amount_cells):
            continue
        if total_row is not None or not any(amount_cells):
            if name:
                footer.append(name)  # footer text such as "Accrual Basis ...": no amount cells at all
            continue
        if re.match(r"^(grand )?total\b", name, re.I) or re.match(r"^(grand )?total\b", label_cell, re.I):
            total_row = (_money(get(r, "debit")), _money(get(r, "credit"))) if cols["debit"] is not None else (None, None)
            continue
        try:
            if cols["balance_debit"] is not None and cols["balance_credit"] is not None:
                dr, cr = _money(get(r, "balance_debit")), _money(get(r, "balance_credit"))
            elif cols["balance"] is not None:
                b = _money(get(r, "balance"))
                dr, cr = (b, 0.0) if b is None or b >= 0 else (0.0, -b)
            else:
                dr, cr = _money(get(r, "debit")), _money(get(r, "credit"))
        except ValueError as exc:
            raise ValueError(f"{path.name} row {n}: {exc}") from exc
        if dr is None or cr is None:
            raise ValueError(f"{path.name} row {n}: '{name}' holds a formula, not an amount")

        lookup = label_cell or name
        detail = ""
        kind = None
        number = first if cols["number"] is not None and NUMBER_ONLY.match(first) else None
        label = label_cell if number else name
        if lookup in types or name in types:
            type_text, detail = types.get(lookup) or types[name]
            kind = _kind_of_type(type_text)
            if kind is None:
                raise ValueError(f"{path.name} row {n}: '{lookup}' has type '{type_text}', which the loader does not know")
        elif cols["type"] is not None and _cell(get(r, "type")):
            kind = _kind_of_type(_cell(get(r, "type")))
        if kind is None and number is None and (m := ACCOUNT_NUMBER.match(name)):
            number, label = m.groups()
        if kind is None and number:
            kind = NUMBER_KINDS.get(number[0])
        if kind is None:
            unknown.append(name)
            continue
        debits += dr
        credits += cr
        accounts.append((label, kind, dr - cr, detail or label))

    if unknown:
        hint = "it is not in the account list" if types else "it has no type or account number; pass the Account List export"
        raise ValueError(f"{path.name}: cannot place {len(unknown)} account(s), because {hint}: {', '.join(unknown[:5])}")
    if abs(debits - credits) > 0.5:
        raise ValueError(f"{path.name}: debits {debits:,.2f} and credits {credits:,.2f} do not balance")
    if total_row and None not in total_row and (abs(total_row[0] - debits) > 0.5 or abs(total_row[1] - credits) > 0.5):
        raise ValueError(f"{path.name}: TOTAL row {total_row} disagrees with the accounts")
    found_basis = next((m for f in footer + titles if (m := re.search(r"\b(accrual|cash) basis\b", f, re.I))), None)
    basis = found_basis.group(1).lower() if found_basis else None
    if basis == "cash":
        warn.append("the report is on a cash basis; covenant tests are normally on accrual figures")
    elif basis is None:
        warn.append("the file does not say accrual or cash basis")

    ref = (f"{profile.name} trial balance export {path.name}"
           + (f", {dated[0]}" if dated else f", period {period}") + (f", {basis} basis" if basis else "")
           + ("" if profile.verified else " (layout unverified)"))
    lines: list[SourceLine] = []

    def add(line, section, amount, is_total=False, note=None):
        lines.append(SourceLine(id=store.next_id("sl"), deal_id=deal_id, company=company, line=line,
                                section=section, period=period, amount=round(amount, 2) + 0.0, unit="USD",
                                source_ref=ref, is_total=is_total, note=note))

    sums = dict(BLANK_KINDS)
    net_income = da = interest = tax = 0.0
    names = {label.strip().lower() for label, *_ in accounts}
    for label, kind, net, detail in accounts:
        section, sign = KINDS[kind]
        amount = net * sign
        add(label, section, amount, note=f"{profile.name} {kind} account" + (f", detail type {detail}" if detail != label else ""))
        if kind in sums:
            sums[kind] += amount
            continue
        net_income -= net  # credits raise income, debits lower it
        if kind in ("expense", "other expense"):
            if DA_DETAIL.search(detail):
                da += amount
            elif INTEREST_DETAIL.search(detail):
                interest += amount
            elif TAX_DETAIL.search(detail):
                tax += amount

    derived = "Derived by the loader from the trial balance accounts."
    add("Net Income", "income_statement", net_income, True, derived)
    # The EBITDA tool reads interest and taxes by line name. Add them as totals (so consolidation does not
    # count them twice) unless an account already carries the name.
    if interest and "interest expense" not in names:
        add("Interest expense", "income_statement", interest, True, "Sum of the interest expense accounts. " + derived)
    if tax and "provision for income taxes" not in names and "income tax expense" not in names:
        add("Provision for income taxes", "income_statement", tax, True, "Sum of the income tax accounts. " + derived)
    add("Current year earnings", "balance_sheet", net_income, False,
        "A trial balance before close keeps the year's income in the income accounts. " + derived)
    add("Total Assets", "balance_sheet", sums["asset"], True, derived)
    add("Total Liabilities", "balance_sheet", sums["liability"], True, derived)
    add("Total Stockholders' Equity", "balance_sheet", sums["equity"] + net_income, True, derived)
    add("Total Liabilities and Stockholders' Equity", "balance_sheet",
        sums["liability"] + sums["equity"] + net_income, True, derived)
    if da:
        add("Depreciation and Amortization", "cash_flow", da, False,
            "Sum of the depreciation and amortization expense accounts. " + derived)
    else:
        warn.append("no depreciation or amortization expense, so EBITDA will not add back D&A")
    if not types and cols["type"] is None and accounts:
        warn.append("no account types given; accounts were placed by account number")
    return lines, warn


# ---- statement-line CSVs ----

def write_lines(path: Path, lines: list[SourceLine]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for sl in lines:
            row = sl.model_dump(include=set(COLUMNS))
            row["amount"] = str(int(sl.amount)) if sl.amount == int(sl.amount) else repr(sl.amount)
            row["note"] = sl.note or ""
            w.writerow(row)


def _fixture_lines() -> list[SourceLine]:
    from app.db.fixtures.kewaunee import build_lines
    return build_lines(MemoryStore())


def main(argv: list[str]) -> int:
    from app.db.fixtures.kewaunee import DEAL_ID
    cmd = argv[1] if len(argv) > 1 else "check"
    if cmd == "export":
        fixture = _fixture_lines()
        for company, path in FILES.items():
            rows = [sl for sl in fixture if sl.company == company]
            write_lines(path, rows)
            print(f"{path.relative_to(ROOT)}: {len(rows)} lines")
        return 0
    if cmd == "check":
        fixture = _fixture_lines()
        store = MemoryStore()
        loaded = [sl for path in FILES.values() for sl in load_lines(path, DEAL_ID, store)]
        strip = lambda sl: sl.model_dump(exclude={"id"})  # noqa: E731
        if [strip(s) for s in loaded] != [strip(s) for s in fixture]:
            for a, b in zip(loaded, fixture):
                if strip(a) != strip(b):
                    print(f"differs: {a.company} / {a.line}")
            print(f"FAIL: {len(loaded)} loaded, {len(fixture)} in the fixture")
            return 1
        print(f"OK: {len(loaded)} lines round-trip with the fixture")
        return 0
    if cmd == "tb" and len(argv) > 2:
        accounts = Path(argv[3]) if len(argv) > 3 else None
        lines, notes = load_trial_balance(Path(argv[2]), DEAL_ID, MemoryStore(), accounts)
        print(f"company: {lines[0].company}, period: {lines[0].period}, source: {lines[0].source_ref}")
        for sl in lines:
            print(f"{sl.section:17} {sl.line:66} {sl.amount:>16,.2f}{'  total' if sl.is_total else ''}")
        for n in notes:
            print(f"warning: {n}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
