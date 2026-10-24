# db

`memory.py` is the in-memory store used by the prototype. Postgres on Tiger Cloud would replace it behind the same interface.
`fixtures/kewaunee.py` loads the demo deal from the public filings: Kewaunee's 10-Q and 10-K lines, Nu Aire's audited lines, the closing financing from the pro forma, and the brief from the PNC loan agreement.
Agent memory (`policies`, `sessions`) survives `POST /dev/reset` unless `keep_memory=false`.
The table design is in `docs/architecture/data-model.md`.
