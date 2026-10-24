# The agents: roles, settings, memory, backends, and how to run them

Last updated: 2026-10-24, 05:10.
This is the reference for the agent layer in `backend/app/agents/`.
`STOCHASTIC.md` holds the product; `architecture/agents-and-work-items.md` holds the contracts; this file holds how the agents are set up, run, read, and debugged.
Claims are tagged [verified] when a test or a run shows them, and [inferred] when they are judgment.

## 1. The three roles in one table

| Role | Actor | What it does | Tools it may call | Where judgment lives | Typed output |
| --- | --- | --- | --- | --- | --- |
| Mapper | `agent:mapper` | Maps every target line to a platform line with confidence and reason; tags every balance sheet line for the covenant; raises flags | none | Here. Which line is which, and what must go to the controller. | `MapperOutput` |
| Preparer | `agent:preparer` | Builds the draft combined books and the leverage figure by calling tools in order | `consolidate`, `ebitda`, `covenant_debt`, `leverage` | Little. It follows the tool sequence and copies the figures. | `PreparerOutput` |
| Reviewer | `agent:reviewer` | Checks the draft: tie-out and limit test | `tie_out`, `limit_test`, `leverage` | Little. Pass when both checks pass, needs-attention when one fails. | `ReviewerOutput` |

The roles are defined in `backend/app/agents/roles.py`: a system prompt, a tool list, an input type, and an output type.
The same role runs on any backend.

## 2. Rules every role is given

From `SHARED_RULES` in `roles.py`:
- Never compute a number. Every figure comes from a math tool run through the gateway, which returns a run id.
- Never approve. A human controller approves. Never post. The gateway posts.
- Unsure means ask: an unsure line becomes a flag. Precision before recall.
- Keep memory. The session and the policies the controller taught are in the input. Apply a policy instead of asking twice, and cite its id.
- Return only the typed result.

The gateway enforces these rules in code, so a model that breaks one is refused and logged, not trusted. [verified: `backend/tests/test_trust_rules.py`]

## 3. What each role receives

- **Mapper** (`MapperInput`): deal id, platform and target names, the target lines, the platform lines, the brief, its policies, its session. Each line carries `note`, what the filing says about it (for example that the financing liability is the Statesville sale-leaseback). The note is data from the filing, not model text. [verified: `backend/app/db/fixtures/kewaunee.py`, `LINE_NOTES`]
- **Preparer** (`PreparerInput`): both companies' lines, the usable mappings (unflagged or approved), the brief, its session.
- **Reviewer** (`ReviewerInput`): the draft rows and figures, all run ids, and the named `consolidate_run_id` and `leverage_run_id`, its session.

## 4. What each role returns, and what the gateway checks

- **Mapper** returns mappings (target line id, platform line name, confidence, reason, policy id), tags (line id, tag, note, policy id), and flag proposals. A covenant flag lists line ids and options whose `tags` give the tag for every line under that reading. A mapping flag lists line ids and options whose `mappings` give target line id to platform line name. The gateway resolves platform line names or ids, re-validates the model, stores the mappings and tags, and opens one flag per proposal with the effect of each option computed by the tools.
- **Preparer** returns rows (each with the consolidate run id), ebitda, debt, leverage, limit, all run ids, and the four named run ids. The gateway refuses a run id that does not exist for the deal, a named run id of the wrong tool, a figure that no run in the list produced, and a limit that is not the brief's. [verified: `test_numbers_without_a_run_id_are_refused`, `test_model_made_number_is_refused_even_with_real_run_ids`]
- **Reviewer** returns pass or needs-attention, reasons, and the run ids of its checks. The gateway stores the review and opens the approval item; a needs-attention verdict opens it as NEEDS_INFO, and the controller cannot approve until a review passes. [verified: `test_result_cannot_be_approved_before_review_passes`]

## 5. Flags: the one human moment the Mapper creates

A flag is a question the Mapper cannot answer alone.
Two kinds:
- `covenant_tag`: lines whose treatment under the covenant is the controller's call. The prompt says exclusions are never decided by the model: a line that one of the brief's exclusions may apply to, or a family of lines that holds more than one instrument, must be tagged `unclear` and put into one flag with two or three readings, the agreement's reading as the default.
- `mapping`: a target line with no honest platform home.

For every option the gateway runs the tools as a what-if (`covenant_debt` naive, `ebitda`, `leverage`, `limit_test`) and writes the effect on the option with a run id. The card never says "goes up"; it says "Senior Funded Bank Debt 71,955K. Leverage 2.57x against 2.50x. Over the limit." [verified]

On the demo deal the intended result is one covenant flag with three readings and one small mapping flag (certificates of deposit). The scripted backend produces that every time. [verified] Model backends are judged against it in section 9.

## 6. Memory: why the agents are stateful

Decided by Cayden on 2026-10-24 (decision D12).

- `Policy`: when the controller answers a flag, the gateway writes one policy per decided line: role, kind, the normalized line name, the decision, who approved, the flag it came from. The Mapper reads its policies before it maps. A policy match becomes a mapping or tag with confidence 0.98 and the reason "Policy p_001: human:controller decided this on wi_002". The gateway counts each application and logs `policy:apply`. [verified: `test_controller_answer_becomes_a_policy_and_the_mapper_applies_it`]
- `AgentSession`: one per role: backend, backend session id, turn count, a short transcript of what it did. The Anthropic backend replays the transcript at the top of the prompt. The Droid backend records the session id. [verified: `gateway.update_session`]
- Both live in the store and survive `POST /dev/reset` (unless `keep_memory=false`). The second run of the demo deal asks nothing.
- What memory is not: model weights, a vector store, or anything the model writes itself. The gateway is the only writer, and a reversal of a flag clears the way for a new decision.

Droid session resume is deliberately not used yet. `Session.resume()` accepts MCP servers and a deny list but not the `restrict_tools` allowlist, so a resumed session could see Droid's built-in tools again. One fresh `run()` per work item keeps the allowlist; memory travels through the store instead. [verified: `droid_sdk.Session.resume` signature; inferred for the risk]

## 7. Backends and settings

One function, `run_agent(role, item)` in `backend/app/agents/runner.py`.

| `AGENT_BACKEND` | What runs | Needs | Use |
| --- | --- | --- | --- |
| `droid` | Factory Droid Python SDK 0.5.0: `run(prompt, output=Model, config=SessionConfig(mcp_servers, restrict_tools, autonomy=HIGH, system_prompt))` in an empty temp directory | `droid` CLI on PATH, `FACTORY_API_KEY` | The Factory track. Say "built with the Droid SDK" only about these runs. |
| `anthropic` | Anthropic SDK, `messages.create` with the role's tools and a `submit` tool typed as the output model, up to 12 turns | `ANTHROPIC_API_KEY` | The real model path without Droid, and the stage fallback. Not yet run live (no key). |
| `scripted` | Deterministic rules: policies, synonyms (accounting practice and Ex 99.2 Note 2), name similarity, flags below 0.6 | nothing | Last fallback and the reference answer. |
| `replay` | Recorded outputs from `backend/recordings/`; the Preparer and Reviewer re-run their tools so run ids are real | the recordings | No-network fallback. |

The runner tries `AGENT_BACKEND`, then each entry of `AGENT_FALLBACK` (default `anthropic,scripted`), and every result carries the backend that produced it (`result.backend`, the audit log, `GET /health`). [verified: `runner.run_agent`]

Settings (all in `.env`, read by `backend/app/agents/settings.py`):

| Setting | Default | Meaning |
| --- | --- | --- |
| `AGENT_BACKEND` | `scripted` (`droid` on the demo laptop) | The backend to try first |
| `AGENT_FALLBACK` | `anthropic,scripted` | Fallbacks in order; empty means none |
| `DROID_MODEL` | `claude-haiku-5-5` | Model for Droid runs |
| `DROID_MODEL_MAPPER`, `DROID_MODEL_PREPARER`, `DROID_MODEL_REVIEWER` | unset | Per-role override; the Mapper is the one to raise to `claude-sonnet-5-5` if it misreads an exclusion |
| `ANTHROPIC_MODEL` and the per-role forms | `claude-haiku-5-5` | Same for the Anthropic backend |
| `DROID_TIMEOUT` | 240 seconds | Per run |
| `DROID_RESTRICT_TOOLS` | unset | Override the allowlist. The default (tool names with and without the `MCP:stochastic/` prefix) worked on 2026-10-24. |
| `RECORD_RUNS` | `1` | Record model runs; `force` records scripted too; `0` records nothing |

Model choice: Haiku 5.5 is the default on both backends to keep the weekend cheap, as Cayden asked. With the filing notes on the lines and the tightened prompts, Haiku 5.5 produced the intended flag on the demo deal (section 9). The Preparer and Reviewer are mechanical and run well on Haiku. If a Haiku Mapper run ever misreads an exclusion again, set `DROID_MODEL_MAPPER=claude-sonnet-5-5` and keep the other two on Haiku.

Models the Factory key can run, from `scripts/droid_probe.py` on 2026-10-24: Claude Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5 and older Claude models, plus GPT-5.x, Gemini 3.x and 4, Mistral, GLM, Kimi, Qwen, DeepSeek, and Grok. [verified]

## 8. How to run and read a run

Whole deal from the command line, recording the outputs:

```
backend/.venv/bin/python scripts/record_run.py --backend droid      # or anthropic, scripted, replay
DROID_MODEL_MAPPER=claude-sonnet-5-5 backend/.venv/bin/python scripts/record_run.py --backend droid
```

Through the API: `POST /deals/d_kequ_nuaire/run` with an optional body `{"backend": "droid"}`; `GET /deals/d_kequ_nuaire/case` shows the flags, the result, and the backend status; `GET /health` shows the configured backend, the fallback chain, the per-role models, which keys are present, and the last runs with their attempts and errors.

Reading a run:
- `result.backend` says which backend produced the shown result.
- `GET /deals/{id}/runs` lists every tool run; `GET /runs/{run_id}` shows one run's inputs and outputs. Every number on screen names one.
- The audit log shows `propose:map_lines`, `ask:flag`, `tool:<name>`, `answer`, `policy:learn`, `policy:apply`, `session:turn`, `approve`, `post`, and any `DENIED` row with the reason.
- `backend/recordings/<role>.json` holds the last recorded output per role and the backend that made it. `backend/recordings/sonnet-5-5/` keeps the Sonnet 5.5 run of 2026-10-24, 03:30.

Failure switch, rehearsed on 2026-10-24, 04:50 [verified]: the API was started with the `droid` CLI missing from PATH. The run returned `mapper ran on scripted`; `GET /health` listed the attempts: droid failed ("Droid executable was not found"), anthropic failed ("ANTHROPIC_API_KEY is not set"), scripted ran. The same chain runs if the droid process dies mid-run or the timeout fires.

Two findings about Droid and models [verified by a probe on 2026-10-24, 05:00]:
- Droid does not report which model ran. The result's messages carry no model id, so `model_confirmed` is false on every Droid run and the health view shows `model_requested` only. The Anthropic backend confirms its model.
- An unknown model id does not fail. `DROID_MODEL=not-a-real-model` ran and returned a result, at about 2.7 times the credits of the same prompt on Haiku 5.5, so Droid fell back to a default model silently. Keep `DROID_MODEL` set to an id the probe listed, and never claim a model name for a Droid run beyond "requested".

## 8a. Cost

Every Droid run returns `usage` with tokens and `factory_credits`; the runner keeps a per-process total, shown in `GET /health` under `backend.totals_this_process`, and each entry of `last_runs` shows its own usage. [verified: probe output `Usage(... factory_credits=206.0)` for a one-line Haiku 5.5 prompt]
Haiku 5.5 is the default for that reason. A full deal on Haiku 5.5 is three Droid runs (the flag what-ifs are code, not model calls). Read the total after each rehearsal and write it into the run log below, so the credits last the weekend.

## 9. Run log on the demo deal

| When | Backend and model | Mapper result | Preparer and Reviewer | Verdict |
| --- | --- | --- | --- | --- |
| 2026-10-24 01:30 | scripted | 1 covenant flag (3 readings), 1 mapping flag | ran, pass | 0.77x OK |
| 2026-10-24 03:20 | droid, claude-sonnet-5-5, first prompt | decided the exclusions itself; 6 small flags (subtotals, short-term borrowings) | ran through MCP, pass | 0.77x OK |
| 2026-10-24 03:30 | droid, claude-sonnet-5-5, prompt with "exclusions are the controller's call" | 1 covenant flag with 3 readings (0.77x, 1.76x, 2.57x), 1 mapping flag | ran, pass | 0.77x OK, recorded in `recordings/sonnet-5-5/` |
| 2026-10-24 04:00 | droid, claude-haiku-5-5, before line notes | 1 covenant flag but the default reading counted the financing liability as debt (did not know it was Statesville); 2 bundled mapping flags using line ids | Preparer ran; Reviewer returned needs-attention over an unnamed leverage run id | 1.76x, review needs-attention |
| 2026-10-24 04:30 | droid, claude-haiku-5-5, with line notes, named run ids, and the tightened prompts | 1 covenant flag with 3 readings (agreement 0.77x, short-term borrowings excluded 0.74x, all counted 2.57x over), 2 mapping flags of three lines each, by name | ran, pass, with reasons citing the run ids | 0.77x OK, recorded in `recordings/` |

Lessons written into the code after these runs:
- The filing's note on a line is data the Mapper needs; it is now on every `SourceLine.note`.
- Multi-line mapping flags are allowed and resolved by name or id.
- The Preparer names its run ids, and the Reviewer is told to use them and to return needs-attention only on a failed check.

## 10. Honest limits of the agent layer

- The Anthropic backend has not run live; no key was available on 2026-10-24.
- Droid sessions are not resumed (section 6), so "stateful" means memory in the store, not a long-lived model context.
- Droid runs cannot prove which model served them (section 8). Say "Claude Haiku 5.5 requested through Droid".
- The scripted backend knows this deal's line names; on a new deal it would flag more and map less. That is the point of the model backends.
- The Mapper's flag quality depends on the model. The run log above is the evidence; say which run is on screen.
