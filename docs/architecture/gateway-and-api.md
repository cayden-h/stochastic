# Gateway and API

The gateway is the only writer.
The console, the job runner, and the agents all call it.
Everything below is a design proposal [inferred], except where it names existing code.
The tags "existing" and "new" refer to `backend/app/api/routes.py`, `backend/app/core/models.py`, and `backend/app/gateway/gateway.py` as read on 2026-10-23.

## Actors

Every request carries an actor in the form `kind:name`.

| Actor | Example | Who it is |
| --- | --- | --- |
| Agent | `agent:mapper`, `agent:preparer`, `agent:reviewer` | An AI agent |
| Human | `human:controller` | The portfolio controller |
| System | `system:gateway` | The gateway itself |

The prototype uses the `X-Actor` header (existing, default `human:reviewer`).
A real deployment would use signed tokens.

## Permission matrix

The existing code gives agents `propose`, `ask`, and `post_plan`, humans `answer`, `approve`, `reject`, `hold`, `inject_event`, and `create_deal`, and the system `post` and `log`.
The matrix below is the new target.

| Action | Mapper | Preparer | Reviewer | Human controller | Gateway |
| --- | --- | --- | --- | --- | --- |
| Return a mapping and flags | yes | no | no | no | no |
| Return a draft result | no | yes | no | no | no |
| Return a review verdict | no | no | yes | no | no |
| Answer a flag | no | no | no | yes | no |
| Approve or reject | no | no | no | yes, not an item they prepared | no |
| Call a math tool | no | yes | yes | no | runs it |
| Post to the record | no | no | no | no | yes |
| Write the audit log | no | no | no | no | yes |

An agent can call only the tools listed for it.
If an actor tries a forbidden action, the gateway returns 403 and writes a DENIED row.

## Checks on every write

1. The actor exists and has the role for this action. (existing)
2. The state change is legal for the work item. (existing)
3. The preparer is not the approver (maker-checker). (existing: proposer cannot approve)
4. Only a human can approve, so the Reviewer agent cannot. (existing: agents lack `approve`)
5. A result cannot be approved while its review verdict is needs-attention. (new)
6. Every number in a result carries a run id that exists. (new; the old design named this check, but the code does not enforce it)
7. The payload matches its Pydantic model. (new)
8. The gateway writes one audit row for each change. (existing)

## Routes

Routes in the existing code:

| Method and path | Who | Purpose |
| --- | --- | --- |
| `GET /health` | any | Health, and whether the audit chain is valid |
| `GET /deals` | any | List deals |
| `GET /deals/{id}` | any | One deal |
| `GET /deals/{id}/work-items` | any | List work items, filter by `state` and `escalation` |
| `GET /deals/{id}/audit` | any | The audit rows and `chain_valid`, including DENIED rows |
| `POST /work-items/{id}/answer` | human | Answer a flag with `option_id` |
| `POST /work-items/{id}/hold` | human | Pause a flag |
| `POST /work-items/{id}/approve` | human | Approve an item. The gateway then posts it |
| `POST /work-items/{id}/reject` | human | Reject with a `reason` |
| `GET /deals/{id}/stream` | any | Server-Sent Events: audit rows |
| `POST /dev/reset` | dev | Reseed the in-memory store |

Existing routes tied to the earlier framing, to remove or ignore: `GET /deals/{id}/plans`, `GET /deals/{id}/facts`, `GET /deals/{id}/clauses`, and `POST /deals/{id}/events`.

New routes the console needs (the shared contract in `../TASKS.md` calls them get the case, answer the flag, approve the result):

| Method and path | Who | Purpose |
| --- | --- | --- |
| `POST /deals` | human | Create a deal from two files and a brief |
| `GET /deals/{id}/case` | any | The whole screen: source lines, mappings, open flags, result, verdict |
| `GET /deals/{id}/source-lines` | any | Source lines for both companies |
| `GET /deals/{id}/mappings` | any | Mappings with confidence and flags |
| `GET /deals/{id}/result` | any | The combined table, leverage, limit, verdict, run ids |
| `POST /work-items` | agent | Store an agent's typed result (used by the job runner) |
| `POST /tools/{name}` | agent | Run a math tool and return its run id |
| `POST /deals/{id}/run` | human or system | Start the job runner for the deal |

The answer and approve routes already exist, so the console needs no new write route for them.

## JSON shapes

Status key: existing means a type in `backend/app/core/models.py`. New means it is not there yet.

### Source line (new)

```json
{
  "id": "sl_014",
  "deal_id": "d_001",
  "company": "Nu Aire",
  "line": "Total current liabilities",
  "section": "balance_sheet",
  "period": "2024-09-30",
  "amount": 12345,
  "unit": "USD thousands",
  "source_ref": "8-K/A Ex 99.1"
}
```

The amounts above are placeholders, not filing figures.

### Mapping (new)

```json
{
  "id": "m_007",
  "deal_id": "d_001",
  "target_line": "Customer deposits",
  "platform_line": "Contract liabilities",
  "confidence": 0.62,
  "reason": "Similar meaning, but the platform has no line named deposits",
  "flagged": true,
  "approved_by": null
}
```

### Result (new)

```json
{
  "id": "r_001",
  "deal_id": "d_001",
  "rows": [
    { "line": "Revenue", "platform": 0, "target": 0, "combined": 0, "run_id": "run_021" }
  ],
  "leverage": 0.0,
  "limit": 2.5,
  "verdict": "ok",
  "review": { "verdict": "pass", "reasons": [] },
  "run_ids": ["run_021"]
}
```

Zero values are placeholders. The limit of 2.50x comes from the PNC credit agreement, Section 4.8(a). [verified: `../STOCHASTIC.md`]

### Work item (existing, extended)

The existing `WorkItem` has `id`, `deal_id`, `type`, `state`, `escalation`, `proposed_by`, `question`, `evidence`, `options`, `default`, `answer`, `reject_reason`, `payload`, and `created_at`.
New work: drop `escalation`, or keep it unused. Put the typed agent result in `payload`.

```json
{
  "id": "wi_003",
  "deal_id": "d_001",
  "type": "flag",
  "state": "NEEDS_INFO",
  "proposed_by": "agent:mapper",
  "question": "Which part of the Financing liability line is covenant debt?",
  "evidence": [{ "quote": "Financing liability", "document_id": "doc_01" }],
  "options": [
    { "id": "a", "label": "Whole line is debt", "effect": "PLACEHOLDER: leverage tool output, not computed yet" },
    { "id": "b", "label": "Only the acquisition financing is debt", "effect": "PLACEHOLDER: leverage tool output, not computed yet" }
  ],
  "default": null,
  "payload": { "mapping_id": "m_007" },
  "created_at": "2026-10-24T09:00:00Z"
}
```

The effect text is an example. The real effect is not computed yet. [verified: `../STOCHASTIC.md`, section 12]

### Audit row (existing)

The existing `AuditRow` has `id`, `at`, `deal_id`, `actor`, `action`, `target`, `result` (ALLOWED or DENIED), `reason`, `evidence`, `prev_hash`, and `hash`.

```json
{
  "id": 42,
  "at": "2026-10-24T09:00:03Z",
  "deal_id": "d_001",
  "actor": "agent:preparer",
  "action": "approve",
  "target": "wi_005",
  "result": "DENIED",
  "reason": "the proposer cannot approve its own item",
  "evidence": [],
  "prev_hash": "ab12...",
  "hash": "cd34..."
}
```

The audit log is append-only.
Each row stores the hash of the row before it, so a change in the past breaks the chain.
`GET /health` and `GET /deals/{id}/audit` report whether the chain is valid.

## run_agent(role, item)

One function runs every agent.
The backend is the only thing that changes.

```python
async def run_agent(role: Role, item: WorkItem) -> BaseModel:
    backend = BACKENDS[os.environ.get("AGENT_BACKEND", "anthropic")]
    result = await backend(role.system, item.model_dump_json(), role.tools, role.result_type)
    return role.result_type.model_validate(result)   # the gateway re-validates, then writes
```

A role is a system prompt, a tool list, and a Pydantic result type.

| Backend | `AGENT_BACKEND` | Use |
| --- | --- | --- |
| Anthropic API with `messages.parse()` and tool use | `anthropic` | The real path and the stage fallback |
| Factory Droid Python SDK with `run(prompt, output=...)` and `restrict_tools` | `droid` | The agents we show as built with Droid |

A recorded run is the last fallback. [inferred, from `../research/agent-framework-options.md`]
Say "built with the Factory Droid SDK" only about runs that went through the `droid` backend.
`.env.example` already lists `AGENT_BACKEND` and `FACTORY_API_KEY`.

## Tools exposed to agents

The math tools are plain Python functions in `backend/app/tools/`.
Agents reach them in one of two ways, and both end in a gateway call.

- **Python `@tool` functions.** In the Droid backend, an in-process `@tool` function calls the gateway route, for example `POST /tools/{name}`. The Anthropic backend uses the same functions as tool definitions.
- **One MCP server.** One MCP server can wrap the same gateway calls. Use it only if a framework needs it. [inferred]

In both cases the tool runs behind the gateway, the gateway records the run id, and the agent never does the math.

## Errors

- 403: the actor may not do this. The gateway also writes a DENIED row.
- 404: the deal or item does not exist.
- 409: the state change is not legal.
- 422: the payload is not valid, such as a number with no run id. (new)
