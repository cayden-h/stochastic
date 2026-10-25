"""Deterministic deal math. Pure functions, no side effects, no model.

Every public function returns a plain dict of outputs. The gateway wraps each call in a ToolRun with a run id,
so every number on screen traces to one call. Rules are in docs/STOCHASTIC.md section 11.
Owner: Tri (backend/app/tools/). Cayden wrote the first version so the agents had something to call.
"""
from __future__ import annotations

import math

from collections import OrderedDict

from app.core.models import Brief, Mapping, SourceLine
from app.tools.edits import (LIABILITIES_AND_EQUITY_TOTALS, active, apply_remap_edits, carry_amount_edits,
                             platform_line_for, remap_moves)

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


def _with_amount_edits(platform_lines: list[SourceLine], target_lines: list[SourceLine],
                       edits) -> tuple[list[SourceLine], list[SourceLine], list[str], dict]:
    """Apply the active amount edits across both companies' lines, carried by the income statement roll-up rule.
    Copies only; the inputs are never changed. The last item is {rollup, rollup_notes} for the run output."""
    edited, applied, rollup, notes = carry_amount_edits(list(platform_lines) + list(target_lines), edits)
    n = len(platform_lines)
    return edited[:n], edited[n:], applied, {"rollup": rollup, "rollup_notes": notes}


def _in_edit_order(edits, applied: set[str]) -> list[str]:
    return [e.id for e in active(edits) if e.id in applied]


def consolidate(platform_lines: list[SourceLine], target_lines: list[SourceLine], mappings: list[Mapping],
                edits=None) -> dict:
    """Add the target's lines onto the platform's lines using the approved mappings.

    A target subtotal (is_total) is added only onto a platform subtotal, never onto a detail line, so nothing
    is counted twice. Unmapped target detail lines are reported, never silently dropped.
    The deal's active edits are applied first: amount edits to both companies' lines, remap edits to the mappings.
    A remapped target line lands on the platform line's own section when the platform has a line of that name, and
    the target subtotals it fed move with it (the remap roll-up rule in app/tools/edits.py): each moved figure is
    listed under remap_rollup as {edit_id, line, section, delta}, where line is the platform subtotal row.
    Returns rows in platform order, each with platform, target, combined (USD thousands), and edits_applied.
    """
    platform_lines, target_lines, amount_ids, carried = _with_amount_edits(platform_lines, target_lines, edits)
    given = {id(m) for m in mappings}
    mappings, remap_ids = apply_remap_edits(mappings, target_lines, platform_lines, edits)
    remapped = {m.target_line_id for m in mappings if id(m) not in given}  # the copies a remap made
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
    landed: dict[str, str] = {}  # target subtotal id -> the platform subtotal row it was added to
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
        section = t.section
        if t.id in remapped:  # a remap may move the line across sections; it lands where the platform line is
            landing = platform_line_for(platform_lines, m.platform_line, t.section, m.platform_line_id)
            section = landing.section if landing else t.section
        k = _key(section, m.platform_line)
        row = platform_rows.get(k)
        if row is None:
            row = platform_rows[k] = {"line": m.platform_line, "section": section, "platform": 0.0,
                                      "target": 0.0, "is_total": t.is_total, "target_lines": []}
        if t.is_total and not row["is_total"]:
            skipped_totals.append(t.line)  # a subtotal onto a detail line would double count
            continue
        row["target"] += tv
        row["target_lines"].append(t.line)
        if t.is_total:
            landed[t.id] = k
    for t in target_lines:
        if t.id not in used and not t.is_total:
            unmapped.append({"line": t.line, "amount": round(to_thousands(t.amount, t.unit), 3)})
    remap_rollup = _carry_remaps(platform_rows, landed, target_lines, platform_lines,
                                 [m for m in mappings if m.target_line_id in remapped], edits)
    rows = []
    for r in platform_rows.values():
        r["platform"] = round(r["platform"], 3)
        r["target"] = round(r["target"], 3)
        r["combined"] = round(r["platform"] + r["target"], 3)
        rows.append(r)
    return {"rows": rows, "unmapped_target_lines": unmapped, "skipped_target_totals": skipped_totals,
            "unit": THOUSANDS, "edits_applied": _in_edit_order(edits, set(amount_ids) | set(remap_ids)), **carried,
            "remap_rollup": remap_rollup}


def _carry_remaps(platform_rows: "OrderedDict[str, dict]", landed: dict[str, str], target_lines: list[SourceLine],
                  platform_lines: list[SourceLine], remapped: list[Mapping], edits) -> list[dict]:
    """Move the target column of the platform subtotal rows by the remap roll-up rule (app/tools/edits.py).

    A moved line leaves each target subtotal it fed, on the row that subtotal landed on, and joins each platform
    subtotal its new platform line feeds, on rows a target subtotal landed on. The rows are changed in place.
    Returns {edit_id, line, section, delta} per moved row, in edit order then row order, without zero moves."""
    fed = set(landed.values())
    order = {k: n for n, k in enumerate(platform_rows)}
    out: list[dict] = []
    for move in remap_moves(target_lines, platform_lines, remapped, edits):
        v = to_thousands(move["line"].amount, move["line"].unit)
        deltas: dict[str, float] = {}
        for total, coef in move["old"]:
            if total.id in landed:
                deltas[landed[total.id]] = deltas.get(landed[total.id], 0.0) - coef * v
        for total, coef in move["new"]:
            k = _key(total.section, total.line)
            if k in fed:
                deltas[k] = deltas.get(k, 0.0) + coef * v
        for k in sorted(deltas, key=order.__getitem__):
            if round(deltas[k], 3) == 0:
                continue
            platform_rows[k]["target"] += deltas[k]
            out.append({"edit_id": move["edit_id"], "line": platform_rows[k]["line"],
                        "section": platform_rows[k]["section"], "delta": round(deltas[k], 3)})
    return out


def _find(rows: list[dict], section: str, names: tuple[str, ...]) -> dict | None:
    for r in rows:
        if r["section"] == section and r["line"].strip().lower() in names:
            return r
    return None


def tie_out(rows: list[dict], tolerance: float = 0.5, edits=None) -> dict:
    """Every row's parts must add to its combined figure. If the balance sheet totals are present,
    combined total assets must equal combined total liabilities and equity.
    The rows already carry any edits (consolidate applied them); edits_applied lists the active edit ids passed."""
    bad_rows = [r["line"] for r in rows if abs((r["platform"] + r["target"]) - r["combined"]) > tolerance]
    assets = _find(rows, "balance_sheet", ("total assets",))
    liab_eq = _find(rows, "balance_sheet", LIABILITIES_AND_EQUITY_TOTALS)
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
            "rows_checked": len(rows), "missing_totals": missing, "edits_applied": [e.id for e in active(edits)]}


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


def ebitda(platform_lines: list[SourceLine], target_lines: list[SourceLine], brief: Brief,
           as_filed: bool = False, edits=None) -> dict:
    """Covenant EBITDA, built the way the agreement defines it.

    Base, per company: net income plus interest expense less interest income plus income taxes plus depreciation
    and amortization (Ex 10.1 Addendum I).
    Then each add-back from the brief is applied up to its cap, and each deduction is subtracted.
    The brief holds the agreement's own definitions, so this function never guesses them.
    as_filed=True stops at the base: reported EBITDA from the filed statements, with no add-back or deduction.
    That is the reading of someone who has not read the agreement, and it pairs with the whole-line debt figure.
    Expense lines are stored as positive amounts; a tax benefit is stored as a negative amount.
    The deal's active amount edits are applied to the lines first; edits_applied lists them.
    """
    platform_lines, target_lines, edit_ids, carried = _with_amount_edits(platform_lines, target_lines, edits)
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
    for a in ([] if as_filed else brief.ebitda_addbacks):
        applied = min(a.amount, a.cap) if a.cap is not None else a.amount
        addbacks.append({"name": a.name, "amount": a.amount, "cap": a.cap, "applied": round(applied, 3),
                         "source_ref": a.source_ref, "inferred": a.inferred})
        total_add += applied
    deductions = []
    total_ded = 0.0
    for d in ([] if as_filed else brief.ebitda_deductions):
        deductions.append({"name": d.name, "amount": d.amount, "source_ref": d.source_ref, "inferred": d.inferred})
        total_ded += d.amount
    value = base + total_add - total_ded
    return {"ebitda": round(value, 3), "base": round(base, 3), "addbacks_total": round(total_add, 3),
            "deductions_total": round(total_ded, 3), "parts": parts, "addbacks": addbacks,
            "deductions": deductions, "basis": "as_filed" if as_filed else "covenant", "unit": THOUSANDS,
            "edits_applied": edit_ids, **carried}


# Borrowed money must be tagged debt, not_debt, or unclear. An 'na' on one of these names is a missed tag.
BORROWING_WORDS = ("borrowing", "loan", "note payable", "notes payable", "debt", "credit facility", "revolver",
                   "term loan", "financing liability", "finance lease", "financing lease")
# Names that mark an asset, reserve, or cost rather than borrowed money, so a borrowing word in them is not a missed tag.
NOT_BORROWING_WORDS = ("receivable", "reserve", "allowance", "issuance cost")


def covenant_debt(platform_lines: list[SourceLine], target_lines: list[SourceLine], brief: Brief,
                  naive: bool = False, edits=None) -> dict:
    """The covenant's debt figure, from the covenant tags on the balance sheet lines.

    Lines tagged `debt` count. Lines tagged `not_debt` are listed as excluded with their note.
    A line tagged `unclear` stops the calculation, unless naive=True, which counts it: that is what a
    careless reading of the balance sheet gives, and it is reported as naive.
    The borrowing check on `na` lines is a name heuristic that fails loudly, and the fix for a false positive
    is to tag the line `not_debt` with a note.
    The deal's active amount edits are applied to the lines first; edits_applied lists them.
    """
    platform_lines, target_lines, edit_ids, carried = _with_amount_edits(platform_lines, target_lines, edits)
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
            "naive": naive, "unit": THOUSANDS, "edits_applied": edit_ids, **carried}


def leverage(debt: float, ebitda_value: float) -> dict:
    if not (math.isfinite(debt) and math.isfinite(ebitda_value)):
        raise ValueError("debt and ebitda must be finite numbers")
    if ebitda_value <= 0:
        raise ValueError("ebitda must be positive")
    return {"leverage": round(debt / ebitda_value, 3), "debt": round(debt, 3), "ebitda": round(ebitda_value, 3)}


def limit_test(leverage_value: float, limit: float, wording: str = "less than", ebitda_value: float | None = None,
               debt: float | None = None, naive_debt: float | None = None,
               rent_deduction: float | None = None, naive_ebitda: float | None = None) -> dict:
    """Test the ratio against the covenant. 'less than' means the ratio must be strictly below the limit.
    Debt capacity (room for the next deal) is reported when EBITDA and debt are given.

    Sensitivity, when naive_debt (the whole-line reading of debt) and EBITDA are given: the naive ratio, and
    naive_flip_addback, the EBITDA add-back at which the naive reading reaches the limit (positive means that much
    more EBITDA is needed; zero or negative means it already passes). With rent_deduction also given,
    naive_flip_rent is the rent deduction at which the naive reading reaches the limit; it is left out when it would
    be below zero, since no rent change can then flip the verdict. naive_ebitda, when given, is the EBITDA the naive
    reading divides by (reported EBITDA, as filed); without it the naive reading uses ebitda_value. naive_ok is tested on the unrounded naive ratio,
    while ok is tested on the leverage as given (rounded to 3 places by the leverage tool), so the two can disagree
    for a ratio within 0.0005 of the limit."""
    given = [leverage_value, limit] + [v for v in (ebitda_value, debt, naive_debt, rent_deduction, naive_ebitda)
                                       if v is not None]
    if not all(math.isfinite(v) for v in given):
        raise ValueError("limit_test inputs must be finite numbers")

    def passes(ratio: float) -> bool:
        return ratio < limit if wording == "less than" else ratio <= limit

    ok = passes(leverage_value)
    out = {"ok": ok, "verdict": "ok" if ok else "over_limit", "leverage": round(leverage_value, 3), "limit": limit,
           "headroom_turns": round(limit - leverage_value, 3), "wording": wording}
    if ebitda_value is not None and debt is not None:
        out["debt_capacity"] = round(limit * ebitda_value - debt, 3)
    naive_eb = naive_ebitda if naive_ebitda is not None else ebitda_value
    if naive_debt is not None and naive_eb is not None:
        if naive_eb <= 0:
            raise ValueError("ebitda must be positive")
        if limit <= 0:
            raise ValueError("limit must be positive")
        flip = round(naive_debt / limit - naive_eb, 3)
        out.update({"naive_debt": round(naive_debt, 3), "naive_leverage": round(naive_debt / naive_eb, 3),
                    "naive_ok": passes(naive_debt / naive_eb), "naive_flip_addback": flip})
        if naive_ebitda is not None:
            out["naive_ebitda"] = round(naive_ebitda, 3)
        if rent_deduction is not None and round(rent_deduction - flip, 3) >= 0:
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

EDIT_RULE = ("An amount edit on an income statement detail line carries into the totals: the first total after it, "
             "if its name starts with 'Total', moves by the change; every later running total (Gross Profit, "
             "Operating profit, Income Before Income Taxes, Net Income) moves by the change times the line's sign, "
             "which is inferred from its name (-1 for a cost, expense, tax, or provision line, +1 for a revenue, "
             "sales, income, or profit line, -1 for a name with neither, named in rollup_notes). Taxes are not "
             "recomputed. An income statement detail edit with no later net income total line is refused. Every "
             "line the carry moved is listed in rollup. An edit on a total line replaces that line only. An amount "
             "edit on a balance sheet detail line is refused: its roll-up is not defined, so code cannot recompute "
             "the totals. A remap moves the target subtotals the line fed in the target's statement to the ones "
             "its new platform line feeds in the platform's statement (each move is listed in remap_rollup), so a "
             "remap across the balance sheet's sides fails the tie-out. An edit that matches no line or several "
             "lines, or a remap onto a platform total or a line the platform does not have, is refused.")

TOOL_DESCRIPTIONS = {
    "consolidate": "Add the target's statement lines onto the platform's lines using the approved mappings. "
                   "No arguments. Applies the deal's active edits (amount and remap) first. "
                   "Returns rows with platform, target, combined, edits_applied, and the run id. " + EDIT_RULE,
    "tie_out": "Check that every row's parts add to its combined figure and that the combined balance sheet balances. "
               "Arguments: run_id (the consolidate run to check). The rows already carry the deal's active edits; "
               "edits_applied lists them.",
    "ebitda": "Compute covenant EBITDA from the statement lines and the brief's add-backs and deductions. "
              "No arguments. Applies the deal's active amount edits first; edits_applied lists them. " + EDIT_RULE,
    "covenant_debt": "Compute the covenant's debt figure from the covenant tags on balance sheet lines. "
                     "Arguments: naive (bool, default false) counts unclear lines as debt. "
                     "Applies the deal's active amount edits first; edits_applied lists them. " + EDIT_RULE,
    "leverage": "Divide debt by EBITDA. Arguments: debt_run_id and ebitda_run_id (the run ids of your covenant_debt and "
                "ebitda runs). Numbers are not accepted. No edits_applied: the edits are on the input runs.",
    "limit_test": "Test leverage against the lender's limit from the brief. Arguments: leverage_run_id or leverage. "
                  "Optional sensitivity: naive_debt_run_id (a covenant_debt run with the whole-line reading) and "
                  "naive_ebitda_run_id (an as-filed ebitda run) add naive_leverage, naive_ok, and naive_flip_addback "
                  "(the EBITDA at which the as-filed reading reaches the limit). "
                  "No edits_applied: the edits are on the input runs.",
}
