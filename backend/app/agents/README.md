# agents

The four agent roles (Brief Reader, Mapper, Preparer, Reviewer), the backends that run them, and the job runner.

| File | What it holds |
| --- | --- |
| `roles.py` | A role is a system prompt, a tool list, an input type, and an output type. |
| `runner.py` | `run_agent(role, item)`: picks the backend from `AGENT_BACKEND`, falls back along `AGENT_FALLBACK`, records model runs to `backend/recordings/latest/`. |
| `settings.py` | The model per role from the environment (default Claude Haiku 5.5) and the reasoning effort. |
| `jobs.py` | The job runner. Plain code. Opens the next work item through the gateway, runs the agent, hands the typed result back. |
| `backends/anthropic_backend.py` | Claude with tool use. The real model path and the stage fallback for Droid. |
| `backends/droid_backend.py` | Factory Droid Python SDK: one session per role, in-process MCP tools that call the gateway, `restrict_tools`, empty working directory. |
| `backends/scripted.py` | Deterministic logic with no model: policies, synonyms, name similarity, flags. The last-resort fallback and the reference answer. |
| `recording.py` | Save and replay agent outputs (`backend/recordings/`); plain `AGENT_BACKEND=replay` reads the pinned Sonnet 5.5 run in `backend/recordings/<role>.json`, the demo paces read `haiku-5-5-run3/`, and a folder's `recording.json` says which model made it, where, and when. |
| `demo_replay.py` | The backend of the `demo` and `factory` paces: the recorded Claude Haiku 5.5 run when the deal's lines are the recorded ones and no earlier memory covers it, with the line ids translated; else the scripted rules, with the reason. |
| `pace.py` | The waits of a paced run: the `human`, `demo`, and `factory` profiles. |

Agents are stateful.
Each role has an `AgentSession` in the store (backend session id, turn count, a short transcript), and the Mapper reads the `Policy` rows the gateway wrote from the controller's answers.
The state lives in the store, so a crash or restart loses nothing, and a second deal starts with what the first one taught.

Agents never write to the store and never talk to each other.
They call tools through the gateway, which records a run id for every number.
