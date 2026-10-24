"""A run that fails marks the deal run_failed, on the sync route the console uses as well as in the background.

Found on 2026-10-25: the console posts {} to /run, which runs sync. When every backend failed for the Preparer, the
route answered 500 but the stage stayed `preparing` with no run:failed row, so the console showed a stuck progress
row and no Run again.
"""
import os

from fastapi.testclient import TestClient

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

from app.db.fixtures.kewaunee import DEAL_ID  # noqa: E402
from app.main import create_app  # noqa: E402


def _fail_every_backend(monkeypatch):
    monkeypatch.setenv("AGENT_BACKEND", "anthropic")
    monkeypatch.setenv("AGENT_FALLBACK", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def _failed_rows(c):
    return [r for r in c.get(f"/deals/{DEAL_ID}/audit").json()["rows"] if r["action"] == "run:failed"]


def test_a_failed_sync_run_of_the_preparer_marks_the_deal_run_failed(monkeypatch):
    c = TestClient(create_app())
    c.post(f"/deals/{DEAL_ID}/run", json={})  # scripted: the Mapper runs and stops on the flags
    case = c.get(f"/deals/{DEAL_ID}/case").json()
    for fid in case["open_flags"]:
        flag = next(f for f in case["flags"] if f["id"] == fid)
        c.post(f"/work-items/{fid}/answer?auto_advance=false", json={"option_id": flag["default"]})
    _fail_every_backend(monkeypatch)
    r = c.post(f"/deals/{DEAL_ID}/run", json={})  # what the console sends
    assert r.status_code == 500 and "every backend failed for preparer" in r.json()["detail"]
    assert c.get(f"/deals/{DEAL_ID}/case").json()["stage"] == "run_failed"
    failed = _failed_rows(c)
    assert len(failed) == 1 and "preparer" in failed[0]["reason"]
    # Run again picks up where it stopped, once a backend works.
    monkeypatch.setenv("AGENT_BACKEND", "scripted")
    monkeypatch.setenv("AGENT_FALLBACK", "scripted")
    assert c.post(f"/deals/{DEAL_ID}/run", json={}).json()["stage"] == "awaiting_approval"


def test_a_failed_background_run_writes_one_run_failed_row(monkeypatch):
    c = TestClient(create_app())
    _fail_every_backend(monkeypatch)
    r = c.post(f"/deals/{DEAL_ID}/run", json={"sync": False})  # TestClient runs the background task before returning
    assert r.status_code == 200
    assert c.get(f"/deals/{DEAL_ID}/case").json()["stage"] == "run_failed"
    assert len(_failed_rows(c)) == 1  # the runner noted it; the route's own note does not add a second row
