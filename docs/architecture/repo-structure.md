# Repository structure and conventions

## Folder map

This matches `main` on 2026-10-25.

```
Stochastic/
  README.md
  CLAUDE.md
  .env.example             Names of keys, no values (the real .env is git-ignored)
  docs/
    README.md              Index of all docs
    STOCHASTIC.md          Product reference (read first)
    TASKS.md               Who builds what
    agents.md              Agent backends, models, recordings, and demo paces
    decisions.md           Decision records
    demo-script.md         The pitch and the demo beats
    glossary.md, review.md, planning-notes.md, hyphenate-workshop.md
    architecture/          How we build it (this folder)
    design/                Screens, brand, the review companion, and UI and UX research
    devpost/               Devpost text, one-pager, images
    tasks/                 One file per person
    research/              Sourced research (deep-problems/ is archive)
    diagrams/              HTML and PDF diagrams from the first framing (stale)
    sponsors/              Sponsor and track research
  backend/                 Python, FastAPI
    pyproject.toml
    app/
      main.py              App entry: builds the store and the gateway, seeds the demo deal and the Dashboard cases
      api/                 routes.py, schemas.py, events.py (the SSE stream), export.py, certificate.py, errors.py, body_limit.py
      gateway/             gateway.py (permissions, states, audit log), whatif.py (a flag's what-ifs in a Tiger fork)
      agents/              runner.py, roles.py, jobs.py (the job runner), pace.py, demo_replay.py, recording.py, settings.py,
                           backends/ (anthropic_backend.py, droid_backend.py, scripted.py)
      tools/               finance.py (consolidation, EBITDA, debt, leverage, limit test), edits.py
      db/                  memory.py, postgres.py, forks.py, loader.py, fixtures/ (kewaunee.py, cases.py, dlh_grsi.py,
                           mamas_crown.py, sstk_envato.py)
      core/                config.py, models.py, policies.py, agreement.py, verifier.py
    recordings/            Committed agent runs that the replay backend and the demo paces play
    tests/                 pytest, one file per area, plus fixtures/kewaunee_ex101_excerpt.txt
  frontend/                Next.js, React, TypeScript, Tailwind
    src/app/               page.tsx (Dashboard), case/, mapping/, agents/, log/, review/
    src/components/        shell, sidebar, gate, launch-splash, stochastic-mark, brief-card, verification-card, flag-card,
                           process-flow, verdict-figures, combined-table, mappings, review-mapping, workbook, your-edits,
                           companion, upload-modal, source, audit-log, toasts, icons, ui, agent-house/
    src/lib/               api.ts, types.ts, deal-context.tsx, edit-context.tsx, edits.ts, conversation.ts, workbook.ts,
                           format.ts, desktop.ts, __tests__/
    public/                agents/ (the Blender characters as .glb), v3/ (the page characters and brand art)
  desktop/                 Electron shell: main.js, preload.js, splash.html, assets/ (icon, fonts)
  e2e/                     Playwright specs for the browser and the Mac app
  art/blender/             The agent models (.blend), build_agents.py, exported .glb in source/
  evals/                   answer_key.csv, score_mapper.py, mapper_trials.py, notes
  data/                    Cached public filings (git-ignored); data/brief/ (the agreement extract and quotes) is tracked
  scripts/                 record_run.py, fetch_filings.py, load_lines.py, run_unseen_deal.py, demo.sh, Droid probes
```

The frontend follows Figma Hi-fi v3: `/` is the Dashboard and `/case` the Case (`frontend/README.md`).

## Where code goes

- Agent code goes in `backend/app/agents/`: a role in `roles.py`, a backend in `backends/`, the job runner in `jobs.py`.
- Math tools go in `backend/app/tools/`.
- Pydantic models go in `backend/app/core/models.py`.
- Routes go in `backend/app/api/routes.py`.
- Fixtures and seeded cases go in `backend/app/db/fixtures/`.
- Python packages go in `backend/pyproject.toml`.

## Conventions

- **Thin routes.** Routes validate input and call the gateway.
  They hold no business rules.
- **One writer.** Only `backend/app/gateway/` writes to the store.
  Agents, the runner, and routes call it.
- **Pure tools.** A tool is a function with typed inputs and outputs and no side effects.
- **Stateful agents.** Each role keeps a session in the store, and the Mapper applies the policies the gateway wrote from the controller's answers.
  An agent still calls tools only through the gateway and does not talk to other agents.
- **Typed contracts.** Pydantic models define source lines, mappings, results, work items, and audit rows.
  The frontend types follow the same shapes.
- **Fixtures.** Fixture data lives in `backend/app/db/fixtures/`.
  The demo deal and the seeded Dashboard cases are built from it.
- **No secrets in git.** Keys live in `.env`.
  `.env.example` lists the names.
- **Tests for the trust rules.** Tests in `backend/tests/` stay green, `test_trust_rules.py` first.
  They cover: the model never writes a number, an agent cannot approve its own item, a denied action is logged, and the tie-out check.

## Naming

- Python: `snake_case` for files and functions, `PascalCase` for classes.
- TypeScript: `PascalCase` for components, `camelCase` for functions, `kebab-case` for route folders.
- Work-item types are `snake_case`.
  States are `UPPER_CASE`, as in `agents-and-work-items.md`.

## Docs

- Each code folder has a `README.md` that says what the folder holds.
- A decision that changes the design goes in `docs/STOCHASTIC.md` first, and then in the matching architecture file.
