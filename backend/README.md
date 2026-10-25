# backend

Python and FastAPI.
It holds the gateway, the agents, the code tools, and the data layer.
The design is in `docs/architecture/`.
It runs the whole add-on integration workflow: the Brief Reader and the Brief verifier, the Mapper, the Preparer, and the Reviewer, through the gateway, with the controller's two touchpoints.

## Folders

| Folder | What it holds |
| --- | --- |
| `app/api/` | HTTP routes. They are thin and call the gateway. |
| `app/gateway/` | Actor and permission checks, the work-item state machine, and the audit log. The only writer. |
| `app/agents/` | The four roles (Brief Reader, Mapper, Preparer, Reviewer), their backends, the job runner, the demo paces, and the replay of recorded runs. |
| `app/tools/` | Consolidation, the tie-out, EBITDA, covenant debt, leverage, and the limit test, plus the controller's edits. No side effects. |
| `app/db/` | The in-memory store, the Postgres store, the upload loader, Tiger forks, and the fixtures (the demo deal and the seeded cases). |
| `app/core/` | Settings, the shared types, the agreement text helpers, the policy rule, and the Brief verifier. |
| `tests/` | Tests for the trust rules, the tools, the API, the agents, the demo paces, and the stores. |

## Tests

```
.venv/bin/python -m pytest -q
```

The normal run uses the memory store and never touches the network.
The Tiger tests skip unless `TEST_DATABASE_URL` is set: 435 pass offline with 18 skipped (verified on 2026-10-25, with the Brief verifier and the two touchpoints in the demo).
To run them against Tiger Cloud, use your own schema so you do not take the demo schema's advisory lock:

```
set -a; . ../.env; set +a
TEST_DATABASE_URL="$DATABASE_URL" DB_SCHEMA=stochastic_<you> .venv/bin/python -m pytest -q
```

Run this before every merge that touches the store, the gateway, or the API.
Expect 448 passed and 5 skipped (verified against Tiger Cloud on 2026-10-25, schema `stochastic_cayden_verify`, in PR #35), and about 100 seconds.

## Status

The gateway enforces the trust rules and writes a hash-chained audit log.
A run that was in progress when the API stopped is marked `run_failed` on the next start, so the Case offers Run again.
The store is in memory by default; with `STORE=postgres` it writes through to Tiger Cloud and reloads the record on start.
The writer is a background thread, so call the store's `flush()` (or wait for `/health` to show `pending: 0`) before you stop a process whose writes you want to keep.
