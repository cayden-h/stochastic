"""Controller edits applied to the inputs of the math tools. Pure functions, no side effects, no model.

Edits are the Edit model from app.core.models (Cayden's C1). They are read by attribute (getattr), so a
SimpleNamespace with the same fields also works in tests that need a shape the model refuses.
An amount edit replaces one line's amount with new_value (USD thousands).
A remap edit moves one target line onto another platform line.
A reverted edit is ignored everywhere. An edit that matches nothing is refused, never guessed.

The income statement roll-up rule (a detail edit carries into the totals the way the filed statement is built).
The sign of a line is inferred from its name, not read from the filing; the fixture figures are verified by the tests.
- line_sign(name) (inferred): -1 (a cost) when the lower-cased name contains "cost", "expense", "tax", "provision", or
  "attributable to the non-controlling"; else +1 when it contains "revenue", "sales", "income", "profit",
  "earnings", or "gain"; else -1 (no word: treated as a cost, and named under rollup_notes in the run output).
- For an amount edit on an income statement detail line (not is_total), delta = new_value - the line's value in
  USD thousands. In statement order (the order of that company's lines as given):
  1. If the first is_total line after the edited line starts with "total" (a group total such as
     "Total Operating Expense"), it moves by +delta (a group total has the nature of its lines).
  2. Every later is_total line whose name does not start with "total" (a running total: Gross Profit,
     Operating profit, Income Before Income Taxes, Net Income, ...) moves by line_sign(edited line) * delta.
  3. No other line moves. Taxes are not recomputed: the edit flows to net income before tax, which the covenant
     EBITDA build adds back, so a 500 cut in a cost raises covenant EBITDA by exactly 500.
  4. Group totals after a running total, and totals before the edited line, do not move.
- Every line the carry moved is reported as {edit_id, company, line, delta} under rollup.
- An amount edit on an is_total line replaces that line only.
A rolls_into field on the fixture lines would replace this rule later.

The remap roll-up rule (a remap moves the subtotals the moved line feeds, so no total is left stale).
A remap moves one target detail line out of the target's own statement and onto a platform line. Its amount v (USD
thousands, after the amount edits) leaves every target subtotal it fed in the target's statement, and joins every
platform subtotal the new platform line feeds in the platform's statement (statement_feeds, below). consolidate
applies the difference to the target column of each platform subtotal row that a target subtotal landed on; a
platform subtotal no target subtotal landed on has no target figure and does not move. For R&D moved from Operating
expenses onto Cost of products sold: Gross profit -v, Operating profit -v + v = 0, and every later total 0.
Which subtotals a line feeds (statement_feeds), in the order of that company's lines of that section:
- Income statement: the carry rule above, with the line's own sign (a platform line's sign for the new place, the
  target line's sign for the old one).
- Balance sheet (and any other section): every amount counts +1 (the sign is in the amount). The "Total Assets" row
  splits the section into two sides; a line feeds the top total of its side ("Total Assets", or the total
  liabilities and equity line that tie_out reads). Under it, a line feeds the first total after it, and every later
  total of its side that nests a total it feeds. A total S nests an earlier total U when U's name holds S's core
  (S's name without "total", "net", a parenthesis, or ", at cost"): "Total Liabilities" nests "Total Current
  Liabilities", "Total Property and Equipment (at Depreciated Cost)" nests "Total Property and Equipment, at Cost".
  The nesting is inferred from the names, as line_sign is; the fixture figures are verified by the tests.
So a remap across sides of the balance sheet moves both side totals, and the tie-out fails, as it should.

Refusals (ValueError), so a total is never left stale and a figure is never guessed:
- An amount edit that matches no line, or more than one line (give the section, or the line is ambiguous).
- An amount edit on an income statement detail line when no later is_total line of that company is a net income
  line (a name holding "net income", "net earnings", or "net loss"): the edit could not reach net income or EBITDA,
  and would look applied with an unchanged verdict.
- An amount edit on a detail line (not is_total) outside the income statement when that company has any is_total
  line in the same section. The balance sheet's nesting is not derivable from order alone, and the tie-out would
  hide a wrong carry, so code does not guess which total a balance sheet detail line feeds. Edits on is_total lines,
  and on detail lines of a balance sheet or cash flow section with no totals, still apply.
- A remap that matches no mapping, that names an old_platform_line other than the mapping's current one (stale), onto
  a platform line the platform does not have, or onto a platform total
  (is_total) for a detail target line.
Owner: Tri (backend/app/tools/).
"""
from __future__ import annotations

import re
from typing import Iterable

from app.core.models import Edit, Mapping, SourceLine

THOUSANDS = "USD thousands"


def _norm(text: str | None) -> str:
    return (text or "").strip().lower()


def active(edits: Iterable[Edit | None] | None) -> list[Edit]:
    """The edits that count: not None and not reverted, in the order given."""
    return [e for e in (edits or []) if e is not None and getattr(e, "status", None) != "reverted"]


def _of_kind(edits: Iterable[Edit] | None, kind: str) -> list[Edit]:
    return [e for e in active(edits) if getattr(e, "kind", None) == kind]


def _line_matches(line: SourceLine, edit: Edit) -> bool:
    section = getattr(edit, "section", None)
    return (_norm(line.company) == _norm(getattr(edit, "company", None))
            and _norm(line.line) == _norm(getattr(edit, "line", None))
            and (not section or line.section == section))


COST_WORDS = ("cost", "expense", "tax", "provision", "attributable to the non-controlling")
REVENUE_WORDS = ("revenue", "sales", "income", "profit", "earnings", "gain")
INCOME_STATEMENT = "income_statement"


def line_sign(name: str) -> int:
    """+1 for a revenue or profit line, -1 for a cost. A name with neither kind of word counts as a cost."""
    n = _norm(name)
    if any(w in n for w in COST_WORDS):
        return -1
    if any(w in n for w in REVENUE_WORDS):
        return 1
    return -1


NET_INCOME_WORDS = ("net income", "net earnings", "net loss")


def is_net_income(name: str) -> bool:
    """A net income line by name: the lower-cased name holds "net income", "net earnings", or "net loss"."""
    n = _norm(name)
    return any(w in n for w in NET_INCOME_WORDS)


def _has_sign_word(name: str) -> bool:
    n = _norm(name)
    return any(w in n for w in COST_WORDS + REVENUE_WORDS)


def _thousands(line: SourceLine) -> float:
    from app.tools.finance import to_thousands  # finance imports this module; import at call time
    return to_thousands(line.amount, line.unit)


ASSETS_TOTALS = ("total assets",)
LIABILITIES_AND_EQUITY_TOTALS = ("total liabilities and stockholders' equity",
                                 "total liabilities and stockholders’ equity",
                                 "total liabilities and shareholders' equity",
                                 "total liabilities and shareholders’ equity",
                                 "total liabilities and equity")


def _is_side_total(line: SourceLine) -> bool:
    return line.is_total and _norm(line.line) in ASSETS_TOTALS + LIABILITIES_AND_EQUITY_TOTALS


def _core(name: str) -> str:
    """A total's name without "total", "net", a parenthesis, or ", at cost": what the totals it nests are named for."""
    n = re.sub(r"\([^)]*\)", "", _norm(name))
    n = re.sub(r",\s*at cost$|,\s*net$", "", n.strip())
    n = re.sub(r"^(total|net)\s+", "", n.strip())
    return n.strip(" ,")


def _nests(total: SourceLine, earlier: SourceLine) -> bool:
    core = _core(total.line)
    return bool(core) and core in _norm(earlier.line)


def statement_feeds(lines: list[SourceLine], i: int) -> list[tuple[int, int]]:
    """The subtotals that detail line i feeds, as (index, coefficient) in statement order.

    `lines` are one company's lines of one section, in statement order. The coefficient is the line's sign in that
    subtotal (+1 or -1). See the module docstring for the income statement and balance sheet rules."""
    line = lines[i]
    later = [j for j in range(i + 1, len(lines)) if lines[j].is_total]
    if line.section == INCOME_STATEMENT:
        out: list[tuple[int, int]] = []
        if later and _norm(lines[later[0]].line).startswith("total"):
            out.append((later[0], 1))
        sign = line_sign(line.line)
        return out + [(j, sign) for j in later if not _norm(lines[j].line).startswith("total")]
    top = next((j for j in later if _is_side_total(lines[j])), None)
    side = [j for j in later if top is None or j <= top]
    fed: list[int] = []
    for j in side:
        if j == top or not fed or any(_nests(lines[j], lines[u]) for u in fed):
            fed.append(j)
    return [(j, 1) for j in fed]


def remap_moves(target_lines: list[SourceLine], platform_lines: list[SourceLine], remapped: list[Mapping],
                edits: Iterable[Edit] | None) -> list[dict]:
    """For each remapped target detail line, the subtotals it leaves and the ones it joins (the remap roll-up rule).

    `remapped` are the mappings apply_remap_edits changed. Returns, in edit order, one dict per moved line:
    {edit_id, line (the target SourceLine), old: [(target total SourceLine, coefficient)],
    new: [(platform total SourceLine, coefficient)]}. A remapped target total moves nothing else and is left out."""
    by_id = {t.id: t for t in target_lines}
    remaps = _of_kind(edits, "remap")
    out = []
    for m in remapped:
        t = by_id.get(m.target_line_id)
        if t is None or t.is_total or not m.platform_line:
            continue
        own = [x for x in target_lines if _norm(x.company) == _norm(t.company) and x.section == t.section]
        old = [(own[j], c) for j, c in statement_feeds(own, next(k for k, x in enumerate(own) if x.id == t.id))]
        p = next(p for p in platform_lines if _norm(p.line) == _norm(m.platform_line))
        theirs = [x for x in platform_lines if _norm(x.company) == _norm(p.company) and x.section == p.section]
        new = [(theirs[j], c) for j, c in statement_feeds(theirs, next(k for k, x in enumerate(theirs) if x.id == p.id))]
        eid = next((getattr(e, "id", "?") for e in remaps if _line_matches(t, e)), "?")
        out.append({"edit_id": eid, "line": t, "old": old, "new": new})
    order = {getattr(e, "id", "?"): n for n, e in enumerate(remaps)}
    return sorted(out, key=lambda x: order.get(x["edit_id"], len(order)))


def carry_amount_edits(lines: list[SourceLine], edits: Iterable[Edit] | None
                       ) -> tuple[list[SourceLine], list[str], list[dict], list[str]]:
    """Copies of the lines with each active amount edit applied and carried by the income statement roll-up rule.

    Returns (lines, applied edit ids in edit order, rollup, rollup_notes). rollup lists every line the carry moved
    as {edit_id, company, line, delta} in USD thousands; rollup_notes names each edited line whose sign was taken
    as a cost because its name has no revenue or cost word. The input lines are never changed.
    Raises ValueError for an edit that matches no line or several lines, and for a detail edit outside the income
    statement in a section where the company has totals (see the module docstring).
    """
    out = list(lines)
    applied: list[str] = []
    rollup: list[dict] = []
    notes: list[str] = []
    for edit in _of_kind(edits, "amount"):
        eid = getattr(edit, "id", "?")
        new_value = getattr(edit, "new_value", None)
        if new_value is None:
            raise ValueError(f"amount edit {eid} has no new value")
        hits = [i for i, line in enumerate(out) if _line_matches(line, edit)]
        if not hits:
            raise ValueError(f"amount edit {eid} matches no line: "
                             f"{getattr(edit, 'line', '?')} ({getattr(edit, 'company', '?')})")
        if len(hits) > 1:
            names = "; ".join(f"{out[i].id} {out[i].line} ({out[i].section})" for i in hits)
            raise ValueError(f"amount edit {eid} matches {len(hits)} lines: {names}. Give the section, "
                             f"or the line is ambiguous")
        i = hits[0]
        line = out[i]
        same = [j for j, o in enumerate(out) if _norm(o.company) == _norm(line.company) and o.section == line.section]
        carry: list[tuple[int, float]] = []
        if not line.is_total and line.section != INCOME_STATEMENT and any(out[j].is_total for j in same):
            raise ValueError(f"amount edit {eid} on {line.line} ({line.company}, {line.section}) is refused: "
                             f"the roll-up for that section is not defined, so code cannot recompute the totals")
        if not line.is_total and line.section == INCOME_STATEMENT:
            later = [j for j in same if j > i and out[j].is_total]
            if not any(is_net_income(out[j].line) for j in later):
                raise ValueError(f"amount edit {eid} on {line.line} ({line.company}, {line.section}) is refused: "
                                 f"no later total line of {line.company} is a net income line, so the edit could "
                                 f"not reach net income or EBITDA")
            delta = round(float(new_value) - _thousands(line), 6)
            if not _has_sign_word(line.line):
                notes.append(f"{line.line} ({line.company}) has no revenue or cost word in its name; "
                             f"the roll-up treated it as a cost")
            carry = [(same[k], c * delta) for k, c in statement_feeds([out[j] for j in same], same.index(i))]
        out[i] = line.model_copy(update={"amount": float(new_value), "unit": THOUSANDS})
        for j, d in carry:
            out[j] = out[j].model_copy(update={"amount": round(_thousands(out[j]) + d, 6), "unit": THOUSANDS})
            rollup.append({"edit_id": edit.id, "company": out[j].company, "line": out[j].line,
                           "delta": round(d, 3)})
        applied.append(edit.id)
    return out, applied, rollup, notes


def apply_amount_edits(lines: list[SourceLine], edits: Iterable[Edit] | None) -> tuple[list[SourceLine], list[str]]:
    """carry_amount_edits without the roll-up report: the new lines and the applied edit ids in edit order."""
    out, applied, _, _ = carry_amount_edits(lines, edits)
    return out, applied


def apply_remap_edits(mappings: list[Mapping], target_lines: list[SourceLine], platform_lines: list[SourceLine],
                      edits: Iterable[Edit] | None) -> tuple[list[Mapping], list[str]]:
    """Copies of the mappings with each active remap edit's new_platform_line in place.

    The mapping is found through its target line (company and line name). platform_line_id is set to the id of the
    platform line of that name (any section).
    Raises ValueError for a remap that matches no mapping, that is stale (old_platform_line set and not the mapping's
    current platform line), onto a line the platform does not have, or onto a
    platform total (is_total) for a detail target line. The input mappings are never changed.
    """
    by_id = {t.id: t for t in target_lines}
    out = list(mappings)
    applied: list[str] = []
    for edit in _of_kind(edits, "remap"):
        new_name = getattr(edit, "new_platform_line", None)
        hit = False
        for i, m in enumerate(out):
            t = by_id.get(m.target_line_id)
            if t is None or not _line_matches(t, edit):
                continue
            old_name = getattr(edit, "old_platform_line", None)
            if old_name and _norm(old_name) != _norm(m.platform_line):
                raise ValueError(f"remap edit {getattr(edit, 'id', '?')} is stale: it expects {old_name}, "
                                 f"but the mapping is now {m.platform_line}")
            p = next((p for p in platform_lines if _norm(p.line) == _norm(new_name)), None)
            if p is None:
                raise ValueError(f"remap edit {getattr(edit, 'id', '?')}: the platform has no line {new_name}")
            if p.is_total and not t.is_total:
                raise ValueError(f"remap edit {getattr(edit, 'id', '?')}: {new_name} is a platform total; "
                                 f"a detail line cannot be mapped onto a total")
            out[i] = m.model_copy(update={"platform_line": new_name, "platform_line_id": p.id})
            hit = True
        if not hit:
            raise ValueError(f"remap edit {getattr(edit, 'id', '?')} matches no mapping: "
                             f"{getattr(edit, 'line', '?')} ({getattr(edit, 'company', '?')})")
        applied.append(edit.id)
    return out, applied
