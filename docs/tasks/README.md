# Task files

Each person has one task file in this folder.
The product and scope are in `../STOCHASTIC.md`.
The full split and the order of work are in `../TASKS.md`.

| Person | Task file | Branch | Folders they own |
| --- | --- | --- | --- |
| Cayden | `cayden.md` | `cayden/agents` | `backend/app/agents/`, `backend/app/gateway/`, `backend/app/core/` |
| Eric | `eric.md` | `eric/data` | `data/`, `scripts/`, `evals/` |
| Tri | `tri.md` | `tri/tools` | `backend/app/tools/`, `backend/app/api/`, `backend/app/db/`, `backend/tests/` |
| Josie | `josie.md` | `josie/design` | `frontend/`, `docs/design/` |

## Rules for working in parallel

1. Edit only the folders that you own. If you need a change in another folder, ask the owner.
2. The shared contract (source line, mapping, result) lives in `backend/app/core/models.py`. Cayden owns this file. Send change requests to Cayden.
3. Only Cayden edits `docs/STOCHASTIC.md`. Everyone edits their own task file.
4. Make small commits. Merge to `main` at least every few hours.
5. Before you merge, pull `main` into your branch and run `backend/.venv/bin/python -m pytest` in `backend/`.
6. Never put a key in git. Keep keys in `.env`.
7. Use a plain hyphen. Never use an em dash.
