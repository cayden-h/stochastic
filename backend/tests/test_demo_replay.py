"""The demo replays a real recorded Claude Haiku 5.5 run (backend/recordings/haiku-5-5-run2/) through the gateway.

The recording is the Mapper's typed output from the Droid run of 2026-10-24 evening (docs/agents.md, section 9).
The Preparer and the Reviewer re-run their tool sequence on replay, so every number is a fresh gateway run.
"""
import json
import os
from pathlib import Path

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

import pytest  # noqa: E402

from app.core.models import MAPPER, MapperOutput  # noqa: E402
from app.db.fixtures.kewaunee import BRIEF, DEAL_ID, seed, seed_demo  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402

RUN2 = Path(__file__).resolve().parents[1] / "recordings" / "haiku-5-5-run2"


@pytest.fixture
def world():
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    return store, gw


def recorded_mapper() -> MapperOutput:
    return MapperOutput.model_validate(json.loads((RUN2 / "mapper.json").read_text())["output"])


def test_a_mapping_option_that_leaves_some_lines_unmapped_is_stated_without_a_crash(world):
    """The Haiku 5.5 run's mapping flag has options whose `mappings` hold None (leave a line unmapped). Stating the
    question once crashed on sorting None with the line names, after the mappings were written."""
    store, gw = world
    item = gw.create_item(DEAL_ID, "map_lines")
    gw.store_mapping(MAPPER, item.id, recorded_mapper())
    flag = next(f for f in gw.open_flags(DEAL_ID) if f.payload["kind"] == "mapping")
    q = next(m for m in gw.conversation(DEAL_ID) if m.kind == "question" and m.item_id == flag.id)
    assert "default_homes) Other accrued expenses, Other assets, Other income, net, Other non-current liabilities, " \
           "Prepaid expenses and other current assets; 1 line left unmapped;" in q.text, q.text
    assert "all_unmapped) Leave all six unmapped until the controller decides where each belongs. Debt" in q.text
    assert store.deals[DEAL_ID].stage == "awaiting_flag"


# ---------------------------------------------------------------------------------------------------- the demo paces
from fastapi.testclient import TestClient  # noqa: E402

from app.agents import demo_replay, pace, runner  # noqa: E402
from app.agents.jobs import advance  # noqa: E402
from app.core.models import CONTROLLER  # noqa: E402
from app.db.fixtures.kewaunee import PLATFORM, TARGET  # noqa: E402
from app.main import create_app  # noqa: E402
from tests.test_demo_fresh import _csv  # noqa: E402
from tests.test_demo_pace import FakeClock, first  # noqa: E402


@pytest.fixture
def paced(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(pace, "ALLOW_IN_TESTS", True)
    monkeypatch.setattr(pace, "_sleep", clock.sleep)
    monkeypatch.delenv("DEMO_PACE", raising=False)
    monkeypatch.setenv("AGENT_BACKEND", "droid")  # the demo laptop's .env; the demo paces never call it
    monkeypatch.setenv("AGENT_FALLBACK", "scripted")
    runner.LAST_RUNS.clear()
    return clock


def timed(gw, clock):
    said = []
    real = gw._say

    def say(*args, **kwargs):
        msg = real(*args, **kwargs)
        if msg is not None:
            said.append((clock.now, msg))
        return msg
    gw._say = say
    return said


def run_beat(gw, clock, pace_name, deal_id=DEAL_ID):
    """Run to the questions, answer each with its default, run to the approval. Returns (to the questions, after)."""
    said = timed(gw, clock)
    advance(gw, deal_id, pace_name=pace_name)
    t_q, _ = first(said, lambda m: m.kind == "question")
    t_answer = clock.now
    for f in gw.open_flags(deal_id):
        gw.answer(CONTROLLER, f.id, f.default)
    advance(gw, deal_id, pace_name=pace_name)
    t_ready, _ = first(said, lambda m: m.kind == "handoff" and m.text.startswith("Ready for your approval"))
    return t_q, t_ready - t_answer


@pytest.fixture
def demo_world():
    """The live demo deal, which starts from the agreement (D23)."""
    store = MemoryStore()
    gw = Gateway(store)
    seed_demo(store, gw)
    return store, gw


def test_the_demo_pace_replays_the_recorded_haiku_run_and_keeps_its_timings(demo_world, paced):
    store, gw = demo_world
    to_q, after = run_beat(gw, paced, "demo")
    assert 7.7 <= to_q <= 8.7 and 6.0 <= after <= 7.2, (to_q, after)  # read 2.8, verify 1.6, Mapper 3.8; then 6.6
    runs = [r for r in runner.LAST_RUNS if r["role"] != "runner"]
    assert [r["role"] for r in runs] == ["brief_reader", "mapper", "preparer", "reviewer"]
    assert (runs[0]["backend"], runs[0]["model"], runs[0]["recorded"]) == ("scripted", None, False)  # no recording
    for r in runs[1:]:
        assert (r["backend"], r["asked"], r["model"], r["recorded"], r["recording"]) == (
            "replay", "replay", "claude-haiku-5-5", True, "haiku-5-5-run2")
        assert r["recorded_backend"] == "droid" and r["recorded_at"].startswith("2026-10-24")
        assert [a["backend"] for a in r["attempts"]] == ["replay"]  # no fallback chain, no live call
    result = store.latest_result(DEAL_ID)
    assert result.backend == "replay" and round(result.leverage, 2) == 0.76 and result.review.verdict == "pass"
    assert store.deals[DEAL_ID].stage == "awaiting_approval"
    notes = [m.text for m in gw.conversation(DEAL_ID) if m.sender == "agent:preparer"]
    assert any(t.startswith("Replay of the recorded Claude Haiku 5.5 run on droid (haiku-5-5-run2)") for t in notes)


def test_the_replayed_mapper_raises_the_covenant_and_the_certificates_of_deposit_questions(world, paced):
    store, gw = world
    advance(gw, DEAL_ID, pace_name="demo")
    flags = gw.open_flags(DEAL_ID)
    assert [f.payload["kind"] for f in flags] == ["covenant_tag", "mapping"]
    cov, cds = flags
    lines = {l.id: l.line for l in store.lines(DEAL_ID)}
    assert {lines[i] for i in cov.payload["line_ids"]} >= {"Financing liability: PNC Term Loan"}
    assert "Certificates of Deposit" in {lines[i] for i in cds.payload["line_ids"]}
    assert {o.id: round(o.leverage, 2) for o in cov.options} == {"agreement_reading": 0.76, "no_exclusions": 2.84,
                                                                  "unsecured_short_term": 0.73}
    msgs = gw.conversation(DEAL_ID)
    assert "Scripted rules" not in " ".join(m.text for m in msgs)
    q1 = next(m.text for m in msgs if m.kind == "question" and m.item_id == cov.id)
    assert "count as debt: leverage 0.76x, under the 2.50x limit; no_exclusions)" in q1  # no "debt.:"
    for f in flags:
        gw.answer(CONTROLLER, f.id, f.default)
    taught = [p for p in store.policies.values() if p.deal_id == DEAL_ID]
    assert taught and {p.learned_from for p in taught} == {cov.id, cds.id}  # the answers teach the policies


def test_the_factory_pace_is_twice_the_demo(demo_world, paced):
    store, gw = demo_world
    to_q, after = run_beat(gw, paced, "factory")
    assert 15.5 <= to_q <= 17.5, to_q  # twice the demo's 8.2 s
    demo_store = MemoryStore()
    demo_gw = Gateway(demo_store)
    seed_demo(demo_store, demo_gw)
    demo_clock = FakeClock()
    pace._sleep = demo_clock.sleep
    d_q, d_after = run_beat(demo_gw, demo_clock, "demo")
    assert to_q == pytest.approx(2 * d_q, abs=0.01) and after == pytest.approx(2 * d_after, abs=0.01)
    assert 12.5 <= after <= 14.0, (after, d_after)
    assert 28.5 <= to_q + after <= 31.5  # the 30-second Factory beat, agent time only
    assert all(r["backend"] == "replay" for r in runner.LAST_RUNS if r["role"] != "brief_reader")


def test_health_and_case_say_replay_with_the_recorded_model(paced):
    c = TestClient(create_app())
    assert c.post(f"/deals/{DEAL_ID}/run", json={"sync": True, "pace": "demo"}).json()["stage"] == "awaiting_flag"
    for status in (c.get("/health").json()["backend"], c.get(f"/deals/{DEAL_ID}/case").json()["backend"]):
        (run,) = [r for r in status["last_runs"] if r["role"] == "mapper"]
        assert (run["backend"], run["model"], run["recorded"]) == ("replay", "claude-haiku-5-5", True)
        rec = status["demo_recording"]
        assert (rec["name"], rec["model"], rec["backend"]) == ("haiku-5-5-run2", "claude-haiku-5-5", "droid")
        assert rec["recorded_at"] == "2026-10-24T03:40:02-07:00" and rec["model_confirmed"] is False


def test_a_demo_run_after_a_fresh_reset_with_the_cases_seeded_still_escalates_and_learns(paced):
    """The store's ids keep counting across resets and the seeded cases, so the recorded line ids are translated."""
    c = TestClient(create_app(demo_cases=True, demo_cases_background=False))
    c.post(f"/deals/{DEAL_ID}/run", json={"sync": True, "pace": "demo"})
    from tests.test_demo_fresh import answer_all
    answer_all(c, DEAL_ID)
    assert c.get(f"/deals/{DEAL_ID}/case").json()["stage"] == "awaiting_approval"
    c.post("/dev/reset?keep_memory=false")
    first_id = min(l["id"] for l in c.get(f"/deals/{DEAL_ID}/case").json()["source_lines"])
    assert first_id != "sl_001"  # not the recording's ids
    runner.LAST_RUNS.clear()
    c.post(f"/deals/{DEAL_ID}/run", json={"sync": True, "pace": "demo"})
    body = c.get(f"/deals/{DEAL_ID}/case").json()
    assert body["stage"] == "awaiting_flag" and len(body["open_flags"]) == 2
    assert runner.LAST_RUNS[-1]["backend"] == "replay" and runner.LAST_RUNS[-1]["meta"]["line_ids_translated"]
    answer_all(c, DEAL_ID)
    body = c.get(f"/deals/{DEAL_ID}/case").json()
    assert body["stage"] == "awaiting_approval" and round(body["verdict"]["leverage"], 2) == 0.76
    assert body["verdict"]["backend"] == "replay"


def test_a_second_run_with_memory_kept_is_scripted_and_says_why(paced):
    """The recording was made with no memory, so with the policies learned it would re-ask what the agents know."""
    c = TestClient(create_app())
    c.post(f"/deals/{DEAL_ID}/run", json={"sync": True, "pace": "demo"})
    from tests.test_demo_fresh import answer_all
    answer_all(c, DEAL_ID)
    c.post("/dev/reset")  # keep memory
    runner.LAST_RUNS.clear()
    c.post(f"/deals/{DEAL_ID}/run", json={"sync": True, "pace": "demo"})
    body = c.get(f"/deals/{DEAL_ID}/case").json()
    assert body["open_flags"] == [] and body["stage"] == "awaiting_approval"  # the policies answered them
    assert {r["backend"] for r in runner.LAST_RUNS} == {"scripted"}
    assert all(r["model"] is None and r["recorded"] is False for r in runner.LAST_RUNS)
    note = next(m for m in c.get(f"/deals/{DEAL_ID}/conversation").json() if m["text"].startswith("Scripted rules"))
    assert "learned policies cover this deal" in note["text"]


def upload(c, name, plat, targ, platform=PLATFORM, target=TARGET):
    brief = (c.app.state.gateway.store.deals[DEAL_ID].brief or BRIEF).model_dump_json()  # read on the first run (D23)
    r = c.post("/deals", files={"platform_csv": ("Kewaunee_10Q.csv", plat, "text/csv"),
                                "target_csv": ("NuAire_FY2024.csv", targ, "text/csv")},
               data={"name": name, "platform": platform, "target": target, "brief": brief})
    assert r.status_code == 201, r.text
    return r.json()["deal_id"]


def test_an_upload_of_the_demo_statements_replays_the_recording_at_the_factory_pace(paced):
    c = TestClient(create_app())
    store = c.app.state.gateway.store
    did = upload(c, "Kewaunee acquires Nu Aire (uploaded)", _csv(store, PLATFORM), _csv(store, TARGET))
    r = c.post(f"/deals/{did}/run", json={"sync": False, "pace": "factory"})
    assert r.status_code == 200
    body = c.get(f"/deals/{did}/case").json()
    assert body["stage"] == "awaiting_flag" and len(body["open_flags"]) == 2
    assert 6.0 <= paced.now <= 8.5, paced.now  # a Brief sent as JSON: no read; the Mapper 2.4 + 2.8 + 1.2, then 1.2
    asked = paced.now
    from tests.test_demo_fresh import answer_all
    answer_all(c, did)  # the last answer continues in the background at the factory pace
    body = c.get(f"/deals/{did}/case").json()
    assert body["stage"] == "awaiting_approval" and body["verdict"]["backend"] == "replay"
    assert 13.0 <= paced.now - asked <= 15.0
    assert {(r["backend"], r["model"]) for r in runner.LAST_RUNS} == {("replay", "claude-haiku-5-5")}


def test_any_other_upload_runs_the_scripted_rules_at_the_factory_pace_and_says_so(paced):
    c = TestClient(create_app())
    store = c.app.state.gateway.store
    targ = _csv(store, TARGET).replace("Certificates of Deposit", "Short-term investments")
    did = upload(c, "Another deal", _csv(store, PLATFORM), targ)
    c.post(f"/deals/{did}/run", json={"sync": True, "pace": "factory"})
    assert paced.now > 0  # paced
    assert {(r["backend"], r["asked"], r["model"], r["recorded"]) for r in runner.LAST_RUNS} == {
        ("scripted", "scripted", None, False)}
    note = next(m for m in c.get(f"/deals/{did}/conversation").json() if m["text"].startswith("Scripted rules"))
    assert "not the recorded Kewaunee and Nu Aire statements" in note["text"]


def test_the_content_hash_ignores_ids_and_company_case_but_not_amounts(world):
    store, gw = world
    lines = store.lines(DEAL_ID)
    base = demo_replay.content_digest(lines, PLATFORM)
    renamed = [l.model_copy(update={"id": "x" + l.id, "company": l.company.lower()}) for l in lines]
    assert demo_replay.content_digest(renamed, PLATFORM.lower()) == base
    changed = [l.model_copy(update={"amount": l.amount + 1}) if i == 3 else l for i, l in enumerate(lines)]
    assert demo_replay.content_digest(changed, PLATFORM) != base


def test_an_agreement_upload_reads_the_brief_with_the_rules_then_replays_the_mapper(paced):
    """No Haiku recording exists for the Brief Reader, so a replayed Factory run reads the Brief with the rules."""
    from tests.test_api_brief import EXCERPT, answer_open_brief_flags, fixture_csv, post_deal
    c = TestClient(create_app())
    r = post_deal(c, agreement=EXCERPT, agreement_name="kewaunee_ex101_excerpt.txt", plat=fixture_csv(PLATFORM),
                  targ=fixture_csv(TARGET), platform=PLATFORM, target=TARGET)
    did = r.json()["deal_id"]
    c.post(f"/deals/{did}/run", json={"sync": True, "pace": "factory"})
    assert [(r["role"], r["backend"]) for r in runner.LAST_RUNS] == [("brief_reader", "scripted")]
    answer_open_brief_flags(c, did)
    gw = c.app.state.gateway
    deal = gw.store.deals[did]
    if deal.brief_status != "approved":
        assert c.post(f"/deals/{did}/brief/approve").status_code == 200, deal.brief_status
    c.post(f"/deals/{did}/run", json={"sync": True, "pace": "factory"})
    assert runner.LAST_RUNS[-1]["role"] == "mapper" and runner.LAST_RUNS[-1]["backend"] == "replay"
    assert len(gw.open_flags(did)) == 2


def test_an_upload_of_the_demo_agreement_and_statements_reads_verifies_and_replays_in_about_30_s(paced):
    """The Factory beat from the agreement (D23): the demo deal's extract and statements uploaded. The verifier fills
    the book amounts and approves the Brief, so the first thing the controller sees is the Mapper's one escalation."""
    from tests.test_api_brief import fixture_csv, post_deal
    from app.db.fixtures.kewaunee import agreement_text
    from tests.test_demo_fresh import answer_all
    c = TestClient(create_app())
    r = post_deal(c, agreement=agreement_text(), agreement_name="kewaunee_ex101_extract.txt",
                  plat=fixture_csv(PLATFORM), targ=fixture_csv(TARGET), platform=PLATFORM, target=TARGET)
    did = r.json()["deal_id"]
    c.post(f"/deals/{did}/run", json={"sync": True, "pace": "factory"})
    body = c.get(f"/deals/{did}/case").json()
    assert body["deal"]["brief_status"] == "approved" and body["brief_verification"]["auto_approved"]
    assert body["stage"] == "awaiting_flag" and len(body["open_flags"]) == 2
    asked = paced.now
    assert 15.5 <= asked <= 18.5, asked
    answer_all(c, did)
    assert c.get(f"/deals/{did}/case").json()["stage"] == "awaiting_approval"
    assert 28.5 <= paced.now <= 32.5, paced.now
    assert [(r["role"], r["backend"]) for r in runner.LAST_RUNS] == [
        ("brief_reader", "scripted"), ("mapper", "replay"), ("preparer", "replay"), ("reviewer", "replay")]


def test_another_agreement_upload_is_not_auto_approved(paced):
    from tests.test_api_brief import EXCERPT, fixture_csv, post_deal
    c = TestClient(create_app())
    r = post_deal(c, agreement=EXCERPT, agreement_name="excerpt.txt", plat=fixture_csv(PLATFORM),
                  targ=fixture_csv(TARGET), platform=PLATFORM, target=TARGET)
    deal = c.app.state.gateway.store.deals[r.json()["deal_id"]]
    assert not deal.brief_auto_approve and deal.book_amounts == []
