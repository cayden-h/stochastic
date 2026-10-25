# Architecture

Status: describes the code on `main` as of 2026-10-25.
The product reference is `../STOCHASTIC.md`.
If this folder and that file disagree, that file is correct.

## Goals

- Keep the system small enough to build in one weekend.
- Make the trust rules true in code: code does the math, only the gateway writes, unsure means ask.
- Run one deal end to end (Kewaunee buys Nu Aire) before adding anything else.
- Agents are stateful.
  What the controller teaches them is kept and applied next time.

## Parts

| Part | Tech | Job |
| --- | --- | --- |
| People and files | Two statement files and the credit agreement (or a Brief as JSON), loaded by `backend/app/db/fixtures/kewaunee.py` or uploaded with `POST /deals` | The input. The demo deal starts from the agreement extract `data/brief/kewaunee_ex101_extract.txt`, and the Brief Reader turns it into the Brief: the lender's limit and definitions. |
| Console | Next.js, React, TypeScript, Tailwind, also packaged as a Mac app with Electron (`desktop/`) | Six pages in a sidebar: Dashboard, Case, Mapping, Agents, Log, Review. The Case is read-only (the Brief, the flags, the pipeline, the figures); edits, approval, and the final files are on Review. |
| Gateway API | Python, FastAPI | The only writer. Checks the actor, the permission, the state change, maker-checker, and the run ids. Writes the audit log and the agents' memory. |
| Agents | Python, `run_agent(role, item)` | Three stateful agents: Mapper, Preparer, Reviewer. A fourth, the Brief Reader, drafts the Brief from the agreement (D20, `brief-reader.md`), and a code verifier checks it field by field (D23). Four backends: anthropic, droid, scripted, replay. |
| Job runner | Python, plain code | Moves work items from one agent to the next. It is not a model. |
| Code tools | Python, `backend/app/tools/finance.py`, `backend/app/tools/edits.py` | All the math: consolidation, tie-out, EBITDA, covenant debt, leverage, limit test, and the controller's edits applied to the tool inputs. No write access. |
| Store | In memory, written through to Postgres on Tiger Cloud with `STORE=postgres` | Holds the record, the work items, the tool runs, the audit log, the policies, and the sessions. The audit log is an append-only TimescaleDB hypertable, and a restart loads everything back (`backend/app/db/postgres.py`). |

## System diagram

```mermaid
flowchart LR
    FILES["Two statement files and the agreement or a Brief"]
    UI["Console (Next.js)"]
    API["Gateway API (FastAPI)"]
    STORE[("Store: record, log, tool runs, policies, sessions")]
    RUN["Job runner (code)"]
    AG["Agents: Brief Reader, Mapper, Preparer, Reviewer (stateful)"]
    TL["Code tools (math)"]
    LLM["Backend: Anthropic API, Droid SDK, scripted, replay"]

    FILES --> API
    UI -- "REST and SSE" --> API
    API <--> STORE
    RUN -- "open items, store results" --> API
    RUN -- "run_agent(role, item)" --> AG
    AG -- "call tools" --> API
    API --> TL
    AG --> LLM
```

## Request flow

1. The fixture loads the platform lines, the target lines, and the agreement extract.
   The gateway creates the deal.
2. `POST /deals/{id}/run`.
   The runner opens `draft_brief`, and the Brief Reader drafts the Brief with a quote for every field.
   The verifier (code) checks each field against the agreement, 22 checks on the demo deal.
   The controller approves the Brief, and the run continues.
3. The runner opens `map_lines`.
   The Mapper (with its policies) returns mappings, tags, and flag proposals.
4. The gateway stores the mappings and tags, and opens a flag per proposal.
   For each option it runs the tools as a what-if and writes the effect on the option.
5. The console shows the flag card.
   The controller answers.
   The gateway applies the tags or the mapping, writes a policy, and posts the flag.
   The run continues.
6. The Preparer calls `consolidate`, `ebitda`, `covenant_debt`, and `leverage` through the gateway and returns the draft with the run ids.
7. The Reviewer calls `tie_out` and `limit_test` and returns pass or needs-attention.
   The gateway opens `approve_result`.
8. On the Review page the controller can edit an amount or remap a line, with a reason, and code recomputes every total.
   The controller approves.
   The gateway posts and the deal stage is `posted`.
9. Run again after a reset: the Mapper applies the policies and asks nothing.

## Documents in this folder

| File | What it holds |
| --- | --- |
| `agents-and-work-items.md` | Work-item types, states, the three agent contracts, the job runner, memory, the two human moments |
| `gateway-and-api.md` | Actors, permissions, checks, routes, the case shape, `run_agent` |
| `data-model.md` | The tables, the audit chain, how a number traces to its source lines |
| `repo-structure.md` | The folder map and the conventions for code |
| `brief-reader.md` | The fourth agent: reading the credit agreement into the Brief, the gateway's quote checks, the verifier, Brief approval, stages (D20, D23) |
