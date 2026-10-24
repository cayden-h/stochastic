# agents

The three agent roles (Mapper, Preparer, Reviewer), the backends that run them, and the job runner.

| File | What it holds |
| --- | --- |
| `roles.py` | A role is a system prompt, a tool list, an input type, and an output type. |
| `runner.py` | `run_agent(role, item)`: picks the backend from `AGENT_BACKEND`, falls back along `AGENT_FALLBACK`, records model runs. |
| `jobs.py` | The job runner. Plain code. Opens the next work item through the gateway, runs the agent, hands the typed result back. |
| `backends/anthropic_backend.py` | Claude with tool use. The real model path and the stage fallback for Droid. |
| `backends/droid_backend.py` | Factory Droid Python SDK: one session per role, in-process MCP tools that call the gateway, `restrict_tools`, empty working directory. |
| `backends/scripted.py` | Deterministic logic with no model: policies, synonyms, name similarity, flags. The last-resort fallback and the reference answer. |
| `recording.py` | Save and replay agent outputs (`backend/recordings/`). |

Agents are stateful.
Each role has an `AgentSession` in the store (backend session id, turn count, a short transcript), and the Mapper reads the `Policy` rows the gateway wrote from the controller's answers.
The state lives in the store, so a crash or restart loses nothing, and a second deal starts with what the first one taught.

Agents never write to the store and never talk to each other.
They call tools through the gateway, which records a run id for every number.
