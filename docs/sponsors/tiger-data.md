# Tiger Data (Cal Hacks 13.0)

## Status after the 2026-10-23 evening reframe

Stochastic is now a PE add-on integration tool.
It merges the books of a newly acquired company into the platform company's books, flags the few lines a human must decide, and checks the combined result against the lender's limit.
Three stateful agents do the work (Mapper, Preparer, Reviewer), code does all the math, and a controller approves. What the controller decides once, the agents keep.
The demo uses a real public deal: Kewaunee Scientific buying Nu Aire. [verified: `../STOCHASTIC.md` section 12]

### How Tiger Data fits now

Tiger Data is a target track since 2026-10-24 evening. [set by Cayden; `../decisions.md` D15]
The store is built on Tiger Cloud: service `stochastic`, PostgreSQL 18.6 with TimescaleDB 2.31, in us-east-1. [verified: 2026-10-24]
- With `STORE=postgres`, every gateway write reaches Postgres, and a restart loads the record, the audit log, and the agents' memory (policies and Droid session ids) back. [verified: `../../backend/tests/test_postgres_store.py`]
- The audit log is a TimescaleDB hypertable on `at`, and a trigger refuses UPDATE and DELETE on it.
- A reset starts a new ledger instead of deleting, so every earlier run stays queryable.
- The Tiger CLI (0.26.0) is installed and lists the service; the Tiger MCP is installed for Claude Code.
- Built 2026-10-24 09:00: forks that hold a covenant flag's what-ifs (`../../backend/app/gateway/whatif.py`, `../../backend/app/db/forks.py`). The gateway forks the ledger when the flag opens, writes each option's tags and computed figures into a `what_if` table in the fork, and deletes the fork when the controller answers; the live ledger keeps only the chosen option. Live: fork ready in 33 s with 3 what-ifs, deleted 1 s after the answer, three FORK rows in the audit log. Settings: `FORKS=tiger`, `TIGER_SERVICE_ID`. [verified]
- History of the spike, 2026-10-24 08:40: `tiger service fork p4a7k2ox3x --no-set-default` failed at once with "You have reached your free service limit. Delete a service or create a paid service instead." The free plan allows two services, and the account holds `stochastic` and `larp-city` (a paused HackRice database). So a fork needs either `larp-city` deleted (Cayden's call) or a paid plan, and then one fork per option would also hit the same two-service limit. Cayden chose to delete `larp-city` (backed up first to `HackRice/backups/larp-city-2026-10-24.dump`, 15 MB). A fork then took 33 to 35 s. With the main service running there is room for one fork at a time, so a second covenant flag while one fork is open gets no fork and says so. [verified]
- What the demo also shows: the restart moment (`../demo-script.md` section 5), the append-only hypertable, and the ledgers kept across resets.

### Which old notes still apply

- The notes on what Tiger Data sells, the free plan, the opt-in mechanics, and the prize text still apply.
- Notes that tie forks or vector search to plan search, Monte Carlo, what-if plans, or the clause reader describe the earlier framing.

---

- Prize at Cal Hacks 13.0: MLH prize "Best Use of Tiger Data", Stream Deck Mini
- Researched: 2026-10-15
## What they do
Tiger Data is the company formerly known as Timescale, behind TimescaleDB and "Agentic Postgres" [verified: https://www.tigerdata.com/blog/introducing-agentic-postgres-free-plan-experiment-ai-on-postgres, search snippet].
It sells managed Postgres (Tiger Cloud) with time-series, vector search, and database forks aimed at AI agents [verified: same URL].
It also ships Postgres extensions pg_textsearch (BM25 keyword ranking) and pgvectorscale (StreamingDiskANN vector index), with hybrid search via Reciprocal Rank Fusion in one SQL query [verified: tigerdata.com blog post on vector index tradeoffs].
## What they sell or ship that a hacker can touch
Tiger Cloud free plan, no credit card, no time limit as announced October 2025 [verified via search snippet: tigerdata.com blog above; current limits not confirmed].
Features named in the DEV challenge: Tiger MCP, Tiger CLI, pg_textsearch, fast zero-copy forks, Fluid Storage [verified: https://dev.to/challenges/tigerdata-2025-10-15].
The Tiger MCP ships inside the Tiger CLI and can create, fork, and resize services [verified: search result, toolradar and Tiger docs].
Signup: create a Tiger Data account at tigerdata.com and start a service [verified: DEV challenge page].
## Track brief and judging analysis

Official prize text: "The team that demonstrates the most innovative, impactful, and performance-driven use of Tiger Data." Reward: Stream Deck Mini [verified: https://www.mlh.com/events/cal-hacks-13-0/prizes].
Requirement wording at other 2026 events: use Tiger Data (a PostgreSQL extension) for real-time data, time-series metrics, or analytics [verified: https://www.mlh.com/events/vthacks-14/prizes].
Opt-in mechanics: the MLH export lists "Opt-In Prizes (any categories/tracks they submitted to)" as a required field, so you tick the category in the Devpost opt-in field [verified: https://guide.mlh.com/general-information/judging-and-submissions/hackathon-submission-portal].
The guide does not say who judges MLH categories, and no Cal Hacks 13.0 judging rubric was published [verified: same guide, plus the https://www.mlh.com/events/cal-hacks-13-0/prizes page has no rubric].
The Devpost page returned HTTP 403 to our fetcher, so Devpost-only wording was not read; the MLH event prize page was [verified: https://www.mlh.com/events/cal-hacks-13-0/prizes].
The MLH Hack Days guide has no Tiger Data page; its partner list is Gemini, Gemma, Snowflake, Cloudflare, Solana [verified: https://hackdays-guide.mlh.com/partner-details/partner-details], so there is no published judge checklist [verified by absence].
The three stated axes are innovative, impactful, performance-driven [verified: prize text], which suggests judges want measured speed or a clever use of forks or time-series, not just a Postgres connection [inferred].

What Tiger Data is pushing: Agentic Postgres launched 2025-10-21 with copy-on-write instant forks, the Tiger MCP server inside the Tiger CLI (`tiger mcp install <client>`), pg_textsearch (BM25), pgvectorscale, and a free plan with forks [verified: https://www.infoq.com/news/2025/12/agentic-postgres-fast-forking/ and https://www.tigerdata.com/blog/five-features-tiger-cli-you-arent-using-but-should via search summaries].
No 2026 feature announcement was found [verified by search, 2026-10-16].
Past judged event: the DEV Agentic Postgres Challenge winners each got $1,000 and were Simran Shaikh (four code-review agents each on its own fork), Mayuresh Smita Suresh (FraudSwarm, hybrid pg_text and pgvector), and Divya (GitResume, four agents) [verified: https://dev.to/devteam/congrats-to-the-winners-of-the-agentic-postgres-challenge-with-tiger-data-51m6].
Judges gave no criteria; the speedups quoted (4x, 23%) are self-reported [verified: same page].
No MLH Best Use of Tiger Data winner was found [verified: searches 2026-10-16].

What a winning entry looks like: forks as a core primitive (one fork per agent or per proposed change), a visible benchmark or timing, and Tiger MCP or CLI in the workflow [inferred from winners].
What loses: ordinary CRUD on a managed Postgres [inferred].

Minimum honest integration and fit: use Tiger Cloud as our session and attribution store (hypertable of line events with actor, session id, timestamp), and run each agent's proposed edit set against a fork of the attribution DB that is merged or dropped on human approval. Effort 4 to 6 hours for the store, plus 2 hours for the fork demo [inferred].
Honesty check: forks are database forks, not code forks, so say that clearly; the fit is attribution history and what-if queries, not replacing Git [inferred].
Worth doing only if Postgres is our real store; otherwise skip.

## Past hackathon winners using them
All from the DEV Agentic Postgres Challenge (Oct 22 to Nov 9, 2025) [verified: https://dev.to/devteam/congrats-to-the-winners-of-the-agentic-postgres-challenge-with-tiger-data-51m6]:
- Multi-agent code review by Simran Shaikh: four agents in parallel, each in its own zero-copy fork; claims 40-60s down to 10-15s (self-reported). https://dev.to/simranshaikh20_50/i-built-a-multi-agent-code-review-system-thats-4x-faster-thanks-to-zero-copy-database-forks-3bd5
- FraudSwarn: five-agent real-time fraud detection with hybrid text and vector search; claims 23% better accuracy (self-reported). https://dev.to/mayu2008/fraudswarn-multi-agent-fraud-detection-13ge
- GitResume: turns GitHub repos into career insights with four agents. https://dev.to/divyasinghdev/your-github-speaks-louder-than-your-resume-a-tiger-cloud-story-3o3
## Idea seeds
- Fork-per-agent ledger: every agent action runs in a zero-copy Postgres fork, and a human approval merges or discards it, with per-action attribution rows (fits our direction, forks are a natural "approve before commit" primitive).
- Git plus Postgres bridge: index repo commits and agent actions in Postgres with hybrid search for "who did this and why".
- Finance agent: parallel fraud or budget scenario agents on forks of a ledger database, human picks the winner.
- Time-series of agent activity with hypertables for anomaly detection on agent behavior.
- MCP-driven agent that provisions its own scratch database via Tiger MCP, then reports back for approval.
## Risks and open questions
Forks and MCP are the differentiators; a plain Postgres app will not stand out.
Free plan limits (fork count, storage) not confirmed; check before demo.
Previous winners already did fork-parallel code review and fraud detection, so avoid those exact ideas.
## Sources
- https://www.tigerdata.com/blog/introducing-agentic-postgres-free-plan-experiment-ai-on-postgres
- https://dev.to/challenges/tigerdata-2025-10-15
- https://dev.to/devteam/congrats-to-the-winners-of-the-agentic-postgres-challenge-with-tiger-data-51m6
- https://www.mlh.com/events/cal-hacks-13-0/prizes
- https://www.mlh.com/events/vthacks-14/prizes
- https://www.infoq.com/news/2025/12/agentic-postgres-fast-forking/
- https://www.tigerdata.com/blog/five-features-tiger-cli-you-arent-using-but-should
