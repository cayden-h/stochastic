"""Deterministic deal math. Pure functions, no side effects, no model.

Every public function returns a plain dict of outputs. The gateway wraps each call in a ToolRun with a run id,
so every number on screen traces to one call. Rules are in docs/STOCHASTIC.md section 11.
Owner: Tri (backend/app/tools/). Cayden wrote the first version so the agents had something to call.
"""
from __future__ import annotations

import math

from collections import OrderedDict

from app.core.models import Brief, Mapping, SourceLine

THOUSANDS = "USD thousands"


def to_thousands(amount: float, unit: str) -> float:
    """Convert an amount to USD thousands. Nu Aire files whole dollars, Kewaunee files thousands."""
    u = unit.strip().lower()
    if u in ("usd thousands", "thousands", "usd k", "k"):
        return float(amount)
    if u in ("usd", "dollars", "usd dollars", "$"):
        return float(amount) / 1000.0
    if u in ("usd millions", "millions", "mm"):
        return float(amount) * 1000.0
    raise ValueError(f"unknown unit '{unit}'")


def _key(section: str, line: str) -> str:
    return f"{section}:{line.strip().lower()}"


def consolidate(platform_lines: list[SourceLine], target_lines: list[SourceLine], mappings: list[Mapping]) -> dict:
    """Add the target's lines onto the platform's lines using the approved mappings.

    A target subtotal (is_total) is added only onto a platform subtotal, never onto a detail line, so nothing
    is counted twice. Unmapped target detail lines are reported, never silently dropped.
    Returns rows in platform order, each with platform, target, combined (USD thousands).
    """
    by_id = {line.id: line for line in target_lines}
    seen: dict[str, Mapping] = {}
    for m in mappings:  # one target line may land in one place only, or it would be counted twice
        if m.target_line_id in seen and m.target_line_id in by_id:
            t = by_id[m.target_line_id]
            raise ValueError(f"target line {t.line} is mapped twice ({seen[m.target_line_id].id}, {m.id})")
        seen[m.target_line_id] = m
    platform_rows: "OrderedDict[str, dict]" = OrderedDict()
    for p in platform_lines:
        k = _key(p.section, p.line)
        pv = to_thousands(p.amount, p.unit)
        if k in platform_rows:
            platform_rows[k]["platform"] += pv
        else:
            platform_rows[k] = {"line": p.line, "section": p.section, "platform": pv, "target": 0.0,
                                "is_total": p.is_total, "target_lines": []}
    unmapped: list[dict] = []
    skipped_totals: list[str] = []
    used: set[str] = set()
    for m in mappings:
        if m.flagged and not m.approved_by:
            raise ValueError(f"mapping {m.id} is flagged and not approved")
        t = by_id.get(m.target_line_id)
        if t is None:
            continue
        used.add(t.id)
        tv = to_thousands(t.amount, t.unit)
        if not m.platform_line:
            if not t.is_total:
                unmapped.append({"line": t.line, "amount": round(tv, 3)})
            continue
        k = _key(t.section, m.platform_line)
        row = platform_rows.get(k)
        if row is None:
            row = platform_rows[k] = {"line": m.platform_line, "section": t.section, "platform": 0.0,
                                      "target": 0.0, "is_total": t.is_total, "target_lines": []}
        if t.is_total and not row["is_total"]:
            skipped_totals.append(t.line)  # a subtotal onto a detail line would double count
            continue
        row["target"] += tv
        row["target_lines"].append(t.line)
    for t in target_lines:
        if t.id not in used and not t.is_total:
            unmapped.append({"line": t.line, "amount": round(to_thousands(t.amount, t.unit), 3)})
    rows = []
    for r in platform_rows.values():
        r["platform"] = round(r["platform"], 3)
        r["target"] = round(r["target"], 3)
        r["combined"] = round(r["platform"] + r["target"], 3)
        rows.append(r)
    return {"rows": rows, "unmapped_target_lines": unmapped, "skipped_target_totals": skipped_totals,
            "unit": THOUSANDS}


def _find(rows: list[dict], section: str, names: tuple[str, ...]) -> dict | None:
    for r in rows:
        if r["section"] == section and r["line"].strip().lower() in names:
            return r
    return None


def tie_out(rows: list[dict], tolerance: float = 0.5) -> dict:
    """Every row's parts must add to its combined figure. If the balance sheet totals are present,
    combined total assets must equal combined total liabilities and equity."""
    bad_rows = [r["line"] for r in rows if abs((r["platform"] + r["target"]) - r["combined"]) > tolerance]
    assets = _find(rows, "balance_sheet", ("total assets",))
    liab_eq = _find(rows, "balance_sheet", ("total liabilities and stockholders' equity",
                                             "total liabilities and stockholders’ equity",
                                             "total liabilities and shareholders' equity",
                                             "total liabilities and shareholders’ equity",
                                             "total liabilities and equity"))
    balance_ok = None
    balance = None
    missing = []
    if any(r["section"] == "balance_sheet" for r in rows):
        # a balance sheet with no total to compare must fail, not pass by default
        if not assets:
            missing.append("total assets")
        if not liab_eq:
            missing.append("total liabilities and equity")
    if assets and liab_eq:
        balance = {"total_assets": assets["combined"], "total_liabilities_and_equity": liab_eq["combined"]}
        balance_ok = abs(assets["combined"] - liab_eq["combined"]) <= tolerance
    ok = not bad_rows and (balance_ok is not False) and not missing
    return {"ok": ok, "bad_rows": bad_rows, "balance_sheet_balances": balance_ok, "balance": balance,
            "rows_checked": len(rows), "missing_totals": missing}


def _matched(lines: list[SourceLine], names: tuple[str, ...], section: str) -> list[str]:
    return [l.line for l in lines if l.section == section and l.line.strip().lower() in names]


def _pick(lines: list[SourceLine], names: tuple[str, ...], section: str) -> float:
    total = 0.0
    for line in lines:
        if line.section == section and line.line.strip().lower() in names:
            total += to_thousands(line.amount, line.unit)
    return total


NET_INCOME = ("net earnings", "net income", "net income (loss)", "net earnings (loss)")
INTEREST = ("interest expense", "interest expense, net")
INTEREST_INCOME = ("interest income", "interest income - net", "interest income, net")
TAXES = ("income tax (benefit) expense", "income tax expense", "provision for income taxes",
         "income tax expense (benefit)", "income taxes")
DA = ("depreciation and amortization", "depreciation", "amortization")


def ebitda(platform_lines: list[SourceLine], target_lines: list[SourceLine], brief: Brief) -> dict:
    """Covenant EBITDA, built the way the agreement defines it.

    Base, per company: net income plus interest expense less interest income plus income taxes plus depreciation
    and amortization (Ex 10.1 Addendum I).
    Then each add-back from the brief is applied up to its cap, and each deduction is subtracted.
    The brief holds the agreement's own definitions, so this function never guesses them.
    Expense lines are stored as positive amounts; a tax benefit is stored as a negative amount.
    """
    parts = []
    base = 0.0
    for company, lines in (("platform", platform_lines), ("target", target_lines)):
        for label, names, section in (("net income", NET_INCOME, "income_statement"),
                                      ("depreciation and amortization", DA, "cash_flow")):
            if not _matched(lines, names, section):  # these two must exist; a missing one would silently understate EBITDA
                raise ValueError(f"{company}: no {label} line found (looked for: {', '.join(names)})")
        used = (_matched(lines, NET_INCOME, "income_statement") + _matched(lines, INTEREST, "income_statement")
                + _matched(lines, INTEREST_INCOME, "income_statement") + _matched(lines, TAXES, "income_statement")
                + _matched(lines, DA, "cash_flow"))
        ni = _pick(lines, NET_INCOME, "income_statement")
        it = _pick(lines, INTEREST, "income_statement")
        ii = _pick(lines, INTEREST_INCOME, "income_statement")
        tx = _pick(lines, TAXES, "income_statement")
        da = _pick(lines, DA, "cash_flow")
        sub = ni + it - ii + tx + da
        parts.append({"company": company, "net_income": round(ni, 3), "interest_expense": round(it, 3),
                      "interest_income": round(ii, 3), "income_taxes": round(tx, 3), "depreciation_amortization": round(da, 3),
                      "subtotal": round(sub, 3), "lines_used": used})
        base += sub
    addbacks = []
    total_add = 0.0
    for a in brief.ebitda_addbacks:
        applied = min(a.amount, a.cap) if a.cap is not None else a.amount
        addbacks.append({"name": a.name, "amount": a.amount, "cap": a.cap, "applied": round(applied, 3),
                         "source_ref": a.source_ref, "inferred": a.inferred})
        total_add += applied
    deductions = []
    total_ded = 0.0
    for d in brief.ebitda_deductions:
        deductions.append({"name": d.name, "amount": d.amount, "source_ref": d.source_ref, "inferred": d.inferred})
        total_ded += d.amount
    value = base + total_add - total_ded
    return {"ebitda": round(value, 3), "base": round(base, 3), "addbacks_total": round(total_add, 3),
            "deductions_total": round(total_ded, 3), "parts": parts, "addbacks": addbacks,
            "deductions": deductions, "unit": THOUSANDS}


# Borrowed money must be tagged debt, not_debt, or unclear. An 'na' on one of these names is a missed tag.
BORROWING_WORDS = ("borrowing", "loan", "note payable", "notes payable", "debt", "credit facility", "revolver",
                   "term loan", "financing liability", "finance lease", "financing lease")
# Names that mark an asset, reserve, or cost rather than borrowed money, so a borrowing word in them is not a missed tag.
NOT_BORROWING_WORDS = ("receivable", "reserve", "allowance", "issuance cost")


def covenant_debt(platform_lines: list[SourceLine], target_lines: list[SourceLine], brief: Brief,
                  naive: bool = False) -> dict:
    """The covenant's debt figure, from the covenant tags on the balance sheet lines.

    Lines tagged `debt` count. Lines tagged `not_debt` are listed as excluded with their note.
    A line tagged `unclear` stops the calculation, unless naive=True, which counts it: that is what a
    careless reading of the balance sheet gives, and it is reported as naive.
    The borrowing check on `na` lines is a name heuristic that fails loudly, and the fix for a false positive
    is to tag the line `not_debt` with a note.
    """
    included = []
    excluded = []
    unclear = []
    total = 0.0
    for line in list(platform_lines) + list(target_lines):
        if line.section != "balance_sheet":
            continue
        amt = to_thousands(line.amount, line.unit)
        name = line.line.lower()
        if (line.covenant_tag == "na" and any(w in name for w in BORROWING_WORDS)
                and not any(w in name for w in NOT_BORROWING_WORDS)):
            raise ValueError(f"covenant tag is 'na' on a borrowing-like line: {line.line} ({line.company})")
        if line.covenant_tag == "debt":
            included.append({"line": line.line, "company": line.company, "amount": round(amt, 3)})
            total += amt
        elif line.covenant_tag == "unclear":
            if naive:
                included.append({"line": line.line, "company": line.company, "amount": round(amt, 3),
                                 "note": "naive: unclear line counted as debt"})
                total += amt
            else:
                unclear.append(line.line)
        elif line.covenant_tag == "not_debt":
            excluded.append({"line": line.line, "company": line.company, "amount": round(amt, 3),
                             "note": line.covenant_note or ""})
    if unclear and not naive:
        raise ValueError(f"covenant tag is unclear for: {', '.join(unclear)}")
    return {"debt": round(total, 3), "term": brief.debt_term, "included": included, "excluded": excluded,
            "naive": naive, "unit": THOUSANDS}


def leverage(debt: float, ebitda_value: float) -> dict:
    if not (math.isfinite(debt) and math.isfinite(ebitda_value)):
        raise ValueError("debt and ebitda must be finite numbers")
    if ebitda_value <= 0:
        raise ValueError("ebitda must be positive")
    return {"leverage": round(debt / ebitda_value, 3), "debt": round(debt, 3), "ebitda": round(ebitda_value, 3)}


def limit_test(leverage_value: float, limit: float, wording: str = "less than", ebitda_value: float | None = None,
               debt: float | None = None, naive_debt: float | None = None,
               rent_deduction: float | None = None) -> dict:
    """Test the ratio against the covenant. 'less than' means the ratio must be strictly below the limit.
    Debt capacity (room for the next deal) is reported when EBITDA and debt are given.

    Sensitivity, when naive_debt (the whole-line reading of debt) and EBITDA are given: the naive ratio, and
    naive_flip_addback, the EBITDA add-back at which the naive reading reaches the limit (positive means that much
    more EBITDA is needed; zero or negative means it already passes). With rent_deduction also given,
    naive_flip_rent is the rent deduction at which the naive reading reaches the limit."""
    given = [leverage_value, limit] + [v for v in (ebitda_value, debt, naive_debt, rent_deduction) if v is not None]
    if not all(math.isfinite(v) for v in given):
        raise ValueError("limit_test inputs must be finite numbers")

    def passes(ratio: float) -> bool:
        return ratio < limit if wording == "less than" else ratio <= limit

    ok = passes(leverage_value)
    out = {"ok": ok, "verdict": "ok" if ok else "over_limit", "leverage": round(leverage_value, 3), "limit": limit,
           "headroom_turns": round(limit - leverage_value, 3), "wording": wording}
    if ebitda_value is not None and debt is not None:
        out["debt_capacity"] = round(limit * ebitda_value - debt, 3)
    if naive_debt is not None and ebitda_value is not None:
        if ebitda_value <= 0:
            raise ValueError("ebitda must be positive")
        if limit <= 0:
            raise ValueError("limit must be positive")
        flip = round(naive_debt / limit - ebitda_value, 3)
        out.update({"naive_debt": round(naive_debt, 3), "naive_leverage": round(naive_debt / ebitda_value, 3),
                    "naive_ok": passes(naive_debt / ebitda_value), "naive_flip_addback": flip})
        if rent_deduction is not None:
            out["naive_flip_rent"] = round(rent_deduction - flip, 3)
    return out


TOOLS = {
    "consolidate": consolidate,
    "tie_out": tie_out,
    "ebitda": ebitda,
    "covenant_debt": covenant_debt,
    "leverage": leverage,
    "limit_test": limit_test,
}

TOOL_DESCRIPTIONS = {
    "consolidate": "Add the target's statement lines onto the platform's lines using the approved mappings. "
                   "No arguments. Returns rows with platform, target, combined, and the run id.",
    "tie_out": "Check that every row's parts add to its combined figure and that the combined balance sheet balances. "
               "Arguments: run_id (the consolidate run to check).",
    "ebitda": "Compute covenant EBITDA from the statement lines and the brief's add-backs and deductions. No arguments.",
    "covenant_debt": "Compute the covenant's debt figure from the covenant tags on balance sheet lines. "
                     "Arguments: naive (bool, default false) counts unclear lines as debt.",
    "leverage": "Divide debt by EBITDA. Arguments: debt_run_id and ebitda_run_id (preferred) or debt and ebitda values.",
    "limit_test": "Test leverage against the lender's limit from the brief. Arguments: leverage_run_id or leverage. "
                  "Optional sensitivity: naive_debt_run_id (a covenant_debt run with the whole-line reading) and "
                  "ebitda_run_id (its rent deduction) add naive_leverage, naive_ok, naive_flip_addback (the EBITDA "
                  "add-back at which the whole-line reading reaches the limit), and naive_flip_rent.",
}
