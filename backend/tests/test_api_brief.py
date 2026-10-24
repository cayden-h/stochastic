"""The Brief Reader routes (docs/tasks/tri.md T4) through HTTP, scripted backend, over Cayden's gateway (C3).

POST /deals takes agreement_txt or brief, exactly one; POST /deals/{id}/brief/amounts and /brief/approve are thin
over gateway.amend_brief and gateway.approve_brief; /case shows brief_draft. Every expected value was checked by
hand against the gateway's output, never the other way round:
- The synthetic agreement below says "ratio of Total Funded Debt to EBITDA of not more than 3.25 to 1.00" in
  section 6 and names FIRST HARBOR BANK, N.A. in the preamble, so the regex reader drafts limit 3.25, debt term
  "Total Funded Debt", lender "First Harbor Bank, N.A.", and two debt exclusions, all at confidence 0.5 (flags).
- The Kewaunee excerpt (tests/fixtures/kewaunee_ex101_excerpt.txt, under 15 words a quote) is matched by its hash,
  so the reader returns the fixture Brief with every amount at 0 and a flag on each: add-backs [0] pension 4,019 and
  [1] stock compensation 1,018, [2] transaction costs (cap 4,000) and [3] integration costs (cap 1,000), deduction [0]
  cash rent 1,970. With the three amounts entered, covenant EBITDA is 25,311.845 + 5,037 - 1,970 = 28,378.845 and
  leverage 21,633 / 28,378.845 = 0.7623 -> 0.762, the demo figure.
"""
import csv
import io
import json
import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

from app.api.errors import install_error_handlers  # noqa: E402
from app.api.events import next_events  # noqa: E402
from app.api.routes import build_router  # noqa: E402
from app.api.schemas import BriefAmountsResponse, CaseResponse  # noqa: E402
from app.core.models import BRIEF_READER, MAPPER, PREPARER, REVIEWER, State  # noqa: E402
from app.db.fixtures.kewaunee import BRIEF as FIXTURE_BRIEF  # noqa: E402
from app.db.fixtures.kewaunee import PLATFORM, TARGET, build_lines  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import BRIEF_TOOLS, Gateway, Invalid  # noqa: E402

from tests.test_api import BRIEF, TARGET_CSV, platform_csv  # noqa: E402

EXCERPT = (Path(__file__).parent / "fixtures" / "kewaunee_ex101_excerpt.txt").read_text()

# Written for this test (no cached filing). Same shape as the synthetic text in test_brief_reader_gateway.py.
SYNTHETIC = """CREDIT AGREEMENT
This CREDIT AGREEMENT is made between ACME HOLDINGS INC. (the "Borrower") and FIRST HARBOR BANK, N.A. (the "Lender").
1. Definitions . Capitalized terms used here are defined in Annex A.
6. Financial Covenants .
(a) Leverage . The Borrower shall maintain a ratio of Total Funded Debt to EBITDA of not more than 3.25 to 1.00 as of the last day of each fiscal quarter.
ANNEX A
"EBITDA" means net income plus interest expense plus income taxes plus depreciation and amortization.
"Total Funded Debt" means all indebtedness for borrowed money, excluding (i) obligations under operating leases of the Borrower and (ii) subordinated seller notes issued in the acquisition.
"""


@pytest.fixture
def world():
    """A fresh gateway on an empty memory store and an app over it, so tests can read the store and the audit log."""
    store = MemoryStore()
    gw = Gateway(store)
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(build_router(gw))
    return store, gw, TestClient(app)


def post_deal(c, agreement=SYNTHETIC, brief=None, headers=None, agreement_name="agreement.txt", plat=None, targ=None,
              platform="Acme", target="Bolt"):
    files = {"platform_csv": ("platform.csv", plat if plat is not None else platform_csv(), "text/csv"),
             "target_csv": ("target.csv", targ if targ is not None else TARGET_CSV, "text/csv")}
    if agreement is not None:
        files["agreement_txt"] = (agreement_name, agreement, "text/plain")
    data = {"name": "Acme buys Bolt", "platform": platform, "target": target}
    if brief is not None:
        data["brief"] = brief
    return c.post("/deals", files=files, data=data, headers=headers or {})


def case(c, deal_id):
    body = c.get(f"/deals/{deal_id}/case").json()
    CaseResponse.model_validate(body)
    return body


def brief_flags(body):
    return [f for f in body["flags"] if f["payload"].get("kind") == "brief_field"]


def answer_open_brief_flags(c, deal_id):
    for f in brief_flags(case(c, deal_id)):
        if f["state"] == "NEEDS_INFO":
            r = c.post(f"/work-items/{f['id']}/answer?auto_advance=false", json={"option_id": "confirm"})
            assert r.status_code == 200, r.text


def denied(store, action):
    return [r for r in store.audit if r.action == action and r.result == "DENIED"]


def fixture_csv(company: str) -> str:
    """One company's fixture lines in the upload format (data/README.md), so the Kewaunee deal goes through HTTP."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["line", "section", "period", "amount", "unit", "source_ref", "is_total", "covenant_tag"])
    for line in build_lines(MemoryStore()):
        if line.company == company:
            w.writerow([line.line, line.section, line.period, repr(line.amount), line.unit, line.source_ref,
                        str(line.is_total).lower(), line.covenant_tag])
    return out.getvalue()


def kewaunee_deal(c):
    r = post_deal(c, agreement=EXCERPT, agreement_name="kewaunee_ex101_excerpt.txt", plat=fixture_csv(PLATFORM),
                  targ=fixture_csv(TARGET), platform=PLATFORM, target=TARGET)
    assert r.status_code == 201, r.text
    return r.json()["deal_id"]


# ---- 1. exactly one of brief and agreement_txt ------------------------------------------------------------------

def test_post_deals_needs_exactly_one_of_brief_and_agreement(world):
    store, _, c = world
    neither = post_deal(c, agreement=None)
    assert neither.status_code == 422
    assert "brief" in neither.json()["detail"] and "agreement_txt" in neither.json()["detail"]
    both = post_deal(c, brief=json.dumps(BRIEF))
    assert both.status_code == 422 and "exactly one" in both.json()["detail"]
    assert post_deal(c, agreement_name="agreement.pdf").status_code == 422
    bad = post_deal(c, agreement=b"\xff\xfe\x00 not utf-8")
    assert bad.status_code == 422 and "agreement_txt" in bad.json()["detail"]
    assert post_deal(c, agreement="   \n").status_code == 422
    assert not store.deals
    # The JSON path is unchanged, and says its Brief is approved.
    r = post_deal(c, agreement=None, brief=json.dumps(BRIEF))
    assert r.status_code == 201 and r.json()["brief_status"] == "approved"


def test_an_oversized_agreement_is_refused(world):
    _, _, c = world
    r = post_deal(c, agreement=SYNTHETIC + "x" * (3 * 1024 * 1024))
    assert r.status_code == 422  # the `world` app has no BodyLimitMiddleware, so read_upload refuses it
    assert "agreement_txt" in r.json()["detail"]


# ---- 2. a deal from agreement text starts with no Brief ---------------------------------------------------------

def test_a_deal_from_agreement_text_has_no_brief_until_the_reader_runs(world):
    store, gw, c = world
    r = post_deal(c)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["brief_status"] == "none" and body["stage"] == "new"
    assert body["lines"] == {"platform": 6, "target": 4}
    got = case(c, body["deal_id"])
    assert got["deal"]["brief"] is None and got["deal"]["brief_status"] == "none" and got["brief_draft"] is None
    ag = gw.agreement(body["deal_id"])
    assert ag.source == "agreement.txt" and ag.text == SYNTHETIC
    assert any(a.action == "agreement:load" and a.deal_id == body["deal_id"] for a in store.audit)


def test_an_agent_cannot_create_a_deal_from_agreement_text(world):
    store, _, c = world
    assert post_deal(c, headers={"X-Actor": "agent:brief_reader"}).status_code == 403
    rows = denied(store, "create_deal")
    assert len(rows) == 1 and rows[0].actor == "agent:brief_reader"
    assert not store.deals and not store.agreements


# ---- 3. the run reads the agreement and stops on the Brief's flags ----------------------------------------------

def test_the_run_drafts_the_brief_with_citations_and_flags(world):
    store, gw, c = world
    did = post_deal(c).json()["deal_id"]
    run = c.post(f"/deals/{did}/run")
    assert run.status_code == 200, run.text
    assert run.json()["log"][-1] == "waiting on a flag"
    body = case(c, did)
    deal = store.deals[did]
    assert body["stage"] == deal.stage == "awaiting_brief"  # the stage store_brief sets
    assert body["deal"]["brief_status"] == "draft"
    draft = body["brief_draft"]
    assert draft is not None and draft == gw.brief_draft(did).model_dump(mode="json")
    assert draft["brief"]["limit"] == 3.25 and draft["brief"]["debt_term"] == "Total Funded Debt"
    assert draft["brief"]["lender"] == "First Harbor Bank, N.A."
    assert draft["amendments_supplied"] is False
    cited = {x["field"] for x in draft["citations"]}
    assert {"limit", "limit_section", "limit_wording", "lender", "ebitda_definition"} <= cited
    flags = brief_flags(body)
    assert flags and all(f["state"] == "NEEDS_INFO" for f in flags)
    assert set(draft["flags"]) <= {f["id"] for f in flags} and set(draft["flags"]) <= set(body["open_flags"])
    fields = {f["payload"]["field"] for f in flags}
    assert {"lender", "limit", "limit_wording", "debt_term", "debt_excludes[0]", "debt_excludes[1]"} <= fields
    assert not store.deal_items(did, "map_lines")


# ---- 4. the covenant tools wait for the approved Brief ----------------------------------------------------------

def test_the_covenant_tools_are_refused_before_approval(world):
    store, _, c = world
    did = post_deal(c).json()["deal_id"]
    c.post(f"/deals/{did}/run")
    # The gateway gates the three tools that read the Brief (BRIEF_TOOLS) with an IllegalTransition, so 409.
    assert set(BRIEF_TOOLS) == {"ebitda", "covenant_debt", "limit_test"}
    owner = {"ebitda": PREPARER, "covenant_debt": PREPARER, "limit_test": REVIEWER}  # the role allowed each tool
    for tool in BRIEF_TOOLS:
        r = c.post(f"/tools/{tool}", json={"deal_id": did, "inputs": {}}, headers={"X-Actor": owner[tool]})
        assert r.status_code == 409, (tool, r.text)
        assert "waits for the approved Brief" in r.json()["detail"]
        assert denied(store, f"tool:{tool}")


# ---- 5. the controller enters amounts ---------------------------------------------------------------------------

def test_the_controller_enters_an_add_back_amount_with_its_source(world):
    store, gw, c = world
    did = kewaunee_deal(c)
    c.post(f"/deals/{did}/run")
    before = case(c, did)
    assert before["brief_draft"]["brief"]["ebitda_addbacks"][0]["amount"] == 0.0
    flag = next(f for f in brief_flags(before) if f["payload"]["field"] == "ebitda_addbacks[0].amount")
    want = FIXTURE_BRIEF.ebitda_addbacks[0]
    assert want.name == "Noncash pension termination expense" and want.amount == 4019.0
    r = c.post(f"/deals/{did}/brief/amounts", json={"amounts": [
        {"field": "ebitda_addbacks[0].amount", "value": 4019.0, "source_ref": want.source_ref,
         "inferred": False, "note": "from the 10-K MD&A"}]})
    assert r.status_code == 200, r.text
    out = BriefAmountsResponse.model_validate(r.json())
    assert out.brief.ebitda_addbacks[0].amount == 4019.0 and out.brief.ebitda_addbacks[0].source_ref == want.source_ref
    assert out.brief_draft.brief.ebitda_addbacks[0].amount == 4019.0 and out.brief_status == "draft"
    after = case(c, did)
    assert after["brief_draft"]["brief"]["ebitda_addbacks"][0]["amount"] == 4019.0
    assert after["deal"]["brief"]["ebitda_addbacks"][0]["amount"] == 4019.0
    closed = next(f for f in after["flags"] if f["id"] == flag["id"])
    assert closed["answer"] == "amended" and flag["id"] not in after["open_flags"]
    row = next(a for a in store.audit if a.action == "brief:amend" and a.result == "ALLOWED")
    assert row.target == "ebitda_addbacks[0].amount" and "4,019.000" in row.reason


def test_a_new_add_back_is_added_by_its_name_then_its_amount(world):
    _, _, c = world
    did = post_deal(c).json()["deal_id"]
    c.post(f"/deals/{did}/run")
    r = c.post(f"/deals/{did}/brief/amounts", json={"amounts": [
        {"field": "ebitda_addbacks[0].name", "value": "Transaction costs"},
        {"field": "ebitda_addbacks[0].amount", "value": 250, "source_ref": "Bolt GL 6100, FY2025"}]})
    assert r.status_code == 200, r.text
    added = r.json()["brief"]["ebitda_addbacks"]
    assert [(a["name"], a["amount"], a["source_ref"]) for a in added] == [
        ("Transaction costs", 250.0, "Bolt GL 6100, FY2025")]


@pytest.mark.parametrize("value", ["1e400", "-1e400", "NaN", "Infinity", "1" + "0" * 400, "true", "1e12", '"4019"'])
def test_a_non_finite_amount_is_422_naming_the_field(world, value):
    store, _, c = world
    did = kewaunee_deal(c)
    c.post(f"/deals/{did}/run")
    raw = ('{"amounts": [{"field": "ebitda_addbacks[2].amount", "value": %s, "source_ref": "GL"}]}' % value)
    r = c.post(f"/deals/{did}/brief/amounts", content=raw, headers={"Content-Type": "application/json"})
    assert r.status_code == 422, r.text
    err = r.json()["detail"][0]
    assert err["loc"] == ["body", "amounts", 0, "value"] and "ebitda_addbacks[2].amount" in err["msg"]
    assert not [a for a in store.audit if a.action == "brief:amend"]


def test_amounts_refusals(world):
    store, _, c = world
    did = kewaunee_deal(c)
    assert c.post("/deals/nope/brief/amounts", json={"amounts": [{"field": "lender", "value": "x"}]}).status_code == 404
    # No draft yet: the gateway's 409.
    assert c.post(f"/deals/{did}/brief/amounts",
                  json={"amounts": [{"field": "lender", "value": "x"}]}).status_code == 409
    c.post(f"/deals/{did}/run")
    assert c.post(f"/deals/{did}/brief/amounts", json={"amounts": []}).status_code == 422
    unknown = c.post(f"/deals/{did}/brief/amounts", json={"amounts": [{"field": "unicorn", "value": 1}]})
    assert unknown.status_code == 422 and "unknown field 'unicorn'" in unknown.json()["detail"]
    no_source = c.post(f"/deals/{did}/brief/amounts",
                       json={"amounts": [{"field": "ebitda_addbacks[0].amount", "value": 4019.0}]})
    assert no_source.status_code == 422 and "needs its source" in no_source.json()["detail"]
    boolean = c.post(f"/deals/{did}/brief/amounts",
                     json={"amounts": [{"field": "ebitda_addbacks[0].amount", "value": True, "source_ref": "GL"}]})
    assert boolean.status_code == 422
    for actor in (BRIEF_READER, MAPPER, PREPARER):
        r = c.post(f"/deals/{did}/brief/amounts", headers={"X-Actor": actor},
                   json={"amounts": [{"field": "ebitda_addbacks[0].amount", "value": 1.0, "source_ref": "GL"}]})
        assert r.status_code == 403
    # no draft, the unknown field, the missing source, and the three agents (the empty list and the boolean are
    # refused by the request model before the gateway, with no row)
    assert len(denied(store, "amend_brief")) == 6
    assert store.deals[did].brief.ebitda_addbacks[0].amount == 0.0


def test_a_trailing_newline_in_the_field_path_is_refused(world):
    store, _, c = world
    did = post_deal(c).json()["deal_id"]
    c.post(f"/deals/{did}/run")
    r = c.post(f"/deals/{did}/brief/amounts", json={"amounts": [{"field": "lender\n", "value": "X"}]})
    assert r.status_code == 422 and r.json()["detail"][0]["loc"] == ["body", "amounts", 0, "field"]
    assert store.deals[did].brief.lender == "First Harbor Bank, N.A."


KEWAUNEE_FOUR = [{"field": "ebitda_addbacks[0].amount", "value": 4019.0, "source_ref": "10-K MD&A"},
                 {"field": "ebitda_addbacks[1].amount", "value": 1018.0, "source_ref": "10-K cash flow"},
                 {"field": "ebitda_addbacks[2].amount", "value": 500.0, "source_ref": ""},
                 {"field": "ebitda_deductions[0].amount", "value": 1970.0, "source_ref": "10-K lease note"}]


def test_a_bad_entry_refuses_the_whole_list_before_any_is_applied(world):
    """The review's case: entry [2] has no source. The dry run refuses the list naming amounts[2], and none of the
    four is applied (no brief:amend row, the add-backs still 0)."""
    store, _, c = world
    did = kewaunee_deal(c)
    c.post(f"/deals/{did}/run")
    r = c.post(f"/deals/{did}/brief/amounts", json={"amounts": KEWAUNEE_FOUR})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail.startswith("amounts[2] (ebitda_addbacks[2].amount): ") and "needs its source" in detail
    assert detail.endswith("nothing was applied")
    brief = store.deals[did].brief
    assert [a.amount for a in brief.ebitda_addbacks[:2]] == [0.0, 0.0] and brief.ebitda_deductions[0].amount == 0.0
    assert not [a for a in store.audit if a.action == "brief:amend"]
    assert denied(store, "amend_brief")[-1].target == "ebitda_addbacks[2].amount"


def test_a_gateway_refusal_mid_list_names_the_index_and_what_was_applied(world, monkeypatch):
    """When the dry run passes and the gateway still refuses entry [2] (here forced, the gateway cannot roll back),
    entries [0] and [1] stay applied, [3] is never tried, and the 422 says so."""
    store, gw, c = world
    did = kewaunee_deal(c)
    c.post(f"/deals/{did}/run")
    real, calls = gw.amend_brief, []

    def amend(actor, deal_id, field, value, **kw):
        calls.append(field)
        if len(calls) == 3:
            raise Invalid(f"{field}: refused by the gateway")
        return real(actor, deal_id, field, value, **kw)

    monkeypatch.setattr(gw, "amend_brief", amend)
    four = [dict(e, source_ref=e["source_ref"] or "10-K MD&A") for e in KEWAUNEE_FOUR]
    r = c.post(f"/deals/{did}/brief/amounts", json={"amounts": four})
    assert r.status_code == 422
    assert r.json()["detail"] == ("amounts[2] (ebitda_addbacks[2].amount): ebitda_addbacks[2].amount: refused by the "
                                  "gateway; applied before it and kept (no rollback): amounts[0] "
                                  "(ebitda_addbacks[0].amount), amounts[1] (ebitda_addbacks[1].amount)")
    assert calls == ["ebitda_addbacks[0].amount", "ebitda_addbacks[1].amount", "ebitda_addbacks[2].amount"]
    brief = store.deals[did].brief
    assert [a.amount for a in brief.ebitda_addbacks[:3]] == [4019.0, 1018.0, 0.0]
    assert brief.ebitda_deductions[0].amount == 0.0
    assert [a.target for a in store.audit if a.action == "brief:amend"] == calls[:2]


def test_only_the_controller_amends_and_approves_the_brief(world):
    store, _, c = world
    did = post_deal(c).json()["deal_id"]
    c.post(f"/deals/{did}/run")
    answer_open_brief_flags(c, did)
    intern = {"X-Actor": "human:intern"}
    r = c.post(f"/deals/{did}/brief/amounts", headers=intern, json={"amounts": [{"field": "lender", "value": "X"}]})
    assert r.status_code == 403 and "only human:controller" in r.json()["detail"]
    r = c.post(f"/deals/{did}/brief/approve", headers=intern)
    assert r.status_code == 403 and "only human:controller" in r.json()["detail"]
    for action in ("amend_brief", "approve_brief"):
        rows = denied(store, action)
        assert len(rows) == 1 and rows[0].actor == "human:intern"
    assert store.deals[did].brief_status == "draft" and store.deals[did].brief.lender == "First Harbor Bank, N.A."
    assert c.post(f"/deals/{did}/brief/approve").status_code == 200


# ---- 6. approval ------------------------------------------------------------------------------------------------

def test_approval_by_the_controller_then_the_deal_maps(world):
    store, gw, c = world
    did = post_deal(c).json()["deal_id"]
    c.post(f"/deals/{did}/run")
    for actor in (BRIEF_READER, MAPPER, PREPARER):
        assert c.post(f"/deals/{did}/brief/approve", headers={"X-Actor": actor}).status_code == 403
    open_first = c.post(f"/deals/{did}/brief/approve")
    assert open_first.status_code == 403 and "open" in open_first.json()["detail"]  # the gateway's Denied
    answer_open_brief_flags(c, did)
    assert c.post(f"/deals/{did}/run").json()["log"][-1] == "waiting on the controller to approve the Brief"
    assert case(c, did)["stage"] == "brief_ready"
    r = c.post(f"/deals/{did}/brief/approve")
    assert r.status_code == 200, r.text
    assert r.json()["brief_status"] == "approved" and r.json()["stage"] == "new" and r.json()["id"] == did
    assert r.json()["brief"]["limit"] == 3.25
    assert c.post(f"/deals/{did}/brief/approve").status_code == 409
    assert c.post(f"/deals/{did}/brief/amounts",
                  json={"amounts": [{"field": "lender", "value": "Someone else"}]}).status_code == 409
    assert len(denied(store, "approve_brief")) == 5  # three agents, the open flag, the second approve
    run = c.post(f"/deals/{did}/run")
    assert run.status_code == 200, run.text
    assert not any("brief reader" in line for line in run.json()["log"])
    assert store.deal_items(did, "map_lines")  # the Mapper ran on the approved Brief
    body = case(c, did)
    assert body["brief_draft"]["brief"]["limit"] == 3.25  # the approved draft stays readable on /case


def test_approve_unknown_deal_and_a_json_deal(world):
    _, _, c = world
    assert c.post("/deals/nope/brief/approve").status_code == 404
    did = post_deal(c, agreement=None, brief=json.dumps(BRIEF)).json()["deal_id"]
    assert c.post(f"/deals/{did}/brief/approve").status_code == 409  # already approved, no draft


def test_the_kewaunee_deal_through_http_ends_at_0_762(world):
    store, gw, c = world
    did = kewaunee_deal(c)
    assert c.post(f"/deals/{did}/run").json()["log"][-1] == "waiting on a flag"
    amounts = []
    for group in ("ebitda_addbacks", "ebitda_deductions"):
        for i, a in enumerate(getattr(FIXTURE_BRIEF, group)):
            if a.amount:
                amounts.append({"field": f"{group}[{i}].amount", "value": a.amount, "source_ref": a.source_ref,
                                "inferred": a.inferred, "note": a.note})
    assert [x["value"] for x in amounts] == [4019.0, 1018.0, 1970.0]
    assert c.post(f"/deals/{did}/brief/amounts", json={"amounts": amounts}).status_code == 200
    answer_open_brief_flags(c, did)
    assert c.post(f"/deals/{did}/brief/approve").status_code == 200
    c.post(f"/deals/{did}/run")
    for fid in case(c, did)["open_flags"]:
        flag = next(f for f in case(c, did)["flags"] if f["id"] == fid)
        assert c.post(f"/work-items/{fid}/answer?auto_advance=false", json={"option_id": flag["default"]}).status_code == 200
    c.post(f"/deals/{did}/run")
    body = case(c, did)
    assert body["verdict"]["leverage"] == 0.762  # 21,633 / 28,378.845
    assert body["result"]["ebitda"] == pytest.approx(28378.845, abs=0.001)
    assert gw.verify_chain()


# ---- 7. the Kewaunee excerpt returns the fixture Brief as the draft ---------------------------------------------

def test_the_kewaunee_excerpt_returns_the_fixture_brief_as_the_draft(world):
    _, _, c = world
    did = kewaunee_deal(c)
    c.post(f"/deals/{did}/run")
    draft = case(c, did)["brief_draft"]["brief"]
    for key in ("lender", "limit", "limit_section", "limit_wording", "debt_term", "debt_definition", "debt_excludes",
                "ebitda_definition"):
        assert draft[key] == json.loads(FIXTURE_BRIEF.model_dump_json())[key], key
    for group in ("ebitda_addbacks", "ebitda_deductions"):
        assert [(a["name"], a["amount"], a["cap"]) for a in draft[group]] == [
            (a.name, 0.0, a.cap) for a in getattr(FIXTURE_BRIEF, group)]
    assert draft["limit"] == 2.5 and draft["debt_term"] == "Senior Funded Bank Debt"


def test_a_second_upload_of_the_same_agreement_reuses_the_approved_brief(world):
    _, _, c = world
    did = post_deal(c).json()["deal_id"]
    c.post(f"/deals/{did}/run")
    answer_open_brief_flags(c, did)
    assert c.post(f"/deals/{did}/brief/approve").status_code == 200
    again = post_deal(c, agreement=SYNTHETIC.replace("\n", "\r\n"))
    assert again.status_code == 201 and again.json()["brief_status"] == "approved"
    assert case(c, again.json()["deal_id"])["deal"]["brief"]["limit"] == 3.25


# ---- 8. the stage event carries brief_status ----------------------------------------------------------------------

def _parse(events):
    out = []
    for e in events:
        lines = e.strip().split("\n")
        out.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return out


def test_the_stage_event_carries_brief_status(world):
    store, _, c = world
    did = post_deal(c).json()["deal_id"]
    events, seen, last = next_events(store, did, 0, None)
    stages = [d for k, d in _parse(events) if k == "stage"]
    assert [(s["stage"], s["brief_status"]) for s in stages] == [("new", "none")]
    c.post(f"/deals/{did}/run")
    events, seen, last = next_events(store, did, seen, last)
    stages = [d for k, d in _parse(events) if k == "stage"]
    assert [(s["stage"], s["brief_status"]) for s in stages] == [("awaiting_brief", "draft")]
    assert stages[0]["open_flags"] == [f.id for f in store.deal_items(did, "flag") if f.state == State.NEEDS_INFO]
    answer_open_brief_flags(c, did)
    c.post(f"/deals/{did}/brief/approve")
    events, seen, last = next_events(store, did, seen, last)
    stages = [d for k, d in _parse(events) if k == "stage"]
    assert [(s["stage"], s["brief_status"]) for s in stages] == [("new", "approved")]
    assert store.deals[did].brief_status == "approved"
