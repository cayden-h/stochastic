# backend

Planned home of the gateway, the agents, the code tools, and the database layer.
No code yet. Project code starts after hacking opens on Friday Oct 23, about 6pm.

Planned parts (see `docs/STOCHASTIC.md`, sections 6 to 11):
- Gateway: the only writer. It enforces permissions, work-item states, and the audit log.
- Agents: deal manager, intake, clause reader, structuring, risk, and memo and approvals.
- Tools: deal math, plan search, seeded Monte Carlo, quote validator, and cached public data.
- Database: Postgres schema, migrations, and forks.
