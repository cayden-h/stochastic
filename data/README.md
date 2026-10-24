# data

Cached public filings go here, such as the Kewaunee and Nu Aire filings, and the two input CSV files built from them.
The folder contents are git-ignored. Only this file is tracked.

Rules:
- Cache everything before the demo. The demo makes no live SEC calls.
- Send a real contact email in the SEC User-Agent. Do not exceed 10 requests per second.
- The SEC redistribution wording is unresolved, so do not publish the cached files.

## CSV columns for POST /deals

Upload one UTF-8 CSV per company, each with a header row, at most 2,000 data rows and 2 MB.
`line` is the statement line name, 1 to 200 characters.
`section` is one of `income_statement`, `balance_sheet`, or `cash_flow`.
`period` is the period label, 1 to 64 characters.
`amount` is a number; commas are allowed and parentheses mean negative, so `(1,234)` is -1234.
`unit` is `USD thousands`, `USD`, or `USD millions` (see `finance.to_thousands` for the accepted spellings).
`source_ref` is where the figure comes from, up to 500 characters, and may be empty.
`is_total` is `true`, `false`, `1`, `0`, `yes`, or `no`; empty means false, and subtotals must be marked true.
An optional `covenant_tag` column pre-tags a line as `debt`, `not_debt`, `unclear`, or `na` (the default).
Extra columns are ignored.
A bad file is rejected with a message naming the file, row, and column, and nothing is loaded.

Example:

```
line,section,period,amount,unit,source_ref,is_total
Net sales,income_statement,FY2025,"10,000",USD thousands,10-K p5,false
Net income,income_statement,FY2025,900,USD thousands,10-K p5,false
Long-term debt,balance_sheet,FY2025,"3,000",USD thousands,10-K p7,false
```
