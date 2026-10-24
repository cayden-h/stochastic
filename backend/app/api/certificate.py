"""Draft compliance certificate for a posted deal. Pure functions, no FastAPI.

Every figure is read from a ToolRun and carries that run's id. Nothing here computes a deal number.
The certificate is a draft: an officer of the borrower signs the one the agreement requires (Ex 10.1 Section 4.2(g)).
Owner: Tri (backend/app/api/).
"""
from __future__ import annotations

import html
from datetime import datetime, timezone

from app.core.models import State

UNIT = "USD thousands"
DRAFT_NOTE = ("Draft. Not signed. Prepared from the approved result; an officer of the borrower signs the "
              "certificate the agreement requires.")


def _run(store, run_id: str | None):
    return store.tool_runs.get(run_id) if run_id else None


def _review_run(store, result, tool: str, prefer_key: str | None = None):
    """The Reviewer's run of `tool`, from review.run_ids. Same lookup as _debt_capacity in routes.py:
    the last such run that carries `prefer_key`, else the last such run."""
    ids = result.review.run_ids if result.review else []
    runs = [t for t in store.tool_runs.values() if t.tool == tool and t.run_id in ids]
    if prefer_key:
        keyed = [t for t in runs if t.outputs.get(prefer_key) is not None]
        if keyed:
            return keyed[-1]
    return runs[-1] if runs else None


def approval_item(items, result):
    """The approve_result item for this result, else the last one that was not rejected or reversed."""
    approvals = [i for i in items if i.type == "approve_result"]
    for i in reversed(approvals):
        if result is not None and i.payload.get("result_id") == result.id:
            return i
    return next((i for i in reversed(approvals) if i.state not in (State.REJECTED, State.REVERSED)), None)


def build_certificate(store, deal, result, items, chain_valid: bool) -> dict:
    """The certificate as a dict. Reads the store and the tool runs; never computes a figure."""
    brief = deal.brief
    by_tool = result.run_ids_by_tool

    periods = {}
    for company in (deal.platform, deal.target):
        periods[company] = sorted({l.period for l in store.lines(deal.id, company)})

    eb = _run(store, by_tool.get("ebitda"))
    ebitda = None
    if eb:
        o = eb.outputs
        ebitda = {"parts": o.get("parts", []), "addbacks": o.get("addbacks", []),
                  "deductions": o.get("deductions", []), "base": o.get("base"),
                  "addbacks_total": o.get("addbacks_total"), "deductions_total": o.get("deductions_total"),
                  "ebitda": o.get("ebitda"), "run_id": eb.run_id}

    dr = _run(store, by_tool.get("covenant_debt"))
    debt = None
    if dr:
        o = dr.outputs
        debt = {"included": o.get("included", []), "excluded": o.get("excluded", []), "debt": o.get("debt"),
                "term": o.get("term"), "run_id": dr.run_id}

    lr = _run(store, by_tool.get("leverage"))
    leverage = None
    if lr:
        o = lr.outputs
        leverage = {"debt": o.get("debt"), "ebitda": o.get("ebitda"), "leverage": o.get("leverage"),
                    "run_id": lr.run_id}

    tr = _review_run(store, result, "limit_test", prefer_key="debt_capacity")
    limit_test = None
    if tr:
        o = tr.outputs
        limit_test = {k: o.get(k) for k in ("leverage", "limit", "wording", "verdict", "headroom_turns",
                                              "debt_capacity")}
        if "naive_flip_addback" in o:
            limit_test["naive_flip_addback"] = o["naive_flip_addback"]
        limit_test["run_id"] = tr.run_id

    tie = _review_run(store, result, "tie_out")
    tie_out = {"ok": result.tie_out_ok, "run_id": tie.run_id if tie else None}

    decisions = []
    for i in items:
        if i.type != "flag":
            continue
        chosen = next((o for o in i.options if o.id == i.answer), None)
        decisions.append({"id": i.id, "kind": i.payload.get("kind"), "question": i.question, "option_id": i.answer,
                          "label": chosen.label if chosen else None, "effect": chosen.effect if chosen else None,
                          "run_id": chosen.run_id if chosen else None, "state": i.state.value})

    appr = approval_item(items, result)
    rows = [a for a in store.audit if a.deal_id == deal.id]
    mappings = store.deal_mappings(deal.id)

    return {
        "header": {"deal": deal.name, "deal_id": deal.id, "platform": deal.platform, "target": deal.target,
                   "lender": brief.lender, "agreement_ref": brief.agreement_ref,
                   "limit_section": brief.limit_section, "limit_wording": brief.limit_wording,
                   "debt_term": brief.debt_term, "unit": UNIT,
                   "generated_at": datetime.now(timezone.utc).isoformat(), "backend": result.backend,
                   "result_id": result.id, "draft": True},
        "test_period": {"periods": periods, "note": brief.test_period_note},
        "ebitda": ebitda,
        "debt": debt,
        "leverage": leverage,
        "limit_test": limit_test,
        "tie_out": tie_out,
        "decisions": decisions,
        "approval": {"item_id": appr.id if appr else None, "state": appr.state.value if appr else None,
                     "audit": {"rows": len(rows), "chain_valid": chain_valid,
                               "denied": len([a for a in rows if a.result == "DENIED"])}},
        "mappings": {"count": len(mappings),
                     "from_policy": len([m for m in mappings if m.reason.startswith("Policy")])},
    }


# ---------------------------------------------------------------------------- rendering


def fmt(x) -> str:
    """Thousands with commas and 3 decimals. Tool outputs are stored at 3 decimals, so this does not round them."""
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return str(x)
    return f"{x:,.3f}"


def _fig(x, run_id) -> str:
    return f"{fmt(x)} [{run_id or 'no run'}]"


def _sections(cert: dict) -> list[tuple[str, list[str]]]:
    """Title and plain-text lines per section, shared by the Markdown and HTML renderers."""
    h = cert["header"]
    out = []
    out.append(("Header", [
        f"Deal: {h['deal']}",
        f"Platform: {h['platform']}. Target: {h['target']}",
        f"Lender: {h['lender']}",
        f"Agreement: {h['agreement_ref']}",
        f"Test: {h['limit_section']}, {h['limit_wording']}",
        f"Debt term: {h['debt_term']}",
        f"Unit: {h['unit']}",
        f"Generated: {h['generated_at']}",
        f"Result: {h['result_id']}",
        f"Agent output produced by the {h['backend']} backend. The gateway, the math, and the audit log are real.",
        DRAFT_NOTE,
    ]))

    tp = cert["test_period"]
    lines = [f"{company}: {', '.join(p) or 'no lines'}" for company, p in tp["periods"].items()]
    if tp["note"]:
        lines.append(tp["note"])
    out.append(("Test period", lines))

    e = cert["ebitda"]
    if e:
        rid = e["run_id"]
        lines = []
        for p in e["parts"]:
            lines.append(f"{p['company']}: net income {_fig(p['net_income'], rid)}, interest expense "
                         f"{_fig(p['interest_expense'], rid)}, interest income {_fig(p['interest_income'], rid)}, "
                         f"income taxes {_fig(p['income_taxes'], rid)}, depreciation and amortization "
                         f"{_fig(p['depreciation_amortization'], rid)}, subtotal {_fig(p['subtotal'], rid)}")
        lines.append(f"Base: {_fig(e['base'], rid)}")
        for a in e["addbacks"]:
            cap = f", cap {_fig(a['cap'], rid)}" if a.get("cap") is not None else ""
            tag = "inferred" if a.get("inferred") else "verified"
            lines.append(f"Add-back {a['name']}: amount {_fig(a['amount'], rid)}{cap}, applied "
                         f"{_fig(a['applied'], rid)} ({tag}; {a['source_ref']})")
        lines.append(f"Add-backs total: {_fig(e['addbacks_total'], rid)}")
        for d in e["deductions"]:
            tag = "inferred" if d.get("inferred") else "verified"
            lines.append(f"Deduction {d['name']}: {_fig(d['amount'], rid)} ({tag}; {d['source_ref']})")
        lines.append(f"Deductions total: {_fig(e['deductions_total'], rid)}")
        lines.append(f"EBITDA: {_fig(e['ebitda'], rid)}")
    else:
        lines = ["No ebitda run on the result."]
    out.append(("EBITDA", lines))

    d = cert["debt"]
    if d:
        rid = d["run_id"]
        lines = [f"Included: {x['line']} ({x['company']}) {_fig(x['amount'], rid)}" for x in d["included"]]
        lines += [f"Excluded: {x['line']} ({x['company']}) {_fig(x['amount'], rid)}"
                  + (f" - {x['note']}" if x.get("note") else "") for x in d["excluded"]]
        lines.append(f"{d['term']}: {_fig(d['debt'], rid)}")
    else:
        lines = ["No covenant_debt run on the result."]
    out.append(("Debt", lines))

    lv = cert["leverage"]
    if lv:
        rid = lv["run_id"]
        lines = [f"Debt: {_fig(lv['debt'], rid)}", f"EBITDA: {_fig(lv['ebitda'], rid)}",
                 f"Leverage: {_fig(lv['leverage'], rid)}"]
    else:
        lines = ["No leverage run on the result."]
    out.append(("Leverage", lines))

    t = cert["limit_test"]
    if t:
        rid = t["run_id"]
        lines = [f"Leverage: {_fig(t['leverage'], rid)}", f"Limit: {_fig(t['limit'], rid)} ({t['wording']})",
                 f"Verdict: {t['verdict']} [{rid}]", f"Headroom (turns): {_fig(t['headroom_turns'], rid)}",
                 f"Debt capacity: {_fig(t['debt_capacity'], rid)}"]
        if "naive_flip_addback" in t:
            lines.append(f"Whole-line reading reaches the limit at an add-back of {_fig(t['naive_flip_addback'], rid)}")
    else:
        lines = ["No limit_test run in the review."]
    out.append(("Limit test", lines))

    to = cert["tie_out"]
    out.append(("Tie-out", [f"Tie-out ok: {to['ok']} [{to['run_id'] or 'no run'}]"]))

    lines = []
    for x in cert["decisions"]:
        lines.append(f"{x['id']} ({x['kind'] or 'flag'}, {x['state']}): {x['question']} Chosen: {x['option_id']} "
                     f"- {x['label']}. Effect: {x['effect']} [{x['run_id'] or 'no run'}]")
    out.append(("Decisions", lines or ["No flags on this deal."]))

    a = cert["approval"]
    au = a["audit"]
    out.append(("Approval", [f"Approval item {a['item_id']}: {a['state']}",
                             f"Audit rows for the deal: {au['rows']}, chain valid: {au['chain_valid']}, "
                             f"denied attempts: {au['denied']}"]))

    m = cert["mappings"]
    out.append(("Mappings", [f"Mappings: {m['count']}, of which applied from a learned policy: {m['from_policy']}"]))
    return out


def render_markdown(cert: dict) -> str:
    parts = ["# Draft compliance certificate", ""]
    for title, lines in _sections(cert):
        parts += [f"## {title}", ""] + [f"- {line}" for line in lines] + [""]
    return "\n".join(parts)


def render_html(cert: dict) -> str:
    e = html.escape
    body = [f"<h1 style=\"font-size:20px\">{e('Draft compliance certificate')}</h1>"]
    for title, lines in _sections(cert):
        body.append(f"<h2 style=\"font-size:16px;margin-top:20px\">{e(title)}</h2>")
        body.append("<ul style=\"padding-left:20px\">" + "".join(f"<li>{e(line)}</li>" for line in lines) + "</ul>")
    return ("<!doctype html><html><head><meta charset=\"utf-8\"><title>Draft compliance certificate</title></head>"
            "<body style=\"font-family:system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;"
            "color:#111;background:#fff;line-height:1.45\">" + "".join(body) + "</body></html>")
