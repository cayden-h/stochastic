# evals

Home of the answer key and the scoring. Owner: Eric.

## Contents

- `fixture_check.md`: every fixture figure checked against the filings.
- `answer_key.csv`: each Nu Aire detail line and its Kewaunee line, from Note 2 of the pro forma filing (8-K/A Ex 99.2).
- `score_mapper.py`: runs the deal in-process and scores the Mapper's mappings against the key.
- The deal-math tests with the real figures live in `backend/tests/test_trust_rules.py` (tie-out, naive versus covenant leverage).

## The answer key is preliminary and matches in shape only

The filing calls its own reclassification review preliminary and says the final one "could be materially different" (Ex 99.2 Note 2, verified).
Note 2 maps Nu Aire's balance sheet at 2024-10-31 and its statement of operations for periods ending 2024-04-30 and 2024-10-31 (verified).
The fixture uses Nu Aire's audited year ended 2024-09-30 (Ex 99.1), so the key says which Kewaunee line each Nu Aire line goes to, not the amounts.

Columns: `target_line` and `platform_line` use the exact fixture names in `backend/app/db/fixtures/kewaunee.py`, then `section`, `basis`, `note2_wording`, `source_ref`, `comment`.
Total and subtotal rows are left out.
The `basis` column says how firm each answer is:
- `note2` (23 rows): Note 2 maps the line directly (verified).
- `note2_total` (10 rows): Note 2 maps only the total, and the fixture carries the parts, so each part goes to the line the total goes to (inferred). These are the six gross PP&E lines and accumulated depreciation (Note 2 maps net PP&E only) and the three operating expense lines (Note 2 maps Total Operating Expense only).
- `none` (4 rows): Note 2 does not cover the line, so `platform_line` is blank and `comment` says why. These are Certificates of Deposit, Noncompete Agreement, Net, Reserve for Uncertain Tax Positions, and the cash flow line Depreciation and Amortization.

Three Note 2 footnotes move only part of a line: (b) $77K of Accounts Payable and (d) $0.2 million of Accrued Compensation move to other lines, and (e) $0.6 million of Other Accrued Expenses moves to Deferred revenue (verified).
The key gives each line its main home and notes the partial move in `comment`.
In the filed table the Deferred revenue row cites footnote (c), but the amounts only add up if it is (e) (inferred).

## Score

Run on 2026-10-24 with the scripted backend:

```
backend/.venv/bin/python evals/score_mapper.py --backend scripted
```

- `note2` rows: 23 of 23 agree.
- `note2_total` rows: 10 of 10 agree.
- All scored rows: 33 of 33 agree, no disagreements, no lines missing from either side.
- Not scored (`none` rows), the Mapper's answers: Certificates of Deposit to Cash and cash equivalents (0.50, flagged), Noncompete Agreement, Net to Other assets (0.60), Reserve for Uncertain Tax Positions to Other non-current liabilities (0.70), Depreciation and Amortization to Depreciation (0.95).

The scripted backend's synonym table was written with Note 2 at hand, so this score shows the key and the scripted Mapper agree; it is not independent evidence of model quality (inferred).
The score that matters is a model backend (`--backend anthropic` or `--backend droid`), which has not been run against the key yet.
The Mapper is scored on what it proposed before any human answer; the default flag answers changed no mappings in this run.
