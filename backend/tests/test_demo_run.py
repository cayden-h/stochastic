"""The 30-second demo, beat by beat, through the API. Every number the screen shows is asserted here.

docs/STOCHASTIC.md section 12 and docs/demo-script.md describe this run. If this test and those files disagree,
fix the words: the figures here are what the tools produce on the filing data.
"""
import os

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.fixtures.kewaunee import DEAL_ID, TARGET  # noqa: E402
from app.main import create_app  # noqa: E402

LIMIT = 2.5
EBITDA = 28378.845  # 18,043 Kewaunee + 7,268.845 Nu Aire + 4,019 pension termination + 1,018 stock compensation - 1,970 rent
DEBT = 21633.0  # 15,000 + 5,563 + 805 + 109 + 156 (the agreement's reading)
LEVERAGE = 0.762  # 21,633 / 28,378.845
DEBT_CAPACITY = 49314.113  # 2.5 * 28,378.845 - 21,633
NAIVE_DEBT = 71955.0  # whole line: 21,633 + 27,782 sale-leaseback + 22,540 seller notes
REPORTED_EBITDA = 25311.845  # as filed: 18,043 Kewaunee + 7,268.845 Nu Aire, no add-backs and no rent deduction
TOTAL_ASSETS = 182456.181  # 134,478 + 47,978.181


def case(c):
    return c.get(f"/deals/{DEAL_ID}/case").json()


def test_the_demo_run_beat_by_beat():
    c = TestClient(create_app())
    assert c.get("/health").json()["chain_valid"]

    # Beat 1: press Run. The Mapper maps every target line and stops on two flags.
    assert c.post(f"/deals/{DEAL_ID}/run").json()["stage"] == "awaiting_flag"
    body = case(c)
    target_lines = [l for l in body["source_lines"] if l["company"] == TARGET]
    assert len(body["mappings"]) == len(target_lines)
    assert body["verdict"] is None
    assert len(body["open_flags"]) == 2

    # Beat 2: the flag card. The financing liability holds three debts; each option shows its computed effect.
    fin = next(f for f in body["flags"] if "Financing liability" in f["question"])
    effects = {o["id"]: o["effect"] for o in fin["options"]}
    assert fin["default"] == "b"
    # The whole-line reading is one reading end to end: balance sheet debt over reported EBITDA, as filed.
    assert effects["a"] == "As filed: debt 71,955K over reported EBITDA 25,312K. Leverage 2.84x against 2.50x. Over the limit."
    assert effects["b"] == "Senior Funded Bank Debt 21,633K. Leverage 0.76x against 2.50x. OK."
    assert effects["c"] == "Senior Funded Bank Debt 44,173K. Leverage 1.56x against 2.50x. OK."
    assert all(o["run_id"] for o in fin["options"])  # every effect traces to a limit_test run
    for o in fin["options"]:
        assert c.get(f"/runs/{o['run_id']}").json()["tool"] == "limit_test"
    cds = next(f for f in body["flags"] if "Certificates of Deposit" in f["question"])
    assert cds["default"] == "a" and "Cash and cash equivalents" in cds["options"][0]["effect"]

    # Beat 3: the controller picks the agreement's reading on both cards.
    for f in (fin, cds):
        r = c.post(f"/work-items/{f['id']}/answer?auto_advance=false", json={"option_id": f["default"]})
        assert r.status_code == 200 and r.json()["state"] == "POSTED"  # the gateway posts the answer itself

    # Beat 4: code combines the books and tests the limit. The Reviewer passes it.
    assert c.post(f"/deals/{DEAL_ID}/run").json()["stage"] == "awaiting_approval"
    body = case(c)
    v = body["verdict"]
    assert v["verdict"] == "ok" and v["limit"] == LIMIT
    assert v["leverage"] == pytest.approx(LEVERAGE, abs=0.0005)
    assert v["headroom_turns"] == pytest.approx(LIMIT - LEVERAGE, abs=0.0005)
    assert v["ebitda"] == pytest.approx(EBITDA, abs=0.001)
    assert v["debt"] == pytest.approx(DEBT, abs=0.001)
    assert v["debt_term"] == "Senior Funded Bank Debt"
    assert v["debt_capacity"] == pytest.approx(DEBT_CAPACITY, abs=0.01)
    assert v["debt_capacity_run_id"] in body["result"]["review"]["run_ids"]
    # Sensitivity: the whole-line reading as filed is 71,955 over reported EBITDA 25,312 = 2.843. It would need
    # 71,955 / 2.5 - 25,312 = 3,470 more EBITDA to pass, so a missed add-back or a rent estimate cannot flip it.
    assert v["naive_debt"] == pytest.approx(NAIVE_DEBT, abs=0.001)
    assert v["naive_ebitda"] == pytest.approx(REPORTED_EBITDA, abs=0.5)
    assert v["naive_leverage"] == pytest.approx(2.843, abs=0.0005)
    assert v["naive_flip_addback"] == pytest.approx(NAIVE_DEBT / LIMIT - v["naive_ebitda"], abs=0.001)
    assert v["naive_flip_addback"] > 3000
    assert c.get(f"/runs/{v['sensitivity_run_id']}").json()["tool"] == "limit_test"
    assert v["review"]["verdict"] == "pass" and v["tie_out_ok"] is True
    assert v["approval_state"] == "PROPOSED" and v["posted"] is False
    assert v["backend"] == "scripted"
    rows = body["result"]["rows"]
    total_assets = next(r for r in rows if r["line"] == "Total Assets")
    total_le = next(r for r in rows if r["line"] == "Total Liabilities and Stockholders' Equity")
    assert total_assets["combined"] == pytest.approx(TOTAL_ASSETS, abs=0.001)
    assert total_le["combined"] == pytest.approx(TOTAL_ASSETS, abs=0.001)  # the combined balance sheet balances
    assert all(r["run_id"] for r in rows)

    # Beat 5: the controller approves and the gateway posts. An agent cannot.
    item = v["approval_item"]
    assert c.post(f"/work-items/{item}/approve", headers={"X-Actor": "agent:preparer"}).status_code == 403
    assert c.post(f"/work-items/{item}/approve").json()["state"] == "POSTED"
    body = case(c)
    assert body["stage"] == "posted" and body["verdict"]["posted"] is True
    assert body["audit"]["chain_valid"] and body["audit"]["denied"] >= 1

    # Beat 6: reset and run again. No flag, because the Mapper applies what the controller decided.
    assert c.post("/dev/reset").json()["ok"]
    assert c.post(f"/deals/{DEAL_ID}/run").json()["stage"] == "awaiting_approval"
    body = case(c)
    assert body["open_flags"] == []
    assert body["verdict"]["leverage"] == pytest.approx(LEVERAGE, abs=0.0005)
    learned = [m for m in body["mappings"] if m["reason"].startswith("Policy")]
    assert learned, "the second run shows the learned chip on at least one mapping"
    log = c.get(f"/deals/{DEAL_ID}/audit").json()
    assert log["chain_valid"] and any(r["action"] == "policy:apply" for r in log["rows"])
