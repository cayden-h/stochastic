"""The scripted backend: deterministic agent logic with no model.

It is the stage fallback when no model backend is available, and it is the reference for what a good answer looks
like. It applies the same rules the prompts give the model: policies first, synonyms from accounting practice and
from the filed Note 2 second, name similarity last, and a flag whenever confidence is low or a line holds two kinds
of debt. It says "scripted" in the result, so nobody can mistake it for a model run.
"""
from __future__ import annotations

import difflib
import re
from typing import Callable

from app.core.models import (
    Evidence,
    FlagOption,
    FlagProposal,
    LineTag,
    MapperInput,
    MapperOutput,
    MappingProposal,
    PreparerInput,
    PreparerOutput,
    ResultRow,
    ReviewerInput,
    ReviewerOutput,
    ToolRun,
)

CallTool = Callable[[str, dict], ToolRun]

FLAG_THRESHOLD = 0.6


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
    mapping_policies = {p.pattern: p for p in inp.policies if p.kind == "mapping"}
    tag_policies = {p.pattern: p for p in inp.policies if p.kind == "covenant_tag"}

    for t in inp.target_lines:
        key = t.line.strip().lower()
        names = _platform_names(inp, t.section)
        pol = mapping_policies.get(key)
        if pol:
            mappings.append(MappingProposal(target_line_id=t.id, platform_line=pol.decision or None, confidence=0.98,
                                            reason=f"Policy {pol.id}: {pol.approved_by} decided this on {pol.learned_from}",
                                            policy_id=pol.id))
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
            flags.append(FlagProposal(kind="mapping", line_ids=[t.id],
                                      question=f"Where does the target's '{t.line}' belong on the platform's chart?",
                                      evidence=[Evidence(quote=t.line, document_id=t.source_ref)],
                                      options=options, default="a"))

    # Covenant tags for balance sheet lines of both companies.
    unclear_ids: list[str] = []
    unclear_lines: list = []
    for line in list(inp.platform_lines) + list(inp.target_lines):
        if line.section != "balance_sheet":
            continue
        key = line.line.strip().lower()
        pol = tag_policies.get(key)
        if pol:
            tags.append(LineTag(line_id=line.id, tag=pol.decision, note=f"Policy {pol.id} from {pol.approved_by}",
                                policy_id=pol.id))
            continue
        tag, note = _tag_rule(line.line)
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

        total = sum(l.amount for l in unclear_lines)
        flags.insert(0, FlagProposal(
            kind="covenant_tag", line_ids=unclear_ids,
            question=f"'Financing liability' holds the Statesville sale-leaseback, the new PNC term loan and revolver, "
                     f"and the 8% seller notes. Which parts count as {inp.brief.debt_term}?",
            evidence=[Evidence(quote=inp.brief.limit_wording, document_id=f"{inp.brief.agreement_ref}, {inp.brief.limit_section}")]
                     + [Evidence(quote=x, document_id=inp.brief.agreement_ref) for x in inp.brief.debt_excludes],
            options=[
                option("a", f"Whole line counts ({total:,.0f}K)", "all"),
                option("b", "Only the PNC term loan and revolver count", "bank_only"),
                option("c", "PNC debt and the seller notes count", "bank_plus_sellers"),
            ],
            default="b",
        ))
    return MapperOutput(mappings=mappings, tags=tags, flags=flags,
                        note="scripted backend: synonyms from accounting practice and Ex 99.2 Note 2, name similarity, "
                             f"flag below {FLAG_THRESHOLD}; policies applied first")


def _tag_rule(line: str) -> tuple[str, str]:
    n = line.lower()
    if "financing liability" in n:
        return "unclear", "One line name holds the sale-leaseback financing and the acquisition financing"
    if "short-term borrowings" in n or "borrowings" in n:
        return "debt", "Borrowed money"
    if "financing lease" in n or "finance lease" in n:
        return "debt", "Finance leases count under the definition"
    if "operating lease" in n or "lease liability - operating" in n:
        return "not_debt", "Operating leases are not borrowed money"
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
    return PreparerOutput(rows=rows, ebitda=eb.outputs["ebitda"], debt=debt.outputs["debt"],
                          leverage=lev.outputs["leverage"], limit=inp.brief.limit,
                          run_ids=[cons.run_id, eb.run_id, debt.run_id, lev.run_id],
                          note="scripted backend: consolidate, ebitda, covenant_debt, leverage")


def scripted_reviewer(inp: ReviewerInput, call_tool: CallTool) -> ReviewerOutput:
    cons_run = inp.rows[0].run_id if inp.rows else None
    lev_run = next((r for r in inp.run_ids if r.startswith("run")), None)
    reasons: list[str] = []
    run_ids: list[str] = []
    tie = call_tool("tie_out", {"run_id": cons_run})
    run_ids.append(tie.run_id)
    if not tie.outputs["ok"]:
        reasons.append(f"Tie-out failed ({tie.run_id}): rows {tie.outputs['bad_rows']}, balance {tie.outputs['balance_sheet_balances']}")
    # the leverage run is the last run id the Preparer listed
    test = call_tool("limit_test", {"leverage_run_id": inp.run_ids[-1]})
    run_ids.append(test.run_id)
    if not test.outputs["ok"]:
        reasons.append(f"Leverage {test.outputs['leverage']:.2f}x is not below the {test.outputs['limit']:.2f}x limit ({test.run_id})")
    return ReviewerOutput(verdict="pass" if not reasons else "needs_attention", reasons=reasons, run_ids=run_ids)
