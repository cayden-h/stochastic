# gateway

The only writer.
It checks the actor, the per-role permission, the state change, maker-checker, the Reviewer verdict before approval, and the run id behind every number.
It runs the math tools (`run_tool`) and records a `ToolRun` for each call.
It writes one audit row for every action and every denied attempt, chained by SHA-256.
It runs the Brief verifier on a draft Brief and records the controller's Brief approval.
It records the controller's edits and their reasons, and re-runs the tools on the edited books.
When the Mapper raises a covenant flag on the Postgres store, `whatif.py` writes each option's what-if into a Tiger fork, never into the live record.
It writes the agents' memory: a `Policy` for every flag the controller answers (and a mapping policy for a remap whose reason the controller asks it to remember), and the per-role `AgentSession`.
See `docs/architecture/gateway-and-api.md` and `docs/architecture/agents-and-work-items.md`.
