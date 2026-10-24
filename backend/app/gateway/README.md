# gateway

The only writer.
It checks the actor, the per-role permission, the state change, maker-checker, the Reviewer verdict before approval, and the run id behind every number.
It runs the math tools (`run_tool`) and records a `ToolRun` for each call.
It writes one audit row for every action and every denied attempt, chained by SHA-256.
It writes the agents' memory: a `Policy` for every flag the controller answers, and the per-role `AgentSession`.
See `docs/architecture/gateway-and-api.md` and `docs/architecture/agents-and-work-items.md`.
