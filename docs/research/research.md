# Stochastic - research log

Started 2026-10-22 by web search.
Tags: verified (with source) or inferred.
Pricing figures come from secondary glossaries and law-firm commentary, not primary deal data, so treat them as ballpark.
The Morgan Stanley pages and the General Atlantic press release returned HTTP 403 to direct fetch, so deal facts come from search summaries of those pages.

## Buyers Edge deal (resolves the open question in README.md)

- $425M preferred equity investment in Buyers Edge Platform, a foodservice procurement company, closed April 8, 2024.
  [verified: https://www.generalatlantic.com/media-article/buyers-edge-platform-announces-425m-preferred-equity-investment-led-by-general-atlantic-credits-atlantic-park-fund-alongside-blackstone-tactical-opportunities-and-morgan-stanley-tactical-va/ (search result title), https://www.williamblair.com/News/Buyers-Edge-Platform-and-Atlantic-Park-Fund-Transaction]
- Led by General Atlantic Credit's Atlantic Park fund, alongside Blackstone Tactical Opportunities and Morgan Stanley Tactical Value.
  So both versions in the pasted notes were partly right: Morgan Stanley and Blackstone were co-investors, not one working for the other, and General Atlantic led. [verified: same sources]
- William Blair was the placement agent.
  The note that JPM was agent for Buyers Edge was not supported by anything found.
  Treat it as wrong unless a source appears. [verified: William Blair page]
- Use of proceeds: platform innovation, strategic M&A, and European expansion.
  Bregal Sagemount, the first institutional investor, exited its minority stake, and founder John Davie increased his majority stake. [verified: pulse2.com summary and the sources above]
- Why it matters for us: it is a real, public example of a company that needed capital outside a normal bank loan and got it from a consortium of special-situations funds, which is the exact story the pitch tells.
  Terms such as the preferred dividend rate and covenants were not found.
  Do not invent them. [verified absence]

## Morgan Stanley Tactical Value team

- Mandate: opportunistic, private, long-term, likely illiquid investments globally, across asset classes and across the capital structure.
  It stresses flexible capital and structuring experience for bespoke needs or idiosyncratic risks, and sources deals through Morgan Stanley's platform.
  Listed under both Private Credit and Private Equity. [verified: https://www.morganstanley.com/im/en-au/institutional-investor/about-us/people-and-teams/investment-teams/tactical-value-team.html (search summary)]
- Not confirmed: the "10 to 20 percent of portfolios" figure in the pasted notes, and any named preferred-equity strategy.
  The page text does not say either. [verified absence]
- Takeaway for the pitch: we are describing the kind of work these teams do.
  Do not claim Morgan Stanley uses AI for it or that they are a customer.

## Instruments and rough pricing (secondary sources, ballpark)

| Instrument | Rough cost | Notes |
| --- | --- | --- |
| Senior secured loan | cheapest | Lowest risk, holds first claim. Direct lending new-issue yields averaged about 9.3 percent all-in in 2025. |
| Second lien | about SOFR + 750 to 1000 bps | Structurally subordinated, narrower investor base. |
| Mezzanine | 8 to 12 percent cash plus 2 to 4 percent PIK, plus warrants | Another source says 12 to 18 percent gross target. Fees about 1 to 3 percent. Interest is generally tax deductible. |
| Preferred equity | sources conflict, 10 to 15 or 18 to 25 percent | Dividends are not tax deductible. Remedies are contractual, and non-payment usually triggers rate step-ups or governance rights, not creditor enforcement. |

- PIK is growing: 11 percent of loans in Lincoln International's private market database paid some PIK in 2025, up from 7 percent in 2021. [verified: search summary of Lincoln International data]
- Unitranche has compressed the traditional mezzanine market. [verified: ibinterviewquestions.com summary]
- Inferred design implication: the structuring agent needs a cost-of-capital table per instrument, stored as labeled assumptions with ranges, not one number.

## Covenants, the trap we want to plant

- Two parallel mechanisms in a credit agreement: a ratio test (new debt allowed if pro forma leverage or coverage meets a threshold) and permitted-debt baskets for specific categories regardless of the ratio.
  [verified: https://www.creditgpt.com/content/how-to-think-about-debt-baskets, https://9fin.com/insights/the-debt-covenant--part-2--the-art-of-basket-weaving-9fin-educational]
- Failing an incurrence test is a closed door, not a default.
  The borrower can still use a basket that does not depend on the ratio. [verified: same]
- Issuers usually use ratio debt capacity first, because basket debt first would raise leverage and cut coverage. [verified: same]
- Ratio tests differ by debt type, for example first lien leverage for first lien debt and total net leverage or interest coverage for unsecured. [verified: same]
- Maintenance versus incurrence covenants are different: maintenance is tested on a schedule, incurrence only when you take an action. [verified: https://www.creditgpt.com/content/maintenance-versus-incurrence-covenants (title and summary)]
- Treat debt baskets as a capacity map: how much, by which entity, secured by what, with what priority. [verified: creditgpt]
- Inferred design implication: the clause-reader agent should output a capacity map, and the hero trap can be a ratio test that passes for the $80M plan on EBITDA but fails once a definition (for example debt including leases) is applied.
  This needs a real credit agreement to copy language from, which is not yet found.

## 2026 update (added 2026-10-22)

The 2024 numbers above are now supplemented by 2026 sources.
Still secondary sources (law firms, advisers, market newsletters), so ballpark only.

### What "capital solutions" is, in 2026 language

Use this phrase in the pitch and in searches, because it is the industry's current name for what Stochastic does.
- Mayer Brown (October 2026) defines capital solutions as "bespoke, hybrid instruments sitting at the intersection of debt and equity", with each deal structured from scratch and returns from current income, deferred returns, and equity upside.
  [verified: https://www.mayerbrown.com/en/insights/publications/2026/10/the-rise-of-private-capital-capital-solutions-and-the-new-architecture-of-credit]
- Instruments: preferred equity (PIK, cash-pay, or hybrid, with liquidation preferences), structured equity (ratchets or guaranteed minimum returns), holdco PIK (financing above the operating company's facilities), convertibles and mandatory convertibles, stretched senior debt, mezzanine and second lien. [verified: same]
- Target returns: 15 to 25 percent gross IRR, versus 8 to 12 percent for conventional lending, and typically 20 percent or more in stressed situations. [verified: same]
  This also settles the conflict in the 2024-era preferred equity numbers above, so use 15 to 25 percent for preferred and structured equity.
- Why companies use it: M&A financing when senior capacity is used up, growth capital without full dilution, dividend recaps, bridge-to-event financing, minority stakes, and shareholder liquidity.
  The common thread: too expensive for common equity, too complex or subordinated for traditional debt, too bespoke for standard terms. [verified: same]
  This matches the restaurant-chain example in the pitch.
- Documents blend loan agreement, shareholder agreement, and convertible concepts.
  Governance and information rights matter more than financial maintenance covenants, and the key issues are intercreditor dynamics, consents under existing facilities, transfer restrictions, exit mechanics, anti-dilution, and change of control. [verified: same]
- Inferred design implication: the hero trap should be a consent or incurrence restriction under the existing facility, not only a leverage ratio, because that is where capital solutions deals actually get stuck.
- Market size: private credit grew from about $500B in 2015 to over $2T by May 2026, projected $3.4T by 2030, with over $240B raised in 2025. [verified: Mayer Brown, self-reported estimates]
  Good "impact the whole industry" numbers for the deck, labeled as estimates.

### 2026 covenant and pricing signals

- Covenant-lite reached 41 percent of upper middle-market and large-cap deals in 1H 2026, up from 34 percent in 2025, but stayed under 4 percent for borrowers under $50M EBITDA.
  [verified: https://cdn.hl.com/pdf/2026/hl-u.s.-private-credit-market-newsletter-summer-2026.pdf (search summary)]
  So a mid-sized company still faces maintenance covenants, which supports a mid-sized fictional borrower for the demo.
- Lord Abbett's 2026 midyear outlook calls it a "lender-friendly reset": less leverage, more covenants, fewer PIK requests, wider spreads. [verified: https://www.lordabbett.com/en-us/financial-advisor/insights/investment-objectives/2026/2026-midyear-investment-outlook-private-credits-lender-friendly-reset.html (search summary)]
- Second lien in the Houlihan Lokey newsletter table: roughly S + 650 to 775 bps with OID around 97 to 98, but the table was hard to parse, so do not cite it until read directly.
- PIK is under watch: Fitch reportedly flags BDC PIK ratios above 15 percent, and of 14 private credit defaults in May 2026, about half used maturity extensions, five introduced PIK, and two involved missed interest. [self-reported by the search summary, unverified]
- Preferred equity quantitative pricing for 2026 was not found.

### Market context that helps the pitch

- AI financing is a live example of layered, hard-to-see structures: Goldman estimates nearly $500B of AI-related debt issuance so far in 2026 and about one-third of AI capex debt financed. [verified: https://www.goldmansachs.com/insights/goldman-sachs-exchanges/how-ai-debt-is-reshaping-the-credit-market (search summary)]
  A Columbia working paper notes growing complexity in the number and structure of claims on the same cash flows. [verified: search summary]
  A possible fictional borrower: a mid-size company building data center capacity, with GPU collateral that depreciates fast (a real collateral risk per the Brookings draft).
  Inferred, not decided.
- Venture debt is growing, and Runway Growth notes Anthropic's roughly $2.5B revolving credit facility is the outer edge and not representative. [verified: https://runwaygrowth.com/venture-debt-review/ (search summary)]

### Prior art (searched 2026-10-22)

- No startup, product launch, or Devpost project doing AI capital-structure advising with simulation and covenant checking turned up in standard searches.
  The finance hackathon found was AdvisoryAI Hackathon 2026 (January, consumer financial advice access), which is a different problem. [verified absence of results, not proof none exists]
- Absence in search is weak evidence.
  Still to do: search EDGAR-adjacent vendors, Hypercore and Ellis (see `../private-credit-market.md`), and ask the Hyphenate booth.

### Still open

- The General Atlantic and Morgan Stanley pages for Buyers Edge returned 403 to direct fetch, so the dividend rate and terms are unread.
  The Business Wire copy (https://www.businesswire.com/news/home/20240408441127/en/) may be fetchable.
- No 2026 preferred equity deals led by these three firms turned up, so Buyers Edge remains the best public anchor, though it is from April 2024.
- Still no primary credit agreement text.

## Gaps to close next

- Find a public credit agreement or indenture (SEC EDGAR exhibit) to copy real covenant language and definitions, and read its debt covenant.
- Read the Hyphenate track brief PDF link in `../sponsors/hyphenate.md` sources, and ask the booth if capital structuring counts.
- Find real Monte Carlo practice for covenant headroom, such as EBITDA volatility and rate path assumptions, so inputs are defensible.
- Find the General Atlantic press release text for terms (dividend rate, PIK toggle, redemption), if public.
- Confirm no one has built this already (Devpost search "capital structure", "covenant", "mezzanine", plus startups such as Hypercore and Ellis, noted in `../private-credit-market.md`).
