"""The Dashboard's five cases: the live demo deal plus four seeded through the real pipeline.

backend/app/db/fixtures/cases.py seeds them; docs/architecture/gateway-and-api.md ("GET /deals", "Seeded cases") is
the contract. The seeding is off under pytest unless a test asks, as these do.
"""
import os

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.fixtures import cases, dlh_grsi, mamas_crown, sstk_envato  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, PLATFORM, TARGET  # noqa: E402
from app.main import create_app  # noqa: E402
from app.tools.finance import to_thousands  # noqa: E402

STAGES = {DEAL_ID: "new", dlh_grsi.DEAL_ID: "posted", mamas_crown.DEAL_ID: "awaiting_approval",
          sstk_envato.DEAL_ID: "awaiting_flag", cases.SAMPLE_ID: "posted"}
SOURCES = {DEAL_ID: "filings", dlh_grsi.DEAL_ID: "filings", mamas_crown.DEAL_ID: "filings",
           sstk_envato.DEAL_ID: "filings", cases.SAMPLE_ID: "sample"}


@pytest.fixture
def seeded():
    app = create_app(demo_cases=True, demo_cases_background=False)
    return app, TestClient(app)


def test_get_deals_returns_the_five_cases_with_the_dashboard_fields(seeded):
    _, c = seeded
    deals = c.get("/deals").json()
    assert [d["deal_id"] for d in deals] == [DEAL_ID, *cases.CASE_IDS]  # the live demo deal first
    for d in deals:
        assert {"deal_id", "platform", "target", "stage", "verdict", "updated_at", "data_source", "note"} <= set(d)
        assert d["deal_id"] == d["id"] and d["stage"] == STAGES[d["deal_id"]]
        assert d["data_source"] == SOURCES[d["deal_id"]] and d["note"] and d["updated_at"]
        if d["verdict"] is not None:
            assert set(d["verdict"]) == {"leverage", "limit", "verdict"}
    by_id = {d["deal_id"]: d for d in deals}
    assert by_id[DEAL_ID]["verdict"] is None and by_id[sstk_envato.DEAL_ID]["verdict"] is None
    assert by_id[dlh_grsi.DEAL_ID]["verdict"] == {"leverage": pytest.approx(3.741, abs=0.0005), "limit": 4.5,
                                                  "verdict": "ok"}
    assert by_id[mamas_crown.DEAL_ID]["verdict"] == {"leverage": pytest.approx(1.898, abs=0.0005), "limit": 3.75,
                                                     "verdict": "ok"}
    assert by_id[cases.SAMPLE_ID]["verdict"]["verdict"] == "ok"


def test_every_seeded_case_is_fully_viewable_with_a_valid_audit_chain(seeded):
    _, c = seeded
    for deal_id in cases.CASE_IDS:
        body = c.get(f"/deals/{deal_id}/case").json()
        assert body["stage"] == STAGES[deal_id] and body["audit"]["chain_valid"] and body["audit"]["denied"] == 0
        targets = [sl for sl in body["source_lines"] if sl["company"] == body["deal"]["target"]]
        assert len(body["mappings"]) == len(targets)  # the Mapping tab: every target line
        msgs = c.get(f"/deals/{deal_id}/conversation").json()
        assert [m for m in msgs if m["kind"] == "question"] and [m for m in msgs if m["policy_id"]]
        assert c.get(f"/deals/{deal_id}/audit").json()["chain_valid"]
        if body["result"]:  # the Review tab: a Reviewer pass read from tie_out and limit_test runs
            assert body["verdict"]["review"]["verdict"] == "pass" and body["verdict"]["tie_out_ok"]
            for rid in body["verdict"]["review"]["run_ids"]:
                assert c.get(f"/runs/{rid}").json()["tool"] in ("tie_out", "limit_test")
    for deal_id in (dlh_grsi.DEAL_ID, cases.SAMPLE_ID):  # posted: the final files download
        assert c.get(f"/deals/{deal_id}/certificate?format=json").status_code == 200
        assert c.get(f"/deals/{deal_id}/export.xlsx").status_code == 200


def test_the_dlh_case_has_its_remembered_remap_and_the_sample_reuses_its_learned_policy(seeded):
    app, c = seeded
    store = app.state.gateway.store
    dlh = c.get(f"/deals/{dlh_grsi.DEAL_ID}/case").json()
    edit, contract = dlh["edits"]
    assert (contract["line"], contract["new_platform_line"], contract["remember"]) == (
        "Other current liabilities", "Deferred revenue", False)
    assert (edit["kind"], edit["line"], edit["new_platform_line"], edit["status"]) == (
        "remap", "Indirect costs", "Contract costs", "reasoned")
    assert store.policies[edit["policy_id"]].scope == "platform" and store.policies[edit["policy_id"]].platform == "DLH"
    loan = next(p for p in store.policies.values()
                if p.deal_id == dlh_grsi.DEAL_ID and p.company == "DLH" and p.decision == "not_debt")
    sample_log = c.get(f"/deals/{cases.SAMPLE_ID}/audit").json()["rows"]
    assert any(r["action"] == "policy:apply" and r["target"] == loan.id for r in sample_log)
    sample = c.get(f"/deals/{cases.SAMPLE_ID}/case").json()
    reused = next(sl for sl in sample["source_lines"] if sl["line"] == loan.pattern.capitalize()
                  or sl["line"].lower() == loan.pattern)
    assert reused["covenant_tag"] == "not_debt" and reused["covenant_policy_id"] == loan.id
    flags = [f for f in sample["flags"] if f["payload"]["kind"] == "covenant_tag"]
    assert len(flags) == 1 and "Mastercard" in flags[0]["question"]  # only the new line is asked
    assert all(sl["source_ref"].startswith("Posted combined books of") for sl in sample["source_lines"]
               if sl["company"] == "DLH")


def test_the_open_case_is_answerable_and_finishes(seeded):
    _, c = seeded
    body = c.get(f"/deals/{sstk_envato.DEAL_ID}/case").json()
    (fid,) = body["open_flags"]
    flag = next(f for f in body["flags"] if f["id"] == fid)
    assert "IFRS 16" in flag["question"] and flag["default"] == "b"
    assert {o["id"]: round(o["leverage"], 2) for o in flag["options"]} == {"a": 1.18, "b": 0.99}
    assert c.post(f"/work-items/{fid}/answer", json={"option_id": "b"}).status_code == 200
    after = c.get(f"/deals/{sstk_envato.DEAL_ID}/case").json()
    assert after["stage"] == "awaiting_approval" and after["verdict"]["leverage"] == pytest.approx(0.994, abs=0.0005)


@pytest.mark.parametrize("keep_memory", [True, False])
def test_reset_resets_only_the_live_deal_and_the_seeded_cases_stay(seeded, keep_memory):
    app, c = seeded
    gw = app.state.gateway
    before = {d: (c.get(f"/deals/{d}/case").json(), c.get(f"/deals/{d}/conversation").json()) for d in cases.CASE_IDS}
    rows_before = {d: [(r["action"], r["target"], r["reason"]) for r in c.get(f"/deals/{d}/audit").json()["rows"]]
                   for d in cases.CASE_IDS}
    c.post(f"/deals/{DEAL_ID}/run")  # the live deal moves on, then is reset
    r = c.post(f"/dev/reset?keep_memory={str(keep_memory).lower()}").json()
    assert r["ok"] and r["kept_deals"] == sorted(cases.CASE_IDS)
    assert gw.verify_chain()
    for d in cases.CASE_IDS:
        case, msgs = c.get(f"/deals/{d}/case").json(), c.get(f"/deals/{d}/conversation").json()
        assert case["stage"] == before[d][0]["stage"] and case["result"] == before[d][0]["result"]
        assert case["mappings"] == before[d][0]["mappings"] and msgs == before[d][1]
        assert [(x["action"], x["target"], x["reason"]) for x in c.get(f"/deals/{d}/audit").json()["rows"]] \
            == rows_before[d]
    seeded_policies = [p for p in gw.store.policies.values() if p.deal_id in cases.CASE_IDS]
    assert seeded_policies  # the memory learned on the cases stays in both modes
    assert c.get(f"/deals/{DEAL_ID}/case").json()["stage"] == "new"
    # The fresh demo run still asks both questions: no seeded policy covers Kewaunee or Nu Aire.
    if not keep_memory:
        assert c.post(f"/deals/{DEAL_ID}/run").json()["stage"] == "awaiting_flag"
        assert len(c.get(f"/deals/{DEAL_ID}/case").json()["open_flags"]) == 2
    ids = [m["id"] for d in [DEAL_ID, *cases.CASE_IDS] for m in c.get(f"/deals/{d}/mappings").json()]
    assert len(ids) == len(set(ids))  # the reset deal's new ids never repeat a kept record's


def test_the_live_deal_still_escalates_on_a_fresh_run_after_seeding(seeded):
    app, c = seeded
    assert c.post(f"/deals/{DEAL_ID}/run").json()["stage"] == "awaiting_flag"
    body = c.get(f"/deals/{DEAL_ID}/case").json()
    assert len(body["open_flags"]) == 2 and not [m for m in body["mappings"] if m["policy_id"]]
    demo = {PLATFORM.casefold(), TARGET.casefold()}
    for p in app.state.gateway.store.policies.values():
        assert (p.company or "").casefold() not in demo and (p.platform or "").casefold() not in demo


def test_seeding_is_idempotent_and_never_touches_existing_records(seeded):
    app, c = seeded
    gw = app.state.gateway
    snapshot = (len(gw.store.audit), len(gw.store.tool_runs), len(gw.store.messages))
    assert cases.seed_cases(gw) == []
    assert (len(gw.store.audit), len(gw.store.tool_runs), len(gw.store.messages)) == snapshot


def test_cases_seeded_from_other_fixtures_are_rebuilt_on_restart_and_the_demo_deal_is_kept():
    """A store seeded by older fixtures (version A, missing two of today's edits) is rebuilt by a new Gateway on the
    same store at version B: the cases are seeded again, the counts read 4 edits, the demo deal and its record are
    untouched, and the audit chain is valid. Seeding again at B rebuilds nothing."""
    from app.gateway.gateway import Gateway

    app = create_app(demo_cases=False)
    c = TestClient(app)
    store = app.state.gateway.store
    assert cases.seed_cases(Gateway(store), version="A") == list(cases.CASE_IDS)
    for e in [e for e in store.edits.values() if e.deal_id == cases.SAMPLE_ID]:
        del store.edits[e.id]  # what an older version seeded
    assert c.get("/memory/counts").json()["edits"] == 2
    demo = (store.deals[DEAL_ID].model_dump(), [sl.id for sl in store.lines(DEAL_ID)])
    policies = len(store.policies)

    gw = Gateway(store)  # a restart on the same store, with new fixtures
    assert cases.seed_cases(gw, version="B") == list(cases.CASE_IDS)
    assert c.get("/memory/counts").json()["edits"] == 4
    assert {d: store.deals[d].seed_version for d in cases.CASE_IDS} == dict.fromkeys(cases.CASE_IDS, "B")
    assert {d: store.deals[d].stage for d in store.deals} == STAGES
    assert (store.deals[DEAL_ID].model_dump(), [sl.id for sl in store.lines(DEAL_ID)]) == demo
    assert len(store.policies) == policies and gw.verify_chain()  # the old cases' memory went with them

    snapshot = (len(store.audit), len(store.tool_runs), len(store.messages))
    assert cases.seed_cases(Gateway(store), version="B") == []
    assert (len(store.audit), len(store.tool_runs), len(store.messages)) == snapshot


def test_seeding_runs_in_the_background_so_health_answers_at_once():
    app = create_app(demo_cases=True)
    c = TestClient(app)
    assert c.get("/health").status_code == 200
    app.state.cases_thread.join(60)
    assert {d["deal_id"] for d in c.get("/deals").json()} == {DEAL_ID, *cases.CASE_IDS}


def test_seeding_is_off_under_pytest_by_default():
    c = TestClient(create_app())
    assert [d["deal_id"] for d in c.get("/deals").json()] == [DEAL_ID]


@pytest.mark.parametrize("module", [dlh_grsi, mamas_crown, sstk_envato])
def test_each_filed_fixture_balances_and_names_its_sources(module):
    assert module.SOURCES and all(u.startswith("https://www.sec.gov/") for u in module.SOURCES.values())
    for blocks in (module.PLATFORM_BLOCKS, module.TARGET_BLOCKS):
        bs = [(line, to_thousands(a, unit), tot) for section, _, unit, _, rows in blocks if section == "balance_sheet"
              for line, a, tot in rows]
        totals = {line.lower(): v for line, v, tot in bs if tot}
        assets = totals["total assets"]
        le = next(v for k, v in totals.items() if k.startswith("total liabilities and"))
        assert assets == pytest.approx(le, abs=0.5)
    names = {line for section, _, _, _, rows in module.TARGET_BLOCKS for line, _, _ in rows}
    assert names <= set(module.MAPPING)  # the scripted Mapper has an answer for every target line


def test_the_seeded_cases_hold_four_reasoned_edits_each_citing_its_source(seeded):
    """The sidebar's Edits counter reads 4 after seeding: real gateway edits (apply_edit, then reason_edit), each
    reason citing the filing note or the sample export that supports it, none remembered as memory."""
    app, c = seeded
    edits = [e for d in cases.CASE_IDS for e in c.get(f"/deals/{d}/case").json()["edits"]]
    assert len(edits) == 4 and all(e["status"] == "reasoned" for e in edits)
    got = {(e["deal_id"], e["line"], e["new_platform_line"]) for e in edits}
    assert got == {(dlh_grsi.DEAL_ID, "Indirect costs", "Contract costs"),
                   (dlh_grsi.DEAL_ID, "Other current liabilities", "Deferred revenue"),
                   (cases.SAMPLE_ID, "Equipment Rental", "General and administrative costs"),
                   (cases.SAMPLE_ID, "Undeposited Funds", "Other current assets")}
    sources = {e["line"]: e["reason_text"] for e in edits}
    assert "Ex 99.3 note 3b" in sources["Indirect costs"]
    assert "Ex 99.2 Note 1" in sources["Other current liabilities"]
    assert "account_list.xlsx" in sources["Equipment Rental"] and "account_list.xlsx" in sources["Undeposited Funds"]
    # Each source says what the reason says (the filing note on the line, or the QuickBooks export).
    assert "contract liabilities" in dlh_grsi.LINE_NOTES["Other current liabilities"]
    accounts = cases.QBO / "account_list.xlsx"
    import openpyxl
    rows = {r[0]: r for r in openpyxl.load_workbook(accounts).active.iter_rows(values_only=True) if r and r[0]}
    assert rows["Equipment Rental"][1] == "Expenses" and rows["Job Expenses:Equipment Rental"][1] == "Expenses"
    assert rows["Undeposited Funds"][1] == "Other Current Assets" and rows["Checking"][1] == "Bank"
    assert [e["remember"] for e in edits].count(True) == 1  # only the DLH remap was remembered (a platform policy)
    for d in cases.CASE_IDS:  # every edited case still ties out and passes review on the edited books
        body = c.get(f"/deals/{d}/case").json()
        if body["edits"]:
            assert body["verdict"]["tie_out_ok"] and body["verdict"]["review"]["verdict"] == "pass"


def test_the_counters_are_totals_across_every_deal_and_the_demo_adds_to_them(seeded):
    app, c = seeded
    store = app.state.gateway.store
    counts = c.get("/memory/counts").json()
    assert counts["edits"] == 4
    assert counts["policies"] == len([p for p in store.policies.values() if not p.retired_by])
    answered = [i for i in store.items.values() if i.type == "flag" and i.answer]
    assert counts["human_answers"] == len(answered) > 0
    assert set(counts["by_deal"]) <= set(cases.CASE_IDS) and sum(v["edits"] for v in counts["by_deal"].values()) == 4
    assert c.get("/health").json()["memory_counts"] == counts
    # The live demo deal adds to them as it runs: two answers, the policies they teach, then one edit.
    c.post(f"/deals/{DEAL_ID}/run", json={"sync": True, "backend": "scripted"})
    for fid in c.get(f"/deals/{DEAL_ID}/case").json()["open_flags"]:
        f = next(x for x in c.get(f"/deals/{DEAL_ID}/case").json()["flags"] if x["id"] == fid)
        c.post(f"/work-items/{fid}/answer?auto_advance=false", json={"option_id": f["default"]})
    c.post(f"/deals/{DEAL_ID}/run", json={"sync": True, "backend": "scripted"})
    mid = c.get("/memory/counts").json()
    assert mid["human_answers"] == counts["human_answers"] + 2 and mid["policies"] > counts["policies"]
    r = c.post(f"/deals/{DEAL_ID}/edits", json={"kind": "remap", "company": "Nu Aire",
                                                "line": "Certificates of Deposit", "platform_line": "Other assets"})
    assert r.status_code == 200, r.text
    c.post(f"/edits/{r.json()['edit']['id']}/reason", json={"chip": 0, "remember": False})
    assert c.get("/memory/counts").json()["edits"] == 5
    # A fresh reset clears the demo deal's answers, its edit, and the policies covering it; the cases keep theirs.
    c.post("/dev/reset?keep_memory=false")
    assert c.get("/memory/counts").json() == counts
