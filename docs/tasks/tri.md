# Tri: math tools, tests, API

Branch: `tri/tools`.
Folders: `backend/app/tools/`, `backend/app/api/`, `backend/app/db/`, `backend/tests/`.

1. Get the missing figures. Take Kewaunee D&A from the 10-K cash flow statement. Take the revolver draw at close from the 10-Q or the 8-K.
2. Compute leverage two ways: a naive way that adds all of the financing liability, and the covenant way. Write down both with sources. Do this first.
3. If both ratios are under 2.50x, tell the team at once. Then choose a different flag.
4. Build the tools in `backend/app/tools/`. They must consolidate two sets of lines, compute EBITDA with the covenant add-backs, compute Senior Funded Bank Debt, compute leverage, and test leverage against the limit.
5. Give every tool output a run id.
6. Write tests with the real figures. Include a tie-out test and a test that the naive and covenant answers differ.
7. Make sure that the existing trust-rule tests stay green.
8. Replace the Northwind fixture with the Kewaunee case in `backend/app/db/fixtures/`.
9. Write the API routes that the console needs. Follow the shared contract. Keep routes thin.
10. If the team agrees on a video, cut it. Hyphenate wants a video that opens with the moment.
