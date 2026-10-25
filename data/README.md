# data

Cached public filings go here, such as the Kewaunee and Nu Aire filings, and the two input CSV files built from them.
The folder contents are git-ignored, except this file and `data/brief/`.
`data/brief/` holds the demo's agreement extract (`kewaunee_ex101_extract.txt`, the passages of the PNC agreement, Ex 10.1, that the demo run starts from) and `kewaunee_quotes.json` (the quote for each field of the demo Brief, which the scripted Brief Reader returns).

Rules:
- Cache everything before the demo.
  The demo makes no live SEC calls.
- Send a real contact email in the SEC User-Agent.
  Do not exceed 10 requests per second.
- The SEC redistribution wording is unresolved, so do not publish the cached files.

## The Dashboard's seeded cases

The four cases besides the live demo deal are built from cached filings the same way as the Kewaunee fixture (`backend/app/db/fixtures/cases.py`).
Only the extracted line values, the Brief, and the source references are committed, in each fixture module; each module's header lists the EDGAR URL of every filing it read.

| Fixture | Deal | Raw cache (local only) |
| --- | --- | --- |
| `backend/app/db/fixtures/dlh_grsi.py` | DLH Holdings acquires GRSi, 2022-12-08 | `data/raw/dlh_grsi/` |
| `backend/app/db/fixtures/mamas_crown.py` | Mama's Creations acquires Crown I, 2025-09-02 | `data/raw/mamas_crown/` |
| `backend/app/db/fixtures/sstk_envato.py` | Shutterstock acquires Envato, 2024-07-22 | `data/raw/sstk_envato/` |
| `backend/app/db/fixtures/cases.py` (`d_dlh_craigs`) | Sample: DLH's next add-on, the QuickBooks Online sample company | `scripts/samples/qbo/` (committed) |

The seeded cases also hold four reasoned controller edits, each citing its source in the reason: two on DLH and GRSi (Ex 99.3 note 3b, Ex 99.2 Note 1) and two on the sample (the QuickBooks account list in `scripts/samples/qbo/account_list.xlsx`); see `docs/architecture/gateway-and-api.md`, "Seeded cases".
Values the filings do not give are marked inferred in the fixtures, and each fixture's `test_period_note` says what the Brief schema could not hold (step-downs, cash netting, a second covenant).
The raw files were fetched with the `SEC_USER_AGENT` from `.env` on 2026-10-24 and stay out of git.

## CSV columns for POST /deals

The API parses uploads with `backend/app/db/loader.py`.
The export from `scripts/load_lines.py export` is in this format, with two extra columns (`company`, `note`) that the API ignores; `scripts/load_lines.py` is for exporting the fixture, checking the round-trip, and reading accounting-system exports, not for the API.

With the CSVs, send either `brief` (a JSON string of the Brief) or `agreement_txt`, exactly one.
`agreement_txt` is the credit agreement as a UTF-8 `.txt` file of at most 2 MB.
The Brief Reader drafts the Brief from it, and the controller enters the adjustment amounts from the books (`POST /deals/{id}/brief/amounts`), answers its flags, and approves it (`POST /deals/{id}/brief/approve`) before mapping starts.
Use a synthetic agreement or excerpts in tests; the cached filings stay out of git.

Upload one UTF-8 CSV per company, each with a header row, at most 2,000 data rows and 2 MB.
`line` is the statement line name, 1 to 200 characters.
`section` is one of `income_statement`, `balance_sheet`, or `cash_flow`.
`period` is the period label, 1 to 64 characters.
`amount` is a number; commas are allowed and parentheses mean negative, so `(1,234)` is -1234.
`unit` is `USD thousands`, `USD`, or `USD millions` (see `finance.to_thousands` for the accepted spellings).
`source_ref` is where the figure comes from, up to 500 characters, and may be empty.
`is_total` is `true`, `false`, `1`, `0`, `yes`, or `no`; empty means false, and subtotals must be marked true.
An optional `covenant_tag` column pre-tags a line as `debt`, `not_debt`, `unclear`, or `na` (the default).
The scripted Mapper re-tags every balance-sheet line by name, so a `covenant_tag` in the CSV is a hint, not a guarantee.
It tags as debt any line whose name contains "borrowings", "financing lease", "finance lease", "notes payable", "term loan", "line of credit", or "revolv".
It tags "operating lease" and "lease liability - operating" as `na` with the note that operating leases are not borrowed money, and "financing liability" as unclear (one flag).
Any other balance-sheet name, such as "Long-term debt", is tagged `na`, and the covenant debt guardrail then raises: a `"sync": true` run returns 500, and the console's background run ends at stage `run_failed` with the error.
Name borrowings with one of the recognized phrases.
The `ebitda` tool needs a net income line in `income_statement` and a D&A line in `cash_flow`, for each company.
Net income names: "net earnings", "net income", "net income (loss)", "net earnings (loss)".
D&A names: "depreciation and amortization", "depreciation", "amortization".
Extra columns are ignored.
A bad file is rejected with a message naming the file, row, and column, and nothing is loaded.

Example:

```
line,section,period,amount,unit,source_ref,is_total
Net sales,income_statement,FY2025,"10,000",USD thousands,10-K p5,false
Net income,income_statement,FY2025,900,USD thousands,10-K p5,false
Depreciation,cash_flow,FY2025,300,USD thousands,10-K p6,false
Short-term borrowings,balance_sheet,FY2025,"3,000",USD thousands,10-K p7,false
```
