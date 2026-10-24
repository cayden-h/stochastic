# evals

Home of the answer key and the scoring. Owner: Eric.

Planned contents (see `docs/STOCHASTIC.md` and `docs/TASKS.md`):
- Answer key: each Nu Aire line and its Kewaunee line, from Note 2 of the pro forma filing (Ex 99.2). It is preliminary and aligned in shape only, not to the dollar.
- A mapping score: run the Mapper (`POST /deals/{id}/run`), read `GET /deals/{id}/mappings`, and count agreements with the key.
- The deal-math tests with the real figures live in `backend/tests/test_trust_rules.py` (tie-out, naive versus covenant leverage).
