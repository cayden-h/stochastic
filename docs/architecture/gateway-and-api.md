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
| `agent:brief_reader` (D20) | The Brief Reader. It may store a draft brief (`propose:draft_brief`) and call the read-only tools `get_section` and `get_definition`, nothing else. See `brief-reader.md`. |
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
| Edit the books, give an edit's reason, revert an edit (D19) | no | no | no | yes, `human:controller` only | no |
| Approve | no | no | no | yes, not an item they prepared | no |
| Create a deal, run the job runner | no | no | no | yes | no |
| Amend and approve the Brief (`amend_brief`, `approve_brief`) | no | no | no | yes | no |
| Post to the record, open work items, write the log, write policies | no | no | no | no | yes |

A forbidden action returns 403 and writes a DENIED row.

## Checks on every write

1. The actor exists and has the permission for this action.
2. The state change is legal for the work item (409 otherwise).
3. The proposer of an item cannot approve it (maker-checker).
   Agents cannot approve at all.
4. A result cannot be approved while the Reviewer verdict is missing or needs-attention.
5. Every number in a result carries a run id that exists for this deal (422 otherwise).
   The named run ids (`consolidate_run_id`, `ebitda_run_id`, `debt_run_id`, `leverage_run_id`, filled from `run_ids` when not named) must point at a run of that tool, made by the Preparer itself, not a what-if, and after the last flag answer.
   The debt run is not naive, the EBITDA run is on the deal's basis (`Deal.ebitda_basis`), the leverage run divides exactly those two runs, the EBITDA, debt, and leverage values equal those runs' outputs, and the rows equal the consolidate run's rows.
   A model cannot slip in a number or borrow another run's.
   Agents call `leverage` with run ids only; numbers are refused.
5a. A Mapper `not_debt` tag is refused unless it cites a live policy learned on that company's line.
    Exclusions are the controller's call.
5b. A Reviewer `pass` must cite a `tie_out` run on the result's consolidate run and a `limit_test` run on its leverage run, both for this deal and both ok.
    The gateway reads the pass from those runs.
5c. A covenant flag option that counts every flagged line as debt is computed as filed (reported EBITDA, `ebitda` with `as_filed`); choosing it puts the deal on the as-filed basis, so the result matches the card.
    Each covenant option carries `leverage`, `ok`, and `basis` from its run chain.
5d. Policies apply only to the company whose line they were learned on; reversing a flag retires the policies it taught (`policy:retire` rows).
A `company` policy with no company applies to nothing.
A `platform` policy applies only to the target lines of a deal whose platform company is `Policy.platform`, and only as a mapping: it never settles a covenant tag, so it never satisfies 5a.
5e. A result cannot be approved while any edit of the deal is `needs_reason`; the DENIED row names the edit.
5f. Only `human:controller` edits, and only while the deal's approval item is `PROPOSED` (or `NEEDS_INFO` when an edit's recompute failed a check).
    The recompute runs as the system through the edit-aware tools, and its figures are read from those runs.
5g. On a deal whose Brief is not approved, `store_mapping` and the tools `ebitda`, `covenant_debt`, and `limit_test` are refused (409 and a DENIED row).
6. The limit must equal the brief's limit.
   Every Brief, sent as JSON or drafted, has finite figures and a limit above zero.
7. The payload matches its Pydantic model.
   The gateway re-validates every agent result.
8. `consolidate` refuses to run while a flag is open.
9. The gateway writes one audit row for each change, and the hash of each row includes the hash of the row before it.

## The agents' memory

The gateway is the only writer of agent memory too.
When the controller answers a flag, the gateway writes a `Policy` for the Mapper: the line name, the decision (a covenant tag or a platform line), who decided, and the flag it came from.
On the next run the Mapper applies the policy instead of asking, and the gateway logs `policy:apply`.
A policy has a `scope`.
Flag answers make `company` policies, which apply only to the company whose line they were learned on (D18).
Remap edits (D19) make `platform` policies, which apply to every add-on of the platform named in `Policy.platform`.
The job runner gives the Mapper only the live policies whose scope covers the deal (`Gateway.policies_for`), so a model never sees another company's answers.
When two policies cover a line, the newest wins, so a later correction beats an earlier answer: the scripted Mapper applies it, the Mapper prompt says so, and the gateway accepts a cited policy only if it is the newest covering the line.
Each remembered remap learns its own policy and never updates an older one, so reverting it makes the older one effective again.
Company and platform names are compared casefolded and stripped.
The rule is in `backend/app/core/policies.py`, shared by the gateway and the scripted Mapper.
A line mapped by a platform policy cites it in its reason and carries its id in `Mapping.policy_id`, so the Learned chip shows it on the next deal.
Each role has an `AgentSession` (backend, session id, turns, a short transcript).
`POST /dev/reset` keeps both unless `keep_memory=false`.

## Routes

| Method and path | Who | Purpose |
| --- | --- | --- |
| `GET /health` | any | `ok`, `chain_valid`, the backend status, and `running` (a job is running for some deal in this process) (typed response) |
| `GET /deals` | any | List deals |
| `GET /deals/{id}` | any | One deal, with its brief |
| `GET /deals/{id}/case` | any | The whole screen in one read (shape below; response model `CaseResponse`, visible at `/docs`) |
| `GET /deals/{id}/source-lines?company=` | any | Statement lines, both companies or one |
| `GET /deals/{id}/mappings` | any | Mappings with confidence, reason, flagged, approved_by |
| `GET /deals/{id}/result` | any | The latest result (404 before the Preparer ran) |
| `GET /deals/{id}/certificate?format=md\|html\|json` | any | Draft compliance certificate from the approved, posted result (default `md`). Every figure is followed by the id of the tool run that produced it. 409 until the approve_result item is POSTED and the deal stage is `posted`. The `json` dict has `header`, `test_period`, `ebitda`, `debt`, `leverage`, `limit_test`, `tie_out`, `decisions`, `edits`, `approval`, `mappings`; each figure block carries `run_id`, and its keys are the tool's own output keys. `edits` lists each active controller edit (`id`, `kind`, `company`, `line`, `old`, `new`, `reason`, `actor`, `at`, `policy_id`), shown in the section "Edits in review" ("None." when there are none). It is a draft, not signed. |
| `GET /deals/{id}/export.xlsx` | any | The final workbook, behind the same 409 gate as the certificate (shared helper; detail "final files are available after the controller approves the result"). Sheets: Combined (the result rows, numbers as numbers, with each row's run id; a cell a controller edited has an amber fill and a note with who, when, the old value in whole thousands as the console shows it ("Line was 6,163"), the reason, and the policy; the figures display as whole thousands with separators, negatives in parentheses, and keep the tool's value), Edits (one row per active edit, amounts in the same display format), Audit (Figure, Value, Run id, Tool for EBITDA, debt, leverage, the limit test, the tie-out, and each combined row, then the audit summary, the backend, and "Draft. Not signed."). Figures are read from the same tool runs as the certificate. Served as `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` with `Content-Disposition: attachment; filename="<platform> + <target> combined books.xlsx"` (ASCII only). |
| `GET /deals/{id}/work-items?state=&type=` | any | Work items |
| `GET /deals/{id}/audit` | any | Audit rows for the deal and `chain_valid` |
| `GET /deals/{id}/timeline?bucket=60` | any | Audit rows counted per time bucket, actor, and action family (the action before the colon). Returns `{"deal_id", "bucket_seconds", "source", "buckets": [{"start", "actor", "kind", "rows", "denied"}]}`, sorted by start, actor, kind. `bucket` is whole seconds, 1 to 86400 (422 otherwise); 404 for an unknown deal. On the Postgres store `source` is `time_bucket` (TimescaleDB `time_bucket` on the written audit log of the current ledger); on the memory store, or after a database error (with the fixed `error` text "timeline query failed; see the server log", the detail only in the server log), it is `memory`. Both floor to the TimescaleDB origin 2000-01-03 00:00 UTC, so they give the same buckets. Counts only, no deal figures. |
| `GET /deals/{id}/runs` | any | Every tool run for the deal |
| `GET /runs/{run_id}` | any | One tool run: tool, inputs, outputs |
| `GET /agents/memory` | any | Policies and sessions |
| `GET /deals/{id}/conversation` | any | The deal's whole conversation in order: what the agents, the gateway, and the controller told each other (shape in "Live events" below). The same messages the stream sends as `conversation` events, for a page opened late or after a restart. 404 for an unknown deal. |
| `GET /deals/{id}/stream` | any | Server-Sent Events: audit rows as they are written, `stage`, `run`, `edit`, `conversation`, and `mapping` events (shapes below) |
| `POST /deals` | human | Create a deal from an upload. Multipart form with `name`, `platform`, `target`, files `platform_csv` and `target_csv`, and exactly one of `brief` (a JSON string of the Brief; the reader is skipped) or `agreement_txt` (the credit agreement as a UTF-8 `.txt` file, same 2 MB limit; the deal starts with `brief_status` `none` and the run starts with the Brief Reader, unless an approved Brief for the same agreement hash is reused). Returns 201 with `{"deal_id", "stage", "lines": {"platform": n, "target": n}, "brief_status"}`. 422 when neither or both of `brief` and `agreement_txt` are sent, for an empty or non-UTF-8 agreement or a name not ending in `.txt`, and naming the file, row, and column for a bad CSV. Limits: 2 MB and 2,000 rows per file. The columns are in [`data/README.md`](../../data/README.md). |
| `POST /deals/{id}/brief/amounts` | `human:controller` only | Set fields of the draft Brief (D20), most often an adjustment amount from the books with its source. Any draft field can be set by its path (the limit, the lender, the definitions, `debt_excludes[k]`, an adjustment's name, amount, or cap); only an amount needs a `source_ref`. Body `{"amounts": [{"field": "ebitda_addbacks[2].amount", "value": 698.0, "source_ref": "...", "inferred": false, "note": ""}]}` (a new adjustment is added by its `.name` at the next index). Every entry is checked first (path, index, type, source); a bad entry refuses the whole list with 422 naming `amounts[i]`, nothing applied, and a DENIED row. The entries are then applied in order through `gateway.amend_brief` under the gateway lock. The gateway cannot roll back: if it still refuses entry i, the 422 names `amounts[i]` and lists the earlier entries, which stay applied. Returns `{"brief", "brief_draft", "brief_status", "stage"}` (response model `BriefAmountsResponse`). 404 unknown deal; 422 for an empty list, a field path that is not `name[i].attr`, or a `value` that is a boolean, non-finite, too big for a float, 1e12 or more in size, or a number sent as text for an amount, a cap, or the limit (loc `amounts[i].value`, the message names the field path); 403 with a DENIED row for any actor but `human:controller` (an agent, `human:intern`), before any write; 409 when there is no draft or the Brief is approved. |
| `POST /deals/{id}/brief/approve` | `human:controller` only | Approve the draft Brief through `gateway.approve_brief`; it is locked and the deal is back at stage `new`. The run does not continue by itself: the console calls `POST /deals/{id}/run` next. Returns the deal (response model `Deal`, `brief_status` `approved`, `stage` `new`). 404 unknown deal; 403 with a DENIED row for any actor but `human:controller`, or while a `brief_field` flag is open; 409 when there is no draft (a second approve, or a deal whose Brief came as JSON). |
| `POST /deals/{id}/run` | human | Run the job runner until the deal waits on a human. Body `{"backend": "droid", "sync": true}` is optional. |
| `POST /work-items/{id}/answer` | human | `{"option_id": "b"}`. Posts the flag and, if no flag is open, continues the run in the background. `?auto_advance=false` turns that off. |
| `POST /work-items/{id}/approve` | human | Approve the result. The gateway posts it. |
| `POST /work-items/{id}/reject` | human | `{"reason": "..."}` |
| `POST /work-items/{id}/hold` | human | Keep a flag open and log the hold |
| `POST /work-items/{id}/reverse` | human | `{"reason": "..."}`. A new item linked to the original. Nothing is deleted. |
| `POST /deals/{id}/edits` | human (controller) | Edit the combined books after the agents and before approval (D19). Body `{"kind": "amount", "company", "line", "value", "section"?}` (`value` in USD thousands, finite) or `{"kind": "remap", "company", "line", "platform_line", "section"?}`. Returns `{"edit", "result", "verdict", "approval", "reasons"}` (response model `EditResponse`); the verdict is read from the recompute's tool runs. 404 unknown deal; 422 for a missing or non-finite `value`, a missing `platform_line`, or a gateway refusal (subtotal, unknown line or company, unchanged value); 403 for any actor but `human:controller`; 409 outside the PROPOSED window or for a second live edit on the line. An income statement detail edit carries into the totals by the roll-up rule in `backend/app/tools/edits.py`; a balance sheet detail edit is refused (422). A remap moves the subtotals the line fed by the remap roll-up rule in the same file, so a remap across the balance sheet's sides fails the tie-out. |
| `POST /edits/{id}/reason` | human (controller) | `{"chip": 0}` or `{"text": "..."}`, with `"remember": true` by default. Returns the edit (`status` `reasoned`, plus `adjustment_id` or `policy_id` when remembered). 422 when both `chip` and `text` are missing, or for an unknown chip; 404 unknown edit; 409 when the edit already has a reason; 403 for any other actor. |
| `DELETE /edits/{id}` | human (controller) | Undo an edit (marked `reverted`, never deleted; its policy or adjustment is retired) and recompute. Same shape as `POST /deals/{id}/edits`. 404 unknown edit; 409 when already reverted or outside the PROPOSED window; 403 for any other actor. |
| `POST /tools/{name}` | agent | `{"deal_id": "...", "inputs": {}}`. Runs a math tool and returns the run. |
| `POST /dev/reset?keep_memory=true` | dev | Reseed the deal. Agent memory is kept by default; `keep_memory=false` clears it (use it between judges). 409 while a run is in flight; frees the what-if fork slot. |

## The case shape

`GET /deals/{id}/case` returns everything the one screen needs.

```json
{
  "deal": { "id": "d_kequ_nuaire", "name": "Kewaunee Scientific acquires Nu Aire", "platform": "Kewaunee", "target": "Nu Aire", "stage": "awaiting_flag", "brief": { "limit": 2.5, "debt_term": "Senior Funded Bank Debt", "...": "..." }, "brief_status": "approved", "ebitda_basis": "covenant" },
  "stage": "awaiting_flag",
  "source_lines": [ { "id": "sl_001", "company": "Kewaunee", "line": "Cash and cash equivalents", "section": "balance_sheet", "period": "2024-10-31", "amount": 25963, "unit": "USD thousands", "source_ref": "10-Q ...", "is_total": false, "note": null, "covenant_tag": "na", "covenant_note": null, "covenant_policy_id": null } ],
  "mappings": [ { "id": "m_001", "target_line": "Net Revenues", "platform_line": "Net sales", "confidence": 0.95, "reason": "...", "flagged": false, "approved_by": null, "policy_id": null } ],
  "flags": [ { "id": "wi_002", "type": "flag", "state": "NEEDS_INFO", "question": "...", "evidence": [ { "quote": "...", "document_id": "8-K Ex 10.1, Section 4.8(a)" } ], "options": [ { "id": "a", "label": "The whole line counts", "effect": "As filed: debt 71,955K over reported EBITDA 25,312K. Leverage 2.84x against 2.50x. Over the limit.", "run_id": "run_004", "added_by": null, "leverage": 2.8427, "ok": false, "basis": "as_filed" } ], "default": "b", "answer": null } ],
  "open_flags": ["wi_002", "wi_003"],
  "result": null,
  "verdict": null,
  "work_items": [ "..." ],
  "policies": [ "..." ],
  "sessions": [ "..." ],
  "audit": { "rows": 12, "chain_valid": true, "denied": 0 },
  "backend": { "configured": "scripted", "fallback": "scripted", "anthropic_key": false, "factory_key": true, "last_runs": [ "..." ] },
  "edits": [],
  "adjustments": [],
  "brief_draft": null,
  "reason_chips": { "amount": [ { "id": 0, "label": "..." } ], "remap": [ "..." ] }
}
```

`edits`, `adjustments`, and `brief_draft` are the phase 2 additions (shapes in the next section).
They are on `/case` and `CaseResponse` now (verified by `backend/tests/test_case_phase2.py`).
The edit routes (`POST /deals/{id}/edits`, `POST /edits/{id}/reason`, `DELETE /edits/{id}`) fill `edits` and `adjustments` (verified by `backend/tests/test_api_edits.py`); `brief_draft` is the live draft from `gateway.brief_draft` (the Brief, its citations, its flag ids, `removed`), null for a deal whose Brief came as JSON or before the reader ran (verified by `backend/tests/test_api_brief.py`).
`deal.brief` is null while a deal from agreement text has no draft yet.
`reason_chips` holds the chips the edit bubble offers, per kind (`amount`, `remap`), from the gateway's `reason_chips`; they are hardcoded per deal for the demo.
`edits` lists the deal's edits in order, reverted ones included; `adjustments` lists every learned adjustment, as `policies` does.
They are declared in `CaseResponse` in `backend/app/api/schemas.py`:

```python
edits: list[Edit] = Field(default_factory=list)
adjustments: list[LearnedAdjustment] = Field(default_factory=list)
brief_draft: BriefDraft | None = None
reason_chips: dict[str, list[ReasonChip]] | None = None
```

After the Preparer and the Reviewer run, `verdict` is filled:

```json
{
  "leverage": 0.762, "limit": 2.5, "verdict": "ok", "headroom_turns": 1.738,
  "ebitda": 28378.845, "debt": 21633.0, "debt_term": "Senior Funded Bank Debt",
  "review": { "verdict": "pass", "reasons": [], "run_ids": ["run_017", "run_018"] },
  "tie_out_ok": true, "backend": "scripted",
  "debt_capacity": 49314.113, "debt_capacity_run_id": "run_018",
  "naive_debt": 71955.0, "naive_ebitda": 25311.845, "naive_leverage": 2.843, "naive_flip_addback": 3470.155,
  "sensitivity_run_id": "run_019",
  "approval_item": "wi_006", "approval_state": "PROPOSED", "posted": false
}
```

`debt_capacity` (a float, or null before the Reviewer runs) is the covenant headroom in USD thousands (the debt that would reach the limit; the next add-on is still capped by the acquisition basket and the revolver), and `debt_capacity_run_id` is the Reviewer's `limit_test` run (or null).
The sensitivity keys (`naive_debt`, `naive_ebitda`, `naive_leverage`, `naive_flip_addback`, `sensitivity_run_id`) are present only after the Reviewer passes the result and a covenant flag opened on the deal; otherwise they are absent.
They come from a separate `limit_test` run the gateway makes as `system:gateway` with `"sensitivity": true` in its inputs, on the first `/case` read after the pass; later reads reuse it.
`naive_debt` and `naive_ebitda` are the whole-line reading as filed, read from the `covenant_debt` and as-filed `ebitda` runs behind the covenant flag option that counts every flagged line as debt (option a on the demo deal).
When no covenant flag opened (for example the second demo run, where a policy settles the financing lines), there is no such run, so the keys are absent and no run is made.
If the gateway refuses the sensitivity run, the keys are absent and `/case` still answers; the refusal is audited once and not retried.
`naive_flip_addback` is the EBITDA increase at which that reading reaches the limit (debt / limit - reported EBITDA): positive means that much more EBITDA is needed, zero or negative means it already passes. On the demo deal it is $3,470K.
`naive_flip_rent` is no longer returned on `/case`: the as-filed reading has no rent deduction. The `limit_test` tool still computes it when given `ebitda_run_id`.
`result.run_ids_by_tool` maps `consolidate`, `ebitda`, `covenant_debt`, and `leverage` to their run ids, so the console can link each figure to `GET /runs/{run_id}`.
`source_lines[].note` is what the filing says about a line (for example the 10-Q note that the financing liability is the Statesville sale-leaseback). Show it on the flag card's evidence.
A mapping flag may cover several target lines; its options then carry `mappings` (target line id to platform line) in `payload.option_actions`, and the option `effect` text lists each line.
`GET /health` returns `backend.settings` with the configured backend, the fallback chain, and the model per role on each backend.
On the Postgres store, `GET /health` `store` also has `writes` (batches written), `avg_write_ms`, and `last_write_ms`: the time from queueing a batch to its commit on Tiger Cloud, rounded to 0.1 ms.
The memory store has no such keys.

`result.rows` is the combined table: `line`, `section`, `platform`, `target`, `combined`, `run_id`, in platform order and in USD thousands.
The three closing financing lines (term loan, revolver, seller notes) carry `period` "2024-11-01 (closing)".

## Phase 2 shapes: review edits (D19) and the Brief Reader (D20)

The models are in `backend/app/core/models.py`.
The routes that use them are planned: `design/review-companion.md` section 10 for edits, `brief-reader.md` section 7 for the reader.
Amounts are in USD thousands.

### Edit

One change the controller made to the combined books, recorded on top of the agents' run.
`kind` is `amount` (uses `old_value` and `new_value`) or `remap` (uses `old_platform_line` and `new_platform_line`).
`status` is `needs_reason`, `reasoned`, or `reverted`.
A `reasoned` edit has `reason_chip` (0 to 2) or `reason_text`.
An `amount` edit must have `new_value` and no platform lines; a `remap` edit must have `new_platform_line` and no values.
Approval is refused while any edit is `needs_reason` (check 5e).
`policy_id` and `adjustment_id` are set by the gateway when a reasoned edit with `remember` teaches something.
`run_ids` are the recompute runs, all new.

```json
{
  "id": "e_001", "deal_id": "d_kequ_nuaire", "kind": "amount", "company": "Nu Aire",
  "line": "Selling, general and administrative", "section": "income_statement",
  "old_value": 9812.0, "new_value": 9312.0, "old_platform_line": null, "new_platform_line": null,
  "status": "reasoned", "reason_chip": 0, "reason_text": "One-time acquisition cost, an allowed add-back",
  "remember": true, "policy_id": null, "adjustment_id": "a_001", "actor": "human:controller",
  "at": "2026-10-25T10:42:00Z", "run_ids": ["run_021", "run_022", "run_023", "run_024", "run_025", "run_026"]
}
```

A remap edit:

```json
{
  "id": "e_002", "deal_id": "d_kequ_nuaire", "kind": "remap", "company": "Nu Aire",
  "line": "Short-term investments", "section": "balance_sheet", "old_value": null, "new_value": null,
  "old_platform_line": "Cash and cash equivalents", "new_platform_line": "Short-term investments",
  "status": "needs_reason", "reason_chip": null, "reason_text": null, "remember": true,
  "policy_id": null, "adjustment_id": null, "actor": "human:controller", "at": "2026-10-25T10:44:00Z", "run_ids": ["run_027"]
}
```

The figures above are placeholders; the demo figures come from the filing.

### LearnedAdjustment (the `adjustments` list)

What a reasoned amount edit teaches.
The Preparer proposes it as a flag on a later deal, and it is never applied silently.
`status` is `applied` (learned on this deal), `proposed` (offered on a later deal), or `retired` (its edit was reverted).
`amount` is the signed change the controller made (new value minus the agents' value), not the value: an add-back is "remove 500 of cost", which carries to another deal only as a change.
In the spec this is called `Adjustment`; the code names it `LearnedAdjustment`, because `Adjustment` is already the Brief's EBITDA add-back or deduction.

```json
{
  "id": "a_001", "deal_id": "d_kequ_nuaire", "company": "Nu Aire", "line": "Selling, general and administrative",
  "amount": -500.0, "reason": "One-time acquisition cost, an allowed add-back", "edit_id": "e_001", "status": "applied",
  "at": "2026-10-25T10:45:00Z"
}
```

### ReasonChip

The reasons the bubble offers, `id` 0 to 2.
They are hardcoded per deal for the demo, and the pitch says so.

```json
[ { "id": 0, "label": "One-time acquisition cost, an allowed add-back" },
  { "id": 1, "label": "Auditor's late adjustment" },
  { "id": 2, "label": "Correcting a typo in the source" } ]
```

### Policy.scope

`Policy` gains `scope` (`company` by default, or `platform`) and `platform` (the platform name, for `platform` scope).
A `platform` policy must name its platform, and a `company` policy must leave `platform` null.
Existing policies read back as `company`, so the D18 rule on `not_debt` tags is unchanged.

```json
{
  "id": "p_012", "role": "agent:mapper", "kind": "mapping", "pattern": "short-term investments",
  "decision": "Short-term investments", "reason": "Not a cash equivalent (over 90 days)",
  "approved_by": "human:controller", "learned_from": "e_002", "deal_id": "d_kequ_nuaire",
  "company": null, "scope": "platform", "platform": "Kewaunee", "retired_by": null,
  "at": "2026-10-25T10:45:00Z", "times_applied": 0
}
```

### The Brief Reader types

- The actor `agent:brief_reader` (`BRIEF_READER`) and the work item type `draft_brief`.
- `Deal.brief_status` is `approved`, `draft`, or `none`.
  The default is `approved`, so a deal created with a Brief JSON, like the demo deal, is unchanged.
  `Deal.brief` is null only while a deal created from agreement text has no draft yet.
  A deal with `brief_status` `approved` must have a Brief; the model refuses it otherwise.
- `AgreementText` holds the agreement apart from `Deal`, because `/case` returns the whole deal: `id`, `deal_id`, `text`, `sha256`, `source`.
- `BriefCitation` is the quote behind one field: `field` (a path such as `ebitda_addbacks[1].cap`), `quote`, `section`, `confidence` (0 to 1), `note`.
- `BriefFieldFlag` is a field the controller must settle: `kind` (`brief_field`), `field`, `question`, `evidence`, `proposed` (the reader's value, or null).
- `BriefReaderInput` gets the indexes and the leverage sections, never the whole agreement: `deal_id`, `item_id`, `agreement_id`, `sha256`, `section_index` (section id to heading), `definition_index` (term to section id), `excerpts` (section id to text), `amendments_supplied`, `session`, `previous_refusal`.
- `BriefReaderOutput` is `brief`, `citations`, `flags`, `note`.
- `BriefDraft` is what `/case` shows as `brief_draft` while the controller reviews: `item_id`, `agreement_id`, `sha256`, `brief`, `citations`, and `flags` (the `brief_field` flag work item ids).

```json
{
  "brief_draft": {
    "item_id": "wi_001", "agreement_id": "ag_001", "sha256": "9f2c...e41a",
    "brief": { "lender": "PNC Bank, National Association", "limit": 2.5, "limit_section": "4.8(a)", "...": "..." },
    "citations": [
      { "field": "limit", "quote": "...", "section": "4.8(a)", "confidence": 0.95, "note": "" },
      { "field": "ebitda_addbacks[2].cap", "quote": "...", "section": "1.1", "confidence": 0.8, "note": "" }
    ],
    "flags": ["wi_002"]
  }
}
```

The quotes are elided here; the gateway checks each one is an exact substring of the agreement (`brief-reader.md` section 6).

## Review edits in the gateway (D19)

The gateway functions below are in `backend/app/gateway/gateway.py`.
The routes over them are `POST /deals/{id}/edits`, `POST /edits/{id}/reason`, and `DELETE /edits/{id}` (routes table above; verified by `backend/tests/test_api_edits.py`).
Every function refuses any actor but `human:controller` with 403 and a DENIED row.

| Function | What it does |
| --- | --- |
| `apply_edit(actor, deal_id, kind, company, line, value=None, platform_line=None, section=None)` | `amount`: one company's value on one statement line, in USD thousands. `remap`: one target line to another platform line. Refuses subtotals, unknown lines and companies, an unchanged value, and a second live edit of the same kind on the same line (409). Records the edit as `needs_reason`, recomputes, and returns `{"edit", "result", "verdict", "approval", "reasons"}`. |
| `reason_edit(actor, edit_id, chip=None, text=None, remember=True)` | Exactly one of `chip` (a `ReasonChip` id) or `text` (at most 500 characters). Sets `reasoned`. With `remember`, a remap writes a `platform` mapping policy (`Edit.policy_id`) and an amount edit writes a `LearnedAdjustment` with status `applied` (`Edit.adjustment_id`). |
| `revert_edit(actor, edit_id)` | Sets `reverted` (the edit is never deleted), retires its policy (`retired_by` is the edit id) or its adjustment (`status` `retired`), and recomputes without it. Returns the same shape as `apply_edit`. |
| `reason_chips(deal_id, kind=None)` | The chips, hardcoded per deal in `backend/app/agents/backends/scripted.py` (`REASON_CHIPS`). A deal with no list of its own gets the demo deal's. With no kind, both lists: `{"amount": [...], "remap": [...]}`. |
| `policies_for(role, deal_id)` | The live policies of a role whose scope covers the deal. |

The edit is recorded on top of the agents' run, never over it: the source lines and the mappings stay as the agents left them.
A remap does not write a new `Mapping`; the edit itself carries the new platform line, and the edit-aware `consolidate` applies it.
The recompute (`Gateway._recompute`) runs as `system:gateway`: `consolidate`, `ebitda`, `covenant_debt` (not naive), `leverage`, `tie_out`, `limit_test`.
Every run is new, and the edit-aware runs carry `edit_ids` (the live edits) in their inputs.
Only the gateway may pass `edit_ids` to a tool, and only to `consolidate`, `ebitda`, and `covenant_debt`.
`tie_out` takes no edits: its rows come from the edited `consolidate` run, so applying the edits again would double count.
If those tools do not take `edits` yet (Tri's T1), the edit is refused with 503 ("edit-aware tools not installed (T1)") and nothing is kept.
When a covenant flag gave the whole-line reading, the recompute also runs that what-if again on the edited books: `covenant_debt` naive with the flagged lines tagged debt (restored after), `ebitda` as filed, and `leverage`, each with `what_if: "whole_line"`.
The new result has `supersedes` (the result it replaces), `edit_ids`, a `review` read from the `tie_out` and `limit_test` runs, and `run_ids_by_tool` for the six tools plus `naive_covenant_debt`, `naive_ebitda`, and `naive_leverage` when the what-if ran.
For Tri: `_whole_line_runs` in `routes.py` still reads the whole-line runs from the covenant flag's option, so the `/case` sensitivity figures do not show edits yet.
It should prefer `result.run_ids_by_tool["naive_covenant_debt"]` and `["naive_ebitda"]` when the latest result has them.
The new approval item is proposed by `system:gateway`, because the revision is the gateway's recompute; the controller approves it, so maker-checker holds.
It is `PROPOSED` when both checks pass, `NEEDS_INFO` otherwise.

For Tri (T2): `/case` should add `edits` (`store.deal_edits`), `adjustments`, and `reason_chips` (`gw.reason_chips(deal_id)`), so the console can open the bubble without a second call.
If a recompute fails for any reason (a tool error included), the edit is refused with 422 and a DENIED row: `apply_edit` keeps nothing, and `revert_edit` leaves the edit live.
`run_tool` turns any tool exception into a 422 with an audit row that names it.

### The T1 contract (edit-aware tools)

```python
consolidate(platform_lines, target_lines, mappings, edits=None)
ebitda(platform_lines, target_lines, brief, as_filed=False, edits=None)
covenant_debt(platform_lines, target_lines, brief, naive=False, edits=None)
tie_out(rows, tolerance=0.5)  # unchanged: no edits
```

- `edits` is a list of `Edit` models: the live edits only, in the order they were made.
- An `amount` edit names its line by `company`, `line`, and `section`, and carries `new_value` in USD thousands.
  Source lines keep their filed unit (Nu Aire files whole dollars), so the tool converts with `to_thousands` before it compares or replaces.
- An amount edit on an income statement line must move the figures that depend on it; for example (500) of G&A raises Net Income, so covenant EBITDA rises by 500.
- A `remap` edit carries `new_platform_line`.
  The agents' `Mapping` is not changed, so `consolidate` must move that target line to the new platform line itself.
- A remap must move the subtotals too, by the remap roll-up rule in `backend/app/tools/edits.py`.
  The moved amount leaves every target subtotal the line fed in the target's own statement and joins every platform subtotal its new platform line feeds, on the rows a target subtotal landed on.
  For example, Nu Aire's Research and Development (532) moved from Operating expenses to Cost of products sold lowers the target's Gross profit from 23,682 to 23,150 and leaves Operating profit, EBITDA, and leverage unchanged.
  On the balance sheet, a line feeds the first total after it, the later totals that nest that total (by name), and its side's total, so a remap from an asset onto a liability fails the tie-out.
  `consolidate` lists each moved subtotal under `remap_rollup` as `{edit_id, line, section, delta}`.
- Each of the three tools returns `edits_applied: list[str]`, the ids of the edits it used.
  The gateway refuses the recompute (a DENIED `edit:apply` or `edit:revert` row) if the key is missing, names an edit it was not given, repeats an id, or, for `consolidate`, leaves out any live edit.
The old approval item becomes `SUPERSEDED` (a new `State`) and stays in the log.

Audit rows of an edit:

| Action | Actor | Target | When |
| --- | --- | --- | --- |
| `edit:apply` | `human:controller` | edit id | The edit is recorded and recomputed (DENIED when refused). |
| `supersede` | `system:gateway` | old approval item | A recompute replaced it. |
| `create:approve_result` | `system:gateway` | new approval item | After every recompute. |
| `edit:reason` | `human:controller` | edit id | The reason is given. |
| `policy:learn` | `system:gateway` | policy or adjustment id | A remembered reason; the reason starts with `source: edit <id>`. |
| `edit:revert` | `human:controller` | edit id | The edit is undone. |
| `policy:retire` | `system:gateway` | policy or adjustment id | Its edit was reverted. |

### Learned adjustments on a later deal

The Preparer offers each live learned adjustment that covers a line of the deal, and the gateway opens it as a flag; it is never applied silently.
The flag opens when the Reviewer's pass creates the PROPOSED approval item, not when the Preparer stores its result, because Apply is an edit and an edit needs that item.
The offers wait on the prepare item as `payload.adjustment_offers` and are checked again when they open.
An adjustment covers a line with the same name at the same company, or at the target of a deal whose platform is `LearnedAdjustment.platform`.
`Gateway.adjustments_for(deal_id)` lists the ones the Preparer may offer: not retired, not learned on this deal's own edits, and not already offered on this deal.
The job runner passes them as `PreparerInput.adjustments`, and the Preparer returns `PreparerOutput.adjustment_flags` (`adjustment_id`, `line_id`, `question`).
`store_result` refuses an offer the gateway would not make: an unknown or retired adjustment, a line it does not cover, or the same adjustment twice.
The question states the change, for example "a change of (500) to Acme Labs's General and Administrative ... from 6,163K to 5,663K".
The flag is a `flag` work item with `payload.kind` `adjustment`, proposed by the Preparer, with options `apply` and `skip` (default `skip`).
While it is open, the adjustment's status is `proposed`.
An adjustment flag does not block the Preparer, the Reviewer, or `consolidate` (`open_flags` leaves it out; `open_adjustment_flags` lists it), but approval is refused while one is open.
Answering `apply` calls `apply_edit` to set that line to this deal's agent value plus the adjustment's `amount`, then `reason_edit` with the adjustment's reason and `remember=False`, so it shows in Your edits with `Edit.from_adjustment_id`.
Answering `skip` leaves the books as the agents made them.
Either way the adjustment goes back to `applied`, live for later deals.
Audit rows: `ask:flag` (the Preparer) and `adjustment:propose` when it opens, `answer` and `adjustment:apply` or `adjustment:skip` when it is answered.

## The Brief Reader in the gateway (D20)

The functions are in `backend/app/gateway/gateway.py`; the text helpers (normalization, the hash, the section and definition indexes) are in `backend/app/core/agreement.py`.
The routes over them are Tri's (T4): `POST /deals` with `agreement_txt` calls `create_deal_from_agreement`, the amounts route calls `amend_brief`, `POST /deals/{id}/brief/approve` calls `approve_brief`, and `/case` reads `brief_draft`.
The amounts route should accept any field path, not only amounts: `amend_brief` is generic, so the console can also correct a limit or a text field.

| Function | What it does |
| --- | --- |
| `create_deal_from_agreement(actor, deal, lines, text, source)` | Creates the deal with `brief_status` `none` and stores the `AgreementText` (kind `agreement`). If an earlier deal's approved Brief has the same agreement hash, it is reused (`brief:reuse`) and the reader is skipped. |
| `brief_reader_input(deal_id, item_id)` | The section index, the definition index, and the sections that mention a leverage ratio; never the whole agreement. |
| `read_agreement(actor, deal_id, name, args)` | `get_section(id)` and `get_definition(term)`, for the reader (and the system) only. Logged as `tool:get_section` and `tool:get_definition`; no `ToolRun` is stored, since they produce no figures. |
| `store_brief(actor, item_id, out)` | The reader's draft. Refused (DENIED) unless it passes the nine checks below; then the deal's Brief is `draft`, its `brief_field` flags open, and the stage is `awaiting_brief`. |
| `amend_brief(actor, deal_id, field, value, source_ref=None, inferred=False, note="")` (`human:controller` only) | The controller sets one field by path, for example `ebitda_addbacks[0].amount` with its `source_ref` (required for an amount). A new adjustment is added by its `.name` at the next index. The open flags on that field close with answer `amended`. |
| `approve_brief(actor, deal_id)` | `human:controller` only, and only with no open `brief_field` flag. Applies the removals, checks the figures again, sets `brief_status` `approved`, and logs the agreement hash. The Brief is then locked: `amend_brief` and `store_brief` answer 409. |
| `brief_draft(deal_id)` | The `BriefDraft` for `/case`: the Brief, its citations, its flag ids, `amendments_supplied` (false: base agreement only), and `removed`. |

The checks on a draft (`brief-reader.md` section 6):
1. Only `agent:brief_reader` stores a draft, on a `draft_brief` item in state NEW.
2. Every citation names a section of the agreement, and its quote, normalized, is an exact substring of that section's text and at least four words.
3. The limit is in its quote as written, and that quote comes from the numbered covenant section the Brief names in `limit_section` (never the preamble or an annex, so a sentence planted there cannot set the limit).
   A cap is in its quote after the unit conversion (4000 is "$4,000,000").
4. Every required field has a verified quote or a reader flag: `lender`, `limit`, `limit_section`, `limit_wording`, `debt_term`, `debt_definition`, each `debt_excludes[i]`, `ebitda_definition`, and each adjustment's `.name` and `.cap`.
5. `limit_wording` is a quote from `limit_section` and contains `debt_term`; the figures are finite and the limit is above zero (0 only while its not-found flag is open).
6. An adjustment amount other than 0 needs `inferred=true` and a reader flag.
7. A field whose best quote has confidence below 0.6 opens a flag (proposed by `system:gateway`); so does every adjustment amount ("Enter the amount from the books with its source, or keep 0").
8. An empty required field needs a reader flag that says "not found in sections ...".
9. The draft is marked base agreement only (`amendments_supplied` false), and the approval row says so.

A flagged field with no verified quote holds no value while its flag is open: empty text, a limit of 0, and a cap of 0 or none (or a cap its verified evidence shows).
Whenever `limit_wording` is set, the limit is the number in it.
The draft item's `proposed_by` is `agent:brief_reader`, so the maker-checker rule applies to its approval.
A reader flag's evidence quotes are checked against the agreement: the ones found stay in `evidence`, and the others move to `payload.unverified_evidence`, for the console to show as the reader's own words.
An approved Brief is also kept by its agreement hash (`ApprovedBrief`, kind `approved_brief`) as agent memory, so reuse survives a reset with memory.
A reset with memory also keeps the `e` and `wi` id counters, as it keeps `p` and `a`, so a new id never repeats one that a kept policy or adjustment names.
Section headings are found as "4.8. Title", "7.1 Title", "Section 7.1 Title", and "SECTION 7.1."; a wrapped cross-reference such as "Section 5.8 ." is not a heading.
A `brief_field` flag is a `flag` work item with `payload.kind` `brief_field` and `payload.field`.
Its options are `confirm` and, for a list item, `remove` (applied at approval).
The runner stops on it, as on any open flag; with every flag answered it stops on "waiting on the controller to approve the Brief".
Audit rows: `agreement:load`, `brief:reuse`, `create:draft_brief`, `tool:get_section`, `tool:get_definition`, `propose:draft_brief` (DENIED when refused, with the reason), `ask:flag`, `answer`, `brief:amend`, `approve_brief`.
A refused draft is retried once with the reason, then made by the scripted backend under the same checks, as for the Mapper.
The scripted reader returns the fixture Brief with the verbatim quotes in `data/brief/kewaunee_quotes.json` when the agreement's normalized hash is listed there (the full Ex 10.1 text or the test excerpt), and a low-confidence regex read otherwise.
`closing_financing` is left empty by the reader: it comes from Ex 99.2, not the agreement, and no tool reads it.

## The stream

`GET /deals/{id}/stream` sends six kinds of event: `audit`, `stage`, `run`, `edit`, `conversation`, and `mapping`.
It looks for new events every quarter second.
On connect it sends everything the deal has so far (every audit row, the whole conversation, every stored mapping), then only what is new.
Audit events are unchanged.
A `stage` event is sent once on connect and again whenever the stage changes:

```
event: stage
data: {"deal_id": "d_kequ_nuaire", "stage": "awaiting_flag", "open_flags": ["wi_002"], "brief_status": "approved", "at": "<iso timestamp>"}
```

`brief_status` is the deal's (`none`, `draft`, or `approved`).
Every change of it in the gateway comes with a stage change, so it has no event of its own (verified by `test_the_stage_event_carries_brief_status` and a read of every `brief_status` write in `gateway.py`).

A `run` event is sent once on connect and again whenever a job for the deal starts or stops.
The job runner ends about a second after the Reviewer's hand-off, with no stage change, so the console needs this event to enable Run and Reset again:

```
event: run
data: {"running": false}
```

`/case` has the same flag as `running`.
The console reads it, never the stage, to tell whether a job is running.

An `edit` event is sent whenever the deal's edits change (an edit applied, reasoned, or reverted), with every edit's id and status in order; nothing is sent on connect while the deal has no edits:

```
event: edit
data: {"deal_id": "d_kequ_nuaire", "edits": [{"id": "e_001", "status": "needs_reason"}], "at": "<iso timestamp>"}
```

A `: keepalive` comment is sent every 15 seconds.

### Live events: the conversation

A `conversation` event is one message between the roles, sent as soon as the gateway writes it:

```
event: conversation
data: {"id": "msg_002", "deal_id": "d_kequ_nuaire", "at": "<iso timestamp>", "from": "agent:mapper", "to": "system:gateway", "kind": "message", "text": "Proposing 53 mappings and 78 covenant tags, 2 questions for the controller", "item_id": "wi_001", "run_id": null, "line_id": null}
```

`from` and `to` are one of `agent:brief_reader`, `agent:mapper`, `agent:preparer`, `agent:reviewer`, `system:gateway`, and `human:controller`.
`kind` is one of these:

| kind | Meaning | Example |
| --- | --- | --- |
| `message` | A statement: a proposal, a tool run's figure, a learned policy, the agent's own reason | Gateway to Preparer: "leverage: 0.76x" (with `run_id`) |
| `handoff` | Work passes to the next role | Mapper to Preparer: "Mappings posted: 53 lines ready to combine; the controller answered 2 questions" |
| `question` | An escalation to the controller, always `to` `human:controller`, with the flag or approval item as `item_id` | Mapper to Controller: the flag's own question |
| `answer` | The controller's answer, always `from` `human:controller`, back to the agent that asked, with the same `item_id` | Controller to Mapper: "Option b: Only the PNC term loan and revolver count" |
| `refusal` | The gateway refused a write, with its reason | Gateway to Mapper: "Refused: tag not_debt on ... is the controller's call: ..." |
| `check` | A check that passed or found a problem | Reviewer to Preparer: "Tie-out passes (run_017), limit test passes (run_018): leverage 0.76x against 2.50x" |

`item_id`, `run_id`, and `line_id` are null when they do not apply.
`run_id` names the tool run a message's figures come from.
Every figure in a message is formatted from the run it cites (or from runs that run is built on), and the only figure without a run is the Brief's limit (verified by `test_every_figure_in_a_message_equals_the_run_it_cites`).
Leverage is written from the unrounded quotient of the run's debt and EBITDA, like the flag effects, so the conversation and the cards agree in the second decimal.
Texts are one line, plain hyphens only, at most 300 characters; a model's reason is cut to fit.

Where the messages come from.
The gateway writes each one in the same write as the thing it describes, so a message is never ahead of the record and never says what did not happen:

| When | Message |
| --- | --- |
| The runner opens a work item (`create_item`) | The hand-off: Gateway to Brief Reader, Gateway or Brief Reader to Mapper (Brief Reader when it drafted the approved Brief), Mapper to Preparer, Preparer to Reviewer |
| An agent hands in a result (`store_mapping`, `store_result`, `store_brief`) | The agent to the Gateway with the counts or figures, then the agent's own `note` when it gave one (the scripted backend's notes are fixed, the Droid and Anthropic notes are the model's) |
| The gateway accepts it | A `check` back to the agent: mappings and tags accepted, and how many a learned policy decided; every figure traced to its runs; citations checked |
| The gateway refuses anything (`_deny`) | A `refusal` to the actor, with the refusal reason |
| An agent's tool run (`run_tool`, `read_agreement`) | Gateway to the agent with the run's figure and `run_id`; the system's what-ifs and recomputes are summed up by the message that uses them instead |
| A flag opens (Mapper, Brief Reader or Gateway, Preparer) or the Reviewer finds a problem | A `question` to the controller with the item id |
| The controller answers, amends a Brief field, holds, rejects, or reverses | The `answer` (or a message) to the agent that asked; one message for the policies the answer taught |
| The Reviewer's review is stored | Reviewer to Preparer `check`, then Reviewer to Controller: `handoff` "Ready for your approval" (pass) or a `question` (needs attention) |
| The controller approves, edits, gives a reason, or undoes an edit | Controller to Gateway, then the Gateway's reply: posted, or "Recomputed after edit ..." |
| The job runner retries a refused model result or falls back to scripted | Gateway to the agent, through `Gateway.note` |
| A run stops on an error | Gateway to Controller: "The run stopped: ..." |

The agents still do not call each other: the job runner moves work items and the gateway is the only writer.
The conversation is a readable view of that record, written as the record is written.
It is stored as a record of kind `conversation` (collection `messages`, ids `msg_001`, ...), in memory and in Postgres, so a page opened late or after a restart replays it whole from `GET /deals/{id}/conversation` or the stream.
`/dev/reset` clears it with the rest of the deal's record.

### Live events: mapping

A `mapping` event is one target line's mapping, sent when the gateway accepts it, in the order the gateway stores them:

```
event: mapping
data: {"mapping_id": "m_001", "line_id": "sl_055", "company": "Nu Aire", "section": "balance_sheet", "line": "Cash and Cash Equivalents", "platform_line": "Cash and cash equivalents", "platform_line_id": "sl_001", "confidence": 1.0, "reason": "Same line", "flagged": false, "approved_by": null, "policy_id": null, "at": "<iso timestamp>"}
```

The gateway checks the Mapper's whole result first, so a refused result sends no mapping event.
It then stores the mappings one by one, and `/case` shows the mappings stored so far while the Mapper's result is being written.
A mapping is sent again when it changes (a mapping flag's answer sets `platform_line` and `approved_by`).
A live model returns all its mappings at once, so they are sent in the order the gateway stores them, a few milliseconds apart; with `DEMO_PACE` on a scripted or replay run, about 0.3 s apart.

### Demo pace

`DEMO_PACE` (default off) makes the job runner wait a little on the scripted and replay backends, so the demo plays at a speed people can follow (`backend/app/agents/pace.py`).
`DEMO_PACE=1` is human speed; 0.5 halves each wait and 2 doubles it (capped at 5).
The waits at `DEMO_PACE=1`: 2.5 s when an agent picks up its work item, 1.0 s before each tool call it makes, 0.3 s after each mapping is stored, 1.5 s before each question opens, and 1.0 s after a result is stored.
On the demo deal that is about 22 s from Run to the two questions (53 mappings) and about 13 s from the last answer to "Ready for your approval" (Preparer 7.5 s, Reviewer 5.5 s), measured on uvicorn on 2026-10-24 as 23 s and 12 s.
The waits are never inside the gateway's checks, a live model backend (`droid`, `anthropic`) gets none, and under pytest the pace is off unless a test turns it on.

## Stages

`new` (loaded), `reading_brief`, `awaiting_brief`, `brief_ready`, `awaiting_flag`, `flags_answered`, `mapped`, `awaiting_review`, `needs_attention`, `awaiting_approval`, `posted`, and `run_failed`.
A deal from agreement text goes `reading_brief`, `awaiting_brief` (open Brief flags), `brief_ready` (all answered), then back to `new` on approval, and maps from there.
A run that stops on an error is `run_failed`, on the sync route as well as in the background, with one `run:failed` row.
Jobs live in the API process, so none survives a restart.
On start, a deal the store loaded at a working stage (`reading_brief`, `mapping`, `mapped`, `flags_answered`, `preparing`, or `awaiting_review`) is moved to `run_failed`, with a `run:failed` row whose reason is "the app restarted mid-run" and a message to the controller, so Run again picks up where it stopped (`Gateway.recover_interrupted_runs`).
`/dev/reset` checks for a running job and resets under the lock a run's claim takes, so a Run and a reset never interleave.
After an edit, the stage is `awaiting_approval` or `needs_attention` again, from the recompute's checks.

## Errors

- 403: the actor may not do this. The gateway also writes a DENIED row.
- 404: the deal, item, or run does not exist.
- 409: the state change is not legal, or `POST /deals/{id}/run` while a run of that deal is in progress (answering the last flag starts one).

Fields the gateway sets, never a model:
- `Option.added_by` is `system:gateway` on the baseline reading the gateway adds to a covenant flag (every flagged line counted as debt) when the Mapper did not offer it; `null` on the Mapper's options.
- `Mapping.policy_id` and `SourceLine.covenant_policy_id` name the learned policy that decided the line, and are set only when the cited policy exists and decided the same thing. The console's Learned chip reads them.
- 422: the payload is not valid, such as a number with no run id, or a tool called while a flag is open.

## run_agent(role, item)

One function runs every agent (`backend/app/agents/runner.py`).

| Backend | `AGENT_BACKEND` | Use |
| --- | --- | --- |
| Anthropic API with tool use and a `submit` tool typed as the output model | `anthropic` | The real model path and the stage fallback |
| Factory Droid Python SDK, `Session(..., config=SessionConfig(mcp_servers, restrict_tools))`, one resumed session per role in its own empty folder | `droid` | The agents we show as built with Droid |
| Deterministic rules, no model | `scripted` | Last fallback and reference answer |
| Recorded outputs from `backend/recordings/` (the Preparer and Reviewer re-run their tools) | `replay` | No-network fallback |

The runner tries `AGENT_BACKEND`, then each backend in `AGENT_FALLBACK` (default `scripted`), and reports which one produced the result.
`result.backend` and `GET /health` show it.
Say "built with the Factory Droid SDK" only about runs that went through `droid`.
