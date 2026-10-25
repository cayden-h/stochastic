"""The scripted backend: deterministic agent logic with no model.

It is the stage fallback when no model backend is available, and it is the reference for what a good answer looks
like. It applies the same rules the prompts give the model: policies first, synonyms from accounting practice and
from the filed Note 2 second, name similarity last, and a flag whenever confidence is low or a line holds two kinds
of debt. It says "scripted" in the result, so nobody can mistake it for a model run.
"""
from __future__ import annotations

import difflib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Callable

from app.core import agreement as agr
from app.core.models import (
    AdjustmentProposal,
    Adjustment,
    Brief,
    BriefCitation,
    BriefFieldFlag,
    BriefReaderInput,
    BriefReaderOutput,
    Evidence,
    FlagOption,
    FlagProposal,
    LineTag,
    MapperInput,
    MapperOutput,
    MappingProposal,
    Policy,
    PreparerInput,
    PreparerOutput,
    ReasonChip,
    ResultRow,
    ReviewerInput,
    ReviewerOutput,
    ToolRun,
)
from app.core.policies import newest_covering
from app.tools.finance import to_thousands

CallTool = Callable[[str, dict], ToolRun]

FLAG_THRESHOLD = 0.6

# The reasons the edit bubble offers (design/review-companion.md section 5). Hardcoded per deal for the demo, and
# the pitch says so; in the product, Claude would suggest them from the line, the change, and the filing notes.
DEMO_REASON_CHIPS: dict[str, list[ReasonChip]] = {
    "amount": [ReasonChip(id=0, label="One-time acquisition cost, an allowed add-back"),
               ReasonChip(id=1, label="Auditor's late adjustment"),
               ReasonChip(id=2, label="Correcting a typo in the source")],
    "remap": [ReasonChip(id=0, label="Not a cash equivalent (over 90 days)"),
              ReasonChip(id=1, label="Matches how the platform reports it"),
              ReasonChip(id=2, label="Auditor's reclassification")],
}
REASON_CHIPS: dict[str, dict[str, list[ReasonChip]]] = {"d_kequ_nuaire": DEMO_REASON_CHIPS}


def reason_chips(deal_id: str, kind: str) -> list[ReasonChip]:
    """The chips for an edit of this kind on this deal. A deal with no list of its own gets the demo deal's."""
    return list(REASON_CHIPS.get(deal_id, DEMO_REASON_CHIPS)[kind])


def _policy_for(inp: MapperInput, kind: str, company: str, key: str) -> Policy | None:
    """The newest live policy covering this line (app/core/policies.py), the same rule the gateway enforces."""
    return newest_covering(inp.policies, kind, key, company, inp.platform, inp.target)


def _policy_reason(pol: Policy) -> str:
    if pol.scope == "platform":
        return (f"Policy {pol.id} (every add-on of {pol.platform}): {pol.approved_by} decided this on "
                f"{pol.learned_from}: {pol.reason}")
    return f"Policy {pol.id}: {pol.approved_by} decided this on {pol.learned_from}"


def norm(s: str) -> str:
    s = s.lower().replace("’", "'")
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    s = re.sub(r"\b(net|the|and|of|at|less|total|current|portion|liability|liabilities|asset|assets)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# target line (normalized) -> (platform line, confidence, reason). Note 2 is the filed reclassification table.
SYNONYMS: dict[str, tuple[str, float, str]] = {
    "revenues": ("Net sales", 0.95, "Revenue line; Kewaunee calls it net sales"),
    "cost revenues": ("Cost of products sold", 0.95, "Cost of sales line"),
    "gross profit": ("Gross profit", 1.0, "Same subtotal"),
    "selling expense": ("Operating expenses", 0.85, "Kewaunee shows one operating expenses line"),
    "general administrative": ("Operating expenses", 0.85, "Kewaunee shows one operating expenses line"),
    "research development": ("Operating expenses", 0.85, "Kewaunee shows one operating expenses line"),
    "operating expense": ("Operating expenses", 0.9, "Subtotal of the three expense lines"),
    "income from operations": ("Operating profit", 0.95, "Same subtotal, different name"),
    "interest income": ("Other income, net", 0.8, "Ex 99.2 Note 2 reclassifies Interest Income - Net to Other income, net"),
    "other income": ("Other income, net", 0.9, "Same meaning"),
    "income before income taxes": ("Profit before income taxes", 0.95, "Same subtotal"),
    "provision for income taxes": ("Income tax (benefit) expense", 0.95, "Tax line"),
    "income": ("Net earnings", 0.95, "Net income is net earnings"),
    "depreciation amortization": ("Depreciation", 0.95, "Cash flow add-back line"),
    "cash cash equivalents": ("Cash and cash equivalents", 1.0, "Same line"),
    "certificates deposit": ("Cash and cash equivalents", 0.5, "Kewaunee has no investments line; could be cash equivalents or other current assets"),
    "accounts receivable": ("Receivables, less allowance", 0.95, "Trade receivables"),
    "inventories": ("Inventories", 1.0, "Same line"),
    "prepaid expenses": ("Prepaid expenses and other current assets", 0.95, "Same line"),
    "income taxes receivable": ("Prepaid expenses and other current assets", 0.75, "Ex 99.2 Note 2 moves income taxes receivable into prepaid and other current assets"),
    "leasehold improvements": ("Property, plant and equipment, at cost", 0.9, "Component of PP&E at cost"),
    "machinery equipment": ("Property, plant and equipment, at cost", 0.9, "Component of PP&E at cost"),
    "office furniture equipment": ("Property, plant and equipment, at cost", 0.9, "Component of PP&E at cost"),
    "vehicles": ("Property, plant and equipment, at cost", 0.9, "Component of PP&E at cost"),
    "software": ("Property, plant and equipment, at cost", 0.85, "Nu Aire carries software inside property and equipment"),
    "construction in process": ("Property, plant and equipment, at cost", 0.9, "Component of PP&E at cost"),
    "property equipment cost": ("Property, plant and equipment, at cost", 0.9, "PP&E at cost subtotal"),
    "accumulated depreciation": ("Accumulated depreciation", 1.0, "Same line"),
    "property equipment depreciated cost": ("Net Property, Plant and Equipment", 0.95, "Net PP&E subtotal"),
    "noncompete agreement": ("Other assets", 0.6, "Kewaunee has no intangibles line before the deal; smallest honest home is other assets"),
    "operating right use": ("Right of use assets", 0.95, "Operating lease asset"),
    "deferred tax": ("Deferred income taxes", 0.9, "Deferred tax asset"),
    "deposits": ("Other assets", 0.8, "Small long-term deposit"),
    "accounts payable": ("Accounts payable", 1.0, "Same line"),
    "lease operating": ("Current portion of operating lease liabilities", 0.95, "Current operating lease liability"),
    "income taxes payable": ("Other accrued expenses", 0.75, "Ex 99.2 Note 2 moves income taxes payable into other accrued expenses"),
    "accrued compensation": ("Employee compensation and amounts withheld", 0.85, "Compensation accrual"),
    "accrued commissions": ("Employee compensation and amounts withheld", 0.8, "Ex 99.2 Note 2 moves accrued commissions into employee compensation"),
    "other accrued expenses": ("Other accrued expenses", 1.0, "Same line"),
    "reserve for uncertain tax positions": ("Other non-current liabilities", 0.7, "Zero balance at 2024-09-30; a tax reserve belongs in other non-current liabilities"),
    "long term lease operating": ("Long-term portion of operating lease liabilities", 0.95, "Long-term operating lease liability"),
    "common stock": ("Common stock", 1.0, "Same line"),
    "additional paid in capital": ("Additional paid-in-capital", 1.0, "Same line"),
    "retained earnings": ("Retained earnings", 1.0, "Same line"),
}

TOTALS: dict[str, str] = {
    "total current assets": "Total Current Assets",
    "total assets": "Total Assets",
    "total current liabilities": "Total Current Liabilities",
    "total liabilities": "Total Liabilities",
    "total stockholders' equity": "Total Stockholders' Equity",
    "total liabilities and stockholders' equity": "Total Liabilities and Stockholders' Equity",
}


def _platform_names(inp: MapperInput, section: str) -> list[str]:
    return [l.line for l in inp.platform_lines if l.section == section]


def scripted_mapper(inp: MapperInput) -> MapperOutput:
    mappings: list[MappingProposal] = []
    flags: list[FlagProposal] = []
    tags: list[LineTag] = []
    for t in inp.target_lines:
        key = t.line.strip().lower()
        names = _platform_names(inp, t.section)
        pol = _policy_for(inp, "mapping", t.company, key)
        if pol:
            mappings.append(MappingProposal(target_line_id=t.id, platform_line=pol.decision or None, confidence=0.98,
                                            reason=_policy_reason(pol), policy_id=pol.id))
            continue
        if key in TOTALS and TOTALS[key] in names:
            mappings.append(MappingProposal(target_line_id=t.id, platform_line=TOTALS[key], confidence=1.0,
                                            reason="Same subtotal"))
            continue
        if t.is_total:
            # A target subtotal that the platform does not carry: its detail lines are mapped, so it is not added.
            pl = SYNONYMS.get(norm(t.line))
            mappings.append(MappingProposal(target_line_id=t.id, platform_line=pl[0] if pl else None,
                                            confidence=pl[1] if pl else 0.0,
                                            reason=(pl[2] if pl else "Subtotal with no platform equivalent") + "; parts are mapped"))
            continue
        n = norm(t.line)
        hit = SYNONYMS.get(n)
        if hit is None:
            # nearest synonym key, then nearest platform name
            close = difflib.get_close_matches(n, list(SYNONYMS), n=1, cutoff=0.8)
            if close:
                hit = SYNONYMS[close[0]]
        if hit is None:
            close = difflib.get_close_matches(t.line, names, n=1, cutoff=0.6)
            if close:
                ratio = difflib.SequenceMatcher(None, t.line.lower(), close[0].lower()).ratio()
                hit = (close[0], round(min(0.85, ratio), 2), f"Name similarity {ratio:.2f}")
        if hit is None:
            if t.is_total:
                mappings.append(MappingProposal(target_line_id=t.id, platform_line=None, confidence=0.0,
                                                reason="Subtotal with no platform equivalent; its parts are mapped"))
                continue
            hit = (None, 0.0, "No platform line found")
        platform_line, conf, reason = hit
        if platform_line is not None and platform_line not in names:
            conf, reason = min(conf, 0.5), f"{reason}; '{platform_line}' is not a {t.section} line on the platform"
        mappings.append(MappingProposal(target_line_id=t.id, platform_line=platform_line, confidence=conf, reason=reason))
        if conf < FLAG_THRESHOLD and not t.is_total:
            alt = [x for x in names if x != platform_line and not x.lower().startswith("total")]
            second = difflib.get_close_matches("other " + t.line, alt, n=1, cutoff=0.0)
            options = [FlagOption(id="a", label=f"Map to {platform_line}" if platform_line else "Leave unmapped",
                                  platform_line=platform_line)]
            if second:
                options.append(FlagOption(id="b", label=f"Map to {second[0]}", platform_line=second[0]))
            options.append(FlagOption(id="c", label="Leave unmapped and list it", platform_line=None))
            amount = f"{to_thousands(t.amount, t.unit):,.0f}K"
            why = f" The Mapper's best match is {platform_line} at confidence {conf:.2f}: {reason}." if platform_line \
                else " The Mapper found no platform line for it."
            flags.append(FlagProposal(kind="mapping", line_ids=[t.id],
                                      question=f"Where does {inp.target}'s '{t.line}' ({amount}) go on {inp.platform}'s "
                                               f"chart of accounts?{why}",
                                      evidence=[Evidence(quote=t.line, document_id=t.source_ref)],
                                      options=options, default="a"))

    # Covenant tags for balance sheet lines of both companies.
    unclear_ids: list[str] = []
    unclear_lines: list = []
    for line in list(inp.platform_lines) + list(inp.target_lines):
        if line.section != "balance_sheet":
            continue
        key = line.line.strip().lower()
        pol = _policy_for(inp, "covenant_tag", line.company, key)
        if pol:
            tags.append(LineTag(line_id=line.id, tag=pol.decision, note=f"Policy {pol.id} from {pol.approved_by}",
                                policy_id=pol.id))
            continue
        tag, note = _tag_rule(line.line, line.note)
        if tag == "unclear":
            unclear_ids.append(line.id)
            unclear_lines.append(line)
        tags.append(LineTag(line_id=line.id, tag=tag, note=note))

    if unclear_ids:
        # One flag for the financing liability family: it holds the sale-leaseback, the PNC debt, and the seller notes.
        def tag_for(line_name: str, rule: str) -> str:
            n = line_name.lower()
            if rule == "all":
                return "debt"
            if "seller" in n:
                return "debt" if rule == "bank_plus_sellers" else "not_debt"
            if "term loan" in n or "revolving" in n:
                return "debt"
            return "not_debt"  # the sale-leaseback portion

        def option(oid: str, label: str, rule: str) -> FlagOption:
            return FlagOption(id=oid, label=label, tags={l.id: tag_for(l.line, rule) for l in unclear_lines})

        def bucket(rule_line: str) -> str:
            n = rule_line.lower()
            return "sellers" if "seller" in n else "bank" if ("term loan" in n or "revolving" in n) else "lease"

        parts = {k: sum(to_thousands(l.amount, l.unit) for l in unclear_lines if bucket(l.line) == k)
                 for k in ("lease", "bank", "sellers")}
        whole = sum(parts.values())
        flags.insert(0, FlagProposal(
            kind="covenant_tag", line_ids=unclear_ids,
            question=f"{inp.platform}'s 'Financing liability' ({whole:,.0f}K across {len(unclear_lines)} lines) holds "
                     f"the Statesville sale-leaseback ({parts['lease']:,.0f}K), the new PNC term loan and revolver "
                     f"({parts['bank']:,.0f}K), and the 8% seller notes ({parts['sellers']:,.0f}K). Which parts count "
                     f"as {inp.brief.debt_term} under {inp.brief.limit_section}?",
            evidence=[Evidence(quote=inp.brief.limit_wording, document_id=f"{inp.brief.agreement_ref}, {inp.brief.limit_section}")]
                     + [Evidence(quote=x, document_id=inp.brief.agreement_ref) for x in inp.brief.debt_excludes],
            options=[
                option("a", "The whole line counts", "all"),
                option("b", "Only the PNC term loan and revolver count", "bank_only"),
                option("c", "PNC debt and the seller notes count", "bank_plus_sellers"),
            ],
            default="b",
        ))
    return MapperOutput(mappings=mappings, tags=tags, flags=flags,
                        note="scripted backend: synonyms from accounting practice and Ex 99.2 Note 2, name similarity, "
                             f"flag below {FLAG_THRESHOLD}; policies applied first")


def _tag_rule(line: str, note: str | None = None) -> tuple[str, str]:
    n = line.lower()
    if "financing liability" in n:
        return "unclear", "One line name holds the sale-leaseback financing and the acquisition financing"
    if "short-term borrowings" in n or "borrowings" in n:
        return "debt", "Borrowed money"
    if "financing lease" in n or "finance lease" in n:
        return "debt", "Finance leases count under the definition"
    if "operating lease" in n or "lease liability - operating" in n:
        return "na", "Operating leases are not borrowed money"
    if "notes payable" in n or "term loan" in n or "line of credit" in n or "revolv" in n:
        return "debt", "Borrowed money"
    return "na", ""


def scripted_preparer(inp: PreparerInput, call_tool: CallTool) -> PreparerOutput:
    cons = call_tool("consolidate", {})
    eb = call_tool("ebitda", {})
    debt = call_tool("covenant_debt", {"naive": False})
    lev = call_tool("leverage", {"debt_run_id": debt.run_id, "ebitda_run_id": eb.run_id})
    rows = [ResultRow(line=r["line"], section=r["section"], platform=r["platform"], target=r["target"],
                      combined=r["combined"], run_id=cons.run_id) for r in cons.outputs["rows"]]
    return PreparerOutput(adjustment_flags=_offer_adjustments(inp),rows=rows, ebitda=eb.outputs["ebitda"], debt=debt.outputs["debt"],
                          leverage=lev.outputs["leverage"], limit=inp.brief.limit,
                          run_ids=[cons.run_id, eb.run_id, debt.run_id, lev.run_id],
                          consolidate_run_id=cons.run_id, ebitda_run_id=eb.run_id, debt_run_id=debt.run_id,
                          leverage_run_id=lev.run_id,
                          note="scripted backend: consolidate, ebitda, covenant_debt, leverage")


def _offer_adjustments(inp: PreparerInput) -> list[AdjustmentProposal]:
    """Offer each learned adjustment on the line it covers: the same company's line of that name first, else the
    target's. The Preparer only asks; the controller decides, and the gateway applies nothing until then."""
    offers = []
    for adj in inp.adjustments:
        key = adj.line.strip().lower()
        named = [l for l in list(inp.platform_lines) + list(inp.target_lines)
                 if l.line.strip().lower() == key and not l.is_total]
        line = next((l for l in named if l.company == adj.company), None)
        line = line or next((l for l in inp.target_lines if l in named), None)
        if line is None:
            continue
        change = f"({abs(adj.amount):,.0f})" if adj.amount < 0 else f"+{adj.amount:,.0f}"
        now_k = to_thousands(line.amount, line.unit)
        offers.append(AdjustmentProposal(
            adjustment_id=adj.id, line_id=line.id,
            question=f"On an earlier deal the controller made a change of {change} to {adj.company}'s {adj.line} "
                     f"('{adj.reason}'). Make the same change of {change} to {line.company}'s {line.line} on this "
                     f"deal, from {now_k:,.0f}K to {now_k + adj.amount:,.0f}K?"))
    return offers


def scripted_reviewer(inp: ReviewerInput, call_tool: CallTool) -> ReviewerOutput:
    cons_run = inp.consolidate_run_id or (inp.rows[0].run_id if inp.rows else None)
    lev_run = inp.leverage_run_id or inp.run_ids[-1]
    reasons: list[str] = []
    run_ids: list[str] = []
    tie = call_tool("tie_out", {"run_id": cons_run})
    run_ids.append(tie.run_id)
    if not tie.outputs["ok"]:
        reasons.append(f"Tie-out failed ({tie.run_id}): rows {tie.outputs['bad_rows']}, balance {tie.outputs['balance_sheet_balances']}")
    # the leverage run is the last run id the Preparer listed
    test = call_tool("limit_test", {"leverage_run_id": lev_run})
    run_ids.append(test.run_id)
    if not test.outputs["ok"]:
        reasons.append(f"Leverage {test.outputs['leverage']:.2f}x is not below the {test.outputs['limit']:.2f}x limit ({test.run_id})")
    return ReviewerOutput(verdict="pass" if not reasons else "needs_attention", reasons=reasons, run_ids=run_ids)


# ---------------------------------------------------------------------------- the Brief Reader (D20)

QUOTES = Path(__file__).resolve().parents[4] / "data" / "brief" / "kewaunee_quotes.json"


@lru_cache(maxsize=1)
def kewaunee_quotes() -> dict:
    """The verbatim Ex 10.1 quotes, with the hashes of the texts they belong to. Empty if the file is missing."""
    try:
        return json.loads(QUOTES.read_text())
    except (OSError, ValueError):
        return {}


def scripted_brief_reader(inp: BriefReaderInput, call_tool: CallTool) -> BriefReaderOutput:
    """On Kewaunee's PNC agreement (matched by its hash), the fixture Brief with the verbatim quotes. On any other
    text, a regex read with low confidence, so the controller is asked about every field."""
    quotes = kewaunee_quotes()
    if quotes and inp.sha256 in quotes.get("sha256", {}).values():
        return _kewaunee_brief(quotes)
    return _regex_brief(inp, call_tool)


def _kewaunee_brief(quotes: dict) -> BriefReaderOutput:
    from app.db.fixtures.kewaunee import BRIEF  # imported here: the fixtures import the gateway, which imports us

    def unknown(a: Adjustment) -> Adjustment:
        return a.model_copy(update={"amount": 0.0, "inferred": True, "source_ref": quotes["source"],
                                    "note": "The agreement names it; the amount comes from the books."})

    brief = BRIEF.model_copy(update={
        "agreement_ref": quotes["source"],
        "ebitda_addbacks": [unknown(a) for a in BRIEF.ebitda_addbacks],
        "ebitda_deductions": [unknown(a) for a in BRIEF.ebitda_deductions],
        "closing_financing": [],  # Ex 99.2, not the agreement
        "test_period_note": "Tested as of the end of each fiscal quarter (Section 4.8(a)). The test period itself is "
                            "not in this Brief (stage 2).",
    })
    citations = [BriefCitation(field=c["field"], quote=c["quote"], section=c["section"], confidence=c["confidence"])
                 for c in quotes["citations"]]
    flags = [BriefFieldFlag(field=g["field"], question=g["question"],
                            evidence=[Evidence(quote=g["quote"], document_id=f"{quotes['source']}, {g['section']}")])
             for g in quotes.get("schema_gaps", [])]
    return BriefReaderOutput(brief=brief, citations=citations, flags=flags,
                             note="scripted backend: the Kewaunee Ex 10.1 quotes, matched by the agreement's hash")


_LIMIT = re.compile(r"ratio of (?P<term>[A-Z][\w ,'-]{2,60}?) to (?:Consolidated )?EBITDA of (?P<cmp>less than|not "
                    r"(?:more|greater) than|no (?:more|greater) than|not to exceed) (?P<x>\d+(?:\.\d+)?) to 1(?:\.0+)?")
# A lender's name ends in a bank word; a borrower's "INC." or "LLC" is not one.
_LENDER = re.compile(r"(?P<name>[A-Z][A-Z&.,' ]{2,80}?(?:BANK(?:, (?:N\.A\.|NATIONAL ASSOCIATION))?|ASSOCIATION|N\.A\.|CAPITAL))(?![A-Za-z])")


def _clip(text: str, start: int, words: int = 12) -> str:
    """At most `words` words of `text` from character `start`, as a quote."""
    return " ".join(text[start:].split()[:words])


def _regex_brief(inp: BriefReaderInput, call_tool: CallTool) -> BriefReaderOutput:
    citations: list[BriefCitation] = []
    flags: list[BriefFieldFlag] = []
    looked = ", ".join(inp.excerpts) or "none"
    where = f"not found in sections {looked}"
    fields = dict(lender="", limit=0.0, limit_section="", limit_wording="", debt_term="", debt_definition="",
                  ebitda_definition="", debt_excludes=[])

    def cite(field: str, quote: str, section: str) -> None:
        citations.append(BriefCitation(field=field, quote=quote, section=section, confidence=0.5,
                                       note="scripted regex read"))

    hit = next(((sid, m) for sid, body in inp.excerpts.items() if (m := _LIMIT.search(body))), None)
    if hit:
        sid, m = hit
        wording = agr.normalize(m.group(0))
        fields.update(limit=float(m.group("x")), limit_section=sid, limit_wording=wording,
                      debt_term=m.group("term").strip())
        for f in ("limit", "limit_section", "limit_wording"):
            cite(f, wording, sid)
    else:
        for f in ("limit", "limit_section", "limit_wording", "debt_term", "debt_definition"):
            flags.append(BriefFieldFlag(field=f, question=f"The leverage covenant's {f} was {where}."))

    def definition(term: str) -> tuple[str, str] | None:
        if term not in inp.definition_index:
            return None
        try:
            run = call_tool("get_definition", {"term": term})
        except Exception:  # noqa: BLE001 - a refused read is a field not found
            return None
        return run.outputs["text"], inp.definition_index[term]

    if fields["debt_term"]:
        got = definition(fields["debt_term"])
        if got:
            body, sid = got
            at = body.find(" means")
            fields["debt_definition"] = agr.normalize(body[at + 1:])[:600] if at >= 0 else body[:600]
            cite("debt_term", _clip(body, 0), sid)
            cite("debt_definition", _clip(body, max(at, 0) + 1), sid)
            ex = re.search(r"excluding (.+)", body)
            parts = [p.strip(" ,;.") for p in re.split(r"\((?:i|ii|iii|iv|v|vi)\)|;| and (?=\()", ex.group(1))
                     if p.strip(" ,;.")] if ex else []
            for i, part in enumerate(parts[:5]):
                fields["debt_excludes"].append(part[:300])
                cite(f"debt_excludes[{i}]", _clip(body, body.find(part), 8), sid)  # the words after it, if short
        else:
            flags.append(BriefFieldFlag(field="debt_definition",
                                        question=f"The definition of {fields['debt_term']} was {where} or the definitions."))
    got = definition("EBITDA")
    if got:
        body, sid = got
        fields["ebitda_definition"] = body[:600]
        cite("ebitda_definition", _clip(body, 0), sid)
    else:
        flags.append(BriefFieldFlag(field="ebitda_definition", question=f"The EBITDA definition was {where}."))
    flags.append(BriefFieldFlag(field="ebitda_addbacks", question="The scripted reader does not list add-backs or "
                                "deductions. Read the EBITDA definition and add each one with its cap."))
    try:
        pre = call_tool("get_section", {"id": agr.PREAMBLE}).outputs["text"]
    except Exception:  # noqa: BLE001
        pre = ""
    if m := _LENDER.search(pre):
        # Title case, keeping short all-caps words such as PNC as they are.
        fields["lender"] = " ".join(w if len(w.strip(",.")) <= 3 else w.title() for w in m.group("name").strip(" ,").split())
        cite("lender", _clip(pre, m.start()), agr.PREAMBLE)
    else:
        flags.append(BriefFieldFlag(field="lender", question="The lender was not found in sections preamble."))
    brief = Brief(agreement_ref="", ebitda_addbacks=[], ebitda_deductions=[], **fields)
    return BriefReaderOutput(brief=brief, citations=citations, flags=flags,
                             note="scripted backend: regex read of the limit and the definitions, low confidence")
