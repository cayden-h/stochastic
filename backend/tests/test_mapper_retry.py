"""The job runner retries a refused Mapper result once, with the gateway's reason in the Mapper's input, and then
falls back to the scripted backend, so a refused model result never fails the deal on stage."""
import dataclasses
import os

import pytest

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

from app.agents import jobs  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway, Invalid  # noqa: E402


@pytest.fixture
def world():
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    return store, gw


def _mapper_that_copies_a_platform_id(store, bad_calls):
    """Wrap run_agent so the first `bad_calls` Mapper results name the platform's first line as a target line,
    the slip Claude Haiku 5.5 made in 2 of 12 runs (sl_001 is Kewaunee's cash line, not Nu Aire's). The bad results
    say they came from droid, since a refused scripted result is not retried."""
    real = jobs.run_agent
    inputs = []

    def run_agent(role, inp, call_tool, session=None, backend=None):
        run = real(role, inp, call_tool, session=session, backend=backend)
        if role.name != "mapper":
            return run
        inputs.append(inp)
        if len(inputs) <= bad_calls and backend != "scripted":
            deal = store.deals[DEAL_ID]
            platform_id = store.lines(DEAL_ID, deal.platform)[0].id
            first = run.output.mappings[0].model_copy(update={"target_line_id": platform_id})
            bad = run.output.model_copy(update={"mappings": [first, *run.output.mappings[1:]]})
            run = dataclasses.replace(run, output=bad, backend="droid")
        return run
    return run_agent, inputs


def test_refused_mapper_result_is_retried_once_with_the_reason(world, monkeypatch):
    store, gw = world
    fake, inputs = _mapper_that_copies_a_platform_id(store, bad_calls=1)
    monkeypatch.setattr(jobs, "run_agent", fake)
    jobs.advance(gw, DEAL_ID)
    assert len(inputs) == 2
    assert inputs[0].previous_refusal is None
    assert "unknown target line" in inputs[1].previous_refusal
    refusals = [r for r in store.audit if r.action == "propose:map_lines" and r.result == "DENIED"]
    assert len(refusals) == 1 and "unknown target line" in refusals[0].reason
    assert any(r.action == "propose:map_lines" and r.result == "ALLOWED" for r in store.audit)
    # the refused result wrote nothing, so each target line is mapped exactly once
    target_ids = [m.target_line_id for m in store.deal_mappings(DEAL_ID)]
    assert len(target_ids) == len(set(target_ids)) == len(store.lines(DEAL_ID, store.deals[DEAL_ID].target))
    assert gw.open_flags(DEAL_ID)
    assert gw.verify_chain()


def test_second_refusal_falls_back_to_scripted(world, monkeypatch):
    store, gw = world
    fake, inputs = _mapper_that_copies_a_platform_id(store, bad_calls=2)
    monkeypatch.setattr(jobs, "run_agent", fake)
    log = jobs.advance(gw, DEAL_ID)
    assert len(inputs) == 3
    assert "mapper fell back to scripted after the refusal" in log
    assert [r.result for r in store.audit if r.action == "propose:map_lines"] == ["DENIED", "DENIED", "ALLOWED"]
    assert gw.open_flags(DEAL_ID)  # the scripted Mapper still raises the covenant flag
    assert gw.verify_chain()


def test_a_refused_scripted_result_is_not_hidden(world, monkeypatch):
    store, gw = world
    real = jobs.run_agent

    def run_agent(role, inp, call_tool, session=None, backend=None):
        run = real(role, inp, call_tool, session=session, backend=backend)
        if role.name == "mapper":
            first = run.output.mappings[0].model_copy(update={"target_line_id": "sl_001"})
            run = dataclasses.replace(run, output=run.output.model_copy(
                update={"mappings": [first, *run.output.mappings[1:]]}))
        return run
    monkeypatch.setattr(jobs, "run_agent", run_agent)
    with pytest.raises(Invalid, match="unknown target line"):
        jobs.advance(gw, DEAL_ID)
    assert not store.deal_mappings(DEAL_ID)
