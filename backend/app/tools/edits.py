"""Controller edits applied to the inputs of the math tools. Pure functions, no side effects, no model.

An edit is read by attribute (getattr), so a Pydantic model, a dataclass, or a SimpleNamespace all work.
The Edit model lands with Cayden's C1 (docs/tasks/cayden.md); until then the shape is the EditLike protocol below.
An amount edit replaces one line's amount with new_value (USD thousands).
A remap edit moves one target line onto another platform line.
A reverted edit is ignored everywhere. An edit that matches nothing is refused, never guessed.
Owner: Tri (backend/app/tools/).
"""
from __future__ import annotations

from typing import Any, Iterable, Protocol

from app.core.models import Mapping, SourceLine

THOUSANDS = "USD thousands"


class EditLike(Protocol):
    id: str
    deal_id: str
    kind: str  # "amount" or "remap"
    company: str
    line: str
    section: str | None
    old_value: float | None
    new_value: float | None  # USD thousands, for an amount edit
    old_platform_line: str | None
    new_platform_line: str | None  # for a remap edit
    status: str  # "needs_reason", "reasoned", "reverted"
    reason_chip: Any
    reason_text: str | None
    remember: bool
    policy_id: str | None
    adjustment_id: str | None
    actor: str
    at: Any
    run_ids: list[str]


def _norm(text: str | None) -> str:
    return (text or "").strip().lower()


def active(edits: Iterable[EditLike | None] | None) -> list[EditLike]:
    """The edits that count: not None and not reverted, in the order given."""
    return [e for e in (edits or []) if e is not None and getattr(e, "status", None) != "reverted"]


def _of_kind(edits, kind: str) -> list[EditLike]:
    return [e for e in active(edits) if getattr(e, "kind", None) == kind]


def _line_matches(line: SourceLine, edit: EditLike) -> bool:
    section = getattr(edit, "section", None)
    return (_norm(line.company) == _norm(getattr(edit, "company", None))
            and _norm(line.line) == _norm(getattr(edit, "line", None))
            and (not section or line.section == section))


def apply_amount_edits(lines: list[SourceLine], edits) -> tuple[list[SourceLine], list[str]]:
    """Copies of the lines with each active amount edit's new_value as the amount, in USD thousands.

    Returns the new lines and the applied edit ids in edit order. The input lines are never changed.
    An amount edit that matches no line raises ValueError.
    """
    out = list(lines)
    applied: list[str] = []
    for edit in _of_kind(edits, "amount"):
        new_value = getattr(edit, "new_value", None)
        if new_value is None:
            raise ValueError(f"amount edit {getattr(edit, 'id', '?')} has no new value")
        hit = False
        for i, line in enumerate(out):
            if _line_matches(line, edit):
                out[i] = line.model_copy(update={"amount": float(new_value), "unit": THOUSANDS})
                hit = True
        if not hit:
            raise ValueError(f"amount edit {getattr(edit, 'id', '?')} matches no line: "
                             f"{getattr(edit, 'line', '?')} ({getattr(edit, 'company', '?')})")
        applied.append(edit.id)
    return out, applied


def apply_remap_edits(mappings: list[Mapping], target_lines: list[SourceLine], platform_lines: list[SourceLine],
                      edits) -> tuple[list[Mapping], list[str]]:
    """Copies of the mappings with each active remap edit's new_platform_line in place.

    The mapping is found through its target line (company and line name). platform_line_id is set to the id of the
    platform line of that name (any section), or None when the platform has no such line.
    A remap that matches no mapping raises ValueError. The input mappings are never changed.
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
            p = next((p for p in platform_lines if _norm(p.line) == _norm(new_name)), None)
            out[i] = m.model_copy(update={"platform_line": new_name, "platform_line_id": p.id if p else None})
            hit = True
        if not hit:
            raise ValueError(f"remap edit {getattr(edit, 'id', '?')} matches no mapping: "
                             f"{getattr(edit, 'line', '?')} ({getattr(edit, 'company', '?')})")
        applied.append(edit.id)
    return out, applied
