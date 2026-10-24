# Glossary

Last updated: 2026-10-23.
This glossary is for teammates and judges who are not finance experts.
Terms are in alphabetical order.
Each entry has a short definition and an "In Stochastic:" line.
Where we can, we give an example from the Kewaunee Scientific and Nu Aire deal.
All deal facts come from `research/real-deal-candidates.md`, `research/post-close-deliverables.md`, and `STOCHASTIC.md`.

## How to read the tags

- [verified: filing] means the fact is in a public filing that the research files cite.
- [verified: source file] means a file in this repo states it, but it is not a filing.
- [our usage] means the term describes how we use or design something in Stochastic. It is not an industry standard.
- [inferred] means it is our judgment.
- Numbers from vendors or authors are labeled self-reported.

We do not invent figures.
If a figure is not in the research files, it is not here.

---

## Acquisition basket

A basket is a dollar allowance in a credit agreement.
An acquisition basket says how large an acquisition can be without the lender's consent.
Above the basket, the borrower usually needs consent or must meet extra conditions.

In Stochastic: the brief names the basket, and the Reviewer can compare a deal to it. [our usage]

Example: the Kewaunee credit agreement allows an acquisition if "each such Acquisition does not exceed $5,000,000" (Ex 10.1, Section 5.8(ii)). [verified: filing]
The basket also requires pro forma compliance with the Section 4.8 financial covenants. [verified: filing]
The Nu Aire purchase itself ($55M, the "Closing Date Acquisition") is carved out of the basket. [verified: filing]
So the basket matters for the next add-on, not for Nu Aire.

## Add-back

An add-back is an item that the credit agreement lets you add to EBITDA.
Examples are one-time costs and non-cash charges.
Add-backs are often capped.
Each deal defines its own list. [verified: source file, `ma-workflow-research.md`]

In Stochastic: the EBITDA tool adds back only what the covenant definition allows, and it shows each add-back. [our usage]

Example: the Kewaunee EBITDA definition adds back transaction costs (up to $4,000,000), integration costs (up to $1,000,000), stock compensation, and a noncash pension termination expense. [verified: filing, Ex 10.1]
It also adds Nu Aire's pro forma EBITDA for the four quarters ended 2024-10-31. [verified: filing]

## Add-on acquisition

An add-on is a smaller company bought to join a company the buyer already owns.
The buyer is the platform company.
The new company is the target. See "Platform company versus target".

In Stochastic: one add-on deal is the whole scope of the product. [verified: source file, `STOCHASTIC.md` section 3]
We cover the steps from two data files to the controller's approval.

Example: Nu Aire is an add-on to Kewaunee. It closed on 2024-11-01 for $55M. [verified: filing]

## Audit log (hash chain)

An audit log is a record of every action in a system.
A hash chain makes the log hard to change in secret.
Each row stores a fingerprint (a hash) of the row before it.
If someone edits an old row, the later fingerprints no longer match.

In Stochastic: the gateway writes one row for every action, including denied ones. Each row is chained to the previous row. [verified: source file, `STOCHASTIC.md` section 9]
The demo shows the log as a small link. A denied row is shown only if a judge asks.

## Brief and Brief Reader

The brief holds the lender's terms that the math needs: the limit, its wording, the defined debt term and what it excludes, and the EBITDA add-backs and deductions with their caps.
Each term names the section of the credit agreement it comes from.

In Stochastic: a person writes the brief today, and the PNC brief is the only one. [verified: `backend/app/db/fixtures/kewaunee.py`]
The Brief Reader is a planned fourth agent that drafts the brief from the agreement, with a verbatim quote for every field. Code checks each quote, and the controller approves the brief before mapping starts. [verified: `decisions.md` D20; not built]

Example: PNC's limit is "less than 2.50 to 1.00" in Section 4.8(a) of Ex 10.1. [verified: filing]
The amounts of the add-backs, such as the $4,019K pension charge, come from the 10-K, not the agreement. [verified: source file]

## Buy-and-build (roll-up)

Buy-and-build is a private equity plan.
The firm buys one platform company, then keeps buying add-ons and merges them into it.
A roll-up is the same idea, often in a fragmented industry.

In Stochastic: these firms are our target customer, because each new add-on needs the books combined again. [verified: source file, `STOCHASTIC.md` section 1]
Kewaunee buying Nu Aire is one add-on step in the same pattern, but Kewaunee is a public company and not a PE roll-up. [inferred]

## Chart of accounts

The chart of accounts (COA) is the numbered list of accounts a company uses to record money.
Examples are "Service Revenue" and "Freight-in".
Two companies almost always have different charts.

In Stochastic: the Mapper matches the target's lines to the platform's chart. [our usage]
The public demo works on statement lines, not on accounts, because filings do not publish accounts. [verified: source file, `real-deal-candidates.md`]

## Combined (consolidated) trial balance

This is the trial balance of the platform and the target added together, after intercompany amounts are removed.
It is the base for the lender's compliance pack.
Each combined line must equal the platform line plus the target lines mapped to it.

In Stochastic: code builds the combined table with columns platform, target, and combined. A tie-out check runs on it. [verified: source file, `STOCHASTIC.md` sections 11 and 12]
Because the demo uses statement lines, our table is a combined statement table of about ten rows. It is not a full trial balance. [our usage]

## Compliance certificate

A compliance certificate is a signed statement to the lender.
An officer states that the company meets the covenants, and shows the calculation.
Credit agreements set when it is due.
The samples found put it 45 to 60 days after quarter end. [verified: snippets, terms vary per deal; Aleph figure is self-reported]

In Stochastic: a downloadable draft certificate is a "should" item, not a "must". [verified: source file, `STOCHASTIC.md` section 13]
A human officer would sign it. We never call our output advice.

Example: the Kewaunee credit agreement requires an acquisition compliance certificate that shows pro forma covenant compliance. [verified: filing, Ex 10.1]

## Covenant

A covenant is a promise a borrower makes to a lender.
A financial covenant sets a limit, such as a maximum debt-to-EBITDA ratio.
The lender tests it on a schedule, often every quarter.

In Stochastic: the verdict line shows combined leverage next to the covenant limit. [verified: source file, `STOCHASTIC.md` section 12]

Example: Kewaunee's Section 4.8(a) requires "Senior Funded Bank Debt to EBITDA of less than 2.50 to 1.00". [verified: filing, Ex 10.1]
Section 4.8(b) requires a fixed charge coverage ratio of at least 1.20 to 1. [verified: filing]

## Credit agreement

A credit agreement is the contract between a borrower and its lenders.
It sets the loan terms, the covenants, the definitions, and what the borrower must report.
Definitions in it, such as EBITDA, are negotiated for each deal.

In Stochastic: the short brief carries the limit and the covenant's own definitions of debt and EBITDA. Code uses those definitions, not generic ones. [verified: source file, `STOCHASTIC.md` sections 10 and 11]

Example: Kewaunee's lender is PNC. The loan agreement is dated 2024-11-01 and is Ex 10.1 to the original 8-K. [verified: filing]
It is a bilateral loan agreement, so it is simpler than a typical sponsor-backed agreement. [verified: source file]

## D&A (depreciation and amortization)

D&A is a non-cash cost that spreads the price of long-lived assets over their life.
Depreciation covers physical assets. Amortization covers intangible assets.
EBITDA adds D&A back to operating profit, so you need it to compute EBITDA.

In Stochastic: the EBITDA tool needs D&A for both companies.

Example: Nu Aire's D&A for the year to 2024-09-30 was $1,830,395. [verified: filing, Ex 99.1 cash flow statement]
Kewaunee's D&A was not in the pages the research read. Tri must get it from the 10-K. [verified: source file, `STOCHASTIC.md` section 18]

## EBITDA and adjusted EBITDA

EBITDA means earnings before interest, taxes, depreciation, and amortization.
It is a common way to measure cash profit before financing and tax choices.
Adjusted EBITDA adds more items (add-backs) and sometimes subtracts others.
In a credit agreement, "EBITDA" is a defined term, so it can differ a lot from a simple EBITDA.

In Stochastic: code computes the covenant version, with each add-back shown. The model never produces a number. [verified: source file, `STOCHASTIC.md` section 11]

Example: Kewaunee's covenant EBITDA is net income plus interest, taxes, D&A, plus add-backs. It then subtracts cash rent on the Statesville property. [verified: filing, Ex 10.1]
So it is "a negotiated number, not the pro forma operating profit". [verified: source file]
For comparison, the filed pro forma operating profit for the year to 2024-04-30 is $20,817K. [verified: filing, Ex 99.2]
That figure is operating profit, not EBITDA.

## Financing liability

This is a balance sheet line in Kewaunee's statements.
In accounting terms, a financing liability is an obligation that is treated like borrowed money.

In Stochastic: this is the one flagged line in the demo. The agent asks the controller which part of it is covenant debt. [verified: source file, `STOCHASTIC.md` section 12]

Example facts [verified: filing, as cited in `real-deal-candidates.md`]:
- At 2024-10-31, Kewaunee shows $750K current and $27,032K long-term.
- The 10-Q says the line comes from a sale-leaseback of the Statesville property, with a carrying value of $27,782,000.
- The pro forma balance sheet adds $3,000K current and $40,103K long-term for the new debt.
- Pro forma total is $3,750K current plus $67,135K long-term.

So one line holds both the sale-leaseback and the acquisition financing.
How much of it counts as covenant debt changes the leverage result. [inferred: not computed yet]

## Fixed charge coverage ratio

This ratio asks if the company earns enough to pay its fixed costs, such as interest and lease payments.
A higher number is safer.
Each agreement defines "fixed charges" its own way.

In Stochastic: it is not in the MVP math. The MVP tests leverage only. [inferred: from `STOCHASTIC.md` section 11]
Adding it is a natural next step. [inferred]

Example: Kewaunee must keep it at least 1.20 to 1 (Section 4.8(b)). [verified: filing]

## Flag

A flag is a line that the system will not decide alone.
The Mapper cannot place it with confidence, so it goes to a human with both options and the effect on the result.
Precision comes before recall: an unsure mapping becomes a flag. [verified: source file, `STOCHASTIC.md` section 11]

In Stochastic: the flag card on the one screen has Approve and Change buttons.

Example: the "Financing liability" line. See that entry.

## Gateway

The gateway is the one part of the system that can write to the record.
It checks who is asking, enforces the work-item states, applies the rules, and writes the audit log.
Agents and the console go through it.

In Stochastic: it is real code in the demo, not a mock. [verified: source file, `STOCHASTIC.md` sections 2 and 6]
Its rules include: only the gateway posts, a preparer cannot approve its own item, and every number carries a run id. [verified: source file, section 9]

## Intercompany elimination

Intercompany amounts are money flows between two companies in the same group.
Examples are a loan or an invoice between the platform and the target.
In combined books they must be removed, or the group counts them twice.

In Stochastic: the MVP has one seeded example at most. Full eliminations are cut. [verified: source file, `STOCHASTIC.md` section 13]
Research calls intercompany identification a common silent failure, from vendor sources (self-reported). [verified: source file, `ma-workflow-research.md`]

Example: no Kewaunee and Nu Aire intercompany amount is in the research files, so any example in the demo is seeded and labeled. [inferred]

## Leverage ratio (naive versus covenant)

A leverage ratio is debt divided by EBITDA.
It shows how many years of EBITDA it would take to repay the debt.
A naive ratio uses the plain numbers as filed: all debt-like lines over reported EBITDA, with none of the agreement's adjustments.
A covenant ratio uses the credit agreement's own definitions of debt and EBITDA.
The two can differ a lot. [verified: source file, `STOCHASTIC.md` section 11]

In Stochastic: the verdict line shows the covenant ratio next to the limit. Tri also computes the naive ratio to show the gap. [verified: source file, `TASKS.md`]

Example: a deliberately naive numerator would add all of "financing liability", which is $70,885K pro forma. [verified: filing figures, naive use is our construction]
The covenant numerator excludes the seller notes and the Statesville lease. [verified: filing, Ex 10.1]
Computed on 2026-10-24: the covenant ratio is 0.76x ($21,633K over covenant EBITDA $28,379K), and the naive ratio as filed is 2.84x ($71,955K over reported EBITDA $25,312K), over the 2.50x limit. [verified: `test_the_demo_run_beat_by_beat`]
The naive debt adds $1,070K of short-term borrowings and finance leases that count in every reading. [verified: fixture]

## Maker-checker

Maker-checker means the person or agent who prepares a result cannot be the one who approves it.
A second party must check it.
It is a standard control in finance.

In Stochastic: the Preparer makes the draft. The Reviewer checks it. A human controller approves. The gateway enforces this. [verified: source file, `STOCHASTIC.md` sections 5 and 9]
The mapping to real accounting roles is our design. [our usage]

## Mapping (confidence, tie-out)

Mapping means matching each line of the target to a line of the platform's chart.
Confidence is a score for how sure the Mapper is.
A tie-out is a check that the parts add up to the total, so no amount was lost or doubled.

In Stochastic: each mapping has a target line, a platform line, a confidence, a reason, and a flag value. [verified: source file, `TASKS.md` shared contract]
A tie-out runs on every combined table. [verified: source file, `STOCHASTIC.md` section 11]

Example: Kewaunee's Note 2 (Ex 99.2) is a filed table that maps Nu Aire lines to Kewaunee lines. [verified: filing]
Examples in it: Accrued Commissions to "Employee compensation and amounts withheld" ($0.9M), Accrued Compensation to "Other accrued expenses" ($0.2M), and Interest Income - Net to "Other income, net" ($0.3M). [verified: filing]
We use it as an answer key for the shape, not to the dollar, because Kewaunee calls its own review preliminary and the fiscal years differ. [verified: source file]
Some Nu Aire lines have no direct Kewaunee line, such as "Certificates of Deposit" and "Noncompete Agreement, Net". [verified: filing]

## Platform company versus target

The platform company is the buyer that keeps its books and chart of accounts.
The target is the company being bought.
The target's lines are mapped into the platform's chart.

In Stochastic: Kewaunee is the platform and Nu Aire is the target. [verified: source file]
Kewaunee's fiscal year ends April 30. Nu Aire's ends September 30. [verified: filing]

## Portfolio controller

A portfolio controller is the finance manager who owns the books and reporting for a PE-backed company.
After an add-on closes, this person often leads the integration of the books.

In Stochastic: this is our user and our human approver. [inferred: no practitioner has checked this]
The one-line seat is "A portfolio controller at a PE-backed company, right after an add-on closes." [verified: source file]

## Pro forma

Pro forma means "as if".
Pro forma numbers show how results would look if an event had happened earlier, such as if the acquisition had closed at the start of the period.
They are estimates and not audited.

In Stochastic: leverage is tested on a combined basis. We use the filed pro forma only as an answer key. [verified: source file, `STOCHASTIC.md` section 12]

Example: Kewaunee's pro forma statements call themselves "for illustrative purposes only". [verified: filing, as quoted in `real-deal-candidates.md`]

## Purchase accounting (ASC 805, provisional)

ASC 805 is the US accounting rule for business combinations.
The buyer records the target's assets and liabilities at fair value, and the rest of the price is goodwill.
The allocation can stay provisional while information is gathered.
The measurement period cannot exceed one year from the acquisition date. [verified: snippet only, PwC link in `post-close-deliverables.md`]

In Stochastic: it is out of scope beyond a "provisional" label. [verified: source file, `STOCHASTIC.md` section 13]
A fair-value allocation needs a valuation, so we do not pretend to do it. [verified: source file, `post-close-deliverables.md`]

Example: Kewaunee's Note 3 says a 10 percent change in intangible values moves annual amortization by about $154K. [verified: filing]

## Quality of earnings

A quality of earnings (QoE) report is an accounting firm's review of a company's profit.
It tests if reported EBITDA is real and repeatable, and checks each add-back.
It is usually done before a sale.

In Stochastic: it is not built. It was the focus of an earlier framing (seller-side finance lead) that we did not choose. [verified: source file, `ma-workflow-research.md`]
Cost and time figures for QoE in the research are self-reported by firms that sell it.

## Regulation S-X Article 11

Regulation S-X is the SEC's rule book for financial statements.
Article 11 sets how a public company shows pro forma financial information after a significant acquisition.
The filing usually has columns for the buyer, the target, and adjustments.

In Stochastic: Article 11 pro forma exhibits are why public deals work for the demo. They show the target's lines next to the buyer's. [verified: source file, `real-deal-candidates.md`]

Example: Kewaunee's Ex 99.2 is the Article 11 pro forma, with a "Nu Aire, Inc. Reclassed" column. [verified: filing]

## Run id

A run id is a unique label on one run of the math code.
Every number in a result carries the run id of the run that made it.
That lets anyone trace a number back to the exact calculation.

In Stochastic: gateway rule 4 says every number carries a run id from the math code. [verified: source file, `STOCHASTIC.md` section 9]
The current gateway has a gap: it does not yet check the run id on numbers. [verified: source file, `TASKS.md`]

## Senior Funded Bank Debt

This is a defined term in Kewaunee's credit agreement.
It is the debt the leverage covenant counts.
It is secured borrowed money including finance leases and letters of credit.
It excludes Subordinated Debt, which is the seller notes.
It also excludes "any capitalized lease obligations relating to the real property located at 2700 West Front Street". [verified: filing, Ex 10.1]

In Stochastic: the Preparer computes this through a tool, using this definition and not a generic one. [verified: source file]
Which part of the financing liability line fits it is the open question for the flag. [verified: source file, `STOCHASTIC.md` section 18]

## Stateless agent

A stateless agent keeps no memory between jobs. A stateful agent does; Stochastic's agents are stateful.
It gets one work item with all inputs, returns one typed result, and stops.
State lives in the store.
Because it has no memory, the same agent can run many times in parallel.

In Stochastic: Mapper, Preparer, and Reviewer are stateful. Each keeps a session, and the Mapper applies the policies the gateway wrote from the controller's answers. A plain job runner, which is code and not a model, moves items between them. [verified: `STOCHASTIC.md` sections 6 and 7, 2026-10-24]

## Statement line versus account

An account is one entry in a company's ledger, such as "6120 Freight-in".
A statement line is a row on a published financial statement, such as "Selling Expense".
Many accounts roll up into one statement line.
Public filings give statement lines, not accounts. [verified: source file, `real-deal-candidates.md`]

In Stochastic: the demo maps statement lines. Account-level detail would be synthetic, so we do not claim it. [verified: source file, `STOCHASTIC.md` section 12]

Example: Nu Aire's income statement has Selling Expense, General and Administrative, and Research and Development. Kewaunee shows one "Operating expenses" line. [verified: filing]

## Subordinated seller notes

A seller note is a loan from the seller to the buyer, used to pay part of the price.
"Subordinated" means it is repaid after the senior lenders.
Credit agreements often leave it out of senior debt.

In Stochastic: it is a possible second flag. [verified: source file, `STOCHASTIC.md` section 13 "Should"]

Example: Kewaunee issued $23M of 8% subordinated seller notes for Nu Aire. [verified: filing]
The other funding was a $15M PNC term loan and a $20M PNC revolver. [verified: filing]
The revolver amount drawn at close is not stated in the pages the research read. [verified: source file]

## Trial balance

A trial balance is a list of every account with its balance at a date.
Debits and credits must be equal.
It is the starting point for financial statements and for consolidation.

In Stochastic: we do not have real trial balances for the demo, because filings do not publish them. [verified: source file]
Any account-level trial balance would be synthetic, built to tie to the real statement lines. [verified: source file, `real-deal-candidates.md`]

## Work item and its states

A work item is one unit of work that moves through the system.
It has a state that says where it is.

The states in `STOCHASTIC.md` section 9 [verified: source file]:
- NEW: the item was created.
- PROPOSED: an agent has proposed a result.
- NEEDS_INFO: a human must answer or choose.
- APPROVED: a human approved it.
- POSTED: the gateway wrote it to the record.
- REJECTED and REVERSED: end states. A reversal is a new item linked to the original, and nothing is deleted.
- DENIED: a forbidden action. The gateway does not apply it, and it writes a row to the log.

In Stochastic: a flag is a work item that waits in NEEDS_INFO until the controller answers.
