"""Final files: the combined books as an Excel workbook. Pure functions, no FastAPI.

Three sheets: Combined (the result rows), Edits (one row per active controller edit), Audit (the run id behind every
figure). Figures are read from the certificate, which reads them from the tool runs, so the two files agree.
Nothing here computes a deal number.
Owner: Tri (backend/app/api/).
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font, PatternFill

from app.api import certificate as cert_doc

AMBER = "FBEBC8"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
EDITS_HEADER = ["Line", "Company", "Agent value", "Final value", "Reason", "Who", "When", "Policy id"]
AUDIT_HEADER = ["Figure", "Value", "Run id", "Tool"]


def _norm(text) -> str:
    return (text or "").strip().lower()


def _when(at) -> str | None:
    if isinstance(at, datetime):
        return f"{at:%Y-%m-%d %H:%M}"
    return str(at) if at is not None else None


def export_filename(platform: str, target: str) -> str:
    """'<platform> + <target> combined books.xlsx', ASCII only; any other character (and quotes) becomes a space."""
    name = f"{platform} + {target} combined books.xlsx"
    return "".join(c if c.isascii() and c.isprintable() and c not in '"\\' else " " for c in name)


def edit_note(edit) -> str:
    """The Excel note on an edited cell."""
    old, _ = cert_doc.edit_values(edit)
    was = cert_doc.fmt(old) if isinstance(old, (int, float)) and not isinstance(old, bool) else (old or "n/a")
    text = (f"Edited by {getattr(edit, 'actor', None) or 'unknown'}, {_when(getattr(edit, 'at', None))}. "
            f"Was {was}. Reason: {cert_doc.edit_reason(edit)}.")
    policy = getattr(edit, "policy_id", None)
    return text + (f" Policy {policy}." if policy else "")


def _edited_cells(store, deal, rows, edits) -> dict[tuple[int, int], object]:
    """(row index into rows, column 3 platform or 4 target) -> the edit that marks that cell. The last edit wins.

    A platform edit marks the row of the same line name. A target edit marks the row its target line maps onto
    (a remap: the new platform line), since the Combined sheet has the platform's line names.
    """
    platform, target = _norm(deal.platform), _norm(deal.target)
    target_lines = {l.id: l for l in store.lines(deal.id, deal.target)}
    mappings = store.deal_mappings(deal.id)
    out: dict[tuple[int, int], object] = {}
    for e in edits:
        company, line, section = _norm(getattr(e, "company", None)), _norm(getattr(e, "line", None)), getattr(e, "section", None)
        if company == platform:
            col, names = 3, {line}
        elif company == target:
            col = 4
            if getattr(e, "kind", None) == "remap":
                names = {_norm(getattr(e, "new_platform_line", None))}
            else:
                names = set()
                for m in mappings:
                    t = target_lines.get(m.target_line_id)
                    if t and _norm(t.line) == line and (not section or t.section == section) and m.platform_line:
                        names.add(_norm(m.platform_line))
        else:
            continue
        for i, r in enumerate(rows):
            if _norm(r.line) in names and (company != platform or not section or r.section == section):
                out[(i, col)] = e
    return out


def _bold(ws) -> None:
    for cell in ws[1]:
        cell.font = Font(bold=True)


def build_workbook(store, deal, result, items, chain_valid: bool, edits=None) -> Workbook:
    """The final workbook. `edits` defaults to the store's active edits for the deal (reverted ones are dropped)."""
    edits = cert_doc.deal_edits(store, deal.id, edits)
    cert = cert_doc.build_certificate(store, deal, result, items, chain_valid, edits=edits)

    wb = Workbook()
    ws = wb.active
    ws.title = "Combined"
    ws.append(["Line", "Section", deal.platform, deal.target, "Combined", "Run id"])
    for r in result.rows:
        ws.append([r.line, r.section, r.platform, r.target, r.combined, r.run_id])
    fill = PatternFill("solid", fgColor=AMBER)
    for (i, col), e in _edited_cells(store, deal, result.rows, edits).items():
        cell = ws.cell(row=i + 2, column=col)
        cell.fill = fill
        cell.comment = Comment(edit_note(e), "Stochastic")
    _bold(ws)

    we = wb.create_sheet("Edits")
    we.append(EDITS_HEADER)
    for e in edits:
        old, new = cert_doc.edit_values(e)
        we.append([getattr(e, "line", None), getattr(e, "company", None), old, new, cert_doc.edit_reason(e),
                   getattr(e, "actor", None), _when(getattr(e, "at", None)), getattr(e, "policy_id", None)])
    _bold(we)

    wa = wb.create_sheet("Audit")
    wa.append(AUDIT_HEADER)

    def tool_of(run_id):
        run = store.tool_runs.get(run_id) if run_id else None
        return run.tool if run else None

    def fig(name, block, key):
        if block:
            wa.append([name, block.get(key), block.get("run_id"), tool_of(block.get("run_id"))])
        else:
            wa.append([name, None, None, None])

    fig("EBITDA", cert["ebitda"], "ebitda")
    fig("Debt", cert["debt"], "debt")
    fig("Leverage", cert["leverage"], "leverage")
    lt = cert["limit_test"]
    fig("Limit test leverage", lt, "leverage")
    fig("Limit test limit", lt, "limit")
    fig("Limit test verdict", lt, "verdict")
    fig("Limit test headroom (turns)", lt, "headroom_turns")
    fig("Limit test debt capacity", lt, "debt_capacity")
    fig("Tie-out ok", cert["tie_out"], "ok")
    for r in result.rows:
        wa.append([f"Combined: {r.line} ({r.section})", r.combined, r.run_id, tool_of(r.run_id)])
    au = cert["approval"]["audit"]
    wa.append([None, None, None, None])
    wa.append(["Audit rows", au["rows"], None, None])
    wa.append(["Chain valid", au["chain_valid"], None, None])
    wa.append(["Denied attempts", au["denied"], None, None])
    wa.append(["Backend", cert["header"]["backend"],
               "Agent output backend. The gateway, the math, and the audit log are real.", None])
    wa.append(["Draft. Not signed.", None, None, None])
    _bold(wa)
    return wb


def workbook_bytes(wb: Workbook) -> bytes:
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
