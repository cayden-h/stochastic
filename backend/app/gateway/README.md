# gateway

The only writer.
It checks the actor, the permission, the state change, the run ids, and the quotes.
It writes one audit row in the same transaction as each change.
See `docs/architecture/gateway-and-api.md` and `docs/architecture/agents-and-work-items.md`.
