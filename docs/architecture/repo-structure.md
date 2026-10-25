# Repository structure and conventions

## Folder map

This matches the repo on 2026-10-23.
Items marked (new) do not exist yet.

```
Stochastic/
  README.md
  CLAUDE.md
  .env.example             Names of keys, no values (the real .env is git-ignored)
  docs/
    README.md              Index of all docs
    STOCHASTIC.md          Product reference (read first)
    TASKS.md               Who builds what
    planning-notes.md      Archive from earlier framings
    hyphenate-workshop.md  Workshop blueprint and gaps
    architecture/          How we build it (this folder)
    design/                UI and UX research
    research/              Sourced research (deep-problems/ is archive)
    diagrams/              HTML and PDF diagrams from the first framing (stale)
    sponsors/              Sponsor and track research
  backend/                 Python, FastAPI
    pyproject.toml
    app/
      main.py              App entry, seeds the demo store
      api/                 routes.py (thin routes)
      gateway/             gateway.py (permissions, states, audit log)
      agents/              Agent code goes here (README only today)
      tools/               deal_math.py, quote_validator.py (the validator is from the earlier framing)
      db/                  memory.py, fixtures/demo.py
      core/                config.py, models.py
    tests/                 test_trust_rules.py
  frontend/                Next.js, React, TypeScript, Tailwind
    src/app/               page.tsx (Dashboard), case/, mapping/, agents/, log/
    src/components/        shell, sidebar, gate, flag-card, verdict-line, combined-table, mappings, upload-modal, source, audit-log, icons, ui
    src/lib/               api.ts, types.ts, deal-context.tsx, format.ts
  evals/                   README only (answer key and scoring, planned)
  data/                    Cached public filings (git-ignored, README tracked)
  scripts/                 README only (helper scripts, planned)
```

The frontend follows Figma Hi-fi v3: `/` is the Dashboard and `/case` the Case (`frontend/README.md`).

## Where new agent code goes

New code goes in `backend/app/agents/`:

```
backend/app/agents/
  run_agent.py        run_agent(role, item) and the AGENT_BACKEND switch (new)
  backends.py         The anthropic and droid backends (new)
  roles.py            Role definitions: system prompt, tools, result type (new)
  mapper.py           Mapper role (new)
  preparer.py         Preparer role (new)
  reviewer.py         Reviewer role (new)
  runner.py           The job runner (new)
  tools.py            @tool functions that call the gateway (new)
```

Other new code:

- Math tools (consolidate, EBITDA, debt, leverage, limit test) go in `backend/app/tools/`.
- New Pydantic models for source line, mapping, and result go in `backend/app/core/models.py`.
- New routes go in `backend/app/api/routes.py`.
- The Kewaunee fixture replaces the invented demo data in `backend/app/db/fixtures/`.
- Droid and Anthropic SDK packages go in `backend/pyproject.toml`.

## Conventions

- **Thin routes.** Routes validate input and call the gateway.
  They hold no business rules.
- **One writer.** Only `backend/app/gateway/` writes to the store.
  Agents, the runner, and routes call it.
- **Pure tools.** A tool is a function with typed inputs and outputs and no side effects.
- **Stateless agents.** An agent gets one work item and returns one typed result.
  It keeps no memory.
- **Typed contracts.** Pydantic models define source lines, mappings, results, work items, and audit rows.
  The frontend types follow the same shapes.
- **Fixtures.** Fixture data lives in `backend/app/db/fixtures/`.
  The prototype runs on it.
- **No secrets in git.** Keys live in `.env`.
  `.env.example` lists the names.
- **Tests for the trust rules.** Tests in `backend/tests/test_trust_rules.py` stay green.
  Add tests for: the model never writes a number, an agent cannot approve its own item, a denied action is logged, and the tie-out check.

## Naming

- Python: `snake_case` for files and functions, `PascalCase` for classes.
- TypeScript: `PascalCase` for components, `camelCase` for functions, `kebab-case` for route folders.
- Work-item types are `snake_case`.
  States are `UPPER_CASE`, as in `agents-and-work-items.md`.

## Docs

- Each code folder has a `README.md` that says what the folder holds.
  Several still describe the earlier framing and need an update.
- A decision that changes the design goes in `docs/STOCHASTIC.md` first, and then in the matching architecture file.
