"""The Brief verifier (D23): code that checks every field of a draft Brief against the agreement text.

Pure functions, no store and no model. The gateway runs them after the Brief Reader's draft passed the nine draft
checks (brief-reader.md section 6), and turns each result into a conversation message and an audit row
(`Gateway.verify_brief`). The draft checks refuse a draft that breaks a rule; the verifier reports field by field what
it confirmed, so the controller (or, on the demo deal, the auto-approval) sees every quote, its section, and the result.

Per field, with the reader's best citation:
- verbatim: the quote is in the agreement, normalized as the draft checks normalize, and at least four words.
- in_section: the section the citation names exists, and its text contains the quote.
- number: a typed number equals the number in its quote. The limit (2.50) appears in its quote and in
  limit_wording; a cap in USD thousands (4000) appears as written ("$4,000,000").
- defined: the debt term and EBITDA are defined terms of the agreement; the debt definition and each exclusion are
  quoted from the debt term's own definition; each add-back and deduction is quoted from the EBITDA definition.
Per adjustment amount: a figure other than 0 has a source outside the agreement (the books), and 0 says it is not
applied.
"""
from __future__ import annotations

import re
from typing import Any

from app.core import agreement as agr
from app.core.models import Adjustment, Brief, BriefCheck, BriefCitation

EBITDA_TERM = "EBITDA"
_GROUPS = ("ebitda_addbacks", "ebitda_deductions")


def section_id(ref: str) -> str:
    """'Section 4.8(a)' and '4.8(a)' name the same section."""
    return re.sub(r"^(section|sec\.|§)\s*", "", (ref or "").strip(), flags=re.I)


def brief_paths(brief: Brief) -> dict[str, Any]:
    """Every required field of the draft checks, by path, with its value."""
    paths: dict[str, Any] = {k: getattr(brief, k) for k in ("lender", "limit", "limit_section", "limit_wording",
                                                             "debt_term", "debt_definition", "ebitda_definition")}
    for i, x in enumerate(brief.debt_excludes):
        paths[f"debt_excludes[{i}]"] = x
    for group in _GROUPS:
        for i, a in enumerate(getattr(brief, group)):
            paths[f"{group}[{i}].name"] = a.name
            if a.cap is not None:
                paths[f"{group}[{i}].cap"] = a.cap
    return paths


def _shown(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}" if value < 100 else f"{value:,.0f}"
    return str(value)[:160]


def _defined(text: str, term: str) -> bool:
    key = agr.normalize(term).casefold()
    return any(t.casefold() == key for t in agr.definition_index(text))


def check_field(path: str, value: Any, brief: Brief, cites: list[BriefCitation], text: str) -> BriefCheck:
    """One field against the agreement. Every check that applies must pass; the first failure is the reason."""
    index = agr.section_index(text)
    if not cites:
        return BriefCheck(field=path, value=_shown(value), section="", quote="", ok=False,
                          reason="no quote backs this field", checks=[])
    # The reader may give several quotes for a field; the one with the most confidence is checked first, and the
    # field passes on the first quote that passes every check.
    first_failure: BriefCheck | None = None
    for c in sorted(cites, key=lambda c: -c.confidence):
        result = _check_citation(path, value, brief, c, text, index)
        if result.ok:
            return result
        first_failure = first_failure or result
    return first_failure


def _check_citation(path: str, value: Any, brief: Brief, c: BriefCitation, text: str,
                    index: dict[str, str]) -> BriefCheck:
    sid = section_id(c.section)
    done: list[str] = []

    def result(ok: bool, reason: str) -> BriefCheck:
        return BriefCheck(field=path, value=_shown(value), section=sid, quote=c.quote, ok=ok, reason=reason,
                          checks=list(done))

    if not agr.quote_in(c.quote, text):
        return result(False, f"the quote is not in the agreement word for word, or is under {agr.MIN_QUOTE_WORDS} "
                             f"words")
    done.append("verbatim")
    if sid not in index:
        return result(False, f"section '{c.section}' is not in the agreement")
    body = agr.section_text(text, sid) or ""
    if not agr.quote_in(c.quote, body):
        return result(False, f"the quote is in the agreement but not in section {sid}")
    done.append("in_section")
    said = [f"quote verbatim in section {sid}"]

    if path == "limit":
        if not agr.ratio_in(c.quote, float(value)):
            return result(False, f"the limit {float(value):.2f} is not in its quote")
        if sid != section_id(brief.limit_section):
            return result(False, f"the limit is quoted from {sid}, not from limit_section {brief.limit_section}")
        done.append("number")
        said.append(f"{float(value):.2f} in the quote")
    elif path.endswith(".cap"):
        if not agr.thousands_in(c.quote, float(value)):
            return result(False, f"the cap {float(value):,.0f}K is not in its quote")
        done.append("number")
        said.append(f"${float(value) * 1000:,.0f} in the quote")
    elif path == "limit_wording":
        if not agr.ratio_in(str(value), brief.limit):
            return result(False, f"the limit {brief.limit:.2f} is not in limit_wording")
        limit_body = agr.section_text(text, section_id(brief.limit_section)) or ""
        if not agr.quote_in(str(value), limit_body):
            return result(False, f"limit_wording is not a quote from the limit section {brief.limit_section}")
        if brief.debt_term.casefold() not in agr.normalize(str(value)).casefold():
            return result(False, f"the debt term '{brief.debt_term}' is not in limit_wording")
        done.append("number")
        said.append(f"the wording is verbatim and states {brief.limit:.2f} and {brief.debt_term}")
    elif path == "limit_section":
        if sid != section_id(str(value)):
            return result(False, f"the quote is from {sid}, not from {value}")
        said = [f"section {sid} exists and holds the covenant"]
    elif path == "debt_term":
        if not _defined(text, str(value)):
            return result(False, f"'{value}' is not a defined term of the agreement")
        if agr.normalize(str(value)).casefold() not in agr.normalize(c.quote).casefold():
            return result(False, f"the quote does not name '{value}'")
        done.append("defined")
        said.append(f"'{value}' is defined")
    elif path in ("debt_definition",) or path.startswith("debt_excludes["):
        definition = agr.definition_text(text, brief.debt_term)
        if definition is None:
            return result(False, f"'{brief.debt_term}' is not defined in the agreement")
        if not agr.quote_in(c.quote, definition):
            return result(False, f"the quote is not from the definition of '{brief.debt_term}'")
        done.append("defined")
        said.append(f"from the definition of {brief.debt_term}")
    elif path == "ebitda_definition" or any(path.startswith(f"{g}[") for g in _GROUPS):
        definition = agr.definition_text(text, EBITDA_TERM)
        if definition is None:
            return result(False, "EBITDA is not defined in the agreement")
        if not agr.quote_in(c.quote, definition):
            return result(False, "the quote is not from the definition of EBITDA")
        done.append("defined")
        said.append("from the definition of EBITDA")
    return result(True, "; ".join(said))


def check_amount(path: str, adj: Adjustment, agreement_ref: str) -> BriefCheck:
    """An amount other than 0 needs its source outside the agreement; 0 means the adjustment is not applied."""
    source = (adj.source_ref or "").strip()
    inferred = " (inferred)" if adj.inferred else ""
    if adj.amount == 0:
        return BriefCheck(field=path, value="0", section=source or agreement_ref, quote=adj.note or source,
                          ok=True, reason="not applied", checks=["source"])
    if not source or source in (agreement_ref,) or source.startswith(agreement_ref or "\0"):
        return BriefCheck(field=path, value=_shown(adj.amount), section=source, quote=adj.note, ok=False,
                          reason="the amount has no source outside the agreement", checks=[])
    return BriefCheck(field=path, value=_shown(adj.amount), section=source.split(":")[0], quote=source,
                      ok=True, reason=f"from the books{inferred}", checks=["source"])


def verify(brief: Brief, citations: list[BriefCitation], text: str, agreement_ref: str) -> list[BriefCheck]:
    """Every field and every amount of the Brief, in the Brief's order."""
    by_field: dict[str, list[BriefCitation]] = {}
    for c in citations:
        by_field.setdefault(c.field, []).append(c)
    fields = brief_paths(brief)
    if brief.test_period_note and "test_period_note" in by_field:  # optional: checked when the reader quoted it
        fields["test_period_note"] = brief.test_period_note
    out = [check_field(path, value, brief, by_field.get(path, []), text) for path, value in fields.items()]
    for group in _GROUPS:
        for i, a in enumerate(getattr(brief, group)):
            out.append(check_amount(f"{group}[{i}].amount", a, agreement_ref))
    return out


def _key(name: str) -> str:
    """An adjustment's name as the books and the Brief may both write it: case, '(capped)', and a leading 'any'
    do not matter. Nothing fuzzier, so a different adjustment never takes another's amount."""
    n = agr.normalize(name).casefold()
    n = re.sub(r"\s*\(capped\)\s*$", "", n)
    return re.sub(r"^any\s+", "", n)


def book_amount(adj: Adjustment, books: list[Adjustment]) -> Adjustment | None:
    """The deal's book amount for this adjustment, matched by name, or None."""
    key = _key(adj.name)
    return next((b for b in books if _key(b.name) == key), None)
