"""What-ifs in a Tiger fork: the lifecycle, the one-slot limit, failures, and that the fork never blocks the flag.

A fake fork client stands in for the Tiger CLI, and background work runs on demand, so every step is checked
in order. The live check against Tiger is `test_tiger_fork_roundtrip`, which runs only with TEST_TIGER_FORKS=1.
"""
import os

import pytest

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

from app.agents.jobs import advance  # noqa: E402
from app.core.models import CONTROLLER, FlagOption, FlagProposal  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.forks import FORK_PREFIX, Fork, ForkError  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402
from app.gateway.whatif import WhatIfForks  # noqa: E402


class FakeForks:
    def __init__(self, fail_create: str | None = None):
        self.fail_create = fail_create
        self.live: dict[str, str] = {}
        self.made = 0

    def create(self, name):
        if self.fail_create:
            raise ForkError(self.fail_create)
        self.made += 1
        sid = f"fk{self.made}"
        self.live[sid] = name
        return Fork(service_id=sid, name=name, dsn="postgresql://fake")

    def delete(self, service_id):
        self.live.pop(service_id)

    def leftovers(self):
        return [(s, n) for s, n in self.live.items() if n.startswith(FORK_PREFIX)]


class Later:
    """Collects background work; `run()` does it, so a test can act while a fork is still being made."""
    def __init__(self):
        self.jobs = []

    def __call__(self, fn):
        self.jobs.append(fn)

    def run(self):
        while self.jobs:
            self.jobs.pop(0)()


def world(client, written=None):
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    later = Later()
    gw.forks = WhatIfForks(gw, client, schema="stochastic", spawn=later,
                           writer=lambda fork, schema, flag_id, rows: (written if written is not None else []).append(
                               (fork.service_id, flag_id, rows)))
    return store, gw, later


def covenant_flag(store, gw):
    return next(i for i in store.items.values() if i.type == "flag" and i.payload.get("kind") == "covenant_tag")


def actions(store):
    return [a.action for a in store.audit if a.action.startswith("fork:")]


def test_flag_whatifs_go_to_a_fork_and_the_fork_is_deleted_after_the_answer():
    client, written = FakeForks(), []
    store, gw, later = world(client, written)
    advance(gw, DEAL_ID)
    flag = covenant_flag(store, gw)
    assert flag.payload["fork"]["state"] == "creating"
    assert gw.open_flags(DEAL_ID)  # the flag is open and answerable before the fork exists

    later.run()
    assert flag.payload["fork"]["state"] == "ready" and flag.payload["fork"]["service_id"] == "fk1"
    (sid, flag_id, rows), = written
    assert (sid, flag_id) == ("fk1", flag.id)
    assert [r["option_id"] for r in rows] == [o.id for o in flag.options]
    assert all(r["outputs"].get("ok") is not None for r in rows if r["run_id"])  # limit_test outputs travel

    gw.answer(CONTROLLER, flag.id, flag.default or flag.options[0].id)
    later.run()
    fork = flag.payload["fork"]
    assert fork["state"] == "discarded" and fork["kept"] == flag.answer
    assert sorted(fork["discarded"]) == sorted(o.id for o in flag.options if o.id != flag.answer)
    assert client.live == {} and gw.forks.active is None
    assert actions(store) == ["fork:create", "fork:ready", "fork:delete"]
    assert gw.verify_chain()


def test_an_answer_before_the_fork_is_ready_deletes_it_when_it_arrives():
    client = FakeForks()
    store, gw, later = world(client)
    advance(gw, DEAL_ID)
    flag = covenant_flag(store, gw)
    gw.answer(CONTROLLER, flag.id, flag.default or flag.options[0].id)
    assert flag.payload["fork"]["state"] == "creating"
    later.run()
    assert flag.payload["fork"]["state"] == "discarded" and client.live == {}
    assert actions(store) == ["fork:create", "fork:ready", "fork:delete"]


def test_a_failed_fork_frees_the_slot_and_the_flag_still_works():
    client = FakeForks(fail_create="You have reached your free service limit.")
    store, gw, later = world(client)
    advance(gw, DEAL_ID)
    flag = covenant_flag(store, gw)
    later.run()
    assert flag.payload["fork"] == {"state": "failed", "reason": "You have reached your free service limit."}
    assert gw.forks.active is None
    gw.answer(CONTROLLER, flag.id, flag.default or flag.options[0].id)
    later.run()
    assert flag.state.value in ("POSTED", "APPROVED") and actions(store) == ["fork:create", "fork:failed"]


def test_one_fork_at_a_time():
    client = FakeForks()
    store, gw, later = world(client)
    advance(gw, DEAL_ID)
    first = covenant_flag(store, gw)
    fin = [l.id for l in store.lines(DEAL_ID, "Kewaunee") if "financing liability" in l.line.lower()]
    parent = next(i for i in store.items.values() if i.type == "map_lines")
    with gw.lock:
        second = gw._open_flag(store.deals[DEAL_ID], parent, FlagProposal(
            kind="covenant_tag", line_ids=fin, question="Again?",
            options=[FlagOption(id="x", label="x", tags={l: "debt" for l in fin})]))
    assert second.payload["fork"]["state"] == "skipped" and first.id in second.payload["fork"]["reason"]
    later.run()
    assert len(client.live) == 1


def test_mapping_flags_get_no_fork_and_leftovers_are_cleaned():
    client = FakeForks()
    client.live = {"old1": FORK_PREFIX + "wi_002-1", "keep": "stochastic"}
    store, gw, later = world(client)
    gw.forks.clean_leftovers()
    later.run()
    assert client.live == {"keep": "stochastic"} and gw.forks.cleanup == {"deleted": [FORK_PREFIX + "wi_002-1"]}
    advance(gw, DEAL_ID)
    assert all("fork" not in i.payload for i in store.items.values()
               if i.type == "flag" and i.payload.get("kind") == "mapping")


@pytest.mark.skipif(os.getenv("TEST_TIGER_FORKS") != "1" or not os.getenv("TIGER_SERVICE_ID"),
                    reason="set TEST_TIGER_FORKS=1 and TIGER_SERVICE_ID to make and delete a real fork (about 40 s)")
def test_tiger_fork_roundtrip():
    from app.db.forks import TigerCliForks

    client = TigerCliForks(os.environ["TIGER_SERVICE_ID"])
    assert not client.leftovers(), "delete leftover stochastic-whatif-* forks first"
    fork = client.create(FORK_PREFIX + "test-roundtrip")
    try:
        assert fork.dsn.startswith("postgresql://")
    finally:
        client.delete(fork.service_id)
    assert not client.leftovers()
