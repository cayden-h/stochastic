# M&A workflow research: three candidate users for Stochastic

Research date: 2026-10-23.
Method: web search plus page fetches.
Labels: VERIFIED means the claim appears on a page I fetched or in a search result for the URL given.
INFERRED means my own reasoning.
Numbers from vendors, advisory firms, or authors are labeled self-reported.
Pages marked "(search snippet only)" were seen in search results but not opened in full.

Honest limit up front.
I found almost no independent, measured data on analyst hours or integration time.
Nearly every number below comes from a vendor or an advisory firm that sells the service.

---

## User A: PE associate or portfolio controller after an add-on closes

### Manual process

1. Get read-only ERP access or monthly trial balance exports for each entity.
Pull at least 12 months of history, plus the credit agreement and KPI definitions.
VERIFIED (self-reported by Aleph, an FP&A vendor): https://www.getaleph.com/answers/portfolio-company-actuals-90-days-post-close
2. Map every GL account of the acquired company to the platform company's chart of accounts, often by hand in a shared spreadsheet.
VERIFIED (Keboola, a data platform vendor, article dated 2026-06-18): https://www.keboola.com/blog/why-your-chart-of-accounts-breaks-at-every-acquisition
3. Produce the first consolidated month, reconcile it line by line to the existing spreadsheet, run a second parallel close, then cut over.
Then build the covenant pack from the consolidated numbers.
VERIFIED (Aleph, self-reported): https://www.getaleph.com/answers/portfolio-company-actuals-90-days-post-close

### How consolidation and pro forma adjusted EBITDA work

- Aleph describes a 12-week plan: weeks 1-2 access and raw data, weeks 3-4 mapping, weeks 5-8 parallel run, weeks 9-12 cutover.
VERIFIED, self-reported, a vendor playbook and not a measured benchmark: https://www.getaleph.com/answers/portfolio-company-actuals-90-days-post-close
- The same page says the sponsor needs four monthly items: a P&L in the sponsor's format, cash and liquidity, the covenant pack, and 3 to 5 operating KPIs.
It says the covenant pack "sets the pace."
VERIFIED, self-reported: same URL.
- Private credit maintenance covenants are "typically tested quarterly", with compliance certificates due 45 to 60 days after quarter end.
VERIFIED, self-reported (Aleph): same URL.
- Credit agreement EBITDA definitions allow pro forma synergy add-backs, often capped.
Examples from filings and law-firm commentary: cap of 20% of EBITDA on term loans; "greater of $20 million or 10%" on notes and ABL; savings often must be actioned within a fixed window, often 36 months, and supported by an officer's certification.
VERIFIED (search snippet only, SEC filings and Davis Polk commentary): https://www.davispolk.com/financial-covenants/ebitda-addbacks-bsl-financings-run-rate-cost-savings-synergies-and-caps
- One 2013 filer's one-time acquisition covenant let pro forma Adjusted EBITDA include expected first-year annualized synergies net of costs to achieve them.
VERIFIED (search snippet only): https://www.sec.gov/Archives/edgar/data/0001169264/000116926413000029/s91113form8-krepricing.htm
- Each deal's real "Consolidated EBITDA" definition must be read from its own credit agreement.
INFERRED from the above: the covenant calc is bespoke per deal, so it cannot be a generic template.

### Tools

- ERPs stay per entity: NetSuite, QuickBooks, Sage Intacct are named.
Deal-team models are Excel or Google Sheets.
Portfolio monitoring tools (Chronograph, iLEVEL) consume clean actuals and do not produce them.
VERIFIED (Aleph, self-reported): https://www.getaleph.com/answers/portfolio-company-actuals-90-days-post-close
- One guide splits the market into consolidation engines (OneStream, Oracle FCC, Planful, Prophix: eliminations, FX translation, audit trail) and spreadsheet-native reporting layers (Cube, Aleph, Datarails).
It comes from Aleph, a competitor of the others, so treat the grouping as that vendor's framing.
VERIFIED (search snippet only): https://www.getaleph.com/answers/multi-entity-consolidation-software
- I found no usable public information on Fathom or Jirav in this context.
NOT FOUND.

### Time to integrate

- Aleph's playbook: about 12 weeks to cutover, first consolidated month in weeks 5-8.
Self-reported, VERIFIED to exist at the URL above, not a measured industry figure.
- Keboola: manual mapping of an example of about 1,400 account codes is "three months to complete"; deferring the chart-of-accounts question until after close makes integration "three months longer"; a governed mapping layer makes new-entity onboarding "a two-week project."
The 1,400 figure is the author's illustrative example, not a measured result.
Self-reported, VERIFIED: https://www.keboola.com/blog/why-your-chart-of-accounts-breaks-at-every-acquisition
- The checklist at manifest.ly warns against running parallel ledgers past 90 days.
VERIFIED (search snippet only): https://app.manifest.ly/public/checklists/acquisition-integration-checklist
- Keboola also cites "70% of finance analyst time spent on data gathering" to unnamed "industry benchmarks."
Treat as unsourced.

### Main failure points

All VERIFIED, self-reported by the vendors named above (Aleph and Keboola pages):
- Starting with the ERP instead of the sponsor's reporting pack.
- Mapping only one month, which misses seasonal and one-off accounts (Aleph says map at least 12 months).
- EBITDA defined differently in the credit agreement, KPI list, and board deck.
- Skipping the parallel run (Aleph says two reconciled months is the minimum).
- Silent restatements of closed months.
- Early ERP migration restating history.
- Unmapped accounts dropping out of totals.
- Mapping logic held by one person.
- Intercompany transactions not identified, so eliminations fail silently.
- Local-GAAP-to-IFRS second mapping layer applied inconsistently.
- Mapping that cannot be traced, which creates audit risk.

### What already exists for A

- Aleph (AI-native FP&A): Excel and Sheets add-ins, a data warehouse layer syncing multiple systems, AI mappings, PE-backed companies as a customer segment, backed by Khosla, Bain Capital Ventures, YC.
Claims go-live in hours, not months (self-reported, from a job posting).
Not found: any evidence it computes covenant-defined pro forma EBITDA with synergy caps from the credit agreement text.
VERIFIED (search snippet only): https://wellfound.com/company/getaleph and https://www.thestar.co.uk/must-read/ai-native-fpa-platform-gains-momentum-with-ps213m-funding-boost-5322952
- Keboola: data platform with a governed mapping layer; its P3 Logistic Parks case (14 systems, 11 countries, 8 weeks) and Creditinfo case (30 markets, close time cut 70%) are vendor-reported customer outcomes.
Not a PE covenant tool.
VERIFIED, self-reported: https://www.keboola.com/blog/why-your-chart-of-accounts-breaks-at-every-acquisition
- Abacum markets FP&A for PE roll-ups and multi-entity complexity.
VERIFIED (search snippet only): https://www.abacum.ai/industry/private-equity
- OneStream, Planful, Cube, Datarails, Prophix: consolidation or FP&A platforms, generally implemented with services.
One PE-focused guide says buyers should ask whether a platform can add an entity and map its chart of accounts "without a professional services engagement."
VERIFIED (search snippet only): https://www.cfoshortlist.com/reports/fpa-software-for-private-equity
- OneStream was taken private by Hg for about $6.4B (completed 2026-04-01), a sign the consolidation category is large and consolidating.
VERIFIED (search snippet only): https://www.barchart.com/story/news/1092901/onestream-announces-completion-of-acquisition-by-hg-for-6-4-billion
- INFERRED gap: nothing I found reads the credit agreement, builds the pro forma adjusted EBITDA bridge for a closed add-on (with synergy cap logic), and produces a lender-ready compliance certificate with a tie-out to the mapped trial balances.
This inference rests on limited search, not an exhaustive market scan.

---

## User B: Seller-side finance lead before a sale

### Manual process

1. Commission a sell-side quality of earnings (QoE) from an accounting firm, give it 24-36 months of financials, and answer a 50-100 item document request (tax returns, monthly P&Ls, balance sheets, bank statements, customer lists, contracts).
VERIFIED (self-reported by CT Acquisitions, an M&A advisory firm): https://www.ctacquisitions.com/quality-of-earnings-report-seller-deep-dive/
2. Build the adjusted EBITDA bridge: each add-back (owner compensation above market, one-time legal fees, etc.) needs support such as invoices, timesheets, W-2s, market-rate benchmarks.
VERIFIED (same source).
3. Build the data room, run a mock diligence pass, then answer buyer requests and keep a Q&A log (date, question, answer, document link) through an active diligence cycle of roughly 4-8 weeks, with requests peaking in weeks 2-3.
VERIFIED (self-reported, vendor guides): https://www.peony.ink/blog/guide-ma-documents and https://www.papermark.com/blog/data-rooms-for-ma-transactions (both search snippet only).

### Time and cost

All of these are self-reported by firms that sell the service.
- Cost: CT Acquisitions $30K-$100K overall, tiered by EBITDA: under $5M EBITDA $30K-$50K; $5M-$15M $50K-$75K; $15M-$50M $75K-$150K; $50M+ $150K-$300K+.
Complex multi-entity or revenue-recognition-heavy cases add 25-50%.
Extras: bring-downs $5K-$15K per quarter, buyer Q&A support $5K-$25K, working capital peg $10K-$25K, sales tax review $10K-$30K.
VERIFIED (fetched): https://www.ctacquisitions.com/quality-of-earnings-report-seller-deep-dive/
- Other ranges: BDE Merson $25K-$150K, with sell-side 10-30% above buy-side scope; Livmo $20K-$60K; MBBI about $25K-$100K for $10M-$100M businesses.
VERIFIED (search snippet only): https://www.bdemerson.com/article/quality-of-earnings-report-cost
- Timeline: CT Acquisitions fieldwork 4-8 weeks, plus 2-3 weeks owner review, total 6-11 weeks, engage 3-4 months before going to market.
Baker Tilly says 4-6 weeks; Livmo 30-45 days; BizQuest 2-4 weeks.
VERIFIED (CT fetched; others search snippet only): https://www.bakertilly.com/insights/quality-of-earnings-report
- Seller burden: one point of contact (controller or CFO) at 5-10 hours per week during fieldwork, 24-48 hour turnarounds.
VERIFIED, self-reported (CT).
- For messy books, CT recommends 12-18 months of cleanup first.
VERIFIED, self-reported (CT).

### Failure points

VERIFIED, self-reported (CT Acquisitions; its own statistics are largely unsourced, so treat as author estimates):
- Revenue recognition timing may reclassify 5-20% of revenue.
- Undocumented add-backs: 10-30% may be struck.
- "One-time" items that recur get reclassified as normal operations.
- Working capital manipulation before close gets re-priced.
- Customer concentration understated.
- Hidden liabilities (sales tax, worker misclassification).
- Scope creep from undefined engagement-letter exclusions.
Add-backs are scrutinized: S&P Global data cited by one source shows add-backs peaked at 32% of management-projected EBITDA in 2021 and fell to 26% by 2023, for large leveraged-loan issuers only.
VERIFIED (search snippet only): https://beancount.io/blog/2026/05/17/quality-of-earnings-qoe-reports-ma-sellers-buyer-due-diligence-adjusted-ebitda-add-backs-avoid-purchase-price-cuts-guide
Findings first raised by the buyer's team near signing can become a price cut, escrow, or dead deal (same source, vendor content).

### What already exists for B

- Audit Sight: QoE platform that flags account movements and candidate EBITDA adjustments; claims 80% prep-time cut (self-reported).
VERIFIED (search snippet only): https://www.businesswire.com/news/home/20250710130349/en/Audit-Sight-Launches-Management-Meeting-Module-for-Transaction-Advisory-Teams-to-Accelerate-Deal-Cycles-and-Surface-Key-Insights
- Finsider.ai: connects to accounting and banking systems, tests 100% of transactions, targets 60% faster diligence (self-reported).
VERIFIED (search snippet only): https://www.barchart.com/story/news/35038707/quality-of-earnings-software-launched-by-finsider-ai-ai-powered-qoe-reports-automation-platform-targets-60-faster-due-diligence-for-ma-deals
- Shepi: trial balance import, anomaly detection, adjustment suggestions, lender-ready export, for small buyers; claims 80% faster (self-reported).
VERIFIED (search snippet only): https://www.producthunt.com/@shepi_ai
- Forvis Mazars (an accounting firm) says AI helps with trial balance mapping, first-draft schedules, anomaly detection, and reconciliations, but "professional judgment remains essential," gives no quantified savings, and notes teams "may still be bottlenecked by a target company's ability to pull requested information."
VERIFIED (fetched): https://www.forvismazars.us/forsights/2026/09/quality-of-earnings-due-diligence-in-an-ai-world
- Data room vendors (Datasite, Peony, Papermark, Ansarada, Intralinks) cover storage, permissions, Q&A logs, and some AI Q&A; see User C.
- What these do not do (INFERRED from the descriptions): most target the QoE provider or the buyer side, not the seller's own finance lead preparing a defensible bridge and a consistent data room before engaging a QoE firm.
Not verified by a full market scan.

---

## User C: Investment banker running a sell-side process

### Manual process

1. Gather financials, call notes, and market data and draft the CIM and management presentation.
VERIFIED (vendor claim, BlueFlame and Hebbia marketing: "associates traditionally spend days gathering data"): https://blueflame.ai/blog/12-ai-use-cases-junior-investment-bankers-deal-lifecycle and https://www.hebbia.com/blog/ai-investment-banking (search snippet only).
2. Stand up and populate the data room, structure it by diligence category, manage permissions per bidder.
VERIFIED (vendor guides, search snippet only): https://www.projectfusion.com/?p=50147
3. Run buyer Q&A: log questions, find source documents, draft answers, get management and counsel sign-off, keep the numbers consistent across CIM, model, and data room.
VERIFIED as a description (Peony vendor page: email diligence is serial, each round trip "costing days", asserted and not quantified): https://www.peony.ink/use-cases/ai-document-qa

### Time and cost

- No independent measure of analyst hours per CIM or per Q&A round was found.
NOT FOUND.
- Junior bankers broadly report 80-100 hour weeks: the Goldman junior survey (13 first-year analysts, self-selected, 2021) reported about 95-100 hours; the WSO 2022 survey (485 bankers) found 14% averaged 91+ hours.
VERIFIED (search snippet only): https://www.cnbc.com/2021/03/18/goldman-sachs-junior-bankers-complain-of-crushing-work-load-amid-spac-fueled-boom-in-wall-street-deals.html
These measure total hours, not hours by task.
- Peony claims buyers "self-serve 80-90% of diligence questions" from the room.
Self-reported, no methodology.
VERIFIED (fetched): https://www.peony.ink/use-cases/ai-document-qa
- A typical diligence cycle is 4-8 weeks from room launch to signing.
Self-reported (vendor guide), VERIFIED (search snippet only): https://www.papermark.com/blog/data-rooms-for-ma-transactions

### Failure points

- Numbers drifting between CIM, model, and data room: INFERRED from the nature of the work, with only vendor assertions of it as a pain.
- Q&A volume is a real burden, but no independent figure on question counts was found.
- General AI assistants lack page-level citations by default and may assert unsupported claims; confidentiality falls on the user.
VERIFIED (search snippet only): https://dev.to/devaland/ai-cim-analysis-tools-compared-2026-23j

### What already exists for C (this is the most crowded)

- Rogo: AI platform for banks, PE, and asset managers; works inside Excel, PowerPoint, Word; its Felix agent handles multi-step tasks like deal screening and CIM generation; connects to Datasite data rooms with existing permissions and citations.
Series D of $160M announced April 2026 (Dealroom reports a $2B valuation); backed by nine banks.
Sources conflict on total funding.
VERIFIED (search snippet only): https://www.fintechfutures.com/venture-capital-funding/rogo-raises-160m-series-d and https://dealroom.co/news/128138-rogo-raises-160m-at-2b-to-bring-ai-to-investment-bankings-back-office/
- Hebbia: large-document analysis and data room research with sentence-level citations.
VERIFIED (search snippet only, competitor-written comparison): https://www.hebbia.com/resources/hebbia-vs-rogo
- Model ML: agents for pitch decks and diligence reports; $75M raised Nov 2025 (Bloomberg).
VERIFIED (search snippet only): https://news.bloomberglaw.com/private-equity/ai-startup-raises-75-million-to-take-junior-bankers-grunt-work
- Farsight ($16M) and Grasp ($7M Series A, Oct 2025): agents for banking and consulting deliverables.
VERIFIED (search snippet only): https://www.axios.com/pro/fintech-deals/2025/06/11/farsight-16-million-investment-workflows and https://www.axios.com/pro/fintech-deals/2025/10/28/grasp-investment-banking-ai-7-million
- Anthropic financial-services agent plugins for pitchbooks, credit memos, KYC.
VERIFIED (search snippet only): https://www.crowdfundinsider.com/?p=277386
- Data rooms with AI Q&A: Datasite, Peony (with approve-before-release moderated Q&A as a separate tier), Papermark.
VERIFIED (fetched, Peony): https://www.peony.ink/use-cases/ai-document-qa
- What Peony says its product does not do: no human review in the base tier, not a representation or warranty, does not answer from outside uploaded files.
VERIFIED, self-reported (same page).
- INFERRED: C already has well-funded incumbents (Rogo at about $2B) and bank-embedded distribution, so a hackathon team would compete head-on with them.

---

## Cross-user comparison (all INFERRED unless marked)

- Coverage by funded products: C is heavily covered, B is partly covered by small QoE tools aimed at accounting firms and buyers, A is covered at the FP&A and consolidation layer but not at the covenant-and-pro-forma tie-out layer.
- Data availability for a demo: A needs two trial balances plus a credit agreement excerpt, which can be synthetic.
B needs a trial balance plus add-back evidence.
C needs a CIM and a data room, which are harder to fake credibly.
- Verifiability of output: A has a hard check (consolidated totals must tie to the sum of mapped entity trial balances; covenant ratio is arithmetic on a defined formula).
That suits an autonomous system with a verifier loop.
- Clearest, least-served problem (INFERRED): User A.
Reasons: a defined deadline (compliance certificate 45-60 days after quarter end, VERIFIED self-reported), a mechanical multi-step workflow, a checkable output, and no product I found that closes the loop from credit agreement to mapped consolidation to covenant certificate.
Risk: the vendor timelines are self-reported, and my market scan was a handful of searches, so a competitor may exist that I did not find.

## Gaps and not found

- No independent benchmark of add-on integration time or analyst hours per task.
- No information on Fathom or Jirav relevant to acquisitions.
- No count of diligence questions per deal.
- The Cherry Bekaert (formerly Calvetti Ferguson) sell-side QoE page redirected and was not read.
- Several sources are search snippets only; open them before citing in a pitch.
