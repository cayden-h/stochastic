"""API shape tests: the typed /case response and the debt capacity that comes from the limit_test run."""
import json
import os

import pytest
from fastapi.testclient import TestClient

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

from app.api.schemas import CaseResponse  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID  # noqa: E402
from app.main import create_app  # noqa: E402


def full_run(c, option="b"):
    c.post(f"/deals/{DEAL_ID}/run")
    case = c.get(f"/deals/{DEAL_ID}/case").json()
    for fid in case["open_flags"]:
        flag = next(f for f in case["flags"] if f["id"] == fid)
        opt = option if any(o["id"] == option for o in flag["options"]) else flag["default"]
        assert c.post(f"/work-items/{fid}/answer?auto_advance=false", json={"option_id": opt}).status_code == 200
    c.post(f"/deals/{DEAL_ID}/run")
    return c.get(f"/deals/{DEAL_ID}/case").json()


def test_case_before_run_validates():
    c = TestClient(create_app())
    body = c.get(f"/deals/{DEAL_ID}/case").json()
    CaseResponse.model_validate(body)
    assert body["verdict"] is None


def test_debt_capacity_from_limit_test_run():
    c = TestClient(create_app())
    body = full_run(c)
    CaseResponse.model_validate(body)
    v = body["verdict"]
    assert v["debt_capacity"] == pytest.approx(47164.113, abs=0.01)
    run = c.get(f"/runs/{v['debt_capacity_run_id']}").json()
    assert run["tool"] == "limit_test"
    assert run["outputs"]["debt_capacity"] == v["debt_capacity"]
    assert v["debt_capacity_run_id"] in body["result"]["review"]["run_ids"]


def test_openapi_and_404():
    c = TestClient(create_app())
    spec = c.get("/openapi.json").json()
    schemas = spec["components"]["schemas"]
    assert "CaseResponse" in schemas and "debt_capacity" in schemas["Verdict"]["properties"]
    assert c.get("/deals/nope/case").status_code == 404


def _parse(events):
    out = []
    for e in events:
        lines = e.strip().split("\n")
        out.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return out


def test_next_events_stage_and_audit():
    from app.agents.jobs import advance
    from app.api.events import next_events
    from app.db.fixtures.kewaunee import seed
    from app.db.memory import MemoryStore
    from app.gateway.gateway import Gateway

    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)

    events, seen, last = next_events(store, DEAL_ID, 0, None)
    parsed = _parse(events)
    stages = [d for k, d in parsed if k == "stage"]
    assert len(stages) == 1 and stages[0]["stage"] == "new" and stages[0]["deal_id"] == DEAL_ID
    assert stages[0]["open_flags"] == [] and stages[0]["at"]
    assert last == "new"

    advance(gw, DEAL_ID)
    events, seen2, last = next_events(store, DEAL_ID, seen, last)
    parsed = _parse(events)
    audits = [d for k, d in parsed if k == "audit"]
    stages = [d for k, d in parsed if k == "stage"]
    assert audits and seen2 == seen + len(audits)
    assert len(stages) == 1 and stages[0]["stage"] == "awaiting_flag"
    assert stages[0]["open_flags"] == [f.id for f in gw.open_flags(DEAL_ID)] and stages[0]["open_flags"]
    assert parsed[-1][0] == "stage"

    events, seen3, last2 = next_events(store, DEAL_ID, seen2, last)
    assert events == [] and seen3 == seen2 and last2 == last


def test_next_events_audit_cursor_after_reset():
    from app.agents.jobs import advance
    from app.api.events import next_events
    from app.db.fixtures.kewaunee import seed
    from app.db.memory import MemoryStore
    from app.gateway.gateway import Gateway

    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    advance(gw, DEAL_ID)
    rows = [a for a in store.audit if a.deal_id == DEAL_ID]
    assert rows

    events, seen, _ = next_events(store, DEAL_ID, len(rows) + 50, "new")
    audits = [d for k, d in _parse(events) if k == "audit"]
    assert len(audits) == len(rows)
    assert seen == len(rows)


def test_next_events_missing_deal():
    from app.api.events import next_events
    from app.db.memory import MemoryStore

    assert next_events(MemoryStore(), "nope", 5, "new") == ([], 5, "new")
