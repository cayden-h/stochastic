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
            for attr in ("deals", "source_lines", "mappings", "items", "results", "tool_runs", "policies", "sessions")}


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


def test_a_second_process_cannot_write_the_same_schema(schema):
    from app.db.postgres import SchemaInUse
    store = open_store(schema)
    with pytest.raises(SchemaInUse, match="DB_SCHEMA"):
        open_store(schema)
    store.close()
    open_store(schema).close()  # free again once the first one closes
