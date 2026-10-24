# Gateway and API

The gateway is the only writer.
The console, the job runner, and the agents all call it.
This file describes the code in `backend/app/gateway/gateway.py` and `backend/app/api/routes.py` as of 2026-10-24.
Shapes are the Pydantic models in `backend/app/core/models.py`.

## Actors

Every request carries an actor in the form `kind:name`, in the `X-Actor` header.
The default is `human:controller`.
A real deployment would use signed tokens.

| Actor | Who it is |
| --- | --- |
| `agent:mapper`, `agent:preparer`, `agent:reviewer` | The three agents. Each has its own permission set. |
| `human:controller` | The portfolio controller. |
| `system:gateway` | The gateway itself. It posts, opens work items, and runs what-if tool calls for flag effects. |

## Permission matrix

| Action | Mapper | Preparer | Reviewer | Controller | Gateway |
| --- | --- | --- | --- | --- | --- |
| Store a mapping and flags (`propose:map_lines`) | yes | no | no | no | no |
| Store a draft result (`propose:prepare_result`) | no | yes | no | no | no |
| Store a review verdict (`propose:review_result`) | no | no | yes | no | no |
| Tools `consolidate`, `ebitda`, `covenant_debt` | no | yes | no | no | yes |
| Tool `leverage` | no | yes | yes | no | yes |
| Tools `tie_out`, `limit_test` | no | no | yes | no | yes |
| Answer a flag, hold, reject, reverse | no | no | no | yes | no |
| Approve | no | no | no | yes, not an item they prepared | no |
| Create a deal, run the job runner | no | no | no | yes | no |
| Post to the record, open work items, write the log, write policies | no | no | no | no | yes |

A forbidden action returns 403 and writes a DENIED row.

## Checks on every write

1. The actor exists and has the permission for this action.
2. The state change is legal for the work item (409 otherwise).
3. The proposer of an item cannot approve it (maker-checker). Agents cannot approve at all.
4. A result cannot be approved while the Reviewer verdict is missing or needs-attention.
5. Every number in a result carries a run id that exists for this deal, and the EBITDA, debt, and leverage values must equal the output of a tool run in the result's run ids (422 otherwise). A model cannot slip in a number. The named run ids (`consolidate_run_id`, `ebitda_run_id`, `debt_run_id`, `leverage_run_id`) must point at a run of that tool.
6. The limit must equal the brief's limit.
7. The payload matches its Pydantic model. The gateway re-validates every agent result.
8. `consolidate` refuses to run while a flag is open.
9. The gateway writes one audit row for each change, and the hash of each row includes the hash of the row before it.

## The agents' memory

The gateway is the only writer of agent memory too.
When the controller answers a flag, the gateway writes a `Policy` for the Mapper: the line name, the decision (a covenant tag or a platform line), who decided, and the flag it came from.
On the next run the Mapper applies the policy instead of asking, and the gateway logs `policy:apply`.
Each role has an `AgentSession` (backend, session id, turns, a short transcript).
`POST /dev/reset` keeps both unless `keep_memory=false`.

## Routes

| Method and path | Who | Purpose |
| --- | --- | --- |
| `GET /health` | any | `ok`, `chain_valid`, and the backend status (typed response) |
| `GET /deals` | any | List deals |
| `GET /deals/{id}` | any | One deal, with its brief |
| `GET /deals/{id}/case` | any | The whole screen in one read (shape below; response model `CaseResponse`, visible at `/docs`) |
| `GET /deals/{id}/source-lines?company=` | any | Statement lines, both companies or one |
| `GET /deals/{id}/mappings` | any | Mappings with confidence, reason, flagged, approved_by |
| `GET /deals/{id}/result` | any | The latest result (404 before the Preparer ran) |
| `GET /deals/{id}/work-items?state=&type=` | any | Work items |
| `GET /deals/{id}/audit` | any | Audit rows for the deal and `chain_valid` |
| `GET /deals/{id}/runs` | any | Every tool run for the deal |
| `GET /runs/{run_id}` | any | One tool run: tool, inputs, outputs |
| `GET /agents/memory` | any | Policies and sessions |
| `GET /deals/{id}/stream` | any | Server-Sent Events: audit rows as they are written, and `stage` events (shape below) |
| `POST /deals` | human | Create a deal from an upload. Multipart form with `name`, `platform`, `target`, `brief` (a JSON string of the Brief), and files `platform_csv` and `target_csv`. Returns 201 with `{"deal_id", "stage", "lines": {"platform": n, "target": n}}`. 422 names the file, row, and column. Limits: 2 MB and 2,000 rows per file. The columns are in [`data/README.md`](../../data/README.md). |
| `POST /deals/{id}/run` | human | Run the job runner until the deal waits on a human. Body `{"backend": "droid", "sync": true}` is optional. |
| `POST /work-items/{id}/answer` | human | `{"option_id": "b"}`. Posts the flag and, if no flag is open, continues the run in the background. `?auto_advance=false` turns that off. |
| `POST /work-items/{id}/approve` | human | Approve the result. The gateway posts it. |
| `POST /work-items/{id}/reject` | human | `{"reason": "..."}` |
| `POST /work-items/{id}/hold` | human | Keep a flag open and log the hold |
| `POST /work-items/{id}/reverse` | human | `{"reason": "..."}`. A new item linked to the original. Nothing is deleted. |
| `POST /tools/{name}` | agent | `{"deal_id": "...", "inputs": {}}`. Runs a math tool and returns the run. |
| `POST /dev/reset?keep_memory=true` | dev | Reseed the deal. Agent memory is kept by default. |

## The case shape

`GET /deals/{id}/case` returns everything the one screen needs.

```json
{
  "deal": { "id": "d_kequ_nuaire", "name": "Kewaunee Scientific acquires Nu Aire", "platform": "Kewaunee", "target": "Nu Aire", "stage": "awaiting_flag", "brief": { "limit": 2.5, "debt_term": "Senior Funded Bank Debt", "...": "..." } },
  "stage": "awaiting_flag",
  "source_lines": [ { "id": "sl_001", "company": "Kewaunee", "line": "Cash and cash equivalents", "section": "balance_sheet", "period": "2024-10-31", "amount": 25963, "unit": "USD thousands", "source_ref": "10-Q ...", "is_total": false, "note": null, "covenant_tag": "na", "covenant_note": null } ],
  "mappings": [ { "id": "m_001", "target_line": "Net Revenues", "platform_line": "Net sales", "confidence": 0.95, "reason": "...", "flagged": false, "approved_by": null } ],
  "flags": [ { "id": "wi_002", "type": "flag", "state": "NEEDS_INFO", "question": "...", "evidence": [ { "quote": "...", "document_id": "8-K Ex 10.1, Section 4.8(a)" } ], "options": [ { "id": "a", "label": "Whole line counts (70,885K)", "effect": "Senior Funded Bank Debt 71,955K. Leverage 2.62x against 2.50x. Over the limit.", "run_id": "run_004" } ], "default": "b", "answer": null } ],
  "open_flags": ["wi_002", "wi_003"],
  "result": null,
  "verdict": null,
  "work_items": [ "..." ],
  "policies": [ "..." ],
  "sessions": [ "..." ],
  "audit": { "rows": 12, "chain_valid": true, "denied": 0 },
  "backend": { "configured": "scripted", "fallback": "anthropic,scripted", "anthropic_key": false, "factory_key": true, "last_runs": [ "..." ] }
}
```

After the Preparer and the Reviewer run, `verdict` is filled:

```json
{
  "leverage": 0.786, "limit": 2.5, "verdict": "ok", "headroom_turns": 1.714,
  "ebitda": 27518.845, "debt": 21633.0, "debt_term": "Senior Funded Bank Debt",
  "review": { "verdict": "pass", "reasons": [], "run_ids": ["run_017", "run_018"] },
  "tie_out_ok": true, "backend": "scripted",
  "debt_capacity": 47164.113, "debt_capacity_run_id": "run_018",
  "approval_item": "wi_006", "approval_state": "PROPOSED", "posted": false
}
```

`debt_capacity` (a float, or null before the Reviewer runs) is the room for the next deal in USD thousands, and `debt_capacity_run_id` is the Reviewer's `limit_test` run (or null).
`result.run_ids_by_tool` maps `consolidate`, `ebitda`, `covenant_debt`, and `leverage` to their run ids, so the console can link each figure to `GET /runs/{run_id}`.
`source_lines[].note` is what the filing says about a line (for example the 10-Q note that the financing liability is the Statesville sale-leaseback). Show it on the flag card's evidence.
A mapping flag may cover several target lines; its options then carry `mappings` (target line id to platform line) in `payload.option_actions`, and the option `effect` text lists each line.
`GET /health` returns `backend.settings` with the configured backend, the fallback chain, and the model per role on each backend.

`result.rows` is the combined table: `line`, `section`, `platform`, `target`, `combined`, `run_id`, in platform order and in USD thousands.
The three closing financing lines (term loan, revolver, seller notes) carry `period` "2024-11-01 (closing)".

## The stream

`GET /deals/{id}/stream` sends two kinds of event.
Audit events are unchanged.
A `stage` event is sent once on connect and again whenever the stage changes:

```
event: stage
data: {"deal_id": "d_kequ_nuaire", "stage": "awaiting_flag", "open_flags": ["wi_002"], "at": "<iso timestamp>"}
```

A `: keepalive` comment is sent every 15 seconds.

## Stages

`new` (loaded), `awaiting_flag`, `flags_answered`, `mapped`, `awaiting_review`, `needs_attention`, `awaiting_approval`, `posted`.

## Errors

- 403: the actor may not do this. The gateway also writes a DENIED row.
- 404: the deal, item, or run does not exist.
- 409: the state change is not legal.
- 422: the payload is not valid, such as a number with no run id, or a tool called while a flag is open.

## run_agent(role, item)

One function runs every agent (`backend/app/agents/runner.py`).

| Backend | `AGENT_BACKEND` | Use |
| --- | --- | --- |
| Anthropic API with tool use and a `submit` tool typed as the output model | `anthropic` | The real model path and the stage fallback |
| Factory Droid Python SDK, `run(prompt, output=Model, config=SessionConfig(mcp_servers, restrict_tools))` in an empty temp directory | `droid` | The agents we show as built with Droid |
| Deterministic rules, no model | `scripted` | Last fallback and reference answer |
| Recorded outputs from `backend/recordings/` (the Preparer and Reviewer re-run their tools) | `replay` | No-network fallback |

The runner tries `AGENT_BACKEND`, then each backend in `AGENT_FALLBACK` (default `anthropic,scripted`), and reports which one produced the result.
`result.backend` and `GET /health` show it.
Say "built with the Factory Droid SDK" only about runs that went through `droid`.
