# db

`memory.py` is the in-memory store.
It is the working set for every read.
`postgres.py` writes it through to Postgres on Tiger Cloud (TimescaleDB) when `STORE=postgres`, and loads it back on start.

How the Postgres store works:
- The gateway is the only writer.
  Every public gateway write holds the gateway lock and calls `store.commit()` on the way out, also when it is denied.
- A commit queues what changed since the last one: changed records, new audit rows, and the id counters.
  One write never splits across transactions.
- One writer thread applies the queue in order, in one pipelined transaction, and retries until the database takes it.
  A whole deal reaches Tiger in about a second, and a request never waits for the network. [verified: 0.04s request path, 1.0s to flush a full deal from San Francisco to us-east-1]
- The write is behind the request, so a crash can lose the last second of queued writes, but never part of one write.
- The audit log is a TimescaleDB hypertable on `at`, and a trigger refuses UPDATE and DELETE on it.
- A reset (`POST /dev/reset`) starts a new ledger instead of deleting.
  Earlier ledgers and their logs stay.
  Agent memory (policies, sessions) sits in ledger 0 and survives a reset unless `keep_memory=false`.
- Each schema has an advisory lock, so a second API process on the same schema starts in memory instead of overwriting the first.
  Use `DB_SCHEMA` for your own copy.
- If Tiger Cloud cannot be reached at start, the API runs in memory and `/health` gives the reason.

Tables (schema `stochastic` by default): `ledger`, `record` (one JSONB body per Pydantic model, by ledger, kind, and id), `id_counter`, `audit_log` (hypertable), and the views `current_work_items` and `current_audit_log`.
Tests: `TEST_DATABASE_URL=<url> .venv/bin/python -m pytest -q tests/test_postgres_store.py` works in a throwaway schema and drops it.
`loader.py` parses and checks the `POST /deals` uploads, and `forks.py` makes the Tiger Cloud forks that hold a covenant flag's what-ifs.
`fixtures/kewaunee.py` loads the demo deal from the public filings: Kewaunee's 10-Q and 10-K lines, Nu Aire's audited lines, the closing financing from the pro forma, and the brief from the PNC loan agreement.
`fixtures/cases.py` seeds the four other Dashboard cases (DLH and GRSi, Mama's Creations and Crown I, Shutterstock and Envato, and the DLH and Craig's sample) after startup, and rebuilds a seeded case when its fixtures change (`seed_version`).
Agent memory (`policies`, `sessions`) survives `POST /dev/reset` unless `keep_memory=false`.
The table design is in `docs/architecture/data-model.md`.
