"""API shape tests: the typed /case response and the debt capacity that comes from the limit_test run."""
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


def test_openapi_and_404():
    c = TestClient(create_app())
    spec = c.get("/openapi.json").json()
    schemas = spec["components"]["schemas"]
    assert "CaseResponse" in schemas and "debt_capacity" in schemas["Verdict"]["properties"]
    assert c.get("/deals/nope/case").status_code == 404
