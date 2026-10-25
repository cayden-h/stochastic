"""The 15-second demo: a paced run that notifies the controller, waits for the decision, learns it, and finishes.

A fake clock replaces the pace's sleep, so the run is measured in virtual seconds and the suite stays fast.
docs/architecture/gateway-and-api.md ("Demo pace", "Live events") and docs/demo-script.md are the contract; the
real-clock numbers measured on uvicorn are in those files.
"""
import os
import re
import threading

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.agents import pace  # noqa: E402
from app.agents.jobs import advance  # noqa: E402
from app.api.events import next_events  # noqa: E402
from app.core.models import CONTROLLER, MAPPER  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed, seed_demo  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402
from app.main import create_app  # noqa: E402
from tests.test_live_events import parse  # noqa: E402


class FakeClock:
    """Virtual seconds: every pace wait moves the clock and takes no real time. While it waits, another thread
    tries the gateway lock, so a wait under the lock (which would block an answer or a read) is caught."""

    def __init__(self, gw=None):
        self.now = 0.0
        self.gw = gw
        self.lock_free: list[bool] = []

    def sleep(self, seconds: float) -> None:
        self.now += seconds
        if self.gw is not None:
            got = []

            def try_lock():
                ok = self.gw.lock.acquire(timeout=1)
                if ok:
                    self.gw.lock.release()  # an RLock is released by the thread that holds it
                got.append(ok)
            t = threading.Thread(target=try_lock)
            t.start()
            t.join()
            self.lock_free.append(bool(got and got[0]))


@pytest.fixture
def world(monkeypatch):
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    clock = FakeClock(gw)
    monkeypatch.setattr(pace, "ALLOW_IN_TESTS", True)
    monkeypatch.setattr(pace, "_sleep", clock.sleep)
    monkeypatch.delenv("DEMO_PACE", raising=False)
    said: list[tuple[float, object]] = []  # (virtual time, message) as the gateway writes each one
    real_say = gw._say

    def say(*args, **kwargs):
        msg = real_say(*args, **kwargs)
        if msg is not None:
            said.append((clock.now, msg))
        return msg
    monkeypatch.setattr(gw, "_say", say)
    return store, gw, clock, said


def first(said, pred):
    return next((t, m) for t, m in said if pred(m))


def test_the_demo_pace_reads_verifies_asks_once_and_finishes_in_about_15_s(world, monkeypatch):
    """The demo deal from its agreement (D23): two human touchpoints, the one-click Brief approval after the verifier,
    and the Mapper's one escalation (two questions, answered together). The rest runs by itself."""
    _, _, clock, _ = world
    store = MemoryStore()
    gw = Gateway(store)
    seed_demo(store, gw)
    clock.gw = gw
    said: list = []
    real_say = gw._say

    def say(*args, **kwargs):
        msg = real_say(*args, **kwargs)
        if msg is not None:
            said.append((clock.now, msg))
        return msg
    monkeypatch.setattr(gw, "_say", say)
    log = advance(gw, DEAL_ID, backend="scripted", pace_name="demo")
    assert log[-1] == "waiting on the controller to approve the Brief"
    t_read, _ = first(said, lambda m: m.kind == "handoff" and m.text.startswith("Draft Brief ready to verify"))
    t_verified, _ = first(said, lambda m: m.kind == "check" and m.text.startswith("Brief verified: 22 of 22"))
    assert 2.0 <= t_read <= 3.0 and 1.0 <= t_verified - t_read <= 2.0, (t_read, t_verified)  # read 2.4, verify 1.6
    assert store.deals[DEAL_ID].stage == "brief_ready" and not gw.open_flags(DEAL_ID)  # nothing to answer or type
    brief_time = clock.now
    gw.approve_brief(CONTROLLER, DEAL_ID)  # touchpoint 1: one click
    advance(gw, DEAL_ID, backend="scripted", pace_name="demo")
    flags = gw.open_flags(DEAL_ID)
    questions = [(t, m) for t, m in said if m.kind == "question"]
    assert len(flags) == 2 and {m.sender for _, m in questions} == {MAPPER}  # touchpoint 2: asked together
    assert len({t for t, _ in questions}) == 1
    to_q = questions[0][0] - brief_time
    assert 3.0 <= to_q <= 4.5, to_q  # the Mapper 1.2 + its mappings over 1.4 + 0.6
    t_answer = clock.now
    for f in flags:
        gw.answer(CONTROLLER, f.id, f.default)
    assert len([m for _, m in said if m.text.startswith("Learned")]) == 2
    advance(gw, DEAL_ID, backend="scripted", pace_name="demo")
    t_ready, _ = first(said, lambda m: m.kind == "handoff" and m.text.startswith("Ready for your approval"))
    after = t_ready - t_answer
    assert 6.0 <= after <= 7.2, after
    assert 13.0 <= brief_time + to_q + after <= 15.5  # the whole demo, agent time only
    assert store.deals[DEAL_ID].stage == "awaiting_approval"
    assert all(clock.lock_free)


def test_the_human_pace_keeps_the_documented_timings(world):
    store, gw, clock, said = world
    advance(gw, DEAL_ID, backend="scripted", pace_name="human")
    t_question, _ = first(said, lambda m: m.kind == "question")
    assert 19.0 <= t_question <= 22.0, t_question  # 2.5 + 53 x 0.3 + 1.5
    start = clock.now
    for f in gw.open_flags(DEAL_ID):
        gw.answer(CONTROLLER, f.id, f.default)
    advance(gw, DEAL_ID, backend="scripted", pace_name="human")
    assert 10.0 <= clock.now - start <= 15.0
    assert all(clock.lock_free)


def test_pace_off_overrides_demo_pace_in_the_environment(world, monkeypatch):
    store, gw, clock, said = world
    monkeypatch.setenv("DEMO_PACE", "1")
    advance(gw, DEAL_ID, backend="scripted", pace_name="off")
    assert clock.now == 0
    advance_env = MemoryStore()
    gw2 = Gateway(advance_env)
    seed(advance_env, gw2)
    advance(gw2, DEAL_ID, backend="scripted")  # no pace asked: DEMO_PACE=1 applies
    assert clock.now > 15


def test_a_live_backend_is_never_paced_even_when_a_run_asks_for_demo(world):
    with pace.using("demo"):
        assert pace.paced("scripted") and pace.paced("replay")
        assert not pace.paced("droid") and not pace.paced("anthropic")
    with pytest.raises(ValueError):
        with pace.using("warp"):
            pass


def test_the_questions_state_each_option_with_the_figure_from_its_run(world):
    store, gw, clock, said = world
    advance(gw, DEAL_ID, backend="scripted")
    fin = next(f for f in gw.open_flags(DEAL_ID) if f.payload["kind"] == "covenant_tag")
    q = next(m for _, m in said if m.kind == "question" and m.item_id == fin.id)
    limit = store.deals[DEAL_ID].brief.limit
    for o in fin.options:
        test = store.tool_runs[o.run_id]
        lev = store.tool_runs[test.inputs["leverage_run_id"]]
        figure = f"{lev.outputs['debt'] / lev.outputs['ebitda']:.2f}x"
        side = "under" if test.outputs["ok"] else "over"
        assert re.search(rf"\b{o.id}\) {re.escape(o.label)}: (leverage )?{re.escape(figure)}( as filed)?, {side}", q.text), \
            (o.id, figure, q.text)
    assert f"over the {limit:.2f}x limit" in q.text and "2.84x as filed" in q.text
    assert "Statesville sale-leaseback (27,782K)" in q.text and "seller notes (22,540K)" in q.text
    assert q.text.startswith("Decision 1 of 2: ") and q.text.endswith("The Preparer waits for both answers.")
    cds = next(f for f in gw.open_flags(DEAL_ID) if f.payload["kind"] == "mapping")
    q2 = next(m for _, m in said if m.kind == "question" and m.item_id == cds.id)
    assert "'Certificates of Deposit' (991K)" in q2.text
    assert "a) Cash and cash equivalents; b) Other assets; c) Leave unmapped and list it." in q2.text
    assert "Debt, EBITDA, and leverage do not change with this answer." in q2.text
    assert all("No change to debt, EBITDA, or leverage." in o.effect for o in cds.options)


def test_each_answer_is_followed_by_what_the_agent_learned_with_its_policy_id(world):
    store, gw, clock, said = world
    advance(gw, DEAL_ID, backend="scripted")
    fin, cds = sorted(gw.open_flags(DEAL_ID), key=lambda f: f.payload["kind"] != "covenant_tag")
    gw.answer(CONTROLLER, fin.id, "b")
    msgs = gw.conversation(DEAL_ID)
    answer_at = next(i for i, m in enumerate(msgs) if m.kind == "answer" and m.item_id == fin.id)
    learn = msgs[answer_at + 1]
    taught = [p for p in store.policies.values() if p.learned_from == fin.id]
    assert (learn.sender, learn.to, learn.kind, learn.item_id) == (MAPPER, CONTROLLER, "message", fin.id)
    assert learn.policy_id == taught[0].id
    assert learn.text.startswith(f"Learned {taught[0].id} to {taught[-1].id} (Kewaunee, Senior Funded Bank Debt): ")
    assert "'Financing liability: PNC Term Loan' count" in learn.text  # the bank debt counts
    assert "'Financing liability: 8% Seller Notes (subordinated)' do not" in learn.text
    assert learn.text.endswith(f"1 question still open ({cds.id}), and the Preparer starts once it is answered.")
    gw.answer(CONTROLLER, cds.id, "a")
    learn2 = gw.conversation(DEAL_ID)[-1]
    p = next(p for p in store.policies.values() if p.learned_from == cds.id)
    assert learn2.policy_id == p.id and learn2.sender == MAPPER
    assert learn2.text == (f"Learned {p.id}: Nu Aire's 'Certificates of Deposit' goes to 'Cash and cash equivalents'. "
                           f"Applying it now, and to this line on later deals without asking. The Preparer is next.")
    others = [m for m in gw.conversation(DEAL_ID) if m.policy_id and m is not learn and m is not learn2]
    assert others == []  # only the learn messages name a policy


def test_one_notify_event_comes_for_the_questions_asked_together_and_not_after_they_are_answered(world):
    """One escalation, two decisions (D23): the Mapper's questions open together, so the controller is notified once."""
    store, gw, clock, said = world
    advance(gw, DEAL_ID, backend="scripted")
    events, _, _ = next_events(store, DEAL_ID, 0, None, live_seen={})
    notes = parse(events, "notify")
    flags = gw.open_flags(DEAL_ID)
    assert len(flags) == 2 and [n["item_id"] for n in notes] == [flags[0].id]
    questions = {m.item_id: m for m in gw.conversation(DEAL_ID) if m.kind == "question"}
    (n,) = notes
    assert set(n) == {"id", "deal_id", "at", "kind", "item_id", "item_ids", "from", "title", "body"}
    assert n["kind"] == "decision" and n["from"] == MAPPER and n["deal_id"] == DEAL_ID
    assert n["item_ids"] == [f.id for f in flags] and n["title"] == "The Mapper needs 2 decisions"
    assert n["body"] == f"{flags[0].question} (and 1 more question, answered together)"
    assert n["id"] == questions[flags[0].id].id
    assert not [m for m in gw.conversation(DEAL_ID) if m.kind == "question" and m.sender != MAPPER]  # no Brief question
    # A page that connects after the answers gets the questions in the conversation, but no notification.
    for f in flags:
        gw.answer(CONTROLLER, f.id, f.default)
    late, _, _ = next_events(store, DEAL_ID, 0, None, live_seen={})
    assert parse(late, "notify") == [] and [m for m in parse(late, "conversation") if m["kind"] == "question"]


def test_the_api_run_takes_pace_and_the_answer_continues_at_that_pace(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(pace, "ALLOW_IN_TESTS", True)
    monkeypatch.setattr(pace, "_sleep", clock.sleep)
    monkeypatch.delenv("DEMO_PACE", raising=False)
    c = TestClient(create_app())
    assert c.post(f"/deals/{DEAL_ID}/run", json={"sync": True, "pace": "fast"}).status_code == 422
    r = c.post(f"/deals/{DEAL_ID}/run", json={"sync": True, "pace": "demo"})
    assert r.status_code == 200 and r.json()["stage"] == "awaiting_flag"
    asked = clock.now
    assert 3.0 <= asked <= 4.5  # the Mapper only: this deal's Brief came as JSON
    body = c.get(f"/deals/{DEAL_ID}/case").json()
    for fid in body["open_flags"]:  # the last answer continues in the background, at the run's pace
        f = next(x for x in body["flags"] if x["id"] == fid)
        assert c.post(f"/work-items/{fid}/answer", json={"option_id": f["default"]}).status_code == 200
    assert c.get(f"/deals/{DEAL_ID}/case").json()["stage"] == "awaiting_approval"
    assert 6.0 <= clock.now - asked <= 8.0
    msgs = c.get(f"/deals/{DEAL_ID}/conversation").json()
    assert [m for m in msgs if m["policy_id"]] and all("policy_id" in m for m in msgs)
