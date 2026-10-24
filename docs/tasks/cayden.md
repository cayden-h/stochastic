# Cayden: agents, gateway, demo

Branch: `cayden/agents`.
Folders: `backend/app/agents/`, `backend/app/gateway/`, `backend/app/core/`.

1. Run `list_models()` with the Factory key. Write down if Droid can run Claude models.
2. If Droid cannot run Claude models, use the Anthropic backend as the main path.
3. Write `run_agent(role, item)` with two backends, `anthropic` and `droid`. Switch with `AGENT_BACKEND`.
4. Write the Mapper, the Preparer, and the Reviewer. Give each agent a typed output.
5. Make the Preparer and the Reviewer call tools through `@tool` functions. These functions call the gateway.
6. Add work-item types to the gateway for mapping, flag, result, and approval.
7. Keep maker-checker and the audit chain. Keep the existing tests green.
8. Fix four gateway gaps. Add a reverse method. Enforce a run id on numbers. Check the Reviewer verdict before approval. Rename the default actor to the controller.
9. Publish the shared contract in `backend/app/core/models.py` first, so Eric, Tri, and Josie can build against it.
10. Write the job runner that moves work items between the agents.
11. Record one full run. Add a switch that replays it.
12. If the Droid backend fails, switch to the replay. Rehearse this switch once.
13. Write the 1:30 pitch and the 30-second demo script.
