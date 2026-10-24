# Eric: data and facts

Branch: `eric/data`. Pull `main` into it first; it is behind.
Folders: `data/`, `scripts/`, `evals/`, and the Devpost text in `docs/devpost/`.

## Done (2026-10-24, merged in PR #2)

1. Every fixture figure checked against the filings (`evals/fixture_check.md`).
2. The two input files exported as CSVs in `data/`, and the loader in `scripts/`.
3. The Note 2 answer key in `evals/`, and the Mapper scored against it.
4. The flag card facts (`docs/devpost/flag-card.md`).
5. The brief as prose (`docs/devpost/brief.md`).
6. The Devpost text and the real-versus-simulated list (`docs/devpost/devpost.md`).

## Open

On 2026-10-24 at 08:20 Cayden moved Eric's open tasks to Cayden and Tri. The list below is kept as history; the owners are in `cayden.md` and `tri.md`.

1. (Cayden) **Submit the Devpost first draft on devpost.com by Saturday night.** The organizers ask for a draft Saturday night and allow edits until 10am Sunday.
   - Add all four teammates, and opt in to Hyphenate, Factory, Figma, and Tiger Data (the MLH opt-in field).
   - Fill in which backend produced the shown run (`devpost.md`, the line that asks Cayden).
   - Replace the line about placeholder mockups once Josie's design is in.
2. (Tri) **Wording for the compliance certificate** (Tri builds the route, his task 2). Find what Ex 10.1 says the compliance certificate must contain, and the test period and delivery deadline. Write the sections and the fixed wording into `docs/devpost/certificate.md`, with the exhibit and section for each and quotes under 15 words. About 1 hour.
3. (Tri) **Check the two inferred inputs again.** The pitch rests on them.
   - The Statesville cash rent ($1,970K): is the 10-K obligations-table figure right for the test period? Write the source, or a better figure, into `evals/fixture_check.md`.
   - Transaction costs ($698K expected, kept at zero): does the 8-K/A or Ex 10.1 say whether they count in the test period? Applying them would put the whole-line reading under 2.50x, so the answer matters.
   - Give any change to Tri; the tools recompute, and Cayden updates the pitch words.
4. (Cayden) **The honest-limits card and a one-page summary**, printable, for the table: what is real, what is inferred, what is cut (purchase accounting, the five-month fiscal year gap), and the four tracks. Base it on `demo-script.md` section 6 and the real-versus-simulated list.
5. (Everyone) **Answer three judge questions without notes** on the filings, Note 2, and the brief (`demo-script.md` section 8).

## Open: Droid rewind and a permission spike (assigned by Cayden, 2026-10-24 10:47)

Branch: `eric/droid-rewind`, cut from the latest `main`.
For this task only, Cayden gives Eric `backend/app/agents/backends/droid_backend.py`, `backend/app/agents/jobs.py`, `backend/app/agents/runner.py`, and new or changed tests in `backend/tests/` for these files.
Do not edit `backend/app/db/postgres.py`; another session is changing its schema now.
If `backend/app/core/models.py` needs a change, ask Cayden first.
Do not edit `docs/STOCHASTIC.md`; give Cayden the decision text and the results at the end.

### Why

When the gateway refuses the Mapper's result, `jobs.py` (the `except Invalid` block in `advance`) runs the Mapper again with `previous_refusal`.
On the Droid backend that second turn resumes the same session, so the refused answer stays in the agent's memory and is carried into later deals.
The pitch line we want is "when the gateway rejects an answer, we rewind the session, so a mistake never becomes memory".
Today that line is false. This task makes it true.

### Task A: rewind the Mapper's session before the retry (the main task)

What the SDK has [verified: `droid_sdk` 0.5.0 in `backend/.venv`, read the source on 2026-10-24]:

- `Session.rewind(message_id, *, restore=(), delete=(), title)` in `droid_sdk/_high_level/_session_operations.py`.
  It returns a `RewindOutcome` whose first field is a successor `Session`.
  The successor has a NEW session id, because rewind forks the session (`fork_title`).
- `Session.rewind_info(message_id)` lists file snapshots. We use no files, so `restore` and `delete` stay empty.
- Message ids are on the message objects in `droid_sdk/_high_level/messages.py` (the classes with `message_id: str`, around line 228).
  Find which streamed message gives the id of the user prompt that starts a turn.

Unknowns to settle first with a small probe script (put it in `scripts/` or a scratch folder, not in the app):

1. Does `rewind(message_id)` keep everything before that message, or everything up to and including it?
   We need the session as it was before the refused turn's prompt.
2. Which message id do you pass: the user prompt of the bad turn, or the last assistant message of the turn before it?
3. Can you rewind a session that is resumed with `Session.resume(...)`, or only one that is still open from the same process?
4. Probe: turn 1 says a codeword ("remember PELICAN"). Turn 2 asks for a different codeword. Rewind to before turn 2. Turn 3 asks for both codewords. Expected: it knows PELICAN and not the second one.
   Use Haiku 5.5 (`DROID_MODEL=claude-haiku-5-5`) to keep credits low.

Then build it:

1. In `droid_backend.py`, record the message id that starts each turn, and return it in the meta (for example `turn_message_id`).
2. Add a way to ask for a rewind before the turn. One option: `run_droid(..., rewind_to=<message id>)`, passed from `runner.py` (`_attempt` and `run_agent`) as an optional argument that every other backend ignores.
   When `rewind_to` is set and the session can be resumed: open it, rewind, close the old one, and run the turn on the successor.
3. The meta must say what happened: `rewound: true`, the old session id, the rewound-to message id, and the successor's id as `session_id`.
   `_remember` in `jobs.py` saves `session_id` from the meta, so the store then points at the successor. Check that this is so.
4. If the rewind fails, do not fail the job.
   Run the retry in the same session as today, and put the reason in the meta (`rewind_error`), the same way `resume_error` works.
   The audit and the demo must show honestly whether the rewind happened.
5. In `jobs.py`, on a refusal, pass the refused run's `turn_message_id` as `rewind_to` for the retry.
   Keep `previous_refusal` in the retry input: the agent forgets its bad answer but still learns why it was refused.
   Read `turn_message_id` from the run's last successful attempt, the same way `_remember` reads `session_id`.
6. The Anthropic, scripted, and replay backends do not change.
   Check that the Anthropic backend's transcript does not hold the refused answer either (`_remember` is not called before the retry, so it should not). Write down what you find.
7. Update the module docstring of `droid_backend.py`, and mark each claim `[verified: ...]` or `[inferred]`, as the rest of that docstring does.

Tests:

- Extend `backend/tests/test_mapper_retry.py`: on a refusal, the retry is called with `rewind_to` equal to the first run's `turn_message_id`, and the saved session id is the successor's.
- A unit test in `test_droid_meta.py` (or a new file) with a fake session: a rewind that raises falls back to the same session and sets `rewind_error`.
- Run all of `backend/.venv/bin/python -m pytest` in `backend/`. Fix any failure or flaky test you see, even outside this task.

Live check (required before we say it in the pitch):

- Run one deal on `AGENT_BACKEND=droid` with a forced refusal (the trick in `_mapper_that_copies_a_platform_id` in the retry test, or a debug flag).
- Then show in Factory's session record (`~/.factory/sessions/<cwd>/<session id>.jsonl`) that the successor session does not hold the refused answer.
- Write the session ids and the result in the commit message, and send them to Cayden.

Done when: the tests pass, the live check passes, and Cayden has the session ids.

### Task B: permission handler spike (time box: 30 minutes, no app code)

Question: can Droid's permission system act as the gateway's front door, with every allow and deny written to our audit log?

What we know [verified from the SDK source]:

- `PermissionHandler` and `QuestionHandler` exist (`droid_sdk/_high_level/interactions.py`, around line 290), and the high-level `Session` sets one through `InteractionHandlers(on_permission=...)`.
- Our sessions use `Autonomy.HIGH`, which the SDK describes as "Allow all commands without prompts". So the handler probably never runs today. [inferred]
- `restrict_tools` already allows each role only its own tools, so the Mapper cannot see the math tools at all.

Run a scratch script (not in the app) and answer each question with evidence:

1. With `Autonomy.HIGH`, does the handler run for a call to one of our MCP tools?
2. With a lower autonomy (`Off`, then `Low`), does the handler run for our MCP tools? What is in the `PermissionRequest` (tool name, arguments)?
3. If the handler denies a call, what does the model see, and does the turn still finish with a typed result?
4. For a tool that is NOT in `restrict_tools`, does the handler ever see the call, or is the tool just invisible to the model?
5. Does the handler still run on a session reopened with `Session.resume`?

Write the answers in this file under a "Permission spike result" heading, with the script path.
If the answers to 2 and 3 are yes, propose (do not build) how each request becomes an audit row through the gateway.
If not, say so plainly, and we drop the "every tool call goes through Droid's permission system" line from the pitch.

### Permission spike result

Script: `scripts/droid_permission_spike.py` (run with `DROID_MODEL=claude-haiku-5-5`, droid CLI v0.249.0, `droid_sdk` 0.5.0).
It opens a session in an empty temp folder with an in-process MCP server `spike` that has two fake tools.
`lookup_rate` is allowed by `restrict_tools` (the same three name forms as `droid_backend.py`), and `hidden_rate` is on the server but not allowed.
The handler prints every `PermissionRequest` and answers `proceed_once`, or `cancel` in the deny case.
Six runs, one turn each: high, off, low, deny, hidden, resume.

1. With `Autonomy.HIGH`, the handler never runs. The model called `spike___lookup_rate`, our tool function ran, and the handler was called 0 times. [verified: run on 2026-10-24]
   So in our backend today the handler would be dead code.
2. With `Autonomy.OFF` and with `Autonomy.LOW`, the handler runs once per call to our MCP tool, before the tool function runs. [verified: run on 2026-10-24]
   The request holds one `McpToolAction` with `tool_name='spike___lookup_rate'`, `server_name='spike'`, `actual_tool_name='lookup_rate'`, `impact_level='high'`, and `tool_use`, which carries the tool call id and the full arguments (`{'code': 'SOFR'}`).
   The options offered were `proceed_once`, `proceed_always`, `proceed_always_tools`, `proceed_always_server`, and `cancel`. `associated_session_ids` was empty.
   The built-in `ToolSearch` call the model makes to load our deferred tool did not reach the handler. [verified: run on 2026-10-24]
   Because Droid rates every MCP tool `impact_level='high'`, `Autonomy.MEDIUM` probably asks too. [inferred]
3. When the handler denies (`cancel`), our tool function does not run, and the model sees a tool result `Error: Tool execution cancelled by user` with `is_error=True`. [verified: run on 2026-10-24]
   The comment we passed with the deny did not appear in that tool result. [verified: run on 2026-10-24]
   The turn does not finish with a typed result: it stops right after the cancel, and the result is `success=False` with `Structured output failed local validation`. [verified: run on 2026-10-24]
   So a deny ends the turn. It cannot tell the model "not that, try something else". `cancel` is the only deny option offered.
4. A tool that is NOT in `restrict_tools` is invisible to the model, and the handler never sees it. The model's `ToolSearch` for `hidden_rate` returned `Error: Tool(s) not found`, the model reported it could see only `ToolSearch` and `spike___lookup_rate`, and the handler was called 0 times. [verified: run on 2026-10-24]
5. On a session reopened with `Session.resume(..., interactions=handlers)`, the handler still runs, and the resumed session keeps `Autonomy.OFF`. [verified: run on 2026-10-24]
   `Session.resume` takes its own `interactions` argument, so every resume must pass the handler again.
   If the handler is missing or raises, the SDK reports an error and answers `cancel`, so it fails closed. [verified from the SDK source, `interaction_adapter.py` lines 254-283; not run]

Verdict: question 2 is yes, but question 3 is only half yes.
A deny is seen and blocks the call, but it ends the turn without a typed result.
Today our sessions run at `Autonomy.HIGH`, so no tool call goes through Droid's permission system.
The pitch line "every tool call goes through Droid's permission system" is false today and should be dropped.
`restrict_tools` is the real front door: a tool outside a role's list does not exist for that agent.

If we ever want it (not proposed for this weekend), here is how it could work [inferred]:
- Open sessions with `Autonomy.OFF` and an `on_permission` handler that calls the gateway.
- The gateway writes one audit row per request, with the role, session id, `tool_use.id`, tool name, arguments, and decision.
- It answers `proceed_once` only, never a `proceed_always*` option, so every call is asked.
- A deny would end the turn, and the runner's existing fallback would handle it.
- The tool's own gateway call would then link to that row by `tool_use.id`.

Pitch line we can defend: "Each agent can only see its own tools (Droid `restrict_tools`), and every call goes through our gateway, which writes the audit log." [verified: runs on 2026-10-24]

### Not in scope

- Forking Droid sessions per what-if option, and `QuestionHandler`. We decided not to build these for now.
