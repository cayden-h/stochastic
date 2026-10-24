# 08 - Real historical deals to replay (candidate ranking)

Written 2026-10-23.
Every claim is labeled "verified (URL)" or "inferred".
Verified means I fetched that URL or SEC endpoint from the shell today and read the text.
Quotes are 15 words or fewer.
Scratch downloads (about 60 MB) are under `/private/tmp/claude-501/-Users-cayden-Documents-GitHub-hackathons-CalHacks/0bb3df36-df56-4ddb-b811-b4ae74bfaf4b/scratchpad/edgar-real/` and not in the repo.
All requests used the User-Agent `CalHacks research contact@example.com` with at least 0.3 seconds between requests.
Replace the example address with a real team inbox before anyone runs the fetch again (same caveat as file 05).

## 0. Bottom line

- Top pick: Organogenesis Holdings, the November 2024 Avista $130M convertible preferred plus the Third Amendment to its SVB-led credit agreement.
  The amendment text is a one-to-one answer key: it lists every clause that blocked the preferred, dividends, and buyback, and how each was fixed.
- Backup: Lifecore Biomedical (formerly Landec), the January 2023 $38.75M PIK convertible preferred plus a "Limited Waiver and Fourth Amendment" to both its term loan and revolver.
  It is a real special situation (covenant defaults, restatement, revolver cut, PIK pricing), but it has more moving parts.
- Stretch or second act: Comtech Telecommunications, June 2024 (new $162M term loan plus $60M ABL, with the preferred holders' veto rights rewritten).
  The blocking clause sits in the preferred stock certificate, not in the credit agreement, which is a nice twist but harder to tell in 30 seconds.
- Not recommended as the main replay: Papa John's (no amendment tied to the deal), Red Robin 2022 (refinancing, old agreement terminated), Carrols (the amendment was a LIBOR switch), Upland (no amendment found in the 8-K), Kodak 2019 and Quantum 2025 (messy or too well known).
- Biggest honest caveat: the "plan" the system is given (raise this much, in this form) has to be taken from the same 8-K that announces the deal.
  So the replay tests whether the system finds the blocking clauses and proposes the same fixes.
  It does not test whether the system would invent the Avista or Magnetar idea.

## 1. How I searched

- EDGAR full-text search (`https://efts.sec.gov/LATEST/search-index`) with phrases such as "Series A Convertible Preferred", "Credit Agreement", "to permit the issuance", "waiver", filtered to 8-K and 2018-2026.
  verified (my queries today returned hits for Organogenesis, Comtech, Lifecore, Quantum, Regis, Kodak, Upland, Lazydays, Bed Bath & Beyond and others)
- The search is noisy, so I used it for leads and then read the 8-K, the exhibits, and the filing index (`.../index.json`) for each lead.
  verified (my tests)
- Filing lists came from `https://data.sec.gov/submissions/CIK##########.json`, and size checks from `companyfacts` JSON.
  verified (my tests)
- Candidates from file 05 (Red Robin, Carrols, Papa John's, BurgerFi, Potbelly, Portillo's) were re-checked only where relevant.
  Potbelly's Sagard agreement is the document that file 01 reads, so it is the end state of a deal, not a pre-deal agreement; I did not use it here (inferred).
- I did not find a clean restaurant case where a new junior instrument needed a credit-agreement carve-out and all four documents exist.
  Restaurants stay a gap; the best restaurant leads are Red Robin 2022 and Carrols 2022, both weak on the "blocking clause" test (see section 3).

## 2. Candidates evaluated (13)

Scores are in section 5.
"Docs" lists the four document types asked for: (a) pre-deal credit agreement and amendments, (b) 8-K with terms, (c) the amendment, consent or waiver the new money needed, (d) 10-K or 10-Q before the deal.

| # | Company and deal | Sector | Docs a / b / c / d | Verdict |
| --- | --- | --- | --- | --- |
| 1 | Organogenesis, Nov 2024, $130M Series A convertible preferred (Avista), Third Amendment, term loan prepaid | Healthcare products | yes / yes / yes / yes | Top pick |
| 2 | Lifecore (Landec), Jan 2023, $38.75M PIK convertible preferred, Limited Waiver and Fourth Amendment | Healthcare CDMO | yes / yes / yes / yes (see caveat) | Backup |
| 3 | Comtech Telecommunications, Jun 2024, TCW $162M term loan plus $60M ABL, Series B to B-1 exchange | Tech hardware | yes / yes / yes (preferred terms) / yes | Stretch |
| 4 | Comtech, Jan 2024, $45M Series B preferred (Magnetar) | Tech hardware | yes / yes / partial / yes | Part of #3 |
| 5 | J.Jill, Sep 30 2020, out-of-court priming loan, term loan consent and waiver, TowerBrook subordinated loan | Retail | yes / yes / yes / yes | Strong third |
| 6 | Papa John's, Feb 2019, $200M Series B preferred (Starboard) | Restaurants | yes / yes / no / yes | Weak on (c) |
| 7 | Red Robin, Mar 2022, Fortress $225M credit agreement replaces Wells Fargo facility | Restaurants | yes / yes / no (old agreement terminated) / yes | Refinancing only |
| 8 | Regis, Jun 2024, TCW $105M term loans plus $25M revolver refinance | Consumer services | partial / yes / no (terminated) / yes | Refinancing only |
| 9 | Upland Software, Jul to Aug 2022, $115M Series A preferred (HGGC) | Software | not checked / yes / not found / not checked | Weak on (c) |
| 10 | Eastman Kodak, May 2019, $100M secured convertible notes to prepay a term loan | Industrial tech | partial / yes / not found / not checked | Too famous |
| 11 | Carrols, Dec 2022, Ninth Amendment and Series D exchange | Restaurants | yes / yes / no / not checked | Amendment was LIBOR to SOFR |
| 12 | Quantum Corp, Sep 2025, debt exchange into convertible notes, Fifteenth Term Loan Amendment | Tech hardware | partial / yes / yes / not checked | Too many amendments, too recent |
| 13 | Bed Bath & Beyond 2022 to 2023 | Retail | not fetched | Screened out: bankruptcy outcome and brand risk (inferred) |

Evidence for the rows:

- Row 1: 8-K https://www.sec.gov/Archives/edgar/data/1661181/000119312524256699/d885519d8k.htm (fetched; Items 1.01, 2.04, 3.02, 3.03, 5.02, 5.03, 8.01).
  verified (that URL)
- Row 2: 8-K https://www.sec.gov/Archives/edgar/data/1005286/000100528623000015/lndc-20230109.htm (fetched).
  verified (that URL)
- Row 3 and 4: 8-Ks https://www.sec.gov/Archives/edgar/data/23197/000095014224001650/eh240496292_8k.htm (June 2024) and https://www.sec.gov/Archives/edgar/data/23197/000095014224000204/eh240441119_8k.htm (January 2024), both fetched.
  verified (those URLs)
- Row 5: 8-K https://www.sec.gov/Archives/edgar/data/1687932/000119312520262616/d945493d8k.htm (fetched).
  verified (that URL)
- Row 6: 8-K https://www.sec.gov/Archives/edgar/data/901491/000110465919005561/a19-3945_18k.htm (fetched).
  The 8-K says about half the proceeds repay the unsecured revolver, and I found no credit agreement amendment in it (text search for "credit", "leverage", "covenant" shows none tied to the deal).
  verified (that URL) for the 8-K content, inferred that no separate consent exists.
- Row 7: 8-K https://www.sec.gov/Archives/edgar/data/1171759/000095014222000996/eh220231699_8k.htm says the prior credit agreement was terminated and paid off.
  verified (that URL)
- Row 8: 8-K https://www.sec.gov/Archives/edgar/data/716643/000119312524167408/d769948d8k.htm says the Financing Agreement refinanced the March 26, 2018 credit agreement and its amendments, which were terminated.
  verified (that URL)
- Row 9: 8-K https://www.sec.gov/Archives/edgar/data/1505155/000150515522000049/upld-20220714.htm says only that cash dividends on the preferred are "subject to the restrictions under its existing credit agreement".
  I did not look for an Upland amendment in the 10-Q.
  verified (that URL) for the quote, inferred for the rest.
- Row 10: 8-K https://www.sec.gov/Archives/edgar/data/31235/000119312519152198/d752945d8k.htm (fetched, read the first section only).
  verified (that URL)
- Row 11: 8-K https://www.sec.gov/Archives/edgar/data/809248/000080924822000123/tast-20221215.htm describes the Ninth Amendment as replacing the LIBOR-based rate with SOFR, among other things.
  verified (that URL)
- Row 12: 8-K https://www.sec.gov/Archives/edgar/data/709283/000119312525212374/d12850d8k.htm (fetched, first section only).
  verified (that URL)

## 3. Deep dives

### 3.1 Organogenesis (top pick)

Plain-English story (30 seconds):
Organogenesis has a bank term loan and revolver whose covenants only allow equity that cannot be redeemed by the holder inside the loan's life, and only common-stock-style dividends.
Avista wants to put in $130M of convertible preferred, and the company wants to use part of it for a $23.5M share buyback and to retire the $62.5M term loan.
The bank group agrees to a Third Amendment that carves out the preferred, its PIK dividends, and the buyback, and in return the term loan is paid off within one business day.
Clear enough for 30 seconds: yes.

The four document types (all fetched today):

- (a) Pre-deal credit agreement dated August 6, 2021, Exhibit 10.1 to the 8-K filed 2021-08-09.
  https://www.sec.gov/Archives/edgar/data/1661181/000119312521240438/d184440dex101.htm (1.43 MB)
  verified (that URL)
- (a) First Amendment (Dec 8, 2022) is Exhibit 10.33 to the 10-K filed 2023-03-01 (https://www.sec.gov/Archives/edgar/data/1661181/000095017023005585/orgo-ex10_33.htm, 3.2 MB, listed in the index, not read).
  Second Amendment (Apr 17, 2023) is Exhibit 10.1 to the 10-Q filed 2023-05-10 (https://www.sec.gov/Archives/edgar/data/1661181/000095017023020627/orgo-ex10_1.htm, 93 KB, listed in the index, not read).
  verified (index.json of each accession for existence), inferred for content.
- (b) 8-K with terms plus press release (Ex 99.1) and the subscription agreement (Ex 10.1).
  https://www.sec.gov/Archives/edgar/data/1661181/000119312524256699/d885519d8k.htm
  verified (that URL)
- (c) Third Amendment, Exhibit 10.2 of the same 8-K.
  https://www.sec.gov/Archives/edgar/data/1661181/000119312524256699/d885519dex102.htm (43 KB, read in full)
  verified (that URL)
- (d) 10-Q for the quarter ended 2024-06-30 (accession 0000950170-24-094009) and the FY2023 10-K (0000950170-24-023150).
  The Q3 10-Q (0000950170-24-125431) was filed 2024-11-12, the day before the 8-K, so treat the Q2 10-Q as the last safe statement for a replay cut-off of about 2024-11-01.
  verified (https://data.sec.gov/submissions/CIK0001661181.json for dates and accessions)
- Size: revenue 355.4M dollars for the nine months to 2024-09-30, term loan about 62.3M dollars at 2024-09-30.
  verified (https://data.sec.gov/api/xbrl/companyfacts/CIK0001661181.json)

Blocking clauses in the pre-deal agreement (section numbers as printed in the Aug 2021 exhibit):

| Clause | What it says (quote) | Why it blocks | Fix in the Third Amendment (verified, Ex 10.2) |
| --- | --- | --- | --- |
| Section 7.6(g), Restricted Payments | "dividends payable solely in Capital Stock (other than Disqualified Stock)" | PIK dividends on a preferred that counts as Disqualified Stock are not allowed | New 7.6(g) allows dividends "in additional shares of Series A Convertible Preferred Stock" |
| Section 1.1, definition of Disqualified Stock | "redeemable at the option of the holder thereof, in whole or in part" | The preferred has holder redemption rights, so it is Disqualified Stock | Preferred is defined and carved out by name, with optional redemption after seven years and 8 percent dividend |
| Section 7.6(e) | "substantially concurrent issue of new shares of its Capital Stock (other than Disqualified Stock)" | A buyback funded by the preferred is not funded by allowed equity | Amended so a buyback of up to $50,000,000 within two weeks of an issuance counts as concurrent |
| Section 7.2, Indebtedness | "Create, issue, incur, assume, become liable in respect of or suffer to exist any Indebtedness, except:" | Disqualified Stock counts toward debt-like limits | New clause permits the preferred "to the extent constituting Disqualified Stock" |
| Section 1.1, Consolidated Total Indebtedness | defined as "all Indebtedness of the Group Members" | Leverage covenant in Section 7.1 would count the preferred | Third Amendment: preferred "shall not constitute Consolidated Total Indebtedness" |
| Section 2.12(a) and (b), Mandatory Prepayments | clause (a) is "[reserved]" before the amendment | Needed a hook to make the lenders agree | New 2.12(a): term loan prepaid "within one (1) Business Day" of the first preferred issuance |
| Section 7.11, Affiliate transactions | not quoted | Buyback from directors is an affiliate transaction | Carved out in 7.11(b) |

verified (https://www.sec.gov/Archives/edgar/data/1661181/000119312521240438/d184440dex101.htm for the pre-deal text, and https://www.sec.gov/Archives/edgar/data/1661181/000119312524256699/d885519dex102.htm for the fixes).
I did not quote the 7.11 pre-deal text, so that row is partly inferred.

What the company and lender actually did (answer key, verified from the 8-K and Ex 10.2):

- Issued 130,000 shares of Series A convertible preferred at $1,000 each to Avista, 8 percent dividend payable in kind at the company's option, holder convertible, optional redemption after seven years.
- Third Amendment: covenant carve-outs above, term loan (about $62.5M) prepaid within one business day, cash settlement of conversion allowed only if no default, pro forma leverage 0.25x inside the covenant, and liquidity of at least $100,000,000.
- $23.5M of proceeds used to repurchase 7,421,731 common shares at $3.1597.
- Judge's note: the amendment text also contains the lenders' conditions, which is a useful second answer key (what the lenders asked for in return).

Leak risk: moderate.
The deal is recent and was press-covered (inferred).
Run a no-documents baseline (section 7) before relying on it.

### 3.2 Lifecore Biomedical, formerly Landec (backup)

Plain-English story:
A company with two credit agreements (a Goldman Sachs and Guggenheim term loan, and a BMO revolver) misses covenants and faces a financial restatement.
Investors put in $38.75M of PIK convertible preferred.
The lenders waive the past defaults, cut the revolver to $60M, raise the term loan margin 2 percent as PIK, push amortization out, and write the preferred into the covenants as "Permitted" with a $30M minimum proceeds test.
Clear in 30 seconds: mostly, but the restatement and the two lender groups add detail.

Documents:

- (a) Term Loan Credit and Guaranty Agreement and Revolving Credit Agreement, both dated December 31, 2020, Exhibits 10.1 and 10.2 to the 8-K filed 2021-01-05 (1.77 MB and 1.82 MB).
  https://www.sec.gov/Archives/edgar/data/1005286/000100528621000003/lndcex101xgscreditandguara.htm
  https://www.sec.gov/Archives/edgar/data/1005286/000100528621000003/lndcex102xbmocreditagreeme.htm
  verified (those URLs, both fetched)
- (a) Amendments One to Three are not separately filed as exhibits that I could find.
  The 10-K for FY2022 mentions only an April 2022 amendment that re-opened $20M of term debt.
  The Fourth Amendment exhibit is a conformed full copy (672 KB of text), so it contains all earlier changes.
  verified (10-K https://www.sec.gov/Archives/edgar/data/1005286/000100528622000047/lndc-20220529.htm text search, and the exhibit list) for the gap, inferred for the conformed-copy conclusion.
  This is the main completeness gap.
- (b) 8-K filed 2023-01-10 with Securities Purchase Agreement, Certificate of Designations, Registration Rights Agreement, and the two amendments as Exhibits 10.1 to 10.4 and 3.1.
  https://www.sec.gov/Archives/edgar/data/1005286/000100528623000015/lndc-20230109.htm
  verified (that URL and its index.json)
- (c) Limited Waiver and Fourth Amendment to each credit agreement (Exhibits 10.3 and 10.4, 717 KB and 791 KB).
  https://www.sec.gov/Archives/edgar/data/1005286/000100528623000015/exhibit103-termloanamend.htm
  verified (that URL, term loan version read for the preferred definitions)
- (d) 10-K for the year ended 2022-05-29 (filed 2022-09-14) and 10-Q for the quarter ended 2022-08-28 (filed 2022-10-07).
  The same day the 10-K was filed, the company filed an Item 4.02 non-reliance notice for earlier interim statements, and the 10-Q for the next quarter was never filed on time (NT 10-Q on 2023-01-09).
  So the financial statements a replay would show are known to be partly unreliable, which is honest but adds noise.
  verified (https://www.sec.gov/Archives/edgar/data/1005286/000100528622000049/lndc-20220913.htm and the submissions JSON)
- Size: total revenues of 185.8M dollars in the FY2022 10-K's first table, debt about 98M to 104M dollars.
  verified (10-K text and companyfacts)

Blocking clauses (Term Loan agreement, Dec 2020):

| Clause | Quote | Why it blocks |
| --- | --- | --- |
| Section 6.5, Restricted Junior Payments | "dividend payments or other distributions payable solely in the common Capital Stock of Holdings" | Only common-stock dividends are allowed, so preferred dividends are blocked; the 8-K confirms cash dividends and redemptions are barred |
| Section 6.5(a) | "(but not any Disqualified Capital Stock)" | Same point for redeemable stock |
| Section 6.19, Amendments to Organizational Documents | "amend or permit any amendments to any of its Organizational Documents" | A new certificate of designations is an organizational document change, adverse if material |
| Section 6.1, Indebtedness | "any Indebtedness, except:" followed by a closed list | Any junior debt alternative would need a basket |
| Section 6.8(b), Fixed Charge Coverage | 1.10:1.00 from the quarter ended 2021-05-30 | Past defaults tied to this test were waived (the 8-K says "past financial covenant defaults") |

verified (https://www.sec.gov/Archives/edgar/data/1005286/000100528621000003/lndcex101xgscreditandguara.htm for 6.5, 6.8, 6.19, 6.1 text).

What was done (answer key, verified from the 8-K and the Fourth Amendment):

- New defined term "Permitted Series A Convertible Preferred Stock": "paid in kind preferred equity evidenced by the Series A Convertible Preferred Stock Documents", with net proceeds "not less than $30,000,000", used only per Section 2.5.
- Condition precedent: the preferred documents must be "reasonably satisfactory to the Requisite Lenders".
- Revolver reduced to the lesser of $60.0M and the borrowing base; term loan margin up 2.0 percent payable in kind; first term loan amortization pushed to the quarter ending about February 28, 2025.
- Preferred pays 7.5 percent PIK, with cash dividends and redemption allowed only from the earlier of June 29, 2026 or a waiver of the credit agreement restriction.
- The preferred holders also got a veto over debt when total outstanding and available debt passes $175,000,000 and over any lien on substantially all assets.

Leak risk: low (obscure, little press, inferred).
Legal and reputational risk: medium, because the story includes a restatement and covenant defaults at a company that still trades (inferred).

### 3.3 Comtech Telecommunications, June 2024 (stretch)

Plain-English story:
Comtech's bank credit facility (Citibank, Third Amended and Restated, matures October 31, 2024) is about to mature, and the auditor language is going-concern.
The $45M Series B preferred that Magnetar and White Hat bought in January 2024 gives those holders a class vote over replacing the credit agreement or adding unsecured debt.
To refinance with TCW and Wingspire (a $162M term loan and a $60M asset-based revolver), the company has to rewrite the preferred holders' consent and put rights, and it exchanges Series B for Series B-1.
Clear in 30 seconds: only if the audience accepts that the blocker is in the preferred certificate.

Documents (all fetched):

- (a) Third Amended and Restated Credit Agreement, Nov 7 2023, Exhibit 10.1 to the 10-Q filed 2023-12-07.
  https://www.sec.gov/Archives/edgar/data/23197/000002319723000070/exhibit101cmtl-2023thirdar.htm (1.0 MB)
  verified (that URL)
- (a) Series B Certificate of Designations (the pre-deal preferred terms), Exhibit 3.1 to the 8-K filed 2024-01-23.
  https://www.sec.gov/Archives/edgar/data/23197/000095014224000204/eh240441119_ex0301.htm (338 KB)
  verified (that URL)
- (b) 8-K filed 2024-06-18 with the new Credit Agreement (Ex 10.1, 1.0 MB), Subscription and Exchange Agreement (Ex 10.2), Series B-1 certificate (Ex 3.1), warrants (Ex 4.1).
  https://www.sec.gov/Archives/edgar/data/23197/000095014224001650/eh240496292_8k.htm
  verified (that URL)
- (c) The consent changes are in Ex 10.2 and Ex 3.1 of that 8-K; there is no separate bank amendment because the Citibank agreement was repaid and terminated (8-K Item 1.02).
  verified (that URL)
- (d) 10-Q for the quarter ended 2024-01-31 (filed 2024-03-18) and 10-K for FY2023 (filed 2023-10-12).
  The 10-Q says the company expects it "may be unable to remain in compliance" with covenants given the October 31, 2024 maturity.
  verified (https://www.sec.gov/Archives/edgar/data/23197/000002319724000034/fy24q2form_finalforwebsi.htm)
- Size: quarterly revenue about 134M to 152M dollars, FY2023 Adjusted EBITDA 53.5M dollars.
  verified (10-Q text and companyfacts)

Blocking clauses:

| Where | Quote | Effect |
| --- | --- | --- |
| Series B certificate, Section 9, consent rights list, item (11) | "amend, restate or replace the Existing Credit Agreement on terms and conditions that" | Holders must approve a replacement credit agreement that is materially different or hurts their repurchase right |
| Same list, item (10) | "incurrence of unsecured indebtedness for borrowed money or issuance of any Disqualified Equity Interest" | Blocks unsecured junior debt |
| Credit agreement Section 6.01(a)(xiv) (printed as 1.01 in the body text of the HTML; the table of contents says 6.01) | "aggregate outstanding principal amount not to exceed $10,000,000" | General unsecured debt basket is tiny |
| Same section, paragraph (b) | "issue any Disqualified Equity Interests" | Blocks redeemable preferred |
| Section 6.15, Minimum Liquidity (body text prints 1.15) | Liquidity not below $25,000,000 | Shapes how much new money is needed |

verified (the two URLs above).
I did not pin the exact lettered sub-paragraph of the Series B certificate's Section 9 consent list, so cite it as Section 9, items (10) and (11).

Answer key (verified from the June 2024 8-K): new facility matures July 31, 2028; term loan priced at SOFR plus 8.50 to 10.00 percent; ABL at SOFR plus 4.75 to 5.25 percent; financial covenants include a Net Leverage Ratio of no more than 3.25x for the first quarters; 1,435,884 lender warrants at $0.10; preferred holders' "existing consent rights and existing put rights" were altered "consistent with the Credit Agreement".
Caution: Comtech did further financings in March 2025, July 2025 and June 2026, so any replay must cut off before 2024-06-17.
verified (submissions JSON lists those 8-Ks with Item 1.01).

### 3.4 J.Jill, September 2020 (strong third; not written up in full)

- Story: pandemic hits a $700M-revenue retailer with a 2015 term loan; lenders holding over 95 percent consent to an out-of-court deal where a new $231M priming term loan buys out consenting lenders at par, the old loan is stripped of covenants and waived, and TowerBrook adds a subordinated loan.
  verified (8-K https://www.sec.gov/Archives/edgar/data/1687932/000119312520262616/d945493d8k.htm)
- Pre-deal documents exist: 2015 Term Loan Credit Agreement (Ex 10.4) and ABL Credit Agreement (Ex 10.6) in the 2017 S-1, 10-K for FY2019 (filed 2020-06-15), 10-Q (2020-07-28), and weekly forbearance 8-Ks from June 2020.
  verified (https://www.sec.gov/Archives/edgar/data/1687932/000119312517037307/d272297dex104.htm and the submissions JSON)
- Blocking clauses in the 2015 term loan: Section 9.04 "create, incur, assume or suffer to exist any Indebtedness, except:", Section 9.01 Liens, Section 9.03 Dividends.
  The answer is a Required Lenders consent plus waiver ("eliminated substantially all of the covenants and events of default").
  verified (term loan exhibit and https://www.sec.gov/Archives/edgar/data/1687932/000119312520262616/d945493dex101.htm)
- Gap: I did not find or read Amendment No. 1 to the term loan, and the story has more actors (TSA, priming lenders, sponsor), so it is harder to explain in 30 seconds.
  inferred

## 4. Other candidates, reasons for the low rank

- Papa John's: the preferred closed without a documented lender consent (the 8-K ties it to repaying an unsecured revolver), the company was not distressed, and the story is widely known.
  verified for the 8-K text (URL in section 2), inferred for the rest.
- Red Robin 2022: file 05 already lists the pre-deal bank trail; the deal terminated the old agreement, so there is no consent or waiver (c) to use as an answer key.
  The Fortress agreement is better used as a "what would a rescue lender ask for" reference.
  verified (8-K) for termination.
- Regis 2024: a full first-lien refinancing at SOFR plus 9.00 percent (up to 4.50 percent PIK) after a strategic review; no amendment answer key.
  verified (8-K).
- Carrols: the Ninth Amendment is a benchmark-rate change; the preferred exchange is a separate event.
  verified (8-K).
- Quantum: 15 term loan amendments and a 2025 debt exchange, too recent and too many parts.
  verified for the "Fifteenth Term Loan Amendment" wording in the 8-K.
- Bed Bath & Beyond: not fetched; ends in bankruptcy, so the answer leaks, and the brand risk is high.
  inferred.

## 5. Scores (1 to 5, higher is better for the demo)

For "Leak" 5 means little public knowledge (low leak risk).
For "Legal" 5 means low reputational risk.
My scores are judgments.

| Candidate | Docs complete | Clear blocking clause | Story clarity | Size and realism | Leak | Legal | Total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Organogenesis Nov 2024 | 5 | 5 | 5 | 4 | 3 | 4 | 26 |
| Lifecore Jan 2023 | 4 | 5 | 4 | 4 | 4 | 3 | 24 |
| Comtech Jun 2024 | 5 | 4 | 3 | 4 | 3 | 3 | 22 |
| J.Jill Sep 2020 | 4 | 3 | 4 | 4 | 3 | 3 | 21 |
| Papa John's Feb 2019 | 3 | 2 | 5 | 3 | 2 | 3 | 18 |
| Red Robin Mar 2022 | 4 | 3 | 4 | 4 | 3 | 3 | 21 |
| Regis Jun 2024 | 3 | 2 | 3 | 3 | 3 | 3 | 17 |

Why Organogenesis scores 4 on size and realism: it is a healthy company, so it is less of a classic rescue, but it matches "needs more capital than the senior loan allows" exactly.
Why Lifecore scores 3 on legal: restatement and default language are sensitive for a company that still trades (inferred).
Why Comtech scores 3 on legal: going-concern language, and the company is still doing deals in 2026 (verified from the submissions JSON).

## 6. Recommendation

- Pick Organogenesis first.
  It has the cleanest, best-documented answer key, the lowest reputational risk, and a story that fits the Hyphenate prompt directly.
- Keep Lifecore as the backup and as the "harder case" in the deck's second act, since it shows waivers, PIK pricing and a revolver cut.
- Use Comtech only if the team wants a case where the blocker is outside the credit agreement.
- For a restaurant example, none of the restaurant candidates passes all four document tests; say so rather than forcing one.

## 7. Replay protocol (inferred design, for the team to confirm)

1. Fix a cut-off date per case: Organogenesis 2024-11-01, Lifecore 2022-12-31, Comtech 2024-06-16.
2. Give the system only filings dated before the cut-off, plus the "plan" as the team writes it (for example "raise $130M of convertible preferred, repurchase $23.5M of common, keep the revolver").
3. Hide the 8-K, the amendment, the press release, and anything filed after the cut-off, including later 10-Qs that describe the deal.
4. Run a no-documents baseline first: ask the same model what happened to the company in that month with no filings.
   If it recites the terms, the case leaks and the demo claim must be weakened.
5. Score against the answer key: blocking clauses found (section numbers), fixes proposed, structure proposed, and the lenders' conditions.
6. Keep the answer key in a private file, not in the shown repo (same advice as file 05).

## 8. What the demo must say to stay honest

- "This is a reconstruction from public SEC filings. It is not the lenders' or the company's internal view."
- "The system saw only documents filed before [cut-off date]. The answer key comes from the 8-K and the amendment filed on [date]."
- "The scenario input (the amount and type of capital) was taken from the company's own public announcement. We are testing clause reading and structuring, not whether the system would have thought of the deal."
- "We claim nothing beyond what is in the filings. We do not know why the parties chose these terms, what else they considered, or what they discussed privately."
- "Numbers marked as company-reported are self-reported in the filings and were not audited by us."
- "No endorsement or criticism of the company, the lenders, or the investors is intended. Names appear only because the filings are public documents."
- "Our output is a research demo, not investment, legal, or credit advice."
- If the system's answer differs from the real deal, show both and do not call the real deal wrong.
- Show the SEC accession numbers on screen so judges can open each source.
- Legal note: I did not research defamation or trademark rules for using a company's name; the points above are a conservative practice, not legal advice (inferred).
  Ask the sponsor whether real-company data is acceptable (open question from file 05).

## 9. Open items

- Read the First and Second Amendments for Organogenesis (existence verified, content not read).
- Find Lifecore Amendments One to Three, or confirm that the Fourth Amendment conformed copy is the only source.
- Check the 8-K Item 1.01 of Organogenesis's 2024-11-22 and 2024-12-02 filings (they follow the deal and must be excluded from the replay); I listed them but did not read them.
- Confirm that the Q3 2024 Organogenesis 10-Q (filed the same day) is excluded.
- Run the no-documents baseline for the three cases.
- Put a real contact address in the User-Agent.
