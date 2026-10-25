"""Live events: the agents' conversation, the per-line mapping events, and the demo pace.

The conversation is written by the gateway in the same write as the thing it describes, so these tests check that it
tells the demo deal's run in order, that every figure in it equals the run it cites, that the stream sends it and the
mappings one by one, and that the pace adds no wait unless DEMO_PACE asks for it. docs/architecture/gateway-and-api.md
("Live events") is the contract.
"""
import json
import os
import re

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.agents import pace  # noqa: E402
from app.agents.backends.scripted import scripted_mapper  # noqa: E402
from app.agents.jobs import advance  # noqa: E402
from app.api.events import next_events  # noqa: E402
from app.core.models import (VERIFIER, BRIEF_READER, CONTROLLER, MAPPER, PREPARER, REVIEWER, ROLES, SYSTEM,  # noqa: E402
                             MapperInput, State)
from app.db.fixtures.kewaunee import DEAL_ID, TARGET, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway, Invalid  # noqa: E402
from app.main import create_app  # noqa: E402

KINDS = {"message", "handoff", "question", "answer", "refusal", "check"}
FIGURE = re.compile(r"(\d[\d,]*(?:\.\d+)?)(K|x)\b")


def fresh():
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    return store, gw


def answer_flags(gw):
    for flag in gw.open_flags(DEAL_ID):
        gw.answer(CONTROLLER, flag.id, flag.default)


def run_to_approval(gw):
    advance(gw, DEAL_ID, backend="scripted")
    answer_flags(gw)
    advance(gw, DEAL_ID, backend="scripted")
    assert gw.store.deals[DEAL_ID].stage == "awaiting_approval"


def parse(events, name):
    out = []
    for e in events:
        head, _, data = e.partition("\n")
        if head == f"event: {name}":
            out.append(json.loads(data.removeprefix("data: ").strip()))
    return out


def find(messages, start, **want):
    """The index of the first message at or after `start` whose fields match `want` (text: a substring)."""
    for i in range(start, len(messages)):
        m = messages[i]
        if all((v in m["text"]) if k == "text" else m[k] == v for k, v in want.items()):
            return i
    raise AssertionError(f"no message {want} after #{start}: {[(m['from'], m['to'], m['text']) for m in messages]}")


# ---- 1. the conversation tells the demo run in order -------------------------------------------------------------

def test_the_demo_conversation_in_order_through_the_api():
    c = TestClient(create_app())
    assert c.post(f"/deals/{DEAL_ID}/run").json()["stage"] == "awaiting_flag"
    flags = c.get(f"/deals/{DEAL_ID}/case").json()["flags"]
    for f in flags:  # the last answer starts the run in the background, as on stage
        assert c.post(f"/work-items/{f['id']}/answer", json={"option_id": f["default"]}).status_code == 200
    case = c.get(f"/deals/{DEAL_ID}/case").json()
    assert case["stage"] == "awaiting_approval"
    result, approval = case["result"], case["verdict"]["approval_item"]
    msgs = c.get(f"/deals/{DEAL_ID}/conversation").json()

    n_target = len([sl for sl in case["source_lines"] if sl["company"] == TARGET])
    i = find(msgs, 0, **{"from": SYSTEM, "to": MAPPER, "kind": "handoff"})
    i = find(msgs, i, **{"from": MAPPER, "to": SYSTEM, "kind": "message", "text": f"Proposing {n_target} mappings"})
    assert "2 questions" in msgs[i]["text"]
    i = find(msgs, i, **{"from": SYSTEM, "to": MAPPER, "kind": "check", "text": f"accepted {n_target} mappings"})
    asked = []
    for f in flags:  # each escalation: the Mapper asks the controller, with the flag's own question and item id
        j = find(msgs, i, **{"from": MAPPER, "to": CONTROLLER, "kind": "question", "item_id": f["id"]})
        assert f["question"] in msgs[j]["text"] and msgs[j]["text"].startswith("Decision")
        assert msgs[j]["text"].endswith("The Preparer waits for both answers.")
        asked.append(j)
    i = max(asked)
    for f in flags:  # and the controller answers the agent that asked, with the option chosen
        label = next(o["label"] for o in f["options"] if o["id"] == f["default"])
        i = find(msgs, i, **{"from": CONTROLLER, "to": MAPPER, "kind": "answer", "item_id": f["id"]})
        assert msgs[i]["text"] == f"Option {f['default']}: {label}"
        # right after it, the Mapper tells the controller what it learned, with the policy id
        assert msgs[i + 1]["from"] == MAPPER and msgs[i + 1]["to"] == CONTROLLER and msgs[i + 1]["kind"] == "message"
        assert msgs[i + 1]["text"].startswith(f"Learned {msgs[i + 1]['policy_id']}")
    i = find(msgs, i, **{"from": MAPPER, "to": PREPARER, "kind": "handoff", "text": "Mappings posted"})
    assert "the controller answered 2 questions" in msgs[i]["text"]
    lev_run = result["run_ids_by_tool"]["leverage"]
    i = find(msgs, i, **{"from": PREPARER, "to": SYSTEM, "kind": "message", "text": f"Draft books {result['id']}",
                         "run_id": lev_run})
    assert "leverage 0.76x against 2.50x" in msgs[i]["text"]
    i = find(msgs, i, **{"from": SYSTEM, "to": PREPARER, "kind": "check", "text": "Every figure traces"})
    i = find(msgs, i, **{"from": PREPARER, "to": REVIEWER, "kind": "handoff"})
    i = find(msgs, i, **{"from": REVIEWER, "to": PREPARER, "kind": "check", "text": "Tie-out passes"})
    assert "limit test passes" in msgs[i]["text"]
    i = find(msgs, i, **{"from": REVIEWER, "to": CONTROLLER, "kind": "handoff", "item_id": approval,
                         "text": "Ready for your approval"})
    assert i == len(msgs) - 1  # nothing after the hand-off until the controller acts

    assert c.post(f"/work-items/{approval}/approve").status_code == 200
    after = c.get(f"/deals/{DEAL_ID}/conversation").json()
    assert after[:len(msgs)] == msgs
    assert [(m["from"], m["to"]) for m in after[len(msgs):]] == [(CONTROLLER, SYSTEM), (SYSTEM, CONTROLLER)]


def test_every_message_has_the_contract_shape_and_plain_text():
    store, gw = fresh()
    run_to_approval(gw)
    msgs = [m.model_dump(mode="json") for m in gw.conversation(DEAL_ID)]
    assert msgs
    for m in msgs:
        assert set(m) == {"id", "deal_id", "at", "from", "to", "kind", "text", "item_id", "run_id", "line_id",
                          "policy_id"}
        assert m["policy_id"] is None or m["policy_id"] in store.policies
        assert m["from"] in ROLES and m["to"] in ROLES and m["from"] != m["to"]
        assert m["kind"] in KINDS
        assert m["text"] and "—" not in m["text"] and "–" not in m["text"] and "\n" not in m["text"]
        # a question lists every option with its effect, and a learn message every line it taught: 700 at most
        assert len(m["text"]) <= (700 if m["kind"] == "question" or m["policy_id"] else 300)
        assert m["run_id"] is None or m["run_id"] in store.tool_runs
        assert m["item_id"] is None or m["item_id"] in store.items
    ats = [m["at"] for m in msgs]
    assert ats == sorted(ats) and [m["id"] for m in msgs] == sorted(m["id"] for m in msgs)
    for m in msgs:  # every escalation is a question to the controller, and every answer comes from the controller
        if m["kind"] == "question":
            assert m["to"] == CONTROLLER and m["item_id"]
        if m["kind"] == "answer":
            assert m["from"] == CONTROLLER and m["item_id"] and store.items[m["item_id"]].proposed_by == m["to"]


def _allowed_figures(store, run_id: str) -> set[str]:
    """Every way a figure from this run, or from the runs it is built on, is written in a message."""
    seen, todo, out = set(), [run_id], set()
    while todo:
        rid = todo.pop()
        run = store.tool_runs.get(rid)
        if run is None or rid in seen:
            continue
        seen.add(rid)
        for v in run.outputs.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out |= {f"{v:,.0f}K", f"{v:.2f}x"}
        if "debt" in run.outputs and "ebitda" in run.outputs:
            out.add(f"{run.outputs['debt'] / run.outputs['ebitda']:.2f}x")
        todo += [v for k, v in run.inputs.items() if k.endswith("run_id") and isinstance(v, str)]
    return out


def _line_amounts(store, line_ids: list[str]) -> set[str]:
    """The filed amounts of these lines in USD thousands, and the sum of every group of them, as a message writes them."""
    from itertools import combinations

    from app.tools.finance import to_thousands
    amounts = [to_thousands(store.source_lines[i].amount, store.source_lines[i].unit) for i in line_ids]
    return {f"{sum(c):,.0f}K" for n in range(1, len(amounts) + 1) for c in combinations(amounts, n)}


def test_every_figure_in_a_message_equals_the_run_it_cites():
    store, gw = fresh()
    run_to_approval(gw)
    limit = f"{store.deals[DEAL_ID].brief.limit:.2f}x"
    result = store.latest_result(DEAL_ID)
    checked = 0
    for m in gw.conversation(DEAL_ID):
        figures = {"".join(f) for f in FIGURE.findall(m.text)}
        if not figures:
            continue
        if m.kind == "question" and m.item_id in store.items:
            # A question's figures: each option's leverage from its own run chain, the flagged lines' filed amounts
            # (and their sums, by component), and the limit.
            flag = store.items[m.item_id]
            allowed = {limit}
            for o in flag.options:
                if o.run_id:
                    allowed |= _allowed_figures(store, o.run_id)
            allowed |= _line_amounts(store, flag.payload.get("line_ids", []))
            assert figures <= allowed, (m.text, figures - allowed)
            checked += 1
            continue
        if m.run_id is None:  # only the Brief's limit may appear without a run behind it
            assert figures == {limit}, (m.text, figures)
            continue
        allowed = _allowed_figures(store, m.run_id) | {limit}
        if m.run_id == result.run_ids_by_tool["leverage"]:  # the draft cites its leverage run, built on its own runs
            allowed |= _allowed_figures(store, result.run_ids_by_tool["consolidate"])
        assert figures <= allowed, (m.text, figures - allowed)
        checked += 1
    assert checked >= 8  # the four Preparer tools, the two Reviewer tools, the draft, the checks, the hand-offs
    draft = next(m for m in gw.conversation(DEAL_ID) if m.text.startswith("Draft books"))
    lev = store.tool_runs[draft.run_id]
    assert lev.tool == "leverage" and lev.run_id == result.run_ids_by_tool["leverage"]
    assert f"EBITDA {result.ebitda:,.0f}K" in draft.text and f"{result.debt:,.0f}K" in draft.text


def test_a_refused_result_is_a_refusal_to_the_agent_that_sent_it():
    store, gw = fresh()
    deal = store.deals[DEAL_ID]
    item = gw.create_item(DEAL_ID, "map_lines")
    inp = MapperInput(deal_id=DEAL_ID, platform=deal.platform, target=deal.target,
                      target_lines=store.lines(DEAL_ID, deal.target), platform_lines=store.lines(DEAL_ID, deal.platform),
                      brief=deal.brief, policies=[])
    out = scripted_mapper(inp)
    unclear = next(t for t in out.tags if t.tag == "unclear")
    out.tags = [t.model_copy(update={"tag": "not_debt"}) if t is unclear else t for t in out.tags]
    with pytest.raises(Invalid):
        gw.store_mapping(MAPPER, item.id, out)
    last = gw.conversation(DEAL_ID)[-1]
    assert (last.sender, last.to, last.kind, last.item_id) == (SYSTEM, MAPPER, "refusal", item.id)
    assert last.text.startswith("Refused: tag not_debt on") and "controller's call" in last.text
    assert not store.deal_mappings(DEAL_ID)  # the refused result left no mapping behind


def test_the_second_run_asks_nothing_and_says_the_policies_decided():
    c = TestClient(create_app())
    c.post(f"/deals/{DEAL_ID}/run")
    for f in c.get(f"/deals/{DEAL_ID}/case").json()["flags"]:
        c.post(f"/work-items/{f['id']}/answer", json={"option_id": f["default"]})
    learned = [m for m in c.get(f"/deals/{DEAL_ID}/conversation").json() if m["text"].startswith("Learned")]
    assert len(learned) == 2  # one per answered flag, from the Mapper to the controller, naming the policy
    assert all(m["from"] == MAPPER and m["to"] == CONTROLLER and m["policy_id"] for m in learned)
    assert c.post("/dev/reset").json()["ok"]
    assert c.get(f"/deals/{DEAL_ID}/conversation").json() == []  # the conversation is the deal's record
    c.post(f"/deals/{DEAL_ID}/run")
    msgs = c.get(f"/deals/{DEAL_ID}/conversation").json()
    assert not [m for m in msgs if m["kind"] == "question"]
    check = next(m for m in msgs if m["kind"] == "check" and m["to"] == MAPPER)
    assert re.search(r"; \d+ decided by a learned policy$", check["text"])


def test_the_brief_reader_speaks_first_on_a_deal_read_from_its_agreement():
    from tests.test_api_brief import FIXTURE_BRIEF, answer_open_brief_flags, kewaunee_deal, post_deal  # noqa: F401
    from fastapi import FastAPI
    from app.api.errors import install_error_handlers
    from app.api.routes import build_router
    store = MemoryStore()
    gw = Gateway(store)
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(build_router(gw))
    c = TestClient(app)
    did = kewaunee_deal(c)
    c.post(f"/deals/{did}/run")
    msgs = c.get(f"/deals/{did}/conversation").json()
    i = find(msgs, 0, **{"from": SYSTEM, "to": BRIEF_READER, "kind": "handoff"})
    i = find(msgs, i, **{"from": BRIEF_READER, "to": SYSTEM, "kind": "message", "text": "Draft Brief: limit 2.50x"})
    i = find(msgs, i, **{"from": SYSTEM, "to": BRIEF_READER, "kind": "check", "text": "against the agreement"})
    # The reader hands its draft to the verifier (D23), which checks each field before anyone is asked anything.
    i = find(msgs, i, **{"from": BRIEF_READER, "to": VERIFIER, "kind": "handoff", "text": "ready to verify"})
    i = find(msgs, i, **{"from": VERIFIER, "to": CONTROLLER, "kind": "check", "text": "Verified limit = 2.50"})
    i = find(msgs, i, **{"from": VERIFIER, "to": CONTROLLER, "kind": "check", "text": "Brief verified:"})
    questions = [m for m in msgs[i:] if m["kind"] == "question"]
    assert questions and all(m["to"] == CONTROLLER and m["item_id"] for m in questions)
    find(msgs, i, **{"from": VERIFIER, "to": CONTROLLER, "kind": "handoff", "text": "questions for you"})
    amounts = [{"field": f"{g}[{k}].amount", "value": a.amount, "source_ref": a.source_ref, "inferred": a.inferred,
                "note": a.note} for g in ("ebitda_addbacks", "ebitda_deductions")
               for k, a in enumerate(getattr(FIXTURE_BRIEF, g)) if a.amount]
    assert c.post(f"/deals/{did}/brief/amounts", json={"amounts": amounts}).status_code == 200
    answer_open_brief_flags(c, did)
    assert c.post(f"/deals/{did}/brief/approve").status_code == 200
    c.post(f"/deals/{did}/run")
    msgs = c.get(f"/deals/{did}/conversation").json()
    answers = [m for m in msgs if m["kind"] == "answer"]
    assert len(answers) == len(questions) and {m["item_id"] for m in answers} == {m["item_id"] for m in questions}
    i = find(msgs, 0, **{"from": CONTROLLER, "to": BRIEF_READER, "text": "Brief approved"})
    find(msgs, i, **{"from": BRIEF_READER, "to": MAPPER, "kind": "handoff", "text": "Brief approved: limit 2.50x"})


# ---- 2. mapping events, one per stored mapping, in order --------------------------------------------------------

def test_mapping_events_arrive_one_per_stored_mapping_in_order():
    store, gw = fresh()
    advance(gw, DEAL_ID, backend="scripted")
    events, _, _ = next_events(store, DEAL_ID, 0, None, live_seen={})
    sent = parse(events, "mapping")
    stored = store.deal_mappings(DEAL_ID)
    assert [e["mapping_id"] for e in sent] == [m.id for m in stored]
    assert [e["at"] for e in sent] == sorted(e["at"] for e in sent)
    first, m = sent[0], stored[0]
    assert first["line_id"] == m.target_line_id and first["line"] == m.target_line
    assert first["platform_line"] == m.platform_line and first["confidence"] == m.confidence
    assert first["company"] == TARGET and {"policy_id", "reason", "flagged", "at", "section"} <= set(first)


def test_mappings_are_stored_and_streamed_line_by_line_during_a_paced_run(monkeypatch):
    """With the pace on, each accepted mapping is in /case and on the stream before the next one is stored."""
    store, gw = fresh()
    cursor, counts, streamed = {}, [], []

    def sleep(seconds):
        counts.append(len(store.deal_mappings(DEAL_ID)))
        events, _, _ = next_events(store, DEAL_ID, len(store.audit), "x", live_seen=cursor)
        streamed.append(len(parse(events, "mapping")))

    monkeypatch.setattr(pace, "ALLOW_IN_TESTS", True)
    monkeypatch.setattr(pace, "_sleep", sleep)
    monkeypatch.setenv("DEMO_PACE", "1")
    advance(gw, DEAL_ID, backend="scripted")
    n = len(store.deal_mappings(DEAL_ID))
    # One wait at the turn (no mapping yet), then one after each mapping, with exactly one new mapping each time.
    assert counts[0] == 0 and counts[1:n + 1] == list(range(1, n + 1))
    assert streamed[1:n + 1] == [1] * n


def test_a_mapping_the_controller_changes_is_sent_again():
    store, gw = fresh()
    advance(gw, DEAL_ID, backend="scripted")
    cursor = {}
    next_events(store, DEAL_ID, 0, None, live_seen=cursor)
    flag = next(f for f in gw.open_flags(DEAL_ID) if f.payload["kind"] == "mapping")
    gw.answer(CONTROLLER, flag.id, flag.default)
    events, _, _ = next_events(store, DEAL_ID, len(store.audit), store.deals[DEAL_ID].stage, live_seen=cursor)
    again = parse(events, "mapping")
    assert [e["line_id"] for e in again] == flag.payload["line_ids"] and again[0]["approved_by"] == CONTROLLER


# ---- 3. the stream sends the conversation, live and replayed ----------------------------------------------------

def test_the_stream_sends_conversation_events_as_they_happen_and_replays_them_to_a_late_page():
    store, gw = fresh()
    cursor = {}
    events, seen, last = next_events(store, DEAL_ID, 0, None, live_seen=cursor)
    assert parse(events, "conversation") == []
    advance(gw, DEAL_ID, backend="scripted")
    events, seen, last = next_events(store, DEAL_ID, seen, last, live_seen=cursor)
    live = parse(events, "conversation")
    assert live and live[-1]["kind"] == "question" and live[-1]["to"] == CONTROLLER  # the escalation, at once
    assert len(parse(events, "mapping")) == len(store.deal_mappings(DEAL_ID))
    flag = gw.open_flags(DEAL_ID)[0]
    gw.answer(CONTROLLER, flag.id, flag.default)
    events, seen, last = next_events(store, DEAL_ID, seen, last, live_seen=cursor)
    new = parse(events, "conversation")
    assert new[0]["kind"] == "answer" and new[0]["item_id"] == flag.id  # only what is new
    late, _, _ = next_events(store, DEAL_ID, 0, None, live_seen={})
    replay = parse(late, "conversation")
    assert replay == live + new == [m.model_dump(mode="json") for m in gw.conversation(DEAL_ID)]


def test_the_stream_cursor_starts_over_after_a_reset():
    store, gw = fresh()
    advance(gw, DEAL_ID, backend="scripted")
    cursor = {}
    next_events(store, DEAL_ID, 0, None, live_seen=cursor)
    store.reset_deals()
    seed(store, gw)
    advance(gw, DEAL_ID, backend="scripted")
    events, _, _ = next_events(store, DEAL_ID, 0, None, live_seen=cursor)
    assert parse(events, "conversation") == [m.model_dump(mode="json") for m in gw.conversation(DEAL_ID)]
    assert len(parse(events, "mapping")) == len(store.deal_mappings(DEAL_ID))


def test_the_conversation_route_404s_for_a_missing_deal():
    c = TestClient(create_app())
    assert c.get("/deals/nope/conversation").status_code == 404


# ---- 4. the demo pace ---------------------------------------------------------------------------------------------

def test_the_pace_is_off_by_default_and_under_pytest(monkeypatch):
    def no_sleep(seconds):
        raise AssertionError("the pace waited")

    monkeypatch.setattr(pace, "_sleep", no_sleep)
    monkeypatch.delenv("DEMO_PACE", raising=False)
    store, gw = fresh()
    run_to_approval(gw)
    monkeypatch.setenv("DEMO_PACE", "1")  # a .env with the pace on never slows the suite
    store, gw = fresh()
    run_to_approval(gw)
    for raw in ("0", "off", "", "nope", "-1", "nan"):
        monkeypatch.setenv("DEMO_PACE", raw)
        monkeypatch.setattr(pace, "ALLOW_IN_TESTS", True)
        assert pace.factor() == 0 and pace.pause("turn", "scripted") == 0


def test_the_paced_demo_run_takes_the_documented_time(monkeypatch):
    waits = []
    monkeypatch.setattr(pace, "ALLOW_IN_TESTS", True)
    monkeypatch.setattr(pace, "_sleep", waits.append)
    monkeypatch.setenv("DEMO_PACE", "1")
    store, gw = fresh()
    advance(gw, DEAL_ID, backend="scripted")
    before = sum(waits)
    assert 20 <= before <= 30, before  # Run to the controller's questions
    waits.clear()
    answer_flags(gw)
    advance(gw, DEAL_ID, backend="scripted")
    after = sum(waits)
    assert 10 <= after <= 15, after  # the last answer to "Ready for your approval"
    monkeypatch.setenv("DEMO_PACE", "0.5")
    assert pace.pause("turn", "scripted") == pace.STEPS["turn"] / 2


def test_a_live_model_backend_is_never_paced(monkeypatch):
    monkeypatch.setattr(pace, "ALLOW_IN_TESTS", True)
    monkeypatch.setenv("DEMO_PACE", "1")
    assert pace.paced("scripted") and pace.paced("replay")
    assert not pace.paced("droid") and not pace.paced("anthropic")
    monkeypatch.setenv("AGENT_BACKEND", "droid")
    assert not pace.paced(None)


def test_open_flags_are_questions_and_only_answers_close_them():
    store, gw = fresh()
    advance(gw, DEAL_ID, backend="scripted")
    questions = {m.item_id for m in gw.conversation(DEAL_ID) if m.kind == "question"}
    assert questions == {f.id for f in gw.open_flags(DEAL_ID)}
    assert all(store.items[i].state == State.NEEDS_INFO for i in questions)
