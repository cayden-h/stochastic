"""Tests for the trust rules (docs/STOCHASTIC.md section 9) and the math on the real Kewaunee figures."""
import os

import pytest
from fastapi.testclient import TestClient

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

from app.agents.jobs import advance  # noqa: E402
from app.core.models import CONTROLLER, MAPPER, PREPARER, PreparerOutput, ResultRow  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Denied, Gateway, IllegalTransition, Invalid  # noqa: E402
from app.main import create_app  # noqa: E402
from app.tools import finance  # noqa: E402


@pytest.fixture
def world():
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    return store, gw


def answer_all(gw, option=None):
    for flag in gw.open_flags(DEAL_ID):
        gw.answer(CONTROLLER, flag.id, option or flag.default or flag.options[0].id)


def run_to_approval(gw):
    advance(gw, DEAL_ID)
    answer_all(gw)
    advance(gw, DEAL_ID)
    return [i for i in gw.store.deal_items(DEAL_ID, "approve_result")][-1]


# ---- the moment: the flag and the two readings -------------------------------------------------------------

def test_mapper_flags_the_financing_liability_and_effects_are_computed(world):
    store, gw = world
    advance(gw, DEAL_ID)
    flags = gw.open_flags(DEAL_ID)
    fin = next(f for f in flags if "Financing liability" in (f.question or ""))
    effects = {o.id: o.effect for o in fin.options}
    assert "Over the limit" in effects["a"]  # whole line counted: 2.57x
    assert "OK" in effects["b"]  # covenant reading: 0.77x
    assert all(o.run_id for o in fin.options)  # every effect traces to a limit_test run


def test_naive_and_covenant_leverage_differ_on_real_figures(world):
    store, gw = world
    advance(gw, DEAL_ID)
    answer_all(gw)
    eb = gw.run_tool("system:gateway", DEAL_ID, "ebitda", {}).outputs["ebitda"]
    covenant = gw.run_tool("system:gateway", DEAL_ID, "covenant_debt", {}).outputs["debt"]
    # naive: retag the sale-leaseback and seller notes as debt
    for line in store.lines(DEAL_ID):
        if "financing liability" in line.line.lower():
            line.covenant_tag = "debt"
    naive = gw.run_tool("system:gateway", DEAL_ID, "covenant_debt", {}).outputs["debt"]
    assert round(eb, 1) == 28032.6  # 18,043 Kewaunee + 7,782.6 Nu Aire + 4,177 pension - 1,970 rent
    assert covenant == 21633.0  # 15,000 + 5,563 + 805 + 109 + 156
    assert naive == 71955.0  # plus 27,782 sale-leaseback and 22,540 seller notes
    assert covenant / eb < 2.5 < naive / eb


def test_tie_out_balances_the_combined_balance_sheet(world):
    store, gw = world
    item = run_to_approval(gw)
    result = store.results[item.payload["result_id"]]
    assert result.tie_out_ok is True
    cons = store.tool_runs[result.rows[0].run_id].outputs
    assert cons["unmapped_target_lines"] == []
    total_assets = next(r for r in result.rows if r.line == "Total Assets")
    assert total_assets.combined == pytest.approx(134478 + 47978.181, abs=0.01)


# ---- gateway rules -------------------------------------------------------------------------------------------

def test_chain_is_valid_after_full_run(world):
    store, gw = world
    item = run_to_approval(gw)
    gw.approve(CONTROLLER, item.id)
    assert store.deals[DEAL_ID].stage == "posted"
    assert store.audit[-1].actor == "system:gateway" and store.audit[-1].action == "post"
    assert gw.verify_chain()


def test_tampering_breaks_the_chain(world):
    store, gw = world
    store.audit[0].reason = "changed after the fact"
    assert not gw.verify_chain()


def test_agents_cannot_approve_and_denial_is_logged(world):
    store, gw = world
    item = run_to_approval(gw)
    for actor in (PREPARER, "agent:reviewer", MAPPER):
        with pytest.raises(Denied):
            gw.approve(actor, item.id)
        assert store.audit[-1].result == "DENIED" and store.audit[-1].actor == actor


def test_proposer_cannot_approve_own_item(world):
    store, gw = world
    item = run_to_approval(gw)
    item.proposed_by = CONTROLLER
    with pytest.raises(Denied):
        gw.approve(CONTROLLER, item.id)


def test_result_cannot_be_approved_before_review_passes(world):
    store, gw = world
    item = run_to_approval(gw)
    store.results[item.payload["result_id"]].review = None
    with pytest.raises(Denied):
        gw.approve(CONTROLLER, item.id)


def test_agent_can_call_only_its_tools(world):
    store, gw = world
    with pytest.raises(Denied):
        gw.run_tool(MAPPER, DEAL_ID, "ebitda", {})
    with pytest.raises(Denied):
        gw.run_tool("agent:reviewer", DEAL_ID, "consolidate", {})
    assert store.audit[-1].result == "DENIED"


def test_numbers_without_a_run_id_are_refused(world):
    store, gw = world
    advance(gw, DEAL_ID)
    answer_all(gw)
    item = gw.create_item(DEAL_ID, "prepare_result")
    fake = PreparerOutput(rows=[ResultRow(line="Net sales", section="income_statement", platform=1, target=1,
                                          combined=2, run_id="run_999")],
                          ebitda=28032.6, debt=21633.0, leverage=0.77, limit=2.5, run_ids=["run_999"])
    with pytest.raises(Invalid):
        gw.store_result(PREPARER, item.id, fake)
    assert store.audit[-1].result == "DENIED"


def test_model_made_number_is_refused_even_with_real_run_ids(world):
    store, gw = world
    advance(gw, DEAL_ID)
    answer_all(gw)
    item = gw.create_item(DEAL_ID, "prepare_result")
    cons = gw.run_tool(PREPARER, DEAL_ID, "consolidate", {})
    eb = gw.run_tool(PREPARER, DEAL_ID, "ebitda", {})
    debt = gw.run_tool(PREPARER, DEAL_ID, "covenant_debt", {})
    lev = gw.run_tool(PREPARER, DEAL_ID, "leverage", {"debt_run_id": debt.run_id, "ebitda_run_id": eb.run_id})
    rows = [ResultRow(line=r["line"], section=r["section"], platform=r["platform"], target=r["target"],
                      combined=r["combined"], run_id=cons.run_id) for r in cons.outputs["rows"]]
    bad = PreparerOutput(rows=rows, ebitda=eb.outputs["ebitda"], debt=debt.outputs["debt"], leverage=0.5, limit=2.5,
                         run_ids=[cons.run_id, eb.run_id, debt.run_id, lev.run_id])
    with pytest.raises(Invalid):
        gw.store_result(PREPARER, item.id, bad)


def test_illegal_transition_is_refused(world):
    store, gw = world
    advance(gw, DEAL_ID)
    flag = gw.open_flags(DEAL_ID)[0]
    with pytest.raises(IllegalTransition):
        gw.approve(CONTROLLER, flag.id)  # still NEEDS_INFO
    with pytest.raises(IllegalTransition):
        gw.answer(CONTROLLER, flag.id, "zzz")


def test_consolidate_refuses_while_a_flag_is_open(world):
    store, gw = world
    advance(gw, DEAL_ID)
    with pytest.raises(Invalid):
        gw.run_tool(PREPARER, DEAL_ID, "consolidate", {})


def test_reverse_is_a_new_item_and_nothing_is_deleted(world):
    store, gw = world
    item = run_to_approval(gw)
    gw.approve(CONTROLLER, item.id)
    n = len(store.items)
    rev = gw.reverse(CONTROLLER, item.id, "wrong treatment of the seller notes")
    assert store.items[item.id].state.value == "REVERSED"
    assert rev.reverses_id == item.id and len(store.items) == n + 1
    assert gw.verify_chain()


# ---- stateful agents -----------------------------------------------------------------------------------------

def test_controller_answer_becomes_a_policy_and_the_mapper_applies_it(world):
    store, gw = world
    advance(gw, DEAL_ID)
    assert gw.open_flags(DEAL_ID)
    answer_all(gw)
    assert any(p.kind == "covenant_tag" and p.decision == "not_debt" for p in store.policies.values())
    store.reset_deals(keep_memory=True)
    seed(store, gw)
    advance(gw, DEAL_ID)
    assert gw.open_flags(DEAL_ID) == []  # asked once, applied next time
    assert any(p.times_applied > 0 for p in store.policies.values())
    assert any(a.action == "policy:apply" for a in store.audit)
    assert store.sessions["mapper"].turns >= 1


# ---- API -----------------------------------------------------------------------------------------------------

def test_api_flow():
    c = TestClient(create_app())
    assert c.get("/health").json()["chain_valid"]
    assert c.post(f"/deals/{DEAL_ID}/run").json()["stage"] == "awaiting_flag"
    case = c.get(f"/deals/{DEAL_ID}/case").json()
    for fid in case["open_flags"]:
        flag = next(f for f in case["flags"] if f["id"] == fid)
        assert c.post(f"/work-items/{fid}/answer?auto_advance=false", json={"option_id": flag["default"]}).status_code == 200
        assert c.post(f"/work-items/{fid}/answer?auto_advance=false", json={"option_id": flag["default"]}).status_code == 409
    c.post(f"/deals/{DEAL_ID}/run")
    case = c.get(f"/deals/{DEAL_ID}/case").json()
    assert case["verdict"]["verdict"] == "ok" and case["verdict"]["review"]["verdict"] == "pass"
    item = case["verdict"]["approval_item"]
    assert c.post(f"/work-items/{item}/approve", headers={"X-Actor": "agent:preparer"}).status_code == 403
    assert c.post(f"/work-items/{item}/approve").json()["state"] == "POSTED"
    log = c.get(f"/deals/{DEAL_ID}/audit").json()
    assert log["chain_valid"] and any(r["result"] == "DENIED" for r in log["rows"])
    assert c.get(f"/runs/{case['result']['rows'][0]['run_id']}").json()["tool"] == "consolidate"


def test_units_and_limit_test():
    assert finance.to_thousands(74850302, "USD") == 74850.302
    assert finance.limit_test(2.499, 2.5)["ok"] and not finance.limit_test(2.5, 2.5)["ok"]
    assert finance.limit_test(0.772, 2.5, ebitda_value=28032.6, debt=21633.0)["debt_capacity"] == pytest.approx(48448.5)
