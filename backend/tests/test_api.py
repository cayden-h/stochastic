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
    assert v["debt_capacity"] == pytest.approx(49314.113, abs=0.01)
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
            "Short-term borrowings,balance_sheet,FY2025,3000,USD thousands,p6,false\n")


TARGET_CSV = (f"{HDR}\nSales,income_statement,FY2025,5000000,USD,t1,false\n"
              "Net income,income_statement,FY2025,400000,USD,t2,false\n"
              "Depreciation,cash_flow,FY2025,50000,USD,t4,false\n"
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
    assert body["lines"] == {"platform": 6, "target": 4} and body["stage"] == "new"
    did = body["deal_id"]
    assert did in [d["id"] for d in c.get("/deals").json()]
    CaseResponse.model_validate(c.get(f"/deals/{did}/case").json())
    run = c.post(f"/deals/{did}/run")
    assert run.status_code == 200 and "stage" in run.json()
    case = c.get(f"/deals/{did}/case").json()
    for fid in case["open_flags"]:
        flag = next(f for f in case["flags"] if f["id"] == fid)
        assert c.post(f"/work-items/{fid}/answer?auto_advance=false", json={"option_id": flag["default"]}).status_code == 200
    assert c.post(f"/deals/{did}/run").status_code == 200
    case = c.get(f"/deals/{did}/case").json()
    assert case["verdict"] is not None and case["verdict"]["verdict"] in ("ok", "over_limit")


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


def test_denied_create_is_audited():
    from fastapi import FastAPI
    from app.api.routes import build_router
    from app.db.memory import MemoryStore
    from app.gateway.gateway import Gateway
    store = MemoryStore()
    gw = Gateway(store)
    app = FastAPI()
    app.include_router(build_router(gw))
    c = TestClient(app)
    assert upload(c, headers={"X-Actor": "agent:mapper"}).status_code == 403
    rows = [a for a in store.audit if a.action == "create_deal" and a.result == "DENIED"]
    assert len(rows) == 1 and rows[0].actor == "agent:mapper" and rows[0].deal_id == "-"
    assert c.get("/health").json()["chain_valid"] is True
    assert not store.deals


@pytest.mark.parametrize("limit", ["1e400", "-1e400", "0", "-1"])
def test_upload_rejects_infinite_or_nonpositive_limit(limit):
    c = TestClient(create_app())
    brief = json.dumps(BRIEF).replace('"limit": 2.5', f'"limit": {limit}')
    files = {"platform_csv": ("p.csv", platform_csv(), "text/csv"), "target_csv": ("t.csv", TARGET_CSV, "text/csv")}
    r = c.post("/deals", files=files, data={"name": "A", "platform": "A", "target": "B", "brief": brief})
    assert r.status_code == 422, r.text
    assert "limit must be a finite number greater than 0" in r.json()["detail"]


def test_upload_spaces_only_name_rejected():
    c = TestClient(create_app())
    assert upload(c, name="   ").status_code == 422


def test_body_limit_middleware_rejects_big_content_length():
    import asyncio
    from app.api.body_limit import BodyLimitMiddleware
    called = []

    async def downstream(scope, receive, send):
        called.append(1)

    sent = []

    async def send(msg):
        sent.append(msg)

    async def receive():
        raise AssertionError("body must not be read")

    mw = BodyLimitMiddleware(downstream, max_bytes=1000)
    scope = {"type": "http", "method": "POST", "path": "/deals", "headers": [(b"content-length", str(100 * 1024 * 1024).encode())]}
    asyncio.run(mw(scope, receive, send))
    assert not called
    assert sent[0]["status"] == 413
    assert b"request body is larger than" in sent[1]["body"]
    small = {"type": "http", "method": "POST", "path": "/deals", "headers": [(b"content-length", b"10")]}
    asyncio.run(mw(small, receive, send))
    assert called == [1]


def test_app_registers_body_limit():
    c = TestClient(create_app())
    r = c.post("/deals", content=b"x", headers={"content-length": str(100 * 1024 * 1024), "content-type": "text/plain"})
    assert r.status_code == 413
    assert "larger than" in r.json()["detail"]


@pytest.mark.parametrize("path,value", [
    ("ebitda_addbacks[0].amount", "NaN"), ("ebitda_addbacks[0].amount", "1e400"),
    ("ebitda_addbacks[0].cap", "NaN"), ("ebitda_addbacks[0].cap", "1e400"),
])
def test_upload_rejects_non_finite_brief_figures(path, value):
    c = TestClient(create_app())
    field = path.split("[")[0], path.rsplit(".", 1)[1]
    adj = {"name": "x", "amount": 1.0, "cap": None, "source_ref": "s"}
    adj[field[1]] = value
    text = json.dumps({**BRIEF, "ebitda_addbacks": [adj]}).replace(f'"{value}"', value)
    files = {"platform_csv": ("p.csv", platform_csv(), "text/csv"), "target_csv": ("t.csv", TARGET_CSV, "text/csv")}
    r = c.post("/deals", files=files, data={"name": "A", "platform": "A", "target": "B", "brief": text})
    assert r.status_code == 422, r.text
    assert f"brief: {path} must be finite" in r.json()["detail"]
    assert c.get("/deals").status_code == 200


def test_verdict_sensitivity_from_limit_test_run():
    # Whole-line debt 71,955 (flag option a) / 28,378.845 = 2.536. Flip add-back 71,955 / 2.5 - 28,378.845 = 403.155.
    # Flip rent 1,970 - 403.155 = 1,566.845.
    c = TestClient(create_app())
    body = full_run(c)
    CaseResponse.model_validate(body)
    v = body["verdict"]
    assert v["naive_debt"] == pytest.approx(71955.0, abs=0.001)
    assert v["naive_leverage"] == pytest.approx(2.536, abs=0.0005)
    assert v["naive_flip_addback"] == pytest.approx(403.155, abs=0.001)
    assert v["naive_flip_rent"] == pytest.approx(1566.845, abs=0.001)
    run = c.get(f"/runs/{v['sensitivity_run_id']}").json()
    assert run["tool"] == "limit_test" and run["inputs"]["sensitivity"] is True
    assert run["inputs"]["leverage_run_id"] == body["result"]["run_ids_by_tool"]["leverage"]
    assert run["outputs"]["naive_flip_addback"] == v["naive_flip_addback"]
    debt_run = c.get(f"/runs/{run['inputs']['naive_debt_run_id']}").json()
    assert debt_run["tool"] == "covenant_debt" and debt_run["outputs"]["debt"] == v["naive_debt"]
    assert v["debt_capacity_run_id"] != v["sensitivity_run_id"]  # the Reviewer's run is untouched
    # A second read reuses the run.
    before = len(c.get(f"/deals/{DEAL_ID}/runs").json())
    again = c.get(f"/deals/{DEAL_ID}/case").json()["verdict"]
    assert again["sensitivity_run_id"] == v["sensitivity_run_id"]
    assert len(c.get(f"/deals/{DEAL_ID}/runs").json()) == before


def test_timeline_counts_match_the_audit_log():
    c = TestClient(create_app())
    full_run(c)
    audit = c.get(f"/deals/{DEAL_ID}/audit").json()["rows"]
    body = c.get(f"/deals/{DEAL_ID}/timeline").json()
    assert body["deal_id"] == DEAL_ID and body["bucket_seconds"] == 60 and body["source"] == "memory"
    buckets = body["buckets"]
    assert buckets and set(buckets[0]) == {"start", "actor", "kind", "rows", "denied"}
    assert sum(b["rows"] for b in buckets) == len(audit)
    assert sum(b["denied"] for b in buckets) == len([a for a in audit if a["result"] == "DENIED"])
    assert {b["kind"] for b in buckets} == {a["action"].split(":")[0] for a in audit}
    keys = [(b["start"], b["actor"], b["kind"]) for b in buckets]
    assert keys == sorted(keys) and len(keys) == len(set(keys))
    hourly = c.get(f"/deals/{DEAL_ID}/timeline?bucket=3600").json()
    assert hourly["bucket_seconds"] == 3600 and sum(b["rows"] for b in hourly["buckets"]) == len(audit)


def test_timeline_bucket_bounds_and_unknown_deal():
    c = TestClient(create_app())
    for bad in (0, -5, 86401, "x"):
        assert c.get(f"/deals/{DEAL_ID}/timeline?bucket={bad}").status_code == 422
    for ok in (1, 86400):
        assert c.get(f"/deals/{DEAL_ID}/timeline?bucket={ok}").status_code == 200
    assert c.get("/deals/nope/timeline").status_code == 404


def test_timeline_buckets_floor_to_the_time_bucket_origin():
    # Hand-made rows. 18:00:05 and 18:00:59 share the 18:00:00 minute; 18:01:00 starts the next one.
    # With 7 s buckets from the TimescaleDB origin 2000-01-03 00:00 UTC: 2026-10-24 18:00:05 is
    # 9,791 days + 64,805 s after the origin = 846,007,205 s; 846,007,205 // 7 * 7 = 846,007,204, so 18:00:04.
    from datetime import datetime, timezone
    from app.core.models import AuditRow
    from app.db.memory import MemoryStore
    store = MemoryStore()
    t = lambda s: datetime(2026, 10, 24, 18, 0, 0, tzinfo=timezone.utc).replace(minute=s // 60, second=s % 60)
    rows = [(5, "agent:mapper", "propose:map_lines", "ALLOWED"), (59, "agent:mapper", "tool:consolidate", "DENIED"),
            (59, "agent:mapper", "propose:map_lines", "ALLOWED"), (60, "human:controller", "answer", "ALLOWED")]
    for i, (s, actor, action, result) in enumerate(rows):
        store.audit.append(AuditRow(id=i + 1, at=t(s), deal_id="d1", actor=actor, action=action, result=result,
                                    prev_hash="x", hash="y"))
    store.audit.append(AuditRow(id=9, at=t(5), deal_id="other", actor="a", action="b", result="ALLOWED",
                                prev_hash="x", hash="y"))
    out = store.timeline("d1", 60)
    assert out["source"] == "memory" and out["bucket_seconds"] == 60
    assert out["buckets"] == [
        {"start": "2026-10-24T18:00:00+00:00", "actor": "agent:mapper", "kind": "propose", "rows": 2, "denied": 0},
        {"start": "2026-10-24T18:00:00+00:00", "actor": "agent:mapper", "kind": "tool", "rows": 1, "denied": 1},
        {"start": "2026-10-24T18:01:00+00:00", "actor": "human:controller", "kind": "answer", "rows": 1, "denied": 0},
    ]
    assert store.timeline("d1", 7)["buckets"][0]["start"] == "2026-10-24T18:00:04+00:00"


def test_no_sensitivity_on_second_run_without_a_covenant_flag():
    # After /dev/reset with memory kept, the policy settles the financing lines and no covenant flag opens, so
    # there is no whole-line covenant_debt run to read. The five keys are left out and no extra run is made.
    c = TestClient(create_app())
    first = full_run(c)
    assert c.post(f"/work-items/{first['verdict']['approval_item']}/approve").json()["state"] == "POSTED"
    assert c.post("/dev/reset").json()["ok"]
    body = full_run(c)
    assert body["open_flags"] == [] and body["verdict"]["review"]["verdict"] == "pass"
    v = body["verdict"]
    for key in ("naive_debt", "naive_leverage", "naive_flip_addback", "naive_flip_rent", "sensitivity_run_id"):
        assert key not in v
    runs = c.get(f"/deals/{DEAL_ID}/runs").json()
    assert not any(r["tool"] == "limit_test" and r["inputs"].get("sensitivity") for r in runs)
    assert not any(r["tool"] == "covenant_debt" and r["inputs"].get("sensitivity") for r in runs)
    assert len(c.get(f"/deals/{DEAL_ID}/runs").json()) == len(runs)  # reading again adds nothing


def test_sensitivity_failure_does_not_fail_case(monkeypatch):
    # A gateway error in the optional sensitivity run returns the verdict without the keys, and is not retried.
    from app.api import routes
    from app.gateway.gateway import Gateway
    monkeypatch.setattr(routes, "_SENSITIVITY_FAILED", set())
    real = Gateway.run_tool

    def failing(self, actor, deal_id, name, inputs=None):
        if name == "limit_test" and (inputs or {}).get("sensitivity"):  # a leverage run is not a covenant_debt run
            inputs = {**inputs, "naive_debt_run_id": inputs["leverage_run_id"]}
        return real(self, actor, deal_id, name, inputs)

    monkeypatch.setattr(Gateway, "run_tool", failing)
    c = TestClient(create_app())
    body = full_run(c)
    assert body["verdict"]["leverage"] == pytest.approx(0.762, abs=0.0005) and "naive_debt" not in body["verdict"]
    audit = c.get(f"/deals/{DEAL_ID}/audit").json()["rows"]
    errors = [a for a in audit if a["action"] == "tool:limit_test" and "covenant_debt run" in (a.get("reason") or "")]
    assert len(errors) == 1  # the failure happened once and was audited
    rows = len(audit)
    again = c.get(f"/deals/{DEAL_ID}/case")
    assert again.status_code == 200 and "naive_debt" not in again.json()["verdict"]
    assert len(c.get(f"/deals/{DEAL_ID}/audit").json()["rows"]) == rows


def test_second_run_while_one_is_in_progress_is_refused(monkeypatch):
    """Answering the last flag starts the job runner; a Run click at the same moment must get 409, not a second Preparer."""
    import threading

    from app.api import routes

    started, finish = threading.Event(), threading.Event()

    def slow_advance(gw, deal_id, backend=None):
        started.set()
        finish.wait(5)
        return ["slow"]

    monkeypatch.setattr(routes, "advance", slow_advance)
    c = TestClient(create_app())
    first = {}
    t = threading.Thread(target=lambda: first.setdefault("r", c.post(f"/deals/{DEAL_ID}/run")))
    t.start()
    assert started.wait(5)
    second = c.post(f"/deals/{DEAL_ID}/run")
    finish.set()
    t.join(5)
    assert second.status_code == 409 and "in progress" in second.json()["detail"]
    assert first["r"].status_code == 200
    assert c.post(f"/deals/{DEAL_ID}/run").status_code == 200  # released after the first run ends
