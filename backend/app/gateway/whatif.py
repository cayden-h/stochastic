"""What-ifs in a Tiger fork. Owner: Cayden.

When the Mapper raises a covenant flag, the gateway forks the ledger on Tiger Cloud and writes every option's
what-if (its tags and its computed debt, EBITDA, leverage, and verdict, each with its tool run id) into the fork,
never into the live record. When the controller answers, the live record keeps the chosen option, and the fork
with the alternatives is deleted, which also frees the free plan's one fork slot.

The fork is extra, never in the way: the flag's options and effects are computed in process as before, a fork
that is slow (about 35 s) or fails only changes the fork state on the flag, and the controller can answer at any
time. Every step is a gateway write, so it is in the audit log and in the hash chain.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Callable

from app.core.models import WorkItem
from app.db.forks import FORK_PREFIX, Fork, ForkClient, ForkError

WHAT_IF_SQL = """
CREATE TABLE IF NOT EXISTS {schema}.what_if (
    flag_id text NOT NULL,
    option_id text NOT NULL,
    label text NOT NULL,
    tags jsonb NOT NULL,
    effect text NOT NULL,
    run_id text,
    outputs jsonb NOT NULL,
    written_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (flag_id, option_id)
)
"""


def write_to_fork(fork: Fork, schema: str, flag_id: str, rows: list[dict]) -> None:
    import psycopg

    with psycopg.connect(fork.dsn, connect_timeout=20, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(WHAT_IF_SQL.format(schema=schema))
        cur.executemany(
            f"INSERT INTO {schema}.what_if (flag_id, option_id, label, tags, effect, run_id, outputs) "
            "VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s::jsonb) ON CONFLICT (flag_id, option_id) DO NOTHING",
            [(flag_id, r["option_id"], r["label"], json.dumps(r["tags"]), r["effect"], r["run_id"],
              json.dumps(r["outputs"])) for r in rows])


def _background(fn: Callable[[], None]) -> None:
    threading.Thread(target=fn, name="stochastic-fork", daemon=True).start()


class WhatIfForks:
    def __init__(self, gw, client: ForkClient, schema: str, spawn: Callable[[Callable[[], None]], None] = _background,
                 writer: Callable[[Fork, str, str, list[dict]], None] = write_to_fork) -> None:
        self.gw, self.client, self.schema = gw, client, schema
        self.spawn, self.writer = spawn, writer
        self._lock = threading.Lock()
        self.active: str | None = None  # the flag that holds the one fork slot
        self._forks: dict[str, Fork] = {}  # flag id -> its fork, once ready
        self._answered: set[str] = set()  # flags answered before their fork was ready
        self.cleanup: dict = {}

    def status(self) -> dict:
        return {"enabled": True, "active_flag": self.active, **({"cleanup": self.cleanup} if self.cleanup else {})}

    def reset(self) -> None:
        """Free the fork slot on /dev/reset. A flag left open by the last judge would otherwise hold it, and every
        later flag would show "one fork at a time" until the API restarted. Ready forks are deleted in the
        background; one still being created is deleted by clean_leftovers on the next start."""
        with self._lock:
            forks = list(self._forks.values())
            self.active = None
            self._forks.clear()
            self._answered.clear()
        for fork in forks:
            self.spawn(lambda f=fork: self._delete_quietly(f))

    def clean_leftovers(self) -> None:
        """Delete forks a crashed process left behind, so the slot is free. Runs in the background at start."""
        def work():
            try:
                found = self.client.leftovers()
                for service_id, _ in found:
                    self.client.delete(service_id)
                self.cleanup = {"deleted": [name for _, name in found]}
            except ForkError as error:
                self.cleanup = {"error": str(error)}
        self.spawn(work)

    # ------------------------------------------------------------------ called by the gateway, under its lock
    def flag_opened(self, item: WorkItem) -> None:
        if item.payload.get("kind") != "covenant_tag":
            return
        with self._lock:
            busy = self.active
            if busy is None:
                self.active = item.id
        if busy:
            self.gw.note_fork(item.id, {"state": "skipped", "reason": f"one fork at a time; flag {busy} holds it"},
                              "fork:skip", f"The free plan allows one fork beside the ledger; flag {busy} holds it")
            return
        self.gw.note_fork(item.id, {"state": "creating", "started": time.time()}, "fork:create",
                          "Forking the ledger on Tiger Cloud to hold this flag's what-ifs")
        self.spawn(lambda: self._create(item.id))

    def flag_answered(self, item: WorkItem) -> None:
        with self._lock:
            if item.id != self.active:
                return
            fork = self._forks.get(item.id)
            if fork is None:  # still creating: discard as soon as it is ready
                self._answered.add(item.id)
                return
        self.spawn(lambda: self._discard(item.id, fork))

    # ------------------------------------------------------------------ background
    def _rows(self, flag_id: str) -> list[dict]:
        item = self.gw.store.items[flag_id]
        actions = item.payload.get("option_actions", {})
        rows = []
        for o in item.options:
            run = self.gw.store.tool_runs.get(o.run_id) if o.run_id else None
            rows.append({"option_id": o.id, "label": o.label, "tags": actions.get(o.id, {}).get("tags", {}),
                         "effect": o.effect, "run_id": o.run_id, "outputs": run.outputs if run else {}})
        return rows

    def _create(self, flag_id: str) -> None:
        started = time.time()
        flush = getattr(self.gw.store, "flush", None)
        if flush:
            flush()  # the fork must already hold this flag: wait for the write-through
        name = f"{FORK_PREFIX}{flag_id}-{int(started)}"
        try:
            fork = self.client.create(name)
        except ForkError as error:
            self._release(flag_id)
            self.gw.note_fork(flag_id, {"state": "failed", "reason": str(error)}, "fork:failed", str(error))
            return
        try:
            rows = self._rows(flag_id)
            self.writer(fork, self.schema, flag_id, rows)
        except Exception as error:  # noqa: BLE001 - a failed write must still free the slot
            self._delete_quietly(fork)
            self._release(flag_id)
            self.gw.note_fork(flag_id, {"state": "failed", "reason": f"writing what-ifs: {type(error).__name__}"},
                              "fork:failed", f"Writing the what-ifs failed ({type(error).__name__}); fork deleted")
            return
        seconds = round(time.time() - started, 1)
        self.gw.note_fork(flag_id, {"state": "ready", "service_id": fork.service_id, "name": fork.name,
                                    "seconds": seconds, "options": len(rows)}, "fork:ready",
                          f"Fork {fork.service_id} holds {len(rows)} what-ifs; ready in {seconds} s")
        with self._lock:
            self._forks[flag_id] = fork
            answered = flag_id in self._answered
        if answered:
            self._discard(flag_id, fork)

    def _discard(self, flag_id: str, fork: Fork) -> None:
        item = self.gw.store.items[flag_id]
        kept = item.answer
        others = [o.id for o in item.options if o.id != kept]
        try:
            self.client.delete(fork.service_id)
            state, reason = "discarded", (f"Kept option {kept} in the ledger; deleted fork {fork.service_id} "
                                          f"with {len(others)} alternatives")
        except ForkError as error:
            state, reason = "delete_failed", f"Fork {fork.service_id} not deleted: {error}"
        self._release(flag_id)
        self.gw.note_fork(flag_id, {**item.payload.get("fork", {}), "state": state, "kept": kept,
                                    "discarded": others}, "fork:delete", reason)

    def _delete_quietly(self, fork: Fork) -> None:
        try:
            self.client.delete(fork.service_id)
        except ForkError:
            pass

    def _release(self, flag_id: str) -> None:
        with self._lock:
            if self.active == flag_id:
                self.active = None
            self._forks.pop(flag_id, None)
            self._answered.discard(flag_id)
