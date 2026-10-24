# Deep problem 1 - reading a credit agreement and finding clauses that block new financing

Date: 2026-10-23.
Tags: "verified (URL)" means I fetched the document and read the text.
"inferred" means market knowledge or reasoning, not checked against a source today.
Every quote is 15 words or fewer.

## 0. Bottom line

- Real agreements fetched fine from EDGAR with a User-Agent header. [verified (https://efts.sec.gov/LATEST/search-index)]
- The best demo document is the Potbelly Corporation credit agreement (Sagard, $25M term loan, Feb 2023).
  It has a tiny general debt basket ($2M), a tiny restricted payments basket ($1.5M), and a definition that counts some preferred stock as debt.
  A "raise $20M of preferred equity" plan would hit all three. [verified (Potbelly URL in section 2)]
- Portillo's has a "greater of" basket, which is the best test case for the formula-evaluation failure mode. [verified (Portillo's URL in section 2)]
- The hard part is not finding the clause text.
  The hard part is resolving defined terms and cross-references, then computing the answer deterministically.
  The agent should treat the LLM as a reader that returns structured fields with quotes, and a plain program as the judge.

## 1. Taxonomy of clauses that matter for new debt or preferred equity

Each row: what it means, a sentence pattern, and how a program tests it.
Sentence patterns marked "verified" are short quotes from the Potbelly or Portillo's agreements.
Patterns marked "inferred" are generic market language written by me, not quotes.

### 1.1 Negative covenant on indebtedness (permitted debt baskets)

- Plain English: the borrower may not owe money to anyone except in listed "baskets".
  Each basket has a purpose and often a dollar cap.
- Pattern (verified, Potbelly 7.01): "Create, incur, assume or suffer to exist any Indebtedness, except:"
- Pattern (verified, Potbelly 7.01(m)): "other Indebtedness in an aggregate principal amount not exceeding $2,000,000 at any one time outstanding"
- Test: parse each basket into {purpose, cap formula, secured or unsecured, subordination needed, conditions}.
  Then for a proposed instrument, check each basket in turn.
  Sum what already sits in each basket from the debt schedule, and test cap minus used >= new amount.
- Why it matters: this is the main "hidden restriction" for the $80M plan.
  A $2M general basket means almost any new tranche needs lender consent.

### 1.2 Ratio debt (incurrence test)

- Plain English: extra debt is allowed if a ratio, measured pro forma for the new debt, stays under a limit.
- Pattern (inferred): "Indebtedness so long as, on a Pro Forma Basis, the Consolidated Total Net Leverage Ratio does not exceed X to 1.00"
- Not seen in Potbelly (its list ends at a $2M basket). [verified (Potbelly URL)]
- Test: recompute EBITDA and debt pro forma (add new debt, add uses of proceeds, apply acquisition EBITDA only if the agreement allows it), then compare to the limit.

### 1.3 "Greater of" and grower baskets

- Plain English: the cap is a fixed dollar amount or a percent of EBITDA or assets, whichever is bigger.
  The basket "grows" with the company.
- Pattern (verified, Portillo's 7.03(m)): "does not exceed the greater of $25,000,000 and 25.0% of Consolidated EBITDA"
- Test: evaluate both sides with the defined EBITDA at the test date, take max.
  Needs the company's EBITDA as the agreement defines it, not as reported.

### 1.4 Lien restrictions (negative pledge)

- Plain English: the borrower cannot give anyone a claim on its assets except listed "Permitted Liens".
  New senior or junior secured debt needs a lien, so it needs a basket or an intercreditor deal.
- Pattern (verified, Potbelly 7.02): "Create, incur, assume or suffer to exist any Lien upon any of its Property"
- Test: list the collateral the new tranche needs.
  Check each lien basket, then check whether the existing lender's collateral package already covers those assets (the existing lender then has first claim).
  Flag any need for an intercreditor agreement.

### 1.5 Restricted payments (dividends, buybacks, redemptions)

- Plain English: limits cash leaving the company to equity holders.
  Preferred dividends and preferred redemptions are restricted payments.
- Pattern (verified, Potbelly 7.06): "Directly or indirectly declare or make any Restricted Payment"
- Pattern (verified, Potbelly 7.06(h)): "other Restricted Payments in an aggregate amount not exceeding $1,500,000"
- Test: project cash dividends or redemptions on the new preferred from the term sheet over the life of the loan.
  Compare the cumulative total to the basket, and check any "no Default" condition.
- Why it matters: a preferred equity deal with a 10 percent cash coupon can exceed a $1.5M lifetime basket in the first year.
  (Illustration only: 10 percent of $20M is $2M. The 10 percent is my assumption, not from any source.)

### 1.6 Treatment of preferred equity (debt-like or not)

- Plain English: if the preferred stock must be paid back on a date, pays mandatory cash dividends, or can be forced out by the holder, the lender treats it as debt.
  Then it counts against debt baskets and leverage tests.
- Pattern (verified, Potbelly definition of Indebtedness): "(d) all obligations in respect of Disqualified Capital Stock"
- Pattern (verified, Potbelly definition of Disqualified Capital Stock, clause iii): "provides for mandatory scheduled payments of dividends in cash"
- The same definition also catches stock that matures or is mandatorily redeemable, that the holder can force the company to redeem, or that converts into debt, when these happen on or before 180 days after the term loan maturity. [verified (Potbelly URL)]
- Portillo's uses a defined term "Disqualified Equity Interests" with the same idea. [verified (Portillo's URL)]
- Test: take each preferred term (mandatory redemption date, put right, cash pay vs PIK, conversion to debt) and check against the definition clause by clause.
  Output "counts as debt: yes, no, or unsure" plus the clause that triggered it.
- Design lever for the agent: re-plan the preferred as PIK (payment in kind, no cash dividend) with a maturity after the loan maturity plus 180 days.
  That is the likely "re-plan" moment. (inferred from the definition above, needs a human lawyer check)

### 1.7 Investments, acquisitions, fundamental changes

- Plain English: the loan may cap acquisitions, mergers, or asset sales.
  A $100M acquisition can be blocked here even if the debt basket is fine.
- Pattern (verified, Potbelly table of contents): 7.03 Investments, 7.04 Fundamental Changes, 7.05 Dispositions.
- Test: classify the target as a subsidiary, joint venture, or other investment, then check the investment basket and any "permitted acquisition" definition.

### 1.8 Financial maintenance covenants (leverage, coverage, fixed charge, liquidity, capex)

- Plain English: ratios the company must pass at every quarter end, regardless of new borrowing.
  New debt raises leverage immediately.
- Potbelly 8.01 has four: fixed charge coverage, liquidity (average liquidity at least $10,000,000), capital expenditures cap, and total net leverage. [verified (Potbelly URL)]
- Pattern (verified, Potbelly 8.01(d), step-down): "July 1, 2024 and for each Fiscal Quarter thereafter 1.00 to 1.00"
- Test: build the ratio from the model's pro forma statements each quarter, per the agreement's definitions.
  Look up the covenant level for each date, because it steps down.
  Monte Carlo then gives a probability of breach per quarter, which is the number the reviewer wants.

### 1.9 Equity cure

- Plain English: if the company breaches a ratio, shareholders can inject cash within a window, and it counts as extra EBITDA.
  This is a safety valve, and it limits what kind of equity counts.
- Pattern (verified, Potbelly 8.01(e)): the cure equity must be "common equity, Qualified Equity or other equity (other than Disqualified Capital Stock)".
  The window is 21 Business Days after financials are due. [verified (Potbelly URL)]
- Test: check whether the proposed preferred qualifies as cure equity.
  Debt-like preferred would not.

### 1.10 Cross-default and cross-acceleration

- Plain English: a default on any other debt above a threshold becomes a default here.
  Every new tranche adds a way to trip the whole stack.
- Pattern (verified, Potbelly 9.01): fails to pay other Indebtedness "having an aggregate principal amount ... of more than $3,000,000"
  (the quote above is shortened from the text; the ellipsis stands for words I cut).
- Portillo's uses a defined "Threshold Amount". [verified (Portillo's URL, 8.01 Cross-Default)]
- Test: take the threshold, then check whether any proposed tranche has its own default triggers (financial covenants, maturity) that fire earlier than the senior ones.
  Flag tight junior covenants as contagion risk.

### 1.11 Change of control

- Plain English: if someone gets a large share of the votes, the loan can be called.
  Preferred equity with voting rights, board seats, or conversion rights can trip it.
- Pattern (verified, Potbelly definition): a person or group becomes beneficial owner of "35% or more of the Capital Stock of Borrower entitled to vote". [verified (Potbelly URL)]
  The text counts shares the person has the right to acquire, so convertible preferred counts as if converted.
- Test: compute the fully converted voting percentage of any new investor and compare to the threshold.

### 1.12 Other clauses that bite

- Prepayment limits on junior debt (Portillo's 7.13 "Prepayments, Etc. of Junior Financing"). [verified (Portillo's URL)]
  Test: check whether the plan repays the junior tranche early.
- Amendments of other debt (Potbelly 7.11), burdensome agreements (7.09, bans contracts that restrict liens or dividends), affiliate transactions (6.19 / 7.08).
  [verified (Potbelly and Portillo's tables of contents)]
- Sale-leaseback ban (Potbelly 7.14, "Enter into any Sale and Leaseback Transaction"). [verified (Potbelly URL)]
  This matters for restaurants because owning real estate and leasing it back is a common way to raise cash.
- Mandatory prepayments, such as an excess cash flow sweep or a requirement to use equity proceeds to repay the loan. (inferred, common market term, not checked in these two documents)
- Incremental facility and accordion: a built-in way to add pari passu debt up to a cap. (inferred)
- Maturity wall and springing maturity: a junior tranche maturing before the senior one may be banned. (inferred)
- Amendment and waiver: consent from required lenders can unlock anything.
  The agent's fallback plan is always "ask the lender for consent", with a cost estimate. (inferred)

## 2. Public agreements fetched

All five were fetched with `curl` and a User-Agent of "Cal Hacks research contact@example.com", at roughly one request per second.
HTTP 200 on each.
Discovery used EDGAR full-text search (efts) filtered by form type and date, which returned results. [verified (https://efts.sec.gov/LATEST/search-index?q=%22restricted%20payments%22%20%22permitted%20indebtedness%22%20%22restaurant%22&forms=8-K,10-K,10-Q)]

| Company | Document | Date | Size | Fetch | URL |
|---|---|---|---|---|---|
| Potbelly Corporation | Credit and Guaranty Agreement, EX-10.1 to 8-K, Sagard Holdings Manager LP as agent | dated Feb 7, 2023, filed Feb 10, 2023 | $25,000,000 term loan. The text also references a "Permitted Revolving Credit Facility" up to a $500,000,000 figure I did not decode. About 477k characters of text. | 200 OK | https://www.sec.gov/Archives/edgar/data/1195734/000119312523031475/d390319dex101.htm |
| Portillo's Holdings, LLC | Credit Agreement, EX-10.1 to 8-K | dated Feb 2, 2023, filed Feb 6, 2023 | Aggregate principal amounts of $300,000,000 and $100,000,000 appear in the opening text (term loan and revolver, my reading of the tranche labels). About 680k characters. | 200 OK | https://www.sec.gov/Archives/edgar/data/1871509/000187150923000005/form8-k2223exhibit101.htm |
| The ONE Group Hospitality (STK) | Credit Agreement, EX-10.1 to 8-K, Deutsche Bank AG New York Branch | dated May 1, 2024 | Dollar figures of $40M, $10M, and $350M appear in the opening text, but I did not confirm which is the facility size. About 734k characters. | 200 OK | https://www.sec.gov/Archives/edgar/data/1399520/000155837024006331/stks-20240501xex10d1.htm |
| Noble Roman's, Inc. | Credit Agreement with Lake Forest Bank and Trust, EX-10.3 to 10-Q | dated June 10, 2026 | Not determined (no dollar figure matched in the opening text). About 237k characters. | 200 OK | https://www.sec.gov/Archives/edgar/data/709005/000165495426007523/nrom_ex103.htm |
| Good Times Restaurants Inc. | Third Amendment to Credit Agreement and Consent, Cadence Bank as agent | dated Sept 30, 2025, filed Oct 3, 2025 | Amendment only, about 19k characters, not the full agreement | 200 OK | https://www.sec.gov/Archives/edgar/data/825324/000121465925014561/ex10_1.htm |

Notes:

- The Potbelly facts above (date, agent, $25M, section numbers) are verified from the fetched text and table of contents. [verified (Potbelly URL)]
- Other candidates from the same search that I did not open: Bloomin' Brands (2026-09-29 and 2024-09-24), Dave & Buster's (several 2023-2024), First Watch (2023, 2024), BJ's Restaurants (2025), CAVA (2026-03-25), Fat Brands (2026-03-30).
  They exist as EX-10 filings per the search index. [verified (efts URL above), contents not read]
- Potbelly is the best fit for the team: small, restaurant, private credit lender, tight baskets.
  Portillo's is the best for formula baskets.
- Practical tip: strip HTML tags and unescape entities before using an LLM.
  The Potbelly file came to about 477k characters, roughly 100k+ tokens (my estimate), so chunk by section, not by page.

## 3. Three real restrictive clauses in the Potbelly agreement

Document: https://www.sec.gov/Archives/edgar/data/1195734/000119312523031475/d390319dex101.htm
All three are [verified (that URL)].

| # | Section | Quote (15 words or fewer) | What it blocks |
|---|---|---|---|
| 1 | 7.01(m) | "other Indebtedness in an aggregate principal amount not exceeding $2,000,000 at any one time outstanding" | Any new debt tranche beyond $2,000,000 total, unless another basket fits. |
| 2 | 7.06(h) | "other Restricted Payments in an aggregate amount not exceeding $1,500,000" | Cash dividends or redemptions on new preferred equity. The text says the basket runs "during the term of this Agreement", so it is a lifetime cap. |
| 3 | 1.01, definition of "Indebtedness", clause (d) | "all obligations in respect of Disqualified Capital Stock" | Preferred equity with cash-pay dividends or a redemption date inside the window counts as debt, so it hits clause 1 as well. |

Supporting clauses from the same document:

- 8.01(d) step-down to a total net leverage ratio of "1.00 to 1.00" from July 1, 2024. [verified (Potbelly URL)]
- 9.01 cross-default threshold of $3,000,000. [verified (Potbelly URL)]
- 8.01(e) cure equity cannot be Disqualified Capital Stock. [verified (Potbelly URL)]

How the "moment" would play: the agent drafts $50M senior, $30M junior, $20M preferred.
The checker finds the $2M general basket (clause 1), finds that a cash-pay preferred is Indebtedness (clause 3), and finds the $1.5M dividend cap (clause 2).
It then re-plans, for example with PIK preferred, a longer maturity, and a recommendation to request a lender consent.
(This storyline is inferred. The clause numbers and amounts are verified. Whether PIK preferred fully escapes the definition needs a lawyer to confirm.)

### Pipeline: LLM extraction plus deterministic checker

1. Fetch and clean: pull the exhibit HTML, strip tags, keep page markers.
2. Segment: split by article and section using the table of contents. Keep the definitions article separate.
3. Extract (LLM, one call per covenant section, structured output).
   Fields: clause_type, section_id, basket_label, cap_amount_text, cap_formula (for example `max(25000000, 0.25*EBITDA)`), conditions, referenced_sections, referenced_defined_terms, exact_quote, confidence.
   Rule: the quote must be a verbatim substring of the source, checked by code. If not, reject the extraction.
4. Resolve: a second pass pulls the definition text for every defined term used in a basket (Indebtedness, Disqualified Capital Stock, Consolidated EBITDA, Permitted Liens).
   Store these as a graph: term to definition to terms it uses.
5. Check (plain code, no LLM): take the proposed instrument as structured data (amount, secured or not, cash-pay or PIK, redemption date, voting percent).
   Evaluate each basket formula with the company's numbers.
   Output pass, fail, or unknown per clause, with remaining headroom.
6. Explain (LLM): write the human-readable finding that cites the section and the quote.
   It may not introduce any number that the checker did not output.
7. Escalate any "unknown" or low-confidence item (section 5).

Why split this way: the LLM does language, the program does arithmetic and logic, so the final numbers are reproducible and auditable.
This is the "system you would hire" argument. (inferred design rationale)

## 4. Answer key and catch-rate score

### Answer key

Build two kinds, because real documents have unlabeled truth.

- Real-clause key (hand labeled): for each of 2 to 3 agreements, a human lists the clauses that matter for new financing, each with section id, type, cap amount, and quote.
  Start with the Potbelly list in section 3 plus 8.01, 9.01, change of control.
  Keep it small (15 to 25 clauses per agreement) so it can be done in an hour or two.
- Planted-clause key (synthetic): take a real agreement and insert a known restrictive sentence into a chosen place, or alter an existing number.
  Example: change "$2,000,000" in 7.01(m) to "$7,000,000" and see if the agent reports the new value.
  Example: insert a sentence in the definitions that makes redeemable preferred count as debt.
  Record each plant in a JSON file with section id, type, and expected value.
  Planted clauses test whether the agent reads the document or recalls training data.
  (Do this on a copy. Do not present planted text as real.)

### Scores

- Catch rate (recall) = clauses found with correct section and correct value / clauses in key.
- Precision = correct findings / all findings. Report both so that spamming findings does not win.
- Value accuracy: share of found clauses where the extracted number or formula equals the key (exact match).
- Quote validity: share of quotes that are exact substrings of the source (should be 100 percent by construction).
- Decision accuracy: for 5 to 10 test financing proposals per agreement, does the checker's verdict (allowed, blocked, needs consent) match a human verdict.
- Escalation quality: of the clauses the agent flagged as low confidence, what share did the model really get wrong, and of its wrong reads, what share did it flag.
  The key number is silent wrong reads, which should be near zero.
- Demo line: "caught 3 of 3 planted restrictions and 0 silent errors on a real filing" is a clear, honest claim if true.
  Do not claim it before measuring.

## 5. Failure modes and escalation

| Failure mode | Example (verified where marked) | What to do |
|---|---|---|
| Cross-references | Potbelly 7.01(d) depends on 7.03(g) and 7.03(j). Liens 7.02(h) depends on 7.01(c). [verified (Potbelly URL)] | Resolve references in code. Pass the referenced text to the LLM. If a reference cannot be resolved, mark unknown. |
| Defined terms | "Indebtedness" includes Disqualified Capital Stock, so preferred depends on a second definition. [verified (Potbelly URL)] | Build a term graph. Never judge a basket without its definitions. Definitions may themselves be amended. |
| "Greater of" and percent-of-EBITDA caps | Portillo's 7.03(m): greater of $25,000,000 and 25.0% of Consolidated EBITDA. [verified (Portillo's URL)] | Parse into a formula, compute with agreement-defined EBITDA. If EBITDA add-backs are unclear, show a range and escalate. |
| Cap usage already consumed | Baskets are "at any one time outstanding", so headroom depends on current balances. | Require the current debt schedule as input. Without it, report the cap but mark headroom unknown. |
| Time-varying levels | Potbelly 8.01(d) steps down by date. [verified (Potbelly URL)] | Store the covenant as a dated schedule, not one number. |
| Amendments and consents | Good Times file is an amendment that changes an earlier agreement. [verified (Good Times URL)] | Ingest the original and every amendment. Apply in date order. If any amendment is missing, mark the whole read as "may be stale". |
| Exhibits and schedules missing | Potbelly refers to "Schedule 7.01" for existing debt. [verified (Potbelly URL)] | Check that schedules were filed. If not, escalate. Exhibits are sometimes omitted from EDGAR copies (inferred). |
| Conditions inside baskets | Potbelly 7.06(c) and (h) require no Default or Event of Default. [verified (Potbelly URL)] | Extract conditions as separate fields. A basket with an unmet condition counts as zero. |
| Pro forma rules | Ratios are tested "on a Pro Forma Basis" (Potbelly 8.01(e)). [verified (Potbelly URL)] | Implement pro forma by the agreement's own definition. Flag when the definition is long or odd. |
| Overlapping baskets | A debt item might fit several baskets, and "reclassification" language may let the borrower pick. (inferred) | Test all baskets, report the most favorable, and note the assumption. |
| Hallucinated clause text | LLM paraphrases or invents a number. | Substring check of every quote. Reject if it fails. Numbers in the answer must come from extracted fields. |
| Long-context miss | Document is about 100k+ tokens (estimate). | Segment by section. Search for known keywords as a second check (for example "Indebtedness", "Restricted Payment", "Disqualified"). |
| Legal judgment calls | Whether PIK preferred escapes the debt definition. | Never decide. Present both readings and send to a human. |

### Escalation rules for the agent

Escalate to the human reviewer when any of these is true.
Do not guess.

1. A quote fails the substring check, or two independent LLM reads of the same section disagree on a number, type, or condition.
2. A basket depends on a defined term or schedule that was not found.
3. A cap is a formula and the inputs (EBITDA add-backs, test period) are not available.
4. The proposed instrument has a term the checker cannot classify (for example, a put right that is partly conditional).
5. Any amendment or waiver may exist that was not loaded.
6. Headroom is within a set margin of the cap (for example 10 percent), because a small data error flips the answer.

The escalation message should contain: the question, the clause id, the exact quote, the two readings, the effect on the plan under each reading, and a default safe action ("treat as blocked until confirmed").
The agent should keep planning under both readings so the human only has to pick one.
Confidence labels on findings: "verified in text", "computed from verified inputs", "needs human".
(This is a design proposal, inferred.)

## 6. Open items

- Read the Portillo's and ONE Group agreements for ratio debt and a general basket to give the team a second, larger test case (not done).
- Decide on a single demo document and freeze a labeled key before building, so the catch-rate score is meaningful.
- Have anyone with legal training check the PIK preferred reading of the Potbelly definitions before the demo claims it.
- Sizes of the ONE Group and Noble Roman's facilities were not extracted.
