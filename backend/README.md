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

## Status

Surface-level prototype. The gateway enforces the trust rules and writes a hash-chained audit log. The store is in memory and seeded with illustrative data.
The real agents come next. Postgres is optional.
