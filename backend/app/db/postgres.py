"""Postgres store on Tiger Cloud (TimescaleDB). The memory store stays the working set; this writes it through.

The gateway is the only writer and calls `commit()` after each write it makes. A commit compares the records
with what was last written and queues the changes: upserts of changed records, the new audit rows, and the id
counters. One writer thread applies each batch in its own transaction, in order, and retries until the
database takes it, so a slow or dropped connection never blocks a request. Reads never touch the database.

On start the store loads the current ledger back: the record, the audit log, the id counters, and the agent
memory (policies and sessions). The hash chain is checked again after a load (`Gateway.verify_chain`).

The audit log is a TimescaleDB hypertable on `at`, and a trigger refuses UPDATE and DELETE on it.
A demo reset starts a new ledger instead of deleting anything, so earlier ledgers stay in the database.
Agent memory belongs to no ledger (ledger 0) and survives a reset unless `keep_memory=false`.
"""
from __future__ import annotations

import logging
import queue
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel

from app.core.models import AgentSession, AuditRow, Deal, Mapping, Policy, Result, SourceLine, ToolRun, WorkItem, now
from app.db.memory import MemoryStore

log = logging.getLogger("stochastic.store")

MEMORY_LEDGER = 0

# kind in the database -> (collection on the store, model, survives a reset)
KINDS: dict[str, tuple[str, type[BaseModel], bool]] = {
    "deal": ("deals", Deal, False),
    "source_line": ("source_lines", SourceLine, False),
    "mapping": ("mappings", Mapping, False),
    "work_item": ("items", WorkItem, False),
    "result": ("results", Result, False),
    "tool_run": ("tool_runs", ToolRun, False),
    "policy": ("policies", Policy, True),
    "session": ("sessions", AgentSession, True),
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ledger (
    id integer PRIMARY KEY,
    started_at timestamptz NOT NULL DEFAULT now(),
    reason text NOT NULL
);
CREATE TABLE IF NOT EXISTS record (
    ledger integer NOT NULL,
    kind text NOT NULL,
    id text NOT NULL,
    deal_id text,
    pos integer NOT NULL,
    body jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (ledger, kind, id)
);
CREATE TABLE IF NOT EXISTS id_counter (
    ledger integer NOT NULL,
    prefix text NOT NULL,
    value integer NOT NULL,
    PRIMARY KEY (ledger, prefix)
);
CREATE TABLE IF NOT EXISTS audit_log (
    ledger integer NOT NULL,
    id integer NOT NULL,
    at timestamptz NOT NULL,
    deal_id text NOT NULL,
    actor text NOT NULL,
    action text NOT NULL,
    target text,
    result text NOT NULL,
    reason text,
    evidence jsonb NOT NULL,
    prev_hash text NOT NULL,
    hash text NOT NULL,
    PRIMARY KEY (ledger, id, at)
);
SELECT create_hypertable('audit_log', by_range('at', INTERVAL '1 day'), if_not_exists => TRUE);
CREATE OR REPLACE FUNCTION audit_log_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append only';
END $$;
CREATE OR REPLACE TRIGGER audit_log_append_only BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_append_only();
CREATE OR REPLACE VIEW current_work_items AS
    SELECT r.id, r.deal_id, r.body->>'type' AS type, r.body->>'state' AS state,
           r.body->>'proposed_by' AS proposed_by, r.updated_at
    FROM record r WHERE r.kind = 'work_item' AND r.ledger = (SELECT max(id) FROM ledger)
    ORDER BY r.pos;
CREATE OR REPLACE VIEW current_audit_log AS
    SELECT * FROM audit_log WHERE ledger = (SELECT max(id) FROM ledger) ORDER BY id;
"""

UPSERT = """
INSERT INTO record (ledger, kind, id, deal_id, pos, body) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
ON CONFLICT (ledger, kind, id) DO UPDATE SET body = EXCLUDED.body, deal_id = EXCLUDED.deal_id, updated_at = now()
"""
INSERT_AUDIT = """
INSERT INTO audit_log (ledger, id, at, deal_id, actor, action, target, result, reason, evidence, prev_hash, hash)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
"""
UPSERT_COUNTER = """
INSERT INTO id_counter (ledger, prefix, value) VALUES (%s, %s, %s)
ON CONFLICT (ledger, prefix) DO UPDATE SET value = EXCLUDED.value
"""


class SchemaInUse(RuntimeError):
    pass


@dataclass
class Batch:
    new_ledger: tuple[int, str] | None = None
    deletes: list[tuple] = field(default_factory=list)
    upserts: list[tuple] = field(default_factory=list)
    audit: list[tuple] = field(default_factory=list)
    counters: list[tuple] = field(default_factory=list)

    def empty(self) -> bool:
        return not (self.new_ledger or self.deletes or self.upserts or self.audit or self.counters)


class PostgresStore(MemoryStore):
    kind = "postgres"

    def __init__(self, dsn: str, schema: str = "stochastic", connect_timeout: int = 10) -> None:
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", schema):
            raise ValueError(f"schema name {schema!r} must be lower case letters, digits, and underscores")
        super().__init__()
        self.schema = schema
        self._dsn, self._timeout = dsn, connect_timeout
        self._lock = threading.RLock()
        self._written: dict[tuple[int, str, str], str] = {}  # (ledger, kind, id) -> body last queued
        self._pos: dict[tuple[int, str], int] = {}
        self._audit_written = 0
        self._seq_written: dict[str, int] = {}
        self._new_ledger: tuple[int, str] | None = None
        self._queue: queue.Queue[Batch | None] = queue.Queue()
        self._info: dict[str, Any] = {"written_batches": 0, "last_error": None, "last_write_at": None}
        self._conn = self._connect()
        self._migrate()
        self.ledger = self._load()
        self._writer = threading.Thread(target=self._drain, name="stochastic-pg-writer", daemon=True)
        self._writer.start()

    # ------------------------------------------------------------------ connection and schema
    def _connect(self) -> psycopg.Connection:
        """Connect and take the schema's advisory lock, so only one API process writes a schema at a time."""
        conn = psycopg.connect(self._dsn, connect_timeout=self._timeout, autocommit=True,
                               options=f"-c search_path={self.schema},public -c TimeZone=UTC")
        if not conn.execute("SELECT pg_try_advisory_lock(hashtext(%s))", (f"stochastic:{self.schema}",)).fetchone()[0]:
            conn.close()
            raise SchemaInUse(f"another API process is writing schema {self.schema!r}; set DB_SCHEMA to your own")
        return conn

    def _migrate(self) -> None:
        with self._conn.transaction():
            self._conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
            self._conn.execute(SCHEMA_SQL)

    def _load(self) -> int:
        """Load the latest ledger and the agent memory into the working set. Returns the ledger id."""
        with self._conn.transaction():
            ledger = self._conn.execute("SELECT coalesce(max(id), 0) FROM ledger").fetchone()[0]
            if ledger == 0:
                self._conn.execute("INSERT INTO ledger (id, reason) VALUES (1, 'first start')")
                return 1
            rows = self._conn.execute(
                "SELECT ledger, kind, id, pos, body FROM record WHERE ledger IN (%s, %s) ORDER BY kind, pos",
                (ledger, MEMORY_LEDGER)).fetchall()
            for led, kind, id_, pos, body in rows:
                attr, model, _ = KINDS[kind]
                obj = model.model_validate(body)
                getattr(self, attr)[id_] = obj
                self._written[(led, kind, id_)] = obj.model_dump_json()
                self._pos[(led, kind)] = max(self._pos.get((led, kind), 0), pos + 1)
            for prefix, value in self._conn.execute(
                    "SELECT prefix, value FROM id_counter WHERE ledger = %s", (ledger,)).fetchall():
                self._seq[prefix] = self._seq_written[prefix] = value
            cols = "id, at, deal_id, actor, action, target, result, reason, evidence, prev_hash, hash"
            with self._conn.cursor(row_factory=dict_row) as cur:
                cur.execute(f"SELECT {cols} FROM audit_log WHERE ledger = %s ORDER BY id", (ledger,))
                self.audit = [AuditRow.model_validate(r) for r in cur.fetchall()]
            self._audit_written = len(self.audit)
        log.info("loaded ledger %s from %s: %s records, %s audit rows", ledger, self.schema, len(rows), len(self.audit))
        return ledger

    def is_empty(self) -> bool:
        return not self.deals

    # ------------------------------------------------------------------ writes
    def _ledger_of(self, kind: str) -> int:
        return MEMORY_LEDGER if KINDS[kind][2] else self.ledger

    def commit(self) -> None:
        with self._lock:
            batch = Batch(new_ledger=self._new_ledger)
            self._new_ledger = None
            live: set[tuple[int, str, str]] = set()
            for kind, (attr, _, _) in KINDS.items():
                led = self._ledger_of(kind)
                for id_, obj in list(getattr(self, attr).items()):
                    key = (led, kind, id_)
                    live.add(key)
                    body = obj.model_dump_json()
                    if self._written.get(key) == body:
                        continue
                    pos = None  # None: the row exists, so only the body changes
                    if key not in self._written:
                        pos = self._pos.get((led, kind), 0)
                        self._pos[(led, kind)] = pos + 1
                    deal_id = obj.id if kind == "deal" else getattr(obj, "deal_id", None)
                    batch.upserts.append((led, kind, id_, deal_id, pos, body))
                    self._written[key] = body
            for key in [k for k in self._written if k not in live]:
                batch.deletes.append(key)
                del self._written[key]
            for row in self.audit[self._audit_written:]:
                batch.audit.append((self.ledger, row.id, row.at, row.deal_id, row.actor, row.action, row.target,
                                    row.result, row.reason,
                                    "[" + ",".join(e.model_dump_json() for e in row.evidence) + "]",
                                    row.prev_hash, row.hash))
            self._audit_written = len(self.audit)
            for prefix, value in self._seq.items():
                if self._seq_written.get(prefix) != value:
                    batch.counters.append((self.ledger, prefix, value))
                    self._seq_written[prefix] = value
            if not batch.empty():
                self._queue.put(batch)

    def reset_deals(self, keep_memory: bool = True) -> None:
        """Start a new ledger. The old ledger and its audit log stay in the database."""
        with self._lock:
            self.commit()
            super().reset_deals(keep_memory=keep_memory)
            self.ledger += 1
            self._new_ledger = (self.ledger, "reset, agent memory kept" if keep_memory else "reset, agent memory cleared")
            self._written = {k: v for k, v in self._written.items() if k[0] == MEMORY_LEDGER}
            self._pos = {k: v for k, v in self._pos.items() if k[0] == MEMORY_LEDGER}
            self._audit_written = 0
            self._seq_written = {}
            self.commit()

    # ------------------------------------------------------------------ the writer thread
    def _apply(self, batches: list[Batch]) -> None:
        """Everything queued goes in one pipelined transaction, in order, so the writer keeps up over a slow link."""
        with self._conn.pipeline(), self._conn.transaction(), self._conn.cursor() as cur:
            for batch in batches:
                self._apply_one(cur, batch)

    @staticmethod
    def _apply_one(cur: psycopg.Cursor, batch: Batch) -> None:
        if batch.new_ledger:
            cur.execute("INSERT INTO ledger (id, reason) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                        batch.new_ledger)
        if batch.deletes:
            cur.executemany("DELETE FROM record WHERE ledger = %s AND kind = %s AND id = %s", batch.deletes)
        if batch.upserts:
            new = [u for u in batch.upserts if u[4] is not None]
            changed = [u for u in batch.upserts if u[4] is None]
            if new:
                cur.executemany(UPSERT, new)
            if changed:
                cur.executemany("UPDATE record SET body = %s::jsonb, deal_id = %s, updated_at = now() "
                                "WHERE ledger = %s AND kind = %s AND id = %s",
                                [(u[5], u[3], u[0], u[1], u[2]) for u in changed])
        if batch.audit:
            cur.executemany(INSERT_AUDIT, batch.audit)
        if batch.counters:
            cur.executemany(UPSERT_COUNTER, batch.counters)

    def _drain(self) -> None:
        while True:
            batches = [self._queue.get()]
            while True:
                try:
                    batches.append(self._queue.get_nowait())
                except queue.Empty:
                    break
            stop = batches[-1] is None
            batches = [b for b in batches if b is not None]
            delay = 0.5
            while batches:
                try:
                    if self._conn.closed:
                        self._conn = self._connect()
                    self._apply(batches)
                    self._info.update(written_batches=self._info["written_batches"] + len(batches),
                                      last_write_at=now().isoformat(), last_error=None)
                    break
                except (psycopg.Error, SchemaInUse) as error:
                    self._info["last_error"] = f"{type(error).__name__}: {error}".strip()
                    log.warning("store write failed, retrying in %.1fs: %s", delay, error)
                    try:
                        self._conn.close()
                    except psycopg.Error:
                        pass
                    time.sleep(delay)
                    delay = min(delay * 2, 10.0)
            for _ in range(len(batches) + stop):
                self._queue.task_done()
            if stop:
                return

    def flush(self, timeout: float = 30.0) -> bool:
        """Wait until every queued batch is in the database. True when the queue drained in time."""
        deadline = time.monotonic() + timeout
        while self._queue.unfinished_tasks:
            if time.monotonic() > deadline:
                return False
            time.sleep(0.02)
        return True

    def close(self) -> None:
        self.flush()
        self._queue.put(None)
        self._writer.join(timeout=5)
        self._conn.close()

    def status(self) -> dict:
        host = re.sub(r"^.*@", "", self._dsn).split("/")[0].split(":")[0]  # never the password
        return {"kind": self.kind, "host": host, "schema": self.schema, "ledger": self.ledger,
                "pending": self._queue.unfinished_tasks, **self._info}
