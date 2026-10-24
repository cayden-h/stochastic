# agents

One module per agent: Mapper, Preparer, and Reviewer.
Each agent is stateless. It receives one work item and returns one typed result.
Agents call tools through the gateway client and never write to the store.
They run through `run_agent(role, item)`, as set out in `docs/STOCHASTIC.md`.
See `docs/architecture/agents-and-work-items.md` for each contract.
