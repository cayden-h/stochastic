"""Agents are stateful: each role keeps one session across work items and deals, and Droid gets its id back."""
import os

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = ""

from app.agents import runner  # noqa: E402
from app.agents.jobs import advance  # noqa: E402
from app.core.models import CONTROLLER  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402


def run_deal(gw):
    advance(gw, DEAL_ID)
    for flag in gw.open_flags(DEAL_ID):
        gw.answer(CONTROLLER, flag.id, flag.default)
    advance(gw, DEAL_ID)


def test_each_role_keeps_one_session_across_deals():
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    run_deal(gw)
    store.reset_deals()
    seed(store, gw)
    advance(gw, DEAL_ID)  # the second deal: the Mapper applies policies, so no flags
    assert {r: s.turns for r, s in store.sessions.items()} == {"mapper": 2, "preparer": 2, "reviewer": 2}
    assert len(store.sessions["mapper"].transcript) == 2


def test_droid_gets_its_session_back_on_the_next_turn(monkeypatch):
    """Every role's Droid session id and setup key are saved, and the next turn for that role receives them."""
    from app.agents.backends import droid_backend
    calls = []

    def fake_droid(role, inp, call_tool, session_id=None, session_key=None):
        calls.append((role.name, session_id, session_key))
        return runner._scripted(role, inp, call_tool), {"session_id": f"droid-{role.name}", "session_key": "k1"}

    monkeypatch.setenv("FACTORY_API_KEY", "test")
    monkeypatch.setattr(droid_backend, "run_droid", fake_droid)
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    advance(gw, DEAL_ID, backend="droid")
    for flag in gw.open_flags(DEAL_ID):
        gw.answer(CONTROLLER, flag.id, flag.default)
    advance(gw, DEAL_ID, backend="droid")
    store.reset_deals()
    seed(store, gw)
    advance(gw, DEAL_ID, backend="droid")
    first = calls[:3]
    second = calls[3:]
    assert first == [("mapper", None, None), ("preparer", None, None), ("reviewer", None, None)]
    assert second == [(r, f"droid-{r}", "k1") for r in ("mapper", "preparer", "reviewer")]


def test_a_backend_change_keeps_the_transcript_but_not_the_session_id():
    store = MemoryStore()
    gw = Gateway(store)
    gw.update_session("mapper", "droid", "wi_x", "mapped", "droid-1", "k1")
    s = gw.update_session("mapper", "scripted", "wi_y", "mapped again")
    assert (s.backend, s.session_id, s.session_key, s.turns, len(s.transcript)) == ("scripted", None, None, 2, 2)


def test_a_changed_setup_is_not_resumed():
    from app.agents.backends.droid_backend import setup_key
    from app.agents.roles import MAPPER_ROLE as MAPPER
    base = setup_key(MAPPER, "claude-haiku-5-5", "medium", ["stochastic/x"])
    assert base == setup_key(MAPPER, "claude-haiku-5-5", "medium", ["stochastic/x"])
    assert base != setup_key(MAPPER, "claude-sonnet-5-5", "medium", ["stochastic/x"])
    assert base != setup_key(MAPPER, "claude-haiku-5-5", "high", ["stochastic/x"])
