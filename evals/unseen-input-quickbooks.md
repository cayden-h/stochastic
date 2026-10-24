# Unseen input: the QuickBooks sample company on live Droid

Run on 2026-10-24 evening, after the gateway guards (commit 0e3829f), with `scripts/run_unseen_deal.py`.
Kewaunee is the platform with the demo deal's brief and the PNC limit.
The target is the QuickBooks Online test-drive company (Craig's Design and Landscaping Services), from the real exports in `scripts/samples/qbo/`.
No agent had seen these line names before. [verified: run output below]
The figures are not a real deal: the point is that the agents and the gateway handle an input nobody prepared.

## Result

| | Scripted backend | Live Droid (Mapper Sonnet 5.5, Preparer and Reviewer Haiku 5.5) |
| --- | --- | --- |
| Questions raised | 40 (one per unknown line name) | 2: the covenant question and one mapping question (Notes Payable) |
| Lines mapped | 53 | 53, 10 below 0.80 confidence |
| Outcome | Stops: the Preparer refuses "Loan Payable" tagged na, a borrowing-like name the rules do not know | 1.03x against 2.50x, Reviewer pass, ready for approval |
| Time | under 1 s | 47 s to the questions, 29 s after the answers |
| Gateway refusals | 0 | 0 |
| Factory credits | 0 | 58,129 |

[verified: run output, 2026-10-24]

## What the model did that the rules could not

- It mapped QuickBooks names such as "Checking", "Undeposited Funds", "Truck:Original Cost" and "Mastercard" to Kewaunee's lines with reasons.
- It tagged "Loan Payable" as debt and mapped it to Short-term borrowings, so the covenant figure counts it.
- It asked about "Notes Payable" ($25K of unknown lender) instead of guessing between the financing liability and other non-current liabilities.
- Its covenant question kept the agreement's exclusions as the controller's call; the as-filed whole-line reading showed 3.99x, over the limit.

## Limits

- The sample company books no depreciation, so the script adds a zero D&A line and says so.
- One run, not a trial: model output varies between runs (see `README.md` in this folder for the Mapper trials on the demo deal).
