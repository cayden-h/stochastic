"""Controller edits applied to the inputs of the math tools. Pure functions, no side effects, no model.

Edits are the Edit model from app.core.models (Cayden's C1). They are read by attribute (getattr), so a
SimpleNamespace with the same fields also works in tests that need a shape the model refuses.
An amount edit replaces one line's amount with new_value (USD thousands).
A remap edit moves one target line onto another platform line.
A reverted edit is ignored everywhere. An edit that matches nothing is refused, never guessed.

Refusals (ValueError), so a total is never left stale and a figure is never guessed:
- An amount edit that matches no line, or more than one line (give the section, or the line is ambiguous).
- An amount edit on a detail line (not is_total) when that company has any is_total line in the same section.
  The statements store totals as filed lines, and no roll-up map says which detail lines feed which total, so code
  cannot recompute the totals (or the net income line EBITDA starts from) after a detail edit. Edits on is_total
  lines, and on detail lines of a section with no totals, still apply. This holds until the team adds a roll-up map.
- A remap that matches no mapping, that names an old_platform_line other than the mapping's current one (stale), onto
  a platform line the platform does not have, or onto a platform total
  (is_total) for a detail target line.
Owner: Tri (backend/app/tools/).
"""
from __future__ import annotations

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


def apply_amount_edits(lines: list[SourceLine], edits: Iterable[Edit] | None) -> tuple[list[SourceLine], list[str]]:
    """Copies of the lines with each active amount edit's new_value as the amount, in USD thousands.

    Returns the new lines and the applied edit ids in edit order. The input lines are never changed.
    Raises ValueError for an edit that matches no line or several lines, and for an edit on a detail line in a
    section where the company has totals (see the module docstring).
    """
    out = list(lines)
    applied: list[str] = []
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
        if not line.is_total and any(o.is_total and _norm(o.company) == _norm(line.company)
                                     and o.section == line.section for o in out):
            raise ValueError(f"amount edit {eid} on {line.line} ({line.company}, {line.section}) is refused: "
                             f"the roll-up for that section is not defined, so code cannot recompute the totals")
        out[i] = line.model_copy(update={"amount": float(new_value), "unit": THOUSANDS})
        applied.append(edit.id)
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
