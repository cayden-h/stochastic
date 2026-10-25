"""A deal left mid-run by a process that stopped is moved to run_failed on start, so Run again works.

Found on 2026-10-24 in the final review: with STORE=postgres, a restart during a run loaded the deal at `mapping`,
no job ran, and the console kept Run, Run it again and Fresh deal disabled until `curl /dev/reset`.
The memory store stands in for the reload here (a new gateway over the same working set); the Postgres test reopens
the schema for real when TEST_DATABASE_URL is set.
"""
import os
import uuid

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.agents import jobs  # noqa: E402
from app.agents.jobs import advance  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import RESTARTED_MID_RUN, Gateway  # noqa: E402

URL = os.getenv("TEST_DATABASE_URL", "")


class ProcessStopped(BaseException):
    """The process dies: not an Exception, so the job runner cannot note it as a failed run."""


def stop_mid_mapping(monkeypatch, after: int = 10):
    """Stop the process after `after` mappings are stored, the way a restart cuts a paced Mapper off."""
    seen = {"n": 0}

    def pause(step, backend=None, **kw):
        if step == "mapping":
            seen["n"] += 1
            if seen["n"] >= after:
                raise ProcessStopped()
    monkeypatch.setattr(jobs.pace, "pause", pause)


def run_until_stopped(gw):
    with pytest.raises(ProcessStopped):
        advance(gw, DEAL_ID, backend="scripted")
    assert gw.store.deals[DEAL_ID].stage == "mapping"
    assert gw.store.deal_mappings(DEAL_ID), "some mappings were stored before the stop"


def assert_recovered(gw, moved):
    assert moved == [DEAL_ID]
    assert gw.store.deals[DEAL_ID].stage == "run_failed"
    rows = [r for r in gw.store.audit if r.deal_id == DEAL_ID and r.action == "run:failed"]
    assert len(rows) == 1 and rows[0].reason == RESTARTED_MID_RUN
    said = gw.store.deal_messages(DEAL_ID)[-1]
    assert said.to == "human:controller" and RESTARTED_MID_RUN in said.text
    assert gw.verify_chain()


def test_a_deal_left_mid_run_is_run_failed_after_a_reload_and_runs_again(monkeypatch):
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    stop_mid_mapping(monkeypatch)
    run_until_stopped(gw)
    monkeypatch.undo()

    restarted = Gateway(store)  # the reload: a new process, the same record, no job
    assert_recovered(restarted, restarted.recover_interrupted_runs())
    assert restarted.recover_interrupted_runs() == []  # a second start finds nothing to move

    log = advance(restarted, DEAL_ID, backend="scripted")  # Run again picks up where it stopped
    assert log[-1] == "waiting on a flag"
    assert restarted.store.deals[DEAL_ID].stage == "awaiting_flag"
    assert len(restarted.open_flags(DEAL_ID)) == 2
    # The cut-off run's mappings were replaced, not added to: each target line is mapped once, so the books combine.
    targets = [m.target_line_id for m in store.deal_mappings(DEAL_ID)]
    assert len(targets) == len(set(targets)) == len(store.lines(DEAL_ID, store.deals[DEAL_ID].target))
    assert any(r.action == "mapping:discard" for r in store.audit)
    for flag in restarted.open_flags(DEAL_ID):
        restarted.answer("human:controller", flag.id, flag.default)
    advance(restarted, DEAL_ID, backend="scripted")
    assert store.deals[DEAL_ID].stage == "awaiting_approval" and restarted.verify_chain()


def test_a_deal_with_a_job_running_is_left_alone():
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    store.deals[DEAL_ID].stage = "preparing"
    gw.running.add(DEAL_ID)
    assert gw.recover_interrupted_runs() == []
    assert store.deals[DEAL_ID].stage == "preparing"


@pytest.mark.parametrize("stage", ["new", "awaiting_flag", "awaiting_approval", "needs_attention", "posted",
                                   "run_failed", "awaiting_brief", "brief_ready"])
def test_a_resting_stage_is_left_alone(stage):
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    store.deals[DEAL_ID].stage = stage
    assert gw.recover_interrupted_runs() == []
    assert store.deals[DEAL_ID].stage == stage


def test_case_and_health_say_whether_a_job_is_really_running():
    from app.main import create_app
    app = create_app()
    c = TestClient(app)
    gw = app.state.gateway
    assert c.get(f"/deals/{DEAL_ID}/case").json()["running"] is False
    assert c.get("/health").json()["running"] is False
    gw.running.add(DEAL_ID)
    try:
        assert c.get(f"/deals/{DEAL_ID}/case").json()["running"] is True
        assert c.get("/health").json()["running"] is True
        assert c.post("/dev/reset").status_code == 409
    finally:
        gw.running.discard(DEAL_ID)
    assert c.post("/dev/reset").status_code == 200


@pytest.mark.skipif(not URL, reason="set TEST_DATABASE_URL to run the Postgres restart test")
def test_postgres_a_deal_left_mid_run_is_run_failed_after_a_restart(monkeypatch):
    import psycopg
    from app.db.postgres import PostgresStore
    schema = f"test_{uuid.uuid4().hex[:10]}"
    try:
        store = PostgresStore(URL, schema=schema)
        gw = Gateway(store)
        seed(store, gw)
        stop_mid_mapping(monkeypatch)
        run_until_stopped(gw)
        monkeypatch.undo()
        store.commit()
        assert store.flush()
        store.close()

        again = PostgresStore(URL, schema=schema)
        assert again.deals[DEAL_ID].stage == "mapping"  # what _load restores
        restarted = Gateway(again)
        assert_recovered(restarted, restarted.recover_interrupted_runs())
        assert again.flush()
        again.close()

        third = PostgresStore(URL, schema=schema)  # the run_failed row and stage were written through
        assert third.deals[DEAL_ID].stage == "run_failed"
        assert Gateway(third).recover_interrupted_runs() == []
        third.close()
    finally:
        with psycopg.connect(URL, autocommit=True) as conn:
            conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
