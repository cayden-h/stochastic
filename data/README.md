# data

Cached public filings go here, such as the Kewaunee and Nu Aire filings, and the two input CSV files built from them.
The folder contents are git-ignored. Only this file is tracked.

Rules:
- Cache everything before the demo. The demo makes no live SEC calls.
- Send a real contact email in the SEC User-Agent. Do not exceed 10 requests per second.
- The SEC redistribution wording is unresolved, so do not publish the cached files.

## CSV columns for POST /deals

The API parses uploads with `backend/app/db/loader.py`. The export from `scripts/load_lines.py export` is in this format, with two extra columns (`company`, `note`) that the API ignores; `scripts/load_lines.py` is for exporting the fixture, checking the round-trip, and reading accounting-system exports, not for the API.

With the CSVs, send either `brief` (a JSON string of the Brief) or `agreement_txt`, exactly one. `agreement_txt` is the credit agreement as a UTF-8 `.txt` file of at most 2 MB; the Brief Reader drafts the Brief from it, the controller enters the adjustment amounts from the books (`POST /deals/{id}/brief/amounts`), answers its flags, and approves it (`POST /deals/{id}/brief/approve`) before mapping starts. Use a synthetic agreement or excerpts in tests; the cached filings stay out of git.

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
It tags "operating lease" and "lease liability - operating" as not debt, and "financing liability" as unclear (one flag).
Any other balance-sheet name, such as "Long-term debt", is tagged `na`, and the covenant debt guardrail then raises and `POST /deals/{id}/run` returns 500.
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
