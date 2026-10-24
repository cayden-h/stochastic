# Post-close deliverables for a PE add-on acquisition

Research date: 2026-10-23.
Method: web search plus a few page fetches.
Labels: VERIFIED means the claim appeared in a page I fetched or in a search result for the URL given.
INFERRED means my own reasoning or practitioner convention that I could not source.
Numbers from vendors or authors are labeled self-reported.
This report does not repeat `ma-workflow-research.md`.

Honest limits up front.
Public sources give phases and workstreams, but almost none give owner, file format, and duration per deliverable.
Owner, format, and duration columns below are therefore mostly INFERRED from general practice.
Several sources are search snippets only.
Open the sources before citing them in a pitch.
The Black Box compliance certificate page returned HTTP 403, so its details come from a search summary.

---

## 1. Standard deliverables in the first 30 to 120 days

### What the sources say about phasing

- One finance checklist splits work into pre-Day 1, Day 1, first 30 days, first 100 days, and full integration.
It lists: prepare opening balance sheet and closing financial statements for both companies, perform valuations (pre-Day 1); gain access to the target's bank accounts and financial systems (Day 1); keep billing, AP, AR running and produce interim combined reports (first 30 days); consolidate budgets, records, and reports, choose the target financial system, prepare transition reports for transaction financing, track synergies (first 100 days).
It names "the Finance team" under an Integration Management Office as owner and gives no per-item format.
It says full integration "could take anywhere from six to 24 months."
VERIFIED (fetched): https://alpinemar.com/blog/m-a-integration-finance-checklist/
- Another source proposes gates at Day 30 (baseline validated, system access complete), Day 60 (decision rights published, synergy owners assigned), Day 90 (first full month of reporting under the new cadence).
VERIFIED (search snippet only): https://www.fooda.com/blog/post-merger-integration-checklist
- A close-software vendor says the first close after a purchase is expected to be difficult, and that the "third close after a purchase" is the better measure of recovery.
Its example: a deal completes "on the eighth" and month-end "lands three weeks later."
Self-reported vendor content, VERIFIED (fetched): https://nominal.so/blog/post-merger-accounting-integration/
- Under US GAAP (ASC 805), a purchase accounting allocation can stay provisional.
The measurement period ends when the acquirer has the needed information and cannot exceed one year from the acquisition date.
Adjustments go through goodwill in the period determined.
VERIFIED (search snippet only): https://viewpoint.pwc.com/dt/us/en/pwc/accounting_guides/business_combination/business_combination__28_US/chapter_2_acquisitio_US/29_measurement_perio_US.html
- One practitioner source says to start valuation work during diligence, not after closing.
VERIFIED (search snippet only): https://www.pcecompanies.com/resources/when-to-hire-valuation-firm-financial-reporting
- I found no source giving a standard number of weeks for a purchase price allocation engagement.
NOT FOUND.

### Deliverables table

Owner, format, and duration are INFERRED unless a source is shown in the notes column.
Durations are rough ranges for a small to mid-size add-on and are my judgment, not measured data.

| Deliverable | Typical owner (INFERRED) | Format (INFERRED) | Duration (INFERRED) | Notes and sources |
|---|---|---|---|---|
| Chart-of-accounts mapping file (target accounts to platform accounts) | Portfolio controller or platform accounting lead, reviewed by sponsor associate | Excel or Google Sheet, sometimes a table in a consolidation tool | Days to a few weeks; Keboola says a 1,400-account example takes about three months by hand (self-reported, author's illustration) | Aleph (self-reported) says map at least 12 months of history. Nominal (self-reported) says mapping needs an owner and a maintenance rhythm, not a completion date. https://www.keboola.com/blog/why-your-chart-of-accounts-breaks-at-every-acquisition and https://www.getaleph.com/answers/portfolio-company-actuals-90-days-post-close |
| Closing-date trial balance for the acquired entity, tied to bank and sub-ledgers | Target's controller with platform accounting | ERP export to Excel | Days to 2 weeks | Nominal says opening balances and schedules must be tied out, often under a different method than the buyer uses. https://nominal.so/blog/post-merger-accounting-integration/ |
| Consolidated trial balance (platform plus add-on, mapped, with eliminations) | Platform controller | Excel, or ERP or consolidation tool report | First one in weeks 5-8 per Aleph (self-reported); first close usually slips | Aleph playbook: weeks 3-4 mapping, weeks 5-8 parallel run, weeks 9-12 cutover (self-reported vendor plan, not a benchmark). https://www.getaleph.com/answers/portfolio-company-actuals-90-days-post-close |
| Opening balance sheet and purchase accounting entries (fair-value allocation, goodwill, intangibles, deferred taxes) | Controller plus valuation firm and auditor | Excel schedules plus journal entries posted to the ERP; valuation report as PDF | Often provisional at first close; measurement period up to 1 year (VERIFIED, PwC link above) | Alpine Mar lists "opening balance sheet" and "perform valuations" as pre-Day 1 items. https://alpinemar.com/blog/m-a-integration-finance-checklist/ |
| Intercompany eliminations schedule | Platform controller | Excel schedule plus ERP elimination entries | Recurs every close | Sources describe timing gaps (invoice booked in June by one entity and July by the other), management fees, cash sweeps, and COA mismatches as causes. Mostly vendor content. https://nominal.so/blog/post-merger-accounting-integration/ and https://www.kognitos.com/blog/intercompany-reconciliation-automating-hardest-close-step-2026/ |
| Pro forma adjusted EBITDA bridge (reported EBITDA to credit-agreement Consolidated EBITDA, with acquired-period EBITDA and capped add-backs) | Sponsor associate or CFO, often with QoE provider support | Excel, with the output feeding the compliance certificate | Days to 2 weeks per test date | White & Case notes synergy add-backs are heavily negotiated and "run-rate cost-savings" is often undefined. https://www.whitecase.com/sites/whitecase/files/files/download/publications/synergising-synergies.pdf (search snippet only) |
| Lender compliance certificate and pro forma leverage calculation | CFO or responsible officer signs; controller or associate prepares | PDF or Word on the form in the credit agreement, with an Excel backup schedule | Due on the credit agreement clock, see section 3 | See section 3. |
| Integration plan or 100-day plan | Integration management office or sponsor operating partner, finance lead for the finance workstream | PowerPoint, Excel tracker, or project tool | Drafted pre-close, refreshed at Day 30, 60, 90 | Alpine Mar and Fooda sources above. |
| Monthly reporting package (P&L in sponsor format, cash and liquidity, covenant pack, 3-5 KPIs) | Portfolio controller to sponsor | Excel or Sheets plus PDF or slide summary | Monthly; Aleph says the covenant pack "sets the pace" | VERIFIED, self-reported: https://www.getaleph.com/answers/portfolio-company-actuals-90-days-post-close |
| Synergy tracker | Integration lead and finance | Excel | Starts by Day 60 per the gate model | https://www.fooda.com/blog/post-merger-integration-checklist (search snippet only) |

INFERRED observation.
The consolidated TB, bridge, and certificate are chained: the mapping feeds the TB, the TB feeds the bridge, and the bridge feeds the certificate.
An error upstream propagates to the lender document.

---

## 2. What a good mapping file and EBITDA bridge look like

I found no authoritative public template for either.
The field lists below combine what vendor and ERP documentation describes with my own judgment.

### Mapping file

What sources support:
- Document each mapping as source account to target account with a reason, and keep it with workpapers for audit support.
VERIFIED (search snippet only, Sage 50 guidance): https://www.cleverence.com/amp/articles/sage-documentation/merge-accounts-sage-50-resources-4183/
- Oracle describes a COA mapping as instructions mapping accounts or whole segments from one chart to another, and requires subsidiary ledgers to be mapped to a common chart before consolidation.
VERIFIED (search snippet only): https://docs.oracle.com/cd/E41507_01/epm91pbr3/eng/epm/pgcs/task_DefiningChartFieldMappingRules-3998a3.html
- Visma warns that a parent chart more detailed than the subsidiary's yields wrong consolidated lines.
VERIFIED (search snippet only): https://docs.vismasoftware.no/visma-net-erp/help/general-ledger/manage-consolidations/about-account-mapping-for-consolidations/
- Keboola says validation should flag unmapped accounts, double mappings, and totals that stop reconciling, and mappings are best kept as versioned auditable tables.
Self-reported vendor content, VERIFIED (search snippet only): https://www.keboola.com/glossary/chart-of-accounts-standardization.md
- Nominal says conversion tables "break the first time an account is added" and failures go unnoticed until review.
Self-reported, VERIFIED (fetched): https://nominal.so/blog/post-merger-accounting-integration/

What a reviewer checks (INFERRED from the above plus general practice):
- Every account with a nonzero balance or activity in the lookback window has exactly one target.
- Sum of source balances equals sum of mapped target balances, per period, per entity.
- No target is a header or inactive account.
- Sign conventions and account types match (a contra-revenue account is not mapped to revenue).
- Low-confidence or judgment mappings have a rationale and a named approver.
- Intercompany accounts are flagged so eliminations can find them.
- At least 12 months are covered (Aleph, self-reported).

Sample layout (INFERRED design, synthetic values):

| src_entity | src_acct | src_name | src_type | tgt_acct | tgt_name | map_type | confidence | tie_out_delta | is_interco | rationale | reviewer | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AddOnCo | 4100 | Service Revenue | Revenue | 4000 | Services Revenue | one-to-one | 0.98 | 0.00 | N | name and type match | JD | approved |
| AddOnCo | 6150 | Misc Office and Software | Expense | 6200 | Software Subscriptions | split 70/30 | 0.62 | 0.00 | N | GL detail shows mostly SaaS | JD | needs review |
| AddOnCo | 1350 | Due from Parent | Asset | 1900 | Intercompany Receivable | one-to-one | 0.95 | 0.00 | Y | counterparty is platform | JD | approved |
| AddOnCo | 7999 | Suspense | Expense | (none) | (unmapped) | unmapped | 0.00 | 18,400.00 | N | needs owner decision | none | open |

### Pro forma adjusted EBITDA bridge

What sources support:
- Definitions vary by credit agreement; the generic build adds acquired-business EBITDA for the pre-ownership period plus permitted run-rate savings to adjusted EBITDA.
VERIFIED (search snippet only): https://altss.com/glossary/adjusted-ebitda.md
- A credit agreement in an ADT filing limits synergy adjustments to 20% of four-quarter EBITDA and requires a financial officer's certificate listing them.
VERIFIED (search snippet only): https://www.sec.gov/Archives/edgar/data/0001703056/000095012317009515/filename20.htm
- A TDS exhibit has a compliance certificate form with a schedule of pro forma adjustments tied to a specified acquisition.
VERIFIED (search snippet only): https://www.sec.gov/Archives/edgar/data/0001051512/000110465918033678/a18-13425_1ex4d1.htm
- A covenant checklist says to schedule each add-back and document the cap test, and says most agreements cap add-backs at 15-25% of unadjusted EBITDA.
Self-reported checklist, VERIFIED (search snippet only): https://app.manifest.ly/public/checklists/d44a94b8f4142dfcdfd5008c101acdec
- Cap and look-forward windows carry over from the earlier report: for example 20% of EBITDA, and actions within 36 months (VERIFIED, search snippet only): https://www.davispolk.com/financial-covenants/ebitda-addbacks-bsl-financings-run-rate-cost-savings-synergies-and-caps

What a reviewer checks (INFERRED):
- Starting net income or EBITDA ties to the consolidated trial balance.
- Each add-back maps to a permitted category in the defined term.
- Each add-back has support (invoice, contract, officer certification for synergies).
- Cap tests are computed, not asserted.
- Acquired EBITDA covers the correct pre-close days only (no double counting after close).
- Test period is the one the agreement specifies (typically trailing four quarters).
- Debt used for leverage includes acquisition debt as if outstanding from the first day of the test period, per sample clauses (section 3).

Sample layout (INFERRED design, synthetic values, USD thousands, LTM test period):

| line | description | amount | basis | cap_test | support_ref |
|---|---|---|---|---|---|
| 1 | Platform reported EBITDA | 24,000 | consolidated TB | n/a | TB_2026Q3 |
| 2 | Add-on EBITDA, pre-close days in LTM | 3,100 | add-on TB, mapped | n/a | MAP_v3 |
| 3 | Transaction costs | 650 | permitted: non-recurring | no cap | invoices |
| 4 | Run-rate cost synergies | 1,200 | officer certificate | cap 20% of line 5 base: 5,750; pass | synergy plan |
| 5 | Covenant Consolidated EBITDA | 28,950 | sum | n/a | |
| 6 | Total funded debt, pro forma | 98,000 | incl. acquisition draw | n/a | debt schedule |
| 7 | Total leverage | 3.39x | line 6 / line 5 | covenant max 4.50x; pass | |

---

## 3. What the lender or credit agreement requires

Caveat: all of these are sample clauses from public contract databases and filings, mostly public-company deals.
Sponsor-backed private credit documents set their own terms.
Each deal must be read from its own agreement and amendments.

- Pre-closing notice and pro forma package.
A Euronet credit agreement conditions an acquisition on prior written notice to the agent, with pro forma financials, projections, and a pro forma compliance certificate showing covenant compliance after the acquisition.
The notice period in that sample is thirty days.
VERIFIED (search snippet only): https://contracts.justia.com/companies/euronet-worldwide-inc-1657/contract/1188131
- Acquisition compliance certificate form.
A Black Box and PNC exhibit has an officer certify the deal is a permitted acquisition on a pro forma basis, delivered at least five days before the acquisition date, with no default before or after.
VERIFIED (search snippet only, page returned 403 on fetch): https://contracts.justia.com/companies/black-box-corp-7384/contract/379678
- Pro forma testing convention.
Sample clauses treat the acquisition and related debt as occurring on the first day of the four-quarter test period.
VERIFIED (search snippet only): https://www.lawinsider.com/clause/pro-forma-calculation
- Size triggers.
One sample requires a CFO or treasurer pro forma leverage certificate above $50 million per deal or $100 million aggregate.
Those thresholds are that sample's numbers only.
VERIFIED (search snippet only): https://lawinsider.com/clause/pro-forma-compliance
- Test date choice.
Some agreements let the borrower test compliance as of signing or as of closing, using the most recent test period.
VERIFIED (search snippet only): https://lawinsider.com/clause/pro-forma-compliance
- Lender consent.
One amendment conditioned consent on a pro forma compliance certificate showing compliance on the latest reported quarter.
VERIFIED (search snippet only): https://www.lawinsider.com/contracts/7wzxppxcI0w
- Ongoing reporting.
Quarterly financials with a compliance certificate within 45 days of quarter end, and in some agreements a monthly compliance certificate within 30 days of month end.
Annual audited financials in one schedule were due within 150 days.
VERIFIED (search snippet only): https://www.lawinsider.com/clause/financial-statements-of-the-borrower/_1 and https://www.lawinsider.com/clause/reporting-covenant-required-complies/_9
- Earlier report cited Aleph (self-reported) for 45 to 60 days after quarter end in private credit.
VERIFIED, self-reported: https://www.getaleph.com/answers/portfolio-company-actuals-90-days-post-close

INFERRED implication.
The pre-close certificate is a forecast deliverable, so the post-close certificate is the first actual-numbers test, and it lands at the next quarter-end deadline, usually 45 to 60 days after quarter end.
Because the acquisition may close mid-quarter, the first post-close certificate needs add-on data mapped before the first consolidation exists.

---

## 4. Slowest or most error-prone deliverable

No source ranks these deliverables, and I found no survey of controllers on this.
NOT FOUND for a direct ranking.

What exists:
- A survey of 270 Canadian CFOs (Robert Half) found technology and finance integration were the hardest areas of M&A, with finance a common source of mistakes.
VERIFIED (search snippet only): https://hrreporter.com/archive/merging-business-systems-finances-top-struggles-in-ma-survey/317145
- A professional-services survey lists mismatched financial data and incompatible finance systems among the most cited integration issues.
VERIFIED (search snippet only): https://itbrief.co.uk/story/professional-firms-face-long-m-a-integrations-due-to-old-systems
- Intercompany reconciliation is described as the hardest close step and the largest source of close rework.
A figure of 99% of multinationals reporting intercompany challenges is attributed to a 2023 Dimensional Research survey.
Vendor content citing the survey, VERIFIED (search snippet only): https://www.kognitos.com/blog/intercompany-reconciliation-automating-hardest-close-step-2026/
- Nominal says conversion tables break silently, intercompany timing causes elimination failures, and estimation-heavy accruals and undocumented schedules are slow.
Self-reported, VERIFIED (fetched): https://nominal.so/blog/post-merger-accounting-integration/
- Keboola and Aleph point to the chart-of-accounts mapping as the long pole: three months by hand for 1,400 accounts, and deferring it makes integration "three months longer" (Keboola, self-reported, author's illustration).
https://www.keboola.com/blog/why-your-chart-of-accounts-breaks-at-every-acquisition

INFERRED conclusion.
Slowest in elapsed time: the purchase price allocation, because it depends on third-party valuation and can run up to a year (VERIFIED provisional period, the duration of the work is not sourced).
Most error-prone and most on the critical path to the lender: the COA mapping plus intercompany identification, because every downstream number (consolidated TB, EBITDA bridge, certificate) inherits its errors, and the errors are silent.
This is the best fit for Stochastic, since the product's job is mapping and integration.

---

## 5. What a 30-second hackathon demo can credibly produce (all INFERRED)

Credible from synthetic data in 30 seconds:
- The mapping file with confidence scores, unmapped accounts flagged, and a tie-out check (source total equals mapped total).
This is checkable arithmetic and shows the verifier loop.
- A consolidated trial balance that ties to the sum of the two entity trial balances, with a visible intercompany elimination for a few seeded pairs.
- A pro forma EBITDA bridge driven by a short synthetic credit agreement excerpt, with a computed cap test and a leverage ratio against a covenant.
Arithmetic is deterministic, and a judge can check it in seconds.
- A draft compliance certificate populated from those numbers, marked as draft for officer review.
- An exception list (unmapped accounts, intercompany timing breaks, cap breach) as the human review queue.

Likely judged too simplistic or not credible in 30 seconds:
- Purchase price allocation and opening balance sheet.
A finance judge knows fair-value allocation needs a valuation, identifiable intangibles, and deferred tax, and cannot be derived from two trial balances.
If shown, label it "provisional, placeholder allocation to goodwill" and do not present it as done.
- Synergy add-backs presented as fact.
Judges know these hinge on credit agreement wording and officer judgment, so show them as inputs with a cap check, not as AI-estimated numbers.
- A single generic EBITDA definition.
Definitions are bespoke per deal, so the demo should visibly read the definition from the agreement text.
- Intercompany elimination with only exact-match pairs.
Judges will ask about timing differences and settlement conventions, so seed at least one timing mismatch and show it flagged.
- The 100-day plan and monthly package as generated slides.
These are easy to generate and look generic, so they add little credibility.

Suggested demo output (INFERRED): one screen showing mapping with tie-out, consolidated TB, bridge with cap test, leverage versus covenant, and a review queue, each number traceable to a source account.

---

## Gaps and not found

- No sourced owner, format, or duration per deliverable beyond the items cited.
- No sourced duration for a purchase price allocation engagement.
- No authoritative public template for a mapping file or EBITDA bridge.
- No survey ranking post-close deliverables by difficulty.
- No lender-requirement source specific to sponsor-backed private credit deals.
- Most evidence is vendor content or search snippets.
