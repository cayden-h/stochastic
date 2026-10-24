"""Illustrative demo data. The company, numbers, and quotes are invented placeholders.

They only show the shapes the console will display. They are not real filings.
"""
from app.core.models import Clause, Deal, Evidence, Fact, Option, Plan
from app.db.memory import MemoryStore
from app.gateway.gateway import Gateway
from app.tools.quote_validator import quote_in_document

DEAL_ID = "d_demo"
DOC_ID = "doc_agreement"
DOC_TEXT = (
    "Section 7.1. The Total Net Leverage Ratio shall not exceed 3.00 to 1.00 at the end of any fiscal quarter. "
    "Disqualified Stock means any stock that is redeemable at the option of the holder on or before the "
    "date that is 91 days after the Maturity Date. "
    "As of the Closing Date, the outstanding Term Loan is $100.0 million. "
    "Consolidated EBITDA for the trailing twelve months was $40.0 million."
)

Q_LIMIT = "The Total Net Leverage Ratio shall not exceed 3.00 to 1.00"
Q_DQ = "redeemable at the option of the holder on or before the date that is 91 days after the Maturity Date"
Q_DEBT = "the outstanding Term Loan is $100.0 million"
Q_EBITDA = "Consolidated EBITDA for the trailing twelve months was $40.0 million"

EXISTING_SENIOR = 100.0
EBITDA = 40.0
LIMIT = 3.0


def seed_demo(store: MemoryStore, gw: Gateway) -> None:
    store.deals[DEAL_ID] = Deal(
        id=DEAL_ID, name="Northwind Foods (illustrative)", situation="Raising money", stage="Needs your input",
        brief="Raise $60M of new capital under the existing credit agreement. Illustrative data only.",
    )
    store.documents[DOC_ID] = DOC_TEXT

    def ev(quote: str, page: int) -> Evidence:
        return Evidence(quote=quote, page=page, document_id=DOC_ID)

    for key, value, quote, page in [
        ("Existing term loan", "$100.0M", Q_DEBT, 14),
        ("Trailing EBITDA", "$40.0M", Q_EBITDA, 12),
    ]:
        fid = store.next_id("fact")
        store.facts[fid] = Fact(id=fid, deal_id=DEAL_ID, key=key, value=value, evidence=ev(quote, page),
                                checked=quote_in_document(quote, DOC_TEXT), confirmed=True)

    limit_clause = ev(Q_LIMIT, 71)
    cid = store.next_id("clause")
    store.clauses[cid] = Clause(id=cid, deal_id=DEAL_ID, section="7.1 Leverage limit",
                                meaning="Total net debt may not exceed 3.0x EBITDA.", evidence=limit_clause,
                                confidence=0.97, checked=quote_in_document(Q_LIMIT, DOC_TEXT))
    cid = store.next_id("clause")
    store.clauses[cid] = Clause(id=cid, deal_id=DEAL_ID, section="1.1 Disqualified Stock",
                                meaning="Unclear whether redeemable preferred counts as debt.", evidence=ev(Q_DQ, 94),
                                confidence=0.55, checked=quote_in_document(Q_DQ, DOC_TEXT))

    gw.propose("agent:intake", DEAL_ID, "extract_facts", payload={"facts": 2})

    gw.ask("agent:clause_reader", DEAL_ID, "clarify_clause", "E3",
           "Does redeemable preferred count as debt under this agreement?",
           [ev(Q_DQ, 94)],
           [Option(id="debt", label="Counts as debt", effect="Plan B net leverage 4.00x. Over the 3.00x max by 1.00x."),
            Option(id="equity", label="Does not count", effect="Plan B net leverage 2.50x. Room of 0.50x.")],
           default="debt",
           context="The preferred can be redeemed in 2031. The loan matures in 2026. The text does not say if that counts.")

    def plan(name: str, instruments: dict[str, float], cost: float, dilution: float, run: str,
             breach_pct: float | None = None, consent: str | None = None) -> Plan:
        metrics = {"cost_of_capital_pct": cost, "dilution_pct": dilution}
        if breach_pct is not None:
            metrics["breach_pct"] = breach_pct
        return Plan(id=store.next_id("plan"), deal_id=DEAL_ID, name=name, instruments=instruments,
                    metrics=metrics, run_id=run, needs_consent=consent is not None, consent_note=consent)

    plans = [
        plan("A. Junior debt $60M", {"junior": 60.0}, 11.5, 0.0, "run_001"),
        plan("B. Preferred $60M", {"preferred": 60.0}, 13.0, 8.0, "run_002", breach_pct=9.0),
        plan("C. Junior $60M with consent", {"junior": 60.0}, 12.1, 0.0, "run_004", breach_pct=31.0,
             consent="Lender vote. Fee 75 bp"),
    ]
    blocked = plans[0]
    for p in plans:
        try:
            gw.post_plan("agent:structuring", p, EXISTING_SENIOR, EBITDA, LIMIT, False, limit_clause)
        except Exception:
            pass
    gw.ask("agent:structuring", DEAL_ID, "plan_blocked", "E4",
           f"{blocked.name} breaks the leverage limit. How do we proceed?",
           [limit_clause],
           [Option(id="redesign", label="Redesign inside the limit", effect="Plan B fits at 2.50x"),
            Option(id="consent", label="Ask the lender for consent", effect="Keeps plan A. Fee 75 bp and a lender vote")],
           default="redesign")

    gw.propose("agent:memo", DEAL_ID, "recommend", escalation="E6",
               payload={"recommended_plan": plans[1].id,
                        "summary": "Plan B has the lowest chance of breach and needs no consent."})
