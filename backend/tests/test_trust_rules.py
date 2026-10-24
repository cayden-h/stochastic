"""Tests for the trust rules: see docs/STOCHASTIC.md section 9."""
import pytest
from fastapi.testclient import TestClient

from app.db.fixtures.demo import DEAL_ID
from app.gateway.gateway import Denied, Gateway, IllegalTransition
from app.main import create_app
from app.db.fixtures.demo import seed_demo
from app.db.memory import MemoryStore
from app.tools.deal_math import leverage_breach
from app.tools.quote_validator import quote_in_document


@pytest.fixture
def world():
    store = MemoryStore()
    gw = Gateway(store)
    seed_demo(store, gw)
    return store, gw


def item_of(store, type_):
    return next(i for i in store.items.values() if i.type == type_)


def test_chain_is_valid_after_seed(world):
    _, gw = world
    assert gw.verify_chain()


def test_blocked_plan_is_logged_as_denied_with_clause(world):
    store, _ = world
    denied = [a for a in store.audit if a.result == "DENIED" and a.action == "post_plan"]
    assert len(denied) == 1
    assert denied[0].evidence and "3.00 to 1.00" in denied[0].evidence[0].quote


def test_agent_cannot_approve(world):
    store, gw = world
    rec = item_of(store, "recommend")
    with pytest.raises(Denied):
        gw.approve("agent:memo", rec.id)
    assert store.audit[-1].result == "DENIED"


def test_proposer_cannot_approve_own_item(world):
    store, gw = world
    rec = item_of(store, "recommend")
    gw.store.items[rec.id].proposed_by = "human:reviewer"
    with pytest.raises(Denied):
        gw.approve("human:reviewer", rec.id)


def test_human_approves_and_gateway_posts(world):
    store, gw = world
    rec = item_of(store, "recommend")
    gw.approve("human:reviewer", rec.id)
    assert store.items[rec.id].state.value == "POSTED"
    assert store.audit[-1].actor == "system:gateway"
    assert gw.verify_chain()


def test_agent_cannot_answer_a_question(world):
    store, gw = world
    q = item_of(store, "clarify_clause")
    with pytest.raises(Denied):
        gw.answer("agent:clause_reader", q.id, "debt")


def test_illegal_transition_is_refused(world):
    store, gw = world
    q = item_of(store, "clarify_clause")
    with pytest.raises(IllegalTransition):
        gw.approve("human:reviewer", q.id)  # still NEEDS_INFO


def test_tampering_breaks_the_chain(world):
    store, gw = world
    store.audit[2].reason = "changed after the fact"
    assert not gw.verify_chain()


def test_event_marks_plans_stale(world):
    store, gw = world
    gw.inject_event("human:reviewer", DEAL_ID, "rate_move", "SOFR up 50bp")
    assert all(p.stale for p in store.plans.values())


def test_math_is_deterministic():
    a = leverage_breach(100, 40, {"junior": 60}, 3.0, False)
    assert a == leverage_breach(100, 40, {"junior": 60}, 3.0, False) == (True, 4.0)
    assert leverage_breach(100, 40, {"preferred": 60}, 3.0, False) == (False, 2.5)
    assert leverage_breach(100, 40, {"preferred": 60}, 3.0, True) == (True, 4.0)


def test_quote_validator():
    assert quote_in_document("shall not exceed 3.00", "The ratio  shall not exceed 3.00 to 1.00")
    assert not quote_in_document("shall not exceed 5.00", "The ratio shall not exceed 3.00 to 1.00")


def test_api_flow():
    c = TestClient(create_app())
    assert c.get("/health").json()["chain_valid"]
    items = c.get(f"/deals/{DEAL_ID}/work-items").json()
    q = next(i for i in items if i["escalation"] == "E3")
    assert c.post(f"/work-items/{q['id']}/answer", json={"option_id": "equity"}).status_code == 200
    assert c.post(f"/work-items/{q['id']}/answer", json={"option_id": "equity"}).status_code == 409
    assert c.post(f"/work-items/{q['id']}/approve", headers={"X-Actor": "agent:x"}).status_code == 403
    log = c.get(f"/deals/{DEAL_ID}/audit").json()
    assert log["chain_valid"] and any(r["result"] == "DENIED" for r in log["rows"])


def test_consent_plan_is_conditional_not_clear(world):
    store, _ = world
    plans = {p.name[0]: p for p in store.plans.values()}
    assert plans["A"].status == "blocked"
    assert plans["B"].status == "ok"
    assert plans["C"].status == "needs_consent" and plans["C"].needs_consent


def test_hold_is_logged_and_keeps_state(world):
    store, gw = world
    q = item_of(store, "clarify_clause")
    gw.hold("human:reviewer", q.id)
    assert store.items[q.id].state.value == "NEEDS_INFO" and store.items[q.id].payload["held"]
    assert store.audit[-1].action == "hold"
