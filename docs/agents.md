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

A fourth role, the Brief Reader (`agent:brief_reader`), is built (D20), and a code verifier (`system:verifier`, not a model) checks its draft field by field before the controller approves it in one click (D23, `architecture/brief-reader.md` section 6a). It reads the credit agreement and drafts the brief with a quote for every field; the gateway checks the quotes and the controller approves the brief before the Mapper runs. Design: `architecture/brief-reader.md`.
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

For every option the gateway runs the tools as a what-if (`covenant_debt` naive, `ebitda`, `leverage`, `limit_test`) and writes the effect on the option with a run id. The card never says "goes up"; it says "As filed: debt 71,955K over reported EBITDA 25,312K. Leverage 2.84x against 2.50x. Over the limit." [verified]
The option that counts every flagged line as debt is computed as filed (reported EBITDA, no add-backs, no rent deduction); the other options use covenant EBITDA. Each option also carries its ratio, verdict, and basis, read from its `limit_test` run, for the console. [verified: `test_gateway_guards.py`]

On the demo deal the intended result is one covenant flag with three readings and one small mapping flag (certificates of deposit). The scripted backend produces that every time. [verified] Model backends are judged against it in section 9.

## 6. Memory: why the agents are stateful

Decided by Cayden on 2026-10-24 (decision D12).

- `Policy`: when the controller answers a flag, the gateway writes one policy per decided line: role, kind, the normalized line name, the decision, who approved, the flag it came from. The Mapper reads its policies before it maps. A policy match becomes a mapping or tag with confidence 0.98 and the reason "Policy p_001: human:controller decided this on wi_002". The gateway counts each application and logs `policy:apply`. [verified: `test_controller_answer_becomes_a_policy_and_the_mapper_applies_it`]
- `AgentSession`: one per role: backend, backend session id, turn count, a short transcript of what it did. The Anthropic backend replays the transcript at the top of the prompt. The Droid backend records the session id and resumes it on the role's next turn. [verified: `gateway.update_session`, `backend/tests/test_agent_sessions.py`]
- Both live in the store and survive `POST /dev/reset` (unless `keep_memory=false`). The second run of the demo deal asks nothing.
- What memory is not: model weights, a vector store, or anything the model writes itself. The gateway is the only writer, and a reversal of a flag clears the way for a new decision.

Droid sessions are resumed since 2026-10-24 evening. Each role keeps one Droid session across work items and deals, in its own empty folder (`DROID_WORKDIR/<role>`, default `~/.cache/stochastic/droid/<role>`), so the Factory session list groups each role's turns together.
Before this, every call opened a new session in a new temp folder, so Droid showed a new project on every call; and a backend name mismatch (`auto` against `droid`) reset the stored session each run, so turn counts never passed 1.
`Session.resume()` does not take the `restrict_tools` allowlist, but a resumed session keeps the one it was opened with, along with its model, reasoning effort, and system prompt. [verified: a probe on 2026-10-24 listed the same two tools on both turns and recalled a word from turn 1 without a tool call; the live deal below confirmed Haiku 5.5 at medium on resumed turns]
Because a resumed session keeps its system prompt, the backend stores a fingerprint of the role's prompt, model, effort, and tools (`session_key`) and starts a new session when it changes. If a session cannot be loaded, a new one starts and the run meta says why (`resume_error`).

## 7. Backends and settings

One function, `run_agent(role, item)` in `backend/app/agents/runner.py`.

| `AGENT_BACKEND` | What runs | Needs | Use |
| --- | --- | --- | --- |
| `droid` | Factory Droid Python SDK 0.5.0: `run(prompt, output=Model, config=SessionConfig(mcp_servers, restrict_tools, autonomy=HIGH, system_prompt))`, one resumed session per role in its own empty folder | `droid` CLI on PATH, `FACTORY_API_KEY` | The Factory track. Say "built with the Droid SDK" only about these runs. |
| `anthropic` | Anthropic SDK, `messages.create` with the role's tools and a `submit` tool typed as the output model, up to 12 turns | `ANTHROPIC_API_KEY` | The real model path without Droid. Ran on Eric's key (one full recorded run in `recordings/anthropic-haiku-5-5/`, 0.76x, Reviewer pass, 32 of 33; about 50 Mapper trials scoring 27 to 33). The demo laptop has no key, so it is out of the default fallback chain since 2026-10-24 08:00; add it to `AGENT_FALLBACK` when a key is in `.env`. |
| `scripted` | Deterministic rules: policies, synonyms (accounting practice and Ex 99.2 Note 2), name similarity, flags below 0.6 | nothing | Last fallback and the reference answer. |
| `replay` | Recorded outputs from `backend/recordings/`; the Preparer and Reviewer re-run their tools so run ids are real | the recordings | No-network fallback, and the backend of the two demo paces (section 7a). |

The runner tries `AGENT_BACKEND`, then each entry of `AGENT_FALLBACK` (default `scripted`), and every result carries the backend that produced it (`result.backend`, the audit log, `GET /health`). [verified: `runner.run_agent`]

## 7a. The demo paces replay the recorded Haiku 5.5 run

Since 2026-10-25 (D22) the two demo paces replay a real recorded Claude Haiku 5.5 run, not the scripted rules (`backend/app/agents/demo_replay.py`).
Before, pace `demo` forced the scripted backend, and the model card said "Scripted rules, no model".

| Pace | Where | Backend | To the questions | Last answer to approval |
| --- | --- | --- | --- | --- |
| `demo` | Run the demo (the Hyphenate beat, about 15 s) | the Brief Reader on the rules, then the replay of `haiku-5-5-run2`, forced | read and verify 4.2 s measured to the Brief approval, then 4.0 s to the questions (D23) | 7.3 s measured (6.6 s fake clock) |
| `factory` | Upload then Begin (the Factory beat, about 30 s) | the same, forced | twice the demo's waits | 14.4 s measured (13.2 s) |
| `human` | `DEMO_PACE=1` timings | `AGENT_BACKEND` and its fallback chain | 20.1 s (scripted) | 12.1 s (scripted) |
| `off` | no waits | `AGENT_BACKEND` and its fallback chain | the backend's own time | the backend's own time |

Measured on uvicorn on 2026-10-25 at 00:05, memory store, the four cases seeded, agent time only, polling `/case` every 50 ms. [verified: `backend/tests/test_demo_replay.py` for the fake-clock figures]

Which recording: `backend/recordings/haiku-5-5-run2/`, the live Droid run of the demo deal with `DROID_MODEL=claude-haiku-5-5`, committed on 2026-10-24 at 03:40 PDT (commit 8b914db, "score it 33 of 33").
Its `recording.json` holds the model, the backend, the time, and `model_confirmed: false`: the served-model check from the droid session record (section 8) came later that day, so the model is the one requested. [verified: git log; inferred: that Droid served Haiku 5.5, from every later checked Haiku run]
It reproduces the demo beat through today's gateway: the Mapper asks two questions, the covenant reading of six Kewaunee lines (agreement 0.76x, as filed 2.84x over, short-term arrangements unsecured 0.73x) and where six Nu Aire lines go, led by the certificates of deposit; the answers teach the policies; the Preparer and the Reviewer finish at 0.76x, Reviewer pass. [verified: `test_demo_replay.py`]
The texts on screen are the model's own, so they differ from the scripted rules' texts: the second question bundles the certificates of deposit with five other lines, and its default leaves the certificates unmapped and listed.
The other Haiku 5.5 recording, `anthropic-haiku-5-5/` (Anthropic API, 2026-10-24 08:28), asks three questions, so the demo does not use it.
`haiku-5-5/` (the 04:30 row of section 9) is refused by today's gateway (an option leaves a line unclear).

The forced backend rule: a `demo` or `factory` run with no `backend` of its own pins every role to one backend with no fallback chain, so it never makes a live call, whatever `.env` says.
That backend is the replay when it fits the deal, and the scripted rules when it does not:
- The deal's statements must be the recorded ones, by a content hash (role, section, line name, amount, total flag).
  The live demo deal and an upload of the same two statements pass; the recorded line ids are translated to the deal's own ids by that content.
- No live policy from outside this run may cover the deal, since the recording was made with no memory.
  After a reset that keeps memory, the second run is scripted, asks nothing, and applies the policies.
- The Brief Reader has no Haiku recording, so a Brief step runs the rules.
When the rules run, the Mapper gets a system note with the reason, and `backend` says `scripted`.

Honesty: the model card says "Claude Haiku 5.5 · recorded run", read from `last_runs[].model` and `recorded` on `/health`.
That is true for the Mapper, whose mappings, tags, questions, and options are the model's typed output from that run.
The Preparer and the Reviewer are mechanical: on replay they re-run the recorded tool sequence, so every figure is live, and their text is the rules' (the Preparer's note says "Replay of the recorded ... run").
Say: "a recorded Claude Haiku 5.5 run, replayed; the gateway, the math, and the log are live".
Never say it is a live model call.

Settings (all in `.env`, read by `backend/app/agents/settings.py`):

| Setting | Default | Meaning |
| --- | --- | --- |
| `AGENT_BACKEND` | `scripted` (`droid` on the demo laptop) | The backend to try first |
| `AGENT_FALLBACK` | `scripted` | Fallbacks in order; empty means none |
| `DROID_MODEL` | `claude-haiku-5-5` | Model for Droid runs |
| `DROID_MODEL_MAPPER`, `DROID_MODEL_PREPARER`, `DROID_MODEL_REVIEWER` | unset (`DROID_MODEL_MAPPER=claude-sonnet-5-5` on the demo laptop) | Per-role override; the Mapper runs on Sonnet 5.5 for the demo (section 9, 08:30) |
| `ANTHROPIC_MODEL` and the per-role forms | `claude-haiku-5-5` | Same for the Anthropic backend |
| `DROID_TIMEOUT` | 90 seconds (75 in the demo .env) | Per run; the measured Mapper takes 47 to 64 s |
| `DROID_RESTRICT_TOOLS` | unset | Override the allowlist. The default (tool names with and without the `MCP:stochastic/` prefix) worked on 2026-10-24. |
| `RECORD_RUNS` | `1` | Record model runs to `recordings/latest/` (git-ignored), so a live run never replaces the pinned replay; `force` (used by `scripts/record_run.py`) writes the pinned `recordings/<role>.json`; `0` records nothing |

Model choice: Haiku 5.5 is the default on both backends to keep the weekend cheap, as Cayden asked. With the filing notes on the lines and the tightened prompts, Haiku 5.5 produced the intended flag on the demo deal (section 9). The Preparer and Reviewer are mechanical and run well on Haiku. Since 2026-10-24 08:30 the demo Mapper runs on Sonnet 5.5 and the other two stay on Haiku: in the live end-to-end tests a Haiku Mapper varied too much from run to run (section 9), and Sonnet held both moments in two trials of two.

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
- `backend/recordings/<role>.json` is the default replay: the Sonnet 5.5 run of 2026-10-24, 03:30 (a copy stays in `backend/recordings/sonnet-5-5/`). `backend/recordings/haiku-5-5/` keeps the Haiku 5.5 run of 04:30, which the gateway now rejects at the Mapper step because its default option left "Short-term borrowings" unclear. `backend/recordings/haiku-5-5-run2/` is the Haiku 5.5 run committed on 2026-10-24 at 03:40, which passes the rule and replays through; since 2026-10-25 it is what the demo paces replay (section 7a). Replay a specific run with `RECORDINGS_DIR=$PWD/backend/recordings/<name>`.

Failure switch, rehearsed on 2026-10-24, 04:50 [verified]: the API was started with the `droid` CLI missing from PATH. The run returned `mapper ran on scripted`; `GET /health` listed the attempts: droid failed ("Droid executable was not found"), anthropic failed ("ANTHROPIC_API_KEY is not set"), scripted ran. The same chain runs if the droid process dies mid-run or the timeout fires.

Two findings about Droid and models [verified by a probe on 2026-10-24, 05:00]:
- The run result does not say which model ran, but the droid CLI's own session record does: every assistant message in `~/.factory/sessions/<cwd>/<session id>.jsonl` carries `modelId` and `reasoningEffort`. Since 2026-10-24 evening the backend reads that record after each run (`served_model`), and `model_confirmed` is true when it matches the request; the health view shows `model_served` and `reasoning_effort_served` next to the requested values. [verified: a probe with `DROID_MODEL=claude-sonnet-5-5` was recorded as `claude-sonnet-5-5`, and the three deal runs as `claude-haiku-5-5`]
- Droid has a router model with the id `auto` ("Auto Model", kind router). Our sessions never use it: every role passes its model id, and the record confirms it. The interactive `droid` CLI may still show "Auto Model" as its own default; that setting is separate from SDK sessions and is changed with `/model` in the CLI. Do not set `DROID_MODEL=auto`.
- Reasoning effort is pinned as well (`DROID_REASONING_EFFORT`, default `medium`, per-role overrides). Without it Droid used `high` on every run, whatever the model's own default (Haiku 5.5's is `medium`).
The default is `medium` since 2026-10-24: the confirmed medium run gave the same flags and verdict as the three high runs, at lower cost. [verified for one run]
- An unknown model id does not fail. `DROID_MODEL=not-a-real-model` ran and returned a result, at about 2.7 times the credits of the same prompt on Haiku 5.5, so Droid fell back to a default model silently. Keep `DROID_MODEL` set to an id the probe listed, and never claim a model name for a Droid run beyond "requested".

## 8a. Cost

Every Droid run returns `usage` with tokens and `factory_credits`; the runner keeps a per-process total, shown in `GET /health` under `backend.totals_this_process`, and each entry of `last_runs` shows its own usage. [verified: probe output `Usage(... factory_credits=206.0)` for a one-line Haiku 5.5 prompt]
Haiku 5.5 is the default for that reason. A full deal on Haiku 5.5 is three Droid runs (the flag what-ifs are code, not model calls). A full deal on Haiku 5.5 at medium effort cost 11,942 credits on 2026-10-24 (see the run log). Read the total after each rehearsal and write it into the run log below, so the credits last the weekend.

## 9. Run log on the demo deal

| When | Backend and model | Mapper result | Preparer and Reviewer | Verdict |
| --- | --- | --- | --- | --- |
| 2026-10-24 01:30 | scripted | 1 covenant flag (3 readings), 1 mapping flag | ran, pass | 0.77x OK |
| 2026-10-24 03:20 | droid, claude-sonnet-5-5, first prompt | decided the exclusions itself; 6 small flags (subtotals, short-term borrowings) | ran through MCP, pass | 0.77x OK |
| 2026-10-24 03:30 | droid, claude-sonnet-5-5, prompt with "exclusions are the controller's call" | 1 covenant flag with 3 readings (0.77x, 1.76x, 2.57x), 1 mapping flag | ran, pass | 0.77x OK, recorded in `recordings/sonnet-5-5/` |
| 2026-10-24 04:00 | droid, claude-haiku-5-5, before line notes | 1 covenant flag but the default reading counted the financing liability as debt (did not know it was Statesville); 2 bundled mapping flags using line ids | Preparer ran; Reviewer returned needs-attention over an unnamed leverage run id | 1.76x, review needs-attention |
| 2026-10-24 04:30 | droid, claude-haiku-5-5, with line notes, named run ids, and the tightened prompts | 1 covenant flag with 3 readings (agreement 0.77x, short-term borrowings excluded 0.74x, all counted 2.57x over), 2 mapping flags of three lines each, by name | ran, pass, with reasons citing the run ids | 0.77x OK, recorded in `recordings/haiku-5-5/`; no longer the default replay, see section 7 |
| 2026-10-24, before 03:40 PDT (the commit time of the recording) | droid, claude-haiku-5-5, after the settle-every-line rule, the add-backs, and the console rebuild | 1 covenant flag over six lines with 3 readings, every option settling every line (agreement 0.76x, none excluded 2.54x, short-term arrangements unsecured 0.73x); 1 mapping flag over six lines | ran, pass, reasons cite the tie-out and limit_test run ids | 0.76x OK, recorded in `recordings/haiku-5-5-run2/`; Mapper scored 33 of 33 against Note 2 |
| 2026-10-24 late | droid, claude-haiku-5-5 at medium effort, model confirmed from the session record | same flags | ran, pass | 0.76x OK, not recorded. Credits: Mapper 5,845, Preparer 5,045, Reviewer 1,052, so 11,942 for the whole deal on Haiku 5.5 |
| 2026-10-24 evening | droid, claude-haiku-5-5 at medium, sessions resumed: two deals in a row on one store | deal 1: same flags; deal 2: none, 6 policies applied | ran, pass on both | 0.76x OK on both, not recorded. All three roles resumed their deal-1 session on deal 2. Credits deal 1: 5,169 + 3,992 + 1,128 = 10,289; deal 2: 2,950 + 4,000 + 341 = 7,291 |

| 2026-10-24 08:06 | droid, Haiku 5.5, `STORE=postgres` | 1 covenant flag with the whole-line reading (2.54x over), 1 mapping flag | ran, pass; a second Preparer started by a Run click during the auto-advance was DENIED by the gateway (now a 409, see lessons) | 0.76x OK, approved; a restart of the API loaded all 55 audit rows, 11 policies, and 3 sessions back from Tiger |
| 2026-10-24 08:10 | same, second run after a reset with memory kept | no flag, 11 policies applied | ran, pass | 0.76x OK in 58 s; but no Learned chip on screen, because the model's reasons read "Controller policy maps ...": fixed with `policy_id` (lessons) |
| 2026-10-24 08:20 | droid, Haiku 5.5, browser, cold | 3 flags; the covenant flag's three readings were all under the limit (0.76x, 1.74x, 1.53x), so the moment did not show | not run | Led to the gateway's baseline option (lessons) |
| 2026-10-24 08:22 | droid, Haiku 5.5, browser, cold, with the baseline | flag at 64 s; the gateway's baseline showed 2.54x over; the mapping flag's suggested answer mapped Interest Income - Net to Interest expense | approve enabled 36 s after the last answer | 0.76x OK. Second run: 8 of 9 policies applied, the wrong interest policy declined after the sign rule, and a new 3-line mapping flag, so not a clean second run |
| 2026-10-24 08:30 | droid, Mapper Sonnet 5.5, Preparer and Reviewer Haiku 5.5, API trial | 49 s; covenant flag with the 2.54x reading from the model itself, 1 mapping flag | 29 s and 9 s, pass | 0.76x OK; second run: no flag, ready for approval in 58 s |
| 2026-10-24 08:53 | droid, Mapper Sonnet 5.5, `FORKS=tiger`, browser, cold | flag at 48 s; Tiger fork ready 33 s later with 3 what-ifs | fork deleted 1 s after the answer; approve live 33 s after the last answer | 0.76x OK, approved; three FORK rows in the log |
| 2026-10-24 08:33 | same, second trial | 47 s; same two flags | pass | 0.76x OK; second run: no flag, 58 s |

Figures in the log are as computed at the time. Since Tri's interest-income fix on 2026-10-24, the same recordings replay at 0.76x covenant; since the as-filed change that evening (D18), the whole-line reading replays at 2.84x.

Lessons written into the code after these runs:
- The filing's note on a line is data the Mapper needs; it is now on every `SourceLine.note`.
- Multi-line mapping flags are allowed and resolved by name or id.
- The Preparer names its run ids, and the Reviewer is told to use them and to return needs-attention only on a failed check.
- Every option of a covenant flag must settle every flagged line as debt or not_debt. The gateway rejects a proposal that leaves one unclear, and the Mapper prompt says so.
- A covenant flag always shows the reading that counts every flagged line as debt. When the Mapper does not offer it, the gateway adds it, computed by the same tools and labelled as the gateway's (`Option.added_by`). The moment no longer depends on the model's wording. (08:20 run)
- A learned line is marked by the gateway from the policy record (`Mapping.policy_id`, `SourceLine.covenant_policy_id`), and only when the cited policy decided the same thing. The console's Learned chip reads that field, not the reason text. (08:10 run)
- The Mapper keeps the sign of a line (an income line never maps to an expense line), and names lines by name in a flag's question, never by id. (08:22 run, and the 08:20 question that read "Sl_015 and sl_023")
- One run per deal at a time: answering the last flag starts the job runner, so `POST /deals/{id}/run` during that run returns 409. (08:06 run)
- The gateway, not the prompt, enforces the rest (risk review, 2026-10-24 evening, D18). Each rule has a test in `backend/tests/test_gateway_guards.py`:
  - A `not_debt` tag from a model is refused unless it cites a live policy learned on that company's line. This also stops text injected into a line name.
  - A result must cite the Preparer's own runs made after the last answer: non-naive debt, the deal's EBITDA basis, a leverage run that divides exactly those two, and rows equal to the consolidate run. Agents cannot pass numbers to `leverage`.
  - The Reviewer's pass is read from its `tie_out` and `limit_test` runs on this result; a pass with no runs, failed runs, or another deal's runs is refused.
  - Policies are scoped to the company; a reversal retires the policies the flag taught.
  - A refused model result is retried once with the reason (Mapper), then made by the scripted backend under the same checks.
- The pinned replay is the Sonnet 5.5 first run (`recordings/sonnet-5-5/`), so replay raises the covenant flag. The earlier pin was a run with memory and showed no flag. (`test_demo_reset.py`)

## 10. Honest limits of the agent layer

- The Anthropic backend ran on Eric's key, not on the demo laptop, so it is out of the stage fallback chain.
- Each role's Droid context grows with every turn, because the whole work item input goes into the conversation. Droid compacts long sessions itself; we have not run enough turns to see it. [inferred]
- The served model comes from the droid CLI's own session record, not from Factory's API (section 8). Say "Claude Haiku 5.5 through Droid, confirmed from the session record".
- The scripted backend knows this deal's line names; on a new deal it would flag more and map less. That is the point of the model backends.
- The Mapper's flag quality depends on the model. The run log above is the evidence; say which run is on screen.
- The brief is written by hand, and only the PNC brief exists. The agents never read the credit agreement today; the Brief Reader (D20) is planned for that.
