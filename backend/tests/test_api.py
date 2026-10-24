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


# ---------------------------------------------------------------------------- POST /deals (uploads)
HDR = "line,section,period,amount,unit,source_ref,is_total"
BRIEF = {"lender": "Bank", "agreement_ref": "Credit Agreement", "limit": 2.5, "limit_section": "7.1",
         "limit_wording": "Leverage shall not exceed 2.50 to 1.00", "debt_term": "Funded Debt",
         "debt_definition": "Borrowed money", "debt_excludes": ["leases"], "ebitda_definition": "Net income plus interest"}


def platform_csv(income_label="Net income"):
    return (f"{HDR}\nNet sales,income_statement,FY2025,10000,USD thousands,p1,false\n"
            f"{income_label},income_statement,FY2025,900,USD thousands,p2,false\n"
            "Interest expense,income_statement,FY2025,100,USD thousands,p3,false\n"
            "Income tax expense,income_statement,FY2025,200,USD thousands,p4,false\n"
            "Depreciation,cash_flow,FY2025,300,USD thousands,p5,false\n"
            "Long-term debt,balance_sheet,FY2025,3000,USD thousands,p6,false\n")


TARGET_CSV = (f"{HDR}\nSales,income_statement,FY2025,5000000,USD,t1,false\n"
              "Net income,income_statement,FY2025,400000,USD,t2,false\n"
              "Notes payable,balance_sheet,FY2025,1000000,USD,t3,false\n")


def upload(c, plat=None, targ=None, headers=None, plat_name="platform.csv", name="Acme", platform="Acme", target="Bolt"):
    files = {"platform_csv": (plat_name, plat if plat is not None else platform_csv(), "text/csv"),
             "target_csv": ("target.csv", targ if targ is not None else TARGET_CSV, "text/csv")}
    data = {"name": name, "platform": platform, "target": target, "brief": json.dumps(BRIEF)}
    return c.post("/deals", files=files, data=data, headers=headers or {})


def test_upload_creates_deal_and_runs():
    c = TestClient(create_app())
    r = upload(c)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["lines"] == {"platform": 6, "target": 3} and body["stage"] == "new"
    did = body["deal_id"]
    assert did in [d["id"] for d in c.get("/deals").json()]
    CaseResponse.model_validate(c.get(f"/deals/{did}/case").json())
    run = c.post(f"/deals/{did}/run")
    assert run.status_code == 200 and "stage" in run.json()


def test_upload_does_not_judge_names_but_ebitda_guardrail_reaches_api():
    c = TestClient(create_app())
    r = upload(c, plat=platform_csv("Net profit"))
    assert r.status_code == 201
    out = c.post("/tools/ebitda", json={"deal_id": r.json()["deal_id"], "inputs": {}}, headers={"X-Actor": "agent:preparer"})
    assert out.status_code == 422
    assert "no net income line found" in out.json()["detail"]


def test_upload_oversized_file_rejected():
    c = TestClient(create_app())
    big = platform_csv() + ("x" * (3 * 1024 * 1024))
    r = upload(c, plat=big)
    assert r.status_code == 422
    assert "platform_csv" in r.json()["detail"]


def test_upload_bad_extension_same_name_agent_and_bad_row():
    c = TestClient(create_app())
    assert upload(c, plat_name="platform.txt").status_code == 422
    assert upload(c, platform="Acme", target="Acme").status_code == 422
    assert upload(c, headers={"X-Actor": "agent:mapper"}).status_code == 403
    bad = upload(c, targ=f"{HDR}\nSales,income_statement,FY,1,USD,,\nOops,ledger,FY,1,USD,,\n")
    assert bad.status_code == 422
    assert "target_csv" in bad.json()["detail"] and "row 3" in bad.json()["detail"]


def test_upload_rejects_non_utf8_and_nonpositive_limit():
    c = TestClient(create_app())
    files = {"platform_csv": ("p.csv", b"\xff\xfe\x00bad", "text/csv"), "target_csv": ("t.csv", TARGET_CSV, "text/csv")}
    data = {"name": "A", "platform": "A", "target": "B", "brief": json.dumps(BRIEF)}
    r = c.post("/deals", files=files, data=data)
    assert r.status_code == 422 and "platform_csv" in r.json()["detail"]
    files["platform_csv"] = ("p.csv", platform_csv(), "text/csv")
    data["brief"] = json.dumps({**BRIEF, "limit": 0})
    assert c.post("/deals", files=files, data=data).status_code == 422
    data["brief"] = "{not json"
    assert c.post("/deals", files=files, data=data).status_code == 422
