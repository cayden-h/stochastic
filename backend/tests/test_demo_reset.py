"""The stage backups: the pinned replay must raise the covenant flag, and a reset between judges must bring it back.

Found by the risk review on 2026-10-24: the pinned replay was a copy of a run made with memory (no flag), and the
reset kept memory, so a second judge saw no flag and a left-open flag held the fork slot.
"""
import os

from fastapi.testclient import TestClient

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

from app.agents import recording  # noqa: E402
from app.agents.jobs import advance  # noqa: E402
from app.core.models import CONTROLLER, MapperOutput  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402
from app.main import create_app  # noqa: E402


def test_the_pinned_replay_is_a_first_run_with_a_covenant_flag():
    out, backend, _ = recording.load("mapper", MapperOutput)
    assert backend in ("droid", "anthropic")
    assert any(f.kind == "covenant_tag" for f in out.flags)
    assert not any(t.policy_id for t in out.tags) and not any(m.policy_id for m in out.mappings)


def test_the_replay_backend_stops_on_the_covenant_flag_and_ends_at_0_76x():
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    advance(gw, DEAL_ID, backend="replay")
    flags = gw.open_flags(DEAL_ID)
    fin = next(f for f in flags if f.payload.get("kind") == "covenant_tag")
    effects = [o.effect for o in fin.options]
    assert any("Over the limit" in e for e in effects) and any(e.startswith("As filed") for e in effects)
    for flag in flags:
        gw.answer(CONTROLLER, flag.id, flag.default or flag.options[0].id)
    advance(gw, DEAL_ID, backend="replay")
    result = store.latest_result(DEAL_ID)
    assert round(result.leverage, 2) == 0.76 and result.review.verdict == "pass"


def full_run(c):
    c.post(f"/deals/{DEAL_ID}/run")
    body = c.get(f"/deals/{DEAL_ID}/case").json()
    for fid in body["open_flags"]:
        flag = next(f for f in body["flags"] if f["id"] == fid)
        c.post(f"/work-items/{fid}/answer?auto_advance=false", json={"option_id": flag["default"]})
    c.post(f"/deals/{DEAL_ID}/run")
    return c.get(f"/deals/{DEAL_ID}/case").json()


def test_a_reset_that_clears_memory_brings_the_flag_back():
    c = TestClient(create_app())
    full_run(c)
    assert c.post("/dev/reset").json()["policies"] > 0  # the default keeps memory: the second-run moment
    assert c.post("/dev/reset?keep_memory=false").json() == {"ok": True, "keep_memory": False, "policies": 0,
                                                             "sessions": 0, "kept_deals": []}
    c.post(f"/deals/{DEAL_ID}/run")
    assert c.get(f"/deals/{DEAL_ID}/case").json()["open_flags"]


def test_reset_is_refused_while_a_run_is_in_flight():
    app = create_app()
    c = TestClient(app)
    gateway = app.state.gateway
    gateway.running.add(DEAL_ID)
    r = c.post("/dev/reset?keep_memory=false")
    assert r.status_code == 409 and "in progress" in r.json()["detail"]
    gateway.running.discard(DEAL_ID)
    assert c.post("/dev/reset?keep_memory=false").status_code == 200


def test_reset_frees_the_fork_slot():
    from app.gateway.whatif import WhatIfForks

    class Client:
        deleted: list[str] = []

        def delete(self, service_id):
            self.deleted.append(service_id)

    store = MemoryStore()
    gw = Gateway(store)
    forks = WhatIfForks(gw, Client(), schema="s", spawn=lambda fn: fn())
    forks.active = "wi_003"
    forks._forks["wi_003"] = type("Fork", (), {"service_id": "svc1", "name": "f"})()
    forks.reset()
    assert forks.active is None and Client.deleted == ["svc1"]
