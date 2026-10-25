"""The demo laptop's "Run the demo": the 15-second run never makes a live call, and a fresh reset clears the memory.

Found on 2026-10-24 by running the installed app. The laptop's .env says AGENT_BACKEND=droid, so a pace "demo" run
went to live Droid (about 45 s to the questions, on Factory credits) instead of the paced scripted run. And three
earlier uploads of the same companies (lowercase names) had left policies that cover the demo deal, so
`/dev/reset?keep_memory=false` still answered `"policies": 3` and a scripted run could skip the questions.
Uploads made before this process started were also crowding the Dashboard; they are hidden now, not deleted.
"""
import csv
import io
import os

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.main as app_main  # noqa: E402
from app.agents import pace, runner  # noqa: E402
from app.agents.backends import droid_backend  # noqa: E402
from app.db.fixtures.kewaunee import BRIEF, DEAL_ID, PLATFORM, TARGET  # noqa: E402
from app.main import create_app  # noqa: E402
from tests.test_demo_pace import FakeClock  # noqa: E402

FRESH_REASON = "fresh demo: clear memory for the demo deal"


@pytest.fixture
def droid_configured(monkeypatch):
    """The demo laptop's .env: AGENT_BACKEND=droid with a key, but here no droid binary. Every call is recorded."""
    calls = []

    def no_droid(role, *args, **kwargs):
        calls.append(role.name)
        raise FileNotFoundError("droid: command not found")
    monkeypatch.setenv("AGENT_BACKEND", "droid")
    monkeypatch.setenv("AGENT_FALLBACK", "scripted")
    monkeypatch.setenv("FACTORY_API_KEY", "test-key")
    monkeypatch.setattr(droid_backend, "run_droid", no_droid)
    clock = FakeClock()
    monkeypatch.setattr(pace, "ALLOW_IN_TESTS", True)
    monkeypatch.setattr(pace, "_sleep", clock.sleep)
    monkeypatch.delenv("DEMO_PACE", raising=False)
    return calls, clock


def answer_all(c, deal_id, auto_advance=True):
    body = c.get(f"/deals/{deal_id}/case").json()
    for fid in body["open_flags"]:
        flag = next(f for f in body["flags"] if f["id"] == fid)
        url = f"/work-items/{fid}/answer" + ("" if auto_advance else "?auto_advance=false")
        assert c.post(url, json={"option_id": flag["default"]}).status_code == 200


def test_a_demo_pace_run_never_calls_droid_and_reaches_the_questions(droid_configured):
    """Since 2026-10-25 the demo replays the recorded Claude Haiku 5.5 run (test_demo_replay.py), not the rules."""
    calls, clock = droid_configured
    runner.LAST_RUNS.clear()
    c = TestClient(create_app())
    r = c.post(f"/deals/{DEAL_ID}/run", json={"sync": False, "pace": "demo"})
    assert r.status_code == 200
    body = c.get(f"/deals/{DEAL_ID}/case").json()
    assert body["stage"] == "awaiting_flag" and len(body["open_flags"]) == 2
    assert calls == []
    assert 5.5 <= clock.now <= 7.0  # paced like the scripted demo, not a live model's own time
    answer_all(c, DEAL_ID)  # the last answer continues in the background, at the same pace and on the same backend
    assert c.get(f"/deals/{DEAL_ID}/case").json()["stage"] == "awaiting_approval"
    assert calls == []
    status = c.get("/health").json()["backend"]
    runs = [r for r in status["last_runs"] if r["role"] != "runner"]
    assert [r["role"] for r in runs] == ["mapper", "preparer", "reviewer"]
    assert all(r["backend"] == "replay" and r["asked"] == "replay" for r in runs)
    assert all([a["backend"] for a in r["attempts"]] == ["replay"] for r in runs)  # no fallback chain
    assert c.get(f"/deals/{DEAL_ID}/case").json()["verdict"]["backend"] == "replay"


def test_a_demo_pace_run_with_an_explicit_backend_uses_that_backend(droid_configured):
    calls, _ = droid_configured
    c = TestClient(create_app())
    c.post(f"/deals/{DEAL_ID}/run", json={"sync": True, "pace": "demo", "backend": "droid"})
    assert calls  # asked for droid, so droid was tried (and fell back, since there is no binary)


def test_the_human_pace_still_follows_the_configured_backend(droid_configured):
    calls, _ = droid_configured
    c = TestClient(create_app())
    c.post(f"/deals/{DEAL_ID}/run", json={"sync": True, "pace": "human"})
    assert calls


def _csv(store, company: str) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["line", "section", "period", "amount", "unit", "source_ref", "is_total"])
    for line in store.lines(DEAL_ID, company):
        w.writerow([line.line, line.section, line.period, line.amount, line.unit, line.source_ref,
                    str(line.is_total).lower()])
    return buf.getvalue()


def upload_demo_companies(c) -> str:
    """Upload the demo deal's own books under lowercase company names, as the laptop's earlier uploads did."""
    store = c.app.state.gateway.store
    demo = store.deals[DEAL_ID]
    files = {"platform_csv": ("platform.csv", _csv(store, PLATFORM), "text/csv"),
             "target_csv": ("target.csv", _csv(store, TARGET), "text/csv")}
    data = {"name": "Kewaunee again", "platform": PLATFORM.lower(), "target": TARGET.lower(),
            "brief": (demo.brief or BRIEF).model_dump_json()}  # the demo deal reads its Brief on its first run (D23)
    r = c.post("/deals", files=files, data=data)
    assert r.status_code == 201, r.text
    return r.json()["deal_id"]


def covering(c) -> list[dict]:
    gw = c.app.state.gateway
    demo = gw.store.deals[DEAL_ID]
    return [p for p in gw.store.policies.values()
            if any(gw._policy_applies(p, DEAL_ID, co) for co in (demo.platform, demo.target))]


def test_a_fresh_reset_retires_the_demo_deals_policies_learned_on_an_upload():
    c = TestClient(create_app(demo_cases=True, demo_cases_background=False))
    did = upload_demo_companies(c)
    c.post(f"/deals/{did}/run")
    answer_all(c, did, auto_advance=False)
    learned = [p for p in covering(c) if p.deal_id == did]
    assert learned  # the upload taught policies that cover the demo deal's companies
    cases = {p.id for p in c.app.state.gateway.store.policies.values() if p.deal_id != did and not p.retired_by}
    assert cases  # the seeded cases' own memory, which covers other companies

    r = c.post("/dev/reset?keep_memory=false").json()
    assert r["policies"] == 0 and did in r["kept_deals"]
    store = c.app.state.gateway.store
    for p in learned:
        assert store.policies[p.id].retired_by  # retired, not deleted
    rows = [a for a in store.audit if a.action == "policy:retire" and a.reason == FRESH_REASON]
    assert sorted(a.target for a in rows) == sorted(p.id for p in learned)
    assert {p.id for p in store.policies.values() if not p.retired_by} == cases  # the cases keep theirs
    assert c.app.state.gateway.verify_chain()

    c.post(f"/deals/{DEAL_ID}/run", json={"sync": True, "pace": "off", "backend": "scripted"})
    body = c.get(f"/deals/{DEAL_ID}/case").json()
    assert body["stage"] == "awaiting_flag" and len(body["open_flags"]) == 2  # both questions asked again


def test_a_reset_that_keeps_memory_keeps_the_upload_policies():
    c = TestClient(create_app())
    did = upload_demo_companies(c)
    c.post(f"/deals/{did}/run")
    answer_all(c, did, auto_advance=False)
    before = len(covering(c))
    assert c.post("/dev/reset").json()["policies"] == before > 0
    assert not [a for a in c.app.state.gateway.store.audit if a.reason == FRESH_REASON]


def test_uploads_from_an_earlier_process_are_hidden_from_the_dashboard_but_kept(monkeypatch):
    first = TestClient(create_app())
    old = upload_demo_companies(first)
    store = first.app.state.gateway.store
    monkeypatch.setattr(app_main, "open_store", lambda: store)  # the next process loads the same record
    c = TestClient(create_app())
    ids = [d["id"] for d in c.get("/deals").json()]
    assert old not in ids and ids[0] == DEAL_ID
    assert old in [d["id"] for d in c.get("/deals?include_uploads=true").json()]
    assert c.get(f"/deals/{old}/case").status_code == 200  # hidden from the list only
    fresh = upload_demo_companies(c)
    ids = [d["id"] for d in c.get("/deals").json()]
    assert fresh in ids and old not in ids and ids[0] == DEAL_ID
    c.post("/dev/reset?keep_memory=false")  # the reset seeds the demo deal again; it stays first
    ids = [d["id"] for d in c.get("/deals").json()]
    assert ids[0] == DEAL_ID and fresh in ids and old not in ids
