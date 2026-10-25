"""The Postgres store on Tiger Cloud: a full deal survives a restart, a reset starts a new ledger, the log is append only.

Opt in, because it talks to a real database: TEST_DATABASE_URL=<url> .venv/bin/python -m pytest -q tests/test_postgres_store.py
Each test works in its own schema and drops it afterwards.
"""
import os
import uuid

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = ""

import pytest  # noqa: E402

URL = os.getenv("TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="set TEST_DATABASE_URL to run the Postgres store tests")

if URL:
    import psycopg  # noqa: E402

from app.agents.jobs import advance  # noqa: E402
from app.core.models import CONTROLLER  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402


@pytest.fixture
def schema():
    name = f"test_{uuid.uuid4().hex[:10]}"
    yield name
    with psycopg.connect(URL, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {name} CASCADE")


def open_store(schema):
    from app.db.postgres import PostgresStore
    return PostgresStore(URL, schema=schema)


def snapshot(store):
    return {attr: {k: v.model_dump(mode="json") for k, v in getattr(store, attr).items()}
            for attr in ("deals", "source_lines", "mappings", "items", "results", "tool_runs", "policies", "sessions",
                         "edits", "adjustments", "agreements", "approved_briefs", "messages")}


def run_to_posted(gw):
    advance(gw, DEAL_ID, backend="scripted")
    for flag in gw.open_flags(DEAL_ID):
        gw.answer(CONTROLLER, flag.id, flag.default)
    advance(gw, DEAL_ID, backend="scripted")
    approval = next(i for i in gw.store.deal_items(DEAL_ID, "approve_result") if i.state.value == "PROPOSED")
    gw.approve(CONTROLLER, approval.id)
    assert gw.store.deals[DEAL_ID].stage == "posted"


def test_a_posted_deal_survives_a_restart(schema):
    store = open_store(schema)
    gw = Gateway(store)
    seed(store, gw)
    run_to_posted(gw)
    assert store.flush() and store.status()["last_error"] is None
    before, audit, seq = snapshot(store), [a.model_dump(mode="json") for a in store.audit], dict(store._seq)
    store.close()

    again = open_store(schema)
    assert snapshot(again) == before
    assert [a.model_dump(mode="json") for a in again.audit] == audit
    assert again._seq == seq
    assert Gateway(again).verify_chain()  # the hash chain checks out on the rows read back from Postgres
    assert list(again.results) == list(before["results"])  # insertion order kept, so latest_result is the same
    assert again.messages and list(again.messages) == list(before["messages"])  # the conversation replays in order
    again.close()


def test_a_reset_starts_a_new_ledger_and_keeps_the_old_log(schema):
    store = open_store(schema)
    gw = Gateway(store)
    seed(store, gw)
    run_to_posted(gw)
    policies = set(store.policies)
    assert policies  # the controller's answers became policies
    first_rows = len(store.audit)
    with gw.lock:
        store.reset_deals(keep_memory=True)
        seed(store, gw)
    assert store.flush()
    store.close()

    again = open_store(schema)
    assert again.ledger == 2 and set(again.policies) == policies
    assert again.deals[DEAL_ID].stage == "new" and len(again.audit) < first_rows
    with psycopg.connect(URL, options=f"-c search_path={schema},public") as conn:
        counts = dict(conn.execute("SELECT ledger, count(*) FROM audit_log GROUP BY ledger").fetchall())
        reasons = [r for (r,) in conn.execute("SELECT reason FROM ledger ORDER BY id").fetchall()]
    assert counts[1] == first_rows and counts[2] == len(again.audit)
    assert reasons == ["first start", "reset, agent memory kept"]
    again.close()


def test_review_edits_survive_a_restart_and_adjustments_survive_a_reset(schema, monkeypatch):
    from tests.test_edits import _recompute_without_edits  # the flow stand-in until T1; no figures are checked
    monkeypatch.setattr(Gateway, "_recompute", _recompute_without_edits)
    store = open_store(schema)
    gw = Gateway(store)
    seed(store, gw)
    advance(gw, DEAL_ID, backend="scripted")
    for flag in gw.open_flags(DEAL_ID):
        gw.answer(CONTROLLER, flag.id, flag.default)
    advance(gw, DEAL_ID, backend="scripted")
    edit = gw.apply_edit(CONTROLLER, DEAL_ID, "amount", "Nu Aire", "General and Administrative", value=5662.806)["edit"]
    gw.reason_edit(CONTROLLER, edit.id, chip=0)
    assert store.flush() and store.status()["last_error"] is None
    before = snapshot(store)
    store.close()

    again = open_store(schema)
    assert snapshot(again) == before and again.edits[edit.id].status == "reasoned"
    assert again.items[again.deal_items(DEAL_ID, "approve_result")[0].id].state.value == "SUPERSEDED"
    with Gateway(again).lock:
        again.reset_deals(keep_memory=True)
    assert again.flush()
    again.close()
    third = open_store(schema)
    assert not third.edits and set(third.adjustments) == {edit.adjustment_id}
    third.close()


def test_an_agreement_and_its_draft_brief_survive_a_restart(schema):
    from tests.test_brief_reader_gateway import new_deal
    store = open_store(schema)
    gw = Gateway(store)
    new_deal(store, gw)
    advance(gw, DEAL_ID, backend="scripted")
    assert store.deals[DEAL_ID].brief_status == "draft"
    assert store.flush() and store.status()["last_error"] is None
    before = snapshot(store)
    store.close()
    again = open_store(schema)
    assert snapshot(again) == before and len(again.agreements) == 1
    gw = Gateway(again)
    assert gw.brief_draft(DEAL_ID).citations
    from tests.test_brief_reader_gateway import answer_kewaunee
    answer_kewaunee(gw)
    gw.approve_brief(CONTROLLER, DEAL_ID)
    with gw.lock:
        again.reset_deals(keep_memory=True)  # an approved Brief is memory: kept by its agreement hash
    assert again.flush()
    again.close()
    third = open_store(schema)
    assert len(third.approved_briefs) == 1 and not third.agreements
    third.close()


def test_the_audit_log_refuses_update_and_delete(schema):
    store = open_store(schema)
    seed(store, Gateway(store))
    assert store.flush()
    store.close()
    with psycopg.connect(URL, options=f"-c search_path={schema},public") as conn:
        for sql in ("UPDATE audit_log SET reason = 'edited'", "DELETE FROM audit_log"):
            with pytest.raises(psycopg.errors.RaiseException, match="append only"):
                conn.execute(sql)
            conn.rollback()
        assert conn.execute("SELECT hypertable_name FROM timescaledb_information.hypertables "
                            "WHERE hypertable_schema = %s", (schema,)).fetchone() == ("audit_log",)


def test_the_writer_reconnects_after_the_connection_drops(schema):
    store = open_store(schema)
    gw = Gateway(store)
    seed(store, gw)
    assert store.flush()
    with psycopg.connect(URL, autocommit=True) as admin:  # drop the writer's session, as a network blip would
        admin.execute("SELECT pg_terminate_backend(%s)", (store._conn.info.backend_pid,))
    advance(gw, DEAL_ID, backend="scripted")
    assert store.flush(timeout=60) and store.status()["last_error"] is None
    rows = len(store.audit)
    store.close()
    again = open_store(schema)
    assert len(again.audit) == rows and Gateway(again).verify_chain()
    again.close()


def test_the_record_reads_in_sql_and_survives_the_columnstore(schema):
    store = open_store(schema)
    gw = Gateway(store)
    seed(store, gw)
    run_to_posted(gw)
    assert store.flush()
    with psycopg.connect(URL, autocommit=True, options=f"-c search_path={schema},public") as conn:
        run = conn.execute("SELECT posted, stage, verdict, flags, answers, seconds FROM ledger_runs").fetchone()
        assert run[:2] == (True, "posted") and run[2] and run[3] >= 1 and run[4] == run[3] and run[5] >= 0
        tests = conn.execute("SELECT debt, ebitda, leverage FROM covenant_runs WHERE NOT naive").fetchall()
        assert tests and all(d and e and abs(float(d) / float(e) - float(lev)) < 0.001 for d, e, lev in tests)
        assert conn.execute("SELECT runs FROM run_stats").fetchone() == (1,)
        assert conn.execute("SELECT sum(rows) FROM audit_activity").fetchone()[0] == len(store.audit)
        top = conn.execute("SELECT search_text FROM record ORDER BY search_text <@> 'lease' LIMIT 1").fetchone()[0]
        assert "lease" in top.lower()
        # Turn the whole audit log columnar now, as the policy does after a day, then keep writing to it.
        conn.execute("SELECT compress_chunk(c) FROM show_chunks('audit_log') c")
        assert conn.execute("SELECT bool_and(is_compressed) FROM timescaledb_information.chunks "
                            "WHERE hypertable_schema = %s AND hypertable_name = 'audit_log'", (schema,)).fetchone()[0]
    with gw.lock:
        store.reset_deals(keep_memory=True)
        seed(store, gw)
    advance(gw, DEAL_ID, backend="scripted")
    assert store.flush() and store.status()["last_error"] is None
    rows = len(store.audit)
    store.close()
    again = open_store(schema)  # the migration runs again on a columnar audit log
    assert again.ledger == 2 and len(again.audit) == rows and Gateway(again).verify_chain()
    again.close()
    with psycopg.connect(URL, options=f"-c search_path={schema},public") as conn:
        with pytest.raises(psycopg.errors.RaiseException, match="append only"):
            conn.execute("DELETE FROM audit_log WHERE ledger = 1")


def test_a_failing_analytics_script_leaves_the_store_on_postgres(schema, monkeypatch):
    import app.db.postgres as pg
    monkeypatch.setattr(pg, "ANALYTICS_SQL", "SELECT no_such_function();")
    store = open_store(schema)
    assert store.kind == "postgres" and "no_such_function" in store.status()["analytics_error"]
    seed(store, Gateway(store))
    assert store.flush() and store.status()["last_error"] is None
    store.close()


def test_a_second_process_cannot_write_the_same_schema(schema):
    from app.db.postgres import SchemaInUse
    store = open_store(schema)
    with pytest.raises(SchemaInUse, match="DB_SCHEMA"):
        open_store(schema)
    store.close()
    open_store(schema).close()  # free again once the first one closes


def test_the_time_bucket_timeline_matches_memory_and_writes_are_timed(schema):
    from app.db.memory import MemoryStore
    store = open_store(schema)
    gw = Gateway(store)
    seed(store, gw)
    advance(gw, DEAL_ID, backend="scripted")
    assert store.flush()
    for bucket in (60, 7):
        pg = store.timeline(DEAL_ID, bucket)
        mem = MemoryStore.timeline(store, DEAL_ID, bucket)
        assert pg["source"] == "time_bucket" and "error" not in pg
        assert sum(b["rows"] for b in pg["buckets"]) == sum(b["rows"] for b in mem["buckets"]) > 0
        assert sum(b["denied"] for b in pg["buckets"]) == sum(b["denied"] for b in mem["buckets"])
        assert pg["buckets"] == mem["buckets"]  # same origin, same floor, same order
    status = store.status()
    assert status["writes"] > 0 and status["avg_write_ms"] > 0 and status["last_write_ms"] is not None
    print(f"writes={status['writes']} avg_write_ms={status['avg_write_ms']} last_write_ms={status['last_write_ms']}")
    store.close()


def test_the_timeline_falls_back_to_memory_on_a_database_error(schema):
    store = open_store(schema)
    seed(store, Gateway(store))
    assert store.flush()
    good_dsn = store._dsn
    store._dsn = "postgresql://nobody@127.0.0.1:1/none?connect_timeout=1"
    out = store.timeline(DEAL_ID, 60)
    store._dsn = good_dsn
    assert out["source"] == "memory" and out["error"] == "timeline query failed; see the server log"
    assert "nobody" not in out["error"] and "127.0.0.1" not in out["error"]  # host and user stay in the log
    assert sum(b["rows"] for b in out["buckets"]) == len([a for a in store.audit if a.deal_id == DEAL_ID])
    store.close()


def test_the_seeded_cases_survive_a_restart_and_a_reset_of_the_demo_deal(schema):
    """The Dashboard's cases go to Postgres like any record; a restart loads them and seeding skips them; a reset of
    the demo deal starts a new ledger that carries the cases, re-chained, while the old ledger keeps its rows."""
    from app.db.fixtures import cases
    store = open_store(schema)
    gw = Gateway(store)
    seed(store, gw)
    assert cases.seed_cases(gw) == list(cases.CASE_IDS)
    assert store.flush() and store.status()["last_error"] is None
    before = snapshot(store)
    store.close()

    again = open_store(schema)
    gw2 = Gateway(again)
    assert snapshot(again) == before and gw2.verify_chain()
    assert cases.seed_cases(gw2) == []  # never overwrites what Postgres loaded
    stages = {d: again.deals[d].stage for d in cases.CASE_IDS}
    with gw2.lock:
        again.reset_deals(keep_memory=False, keep_deals=set(cases.CASE_IDS), rechain=gw2.rechain)
        seed(again, gw2)
    assert again.flush()
    again.close()

    third = open_store(schema)
    gw3 = Gateway(third)
    assert third.ledger == 2 and gw3.verify_chain()
    assert {d: third.deals[d].stage for d in cases.CASE_IDS} == stages and third.deals[DEAL_ID].stage == "new"
    assert {p.deal_id for p in third.policies.values()} <= set(cases.CASE_IDS)  # the demo deal's memory is cleared
    with psycopg.connect(URL, options=f"-c search_path={schema},public") as conn:
        kept = conn.execute("SELECT count(*) FROM audit_log WHERE ledger = 2").fetchone()[0]
    assert kept == len(third.audit)
    third.close()


def test_a_fresh_reset_retires_a_covering_policy_and_the_retirement_survives_a_restart(schema):
    """`/dev/reset?keep_memory=false` retires a policy learned on another deal that covers the demo deal's companies
    (found on the demo laptop, 2026-10-24); the retirement and its audit row are in Postgres after a restart."""
    from app.core.models import Policy
    from app.db.fixtures import cases
    from app.db.fixtures.kewaunee import PLATFORM
    store = open_store(schema)
    gw = Gateway(store)
    seed(store, gw)
    cases.seed_cases(gw)
    kept = cases.CASE_IDS[0]
    with gw.lock:
        p = Policy(id=store.next_id("p"), role="agent:mapper", kind="covenant_tag", pattern="customer deposits",
                   decision="not_debt", reason="test", approved_by=CONTROLLER, learned_from="wi_x", deal_id=kept,
                   company=PLATFORM.lower())
        store.policies[p.id] = p
        store.reset_deals(keep_memory=False, keep_deals=set(cases.CASE_IDS), rechain=gw.rechain)
        seed(store, gw)
    reason = "fresh demo: clear memory for the demo deal"
    assert gw.retire_policies_covering(DEAL_ID, reason) == [p.id]
    assert store.flush()
    store.close()

    again = open_store(schema)
    gw2 = Gateway(again)
    assert again.policies[p.id].retired_by and gw2.verify_chain()
    assert p.id not in [q.id for q in gw2.policies_for("agent:mapper", DEAL_ID)]
    assert [a.target for a in again.audit if a.action == "policy:retire" and a.reason == reason] == [p.id]
    again.close()
