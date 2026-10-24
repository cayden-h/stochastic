# backend

Python and FastAPI.
It holds the gateway, the agents, the code tools, and the data layer.
The design is in `docs/architecture/`.
The current code implements an earlier workflow and is being updated per `docs/TASKS.md`.

## Folders

| Folder | What it holds |
| --- | --- |
| `app/api/` | HTTP routes. They are thin and call the gateway. |
| `app/gateway/` | Actor and permission checks, the work-item state machine, and the audit log. The only writer. |
| `app/agents/` | One module per agent: Mapper, Preparer, Reviewer. |
| `app/tools/` | Consolidation, EBITDA, leverage, and the limit test, plus helpers. No side effects. |
| `app/db/` | Repository interface, the in-memory store, the Postgres store, fixtures, and migrations. |
| `app/core/` | Settings, logging, and shared types. |
| `tests/` | Tests for the trust rules and the tools. |

## Tests

```
.venv/bin/python -m pytest -q
```

The normal run uses the memory store and never touches the network. The Tiger tests skip unless `TEST_DATABASE_URL` is set: 216 pass offline with 10 skipped.
To run them against Tiger Cloud, use your own schema so you do not take the demo schema's advisory lock:

```
set -a; . ../.env; set +a
TEST_DATABASE_URL="$DATABASE_URL" DB_SCHEMA=stochastic_<you> .venv/bin/python -m pytest -q
```

Run this before every merge that touches the store, the gateway, or the API. Expect 176 passed, 1 skipped, and about 50 seconds.

## Status

The gateway enforces the trust rules and writes a hash-chained audit log. The store is in memory by default; with `STORE=postgres` it writes through to Tiger Cloud and reloads the record on start.
The writer is a background thread, so call the store's `flush()` (or wait for `/health` to show `pending: 0`) before you stop a process whose writes you want to keep.
