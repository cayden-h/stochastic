# Slack sponsor channel notes (Cal Hacks 13.0)

Read on 2026-10-23 (Friday, about 11am Pacific) from the Cal Hacks Slack workspace, by clicking through every `spons-`, `cohost-`, and `partner-` channel plus `0-announcements`, `0-general`, and `2-opportunities`.
Everything here is verified from the posts themselves, and prize amounts are as the sponsors posted them (self-reported by the sponsors).
Where a Slack post disagrees with an earlier doc, the disagreement is flagged and the Slack post is newer.
Full criteria and starter packs were still promised on the Live Site, so recheck at kickoff.
Not read: the YC afterparty thread (7 replies), the Jane Street card thread (5 replies), the Nergiz thread in `#cohost-hyphenate` (2 replies), and the team-formation and mentor channels.

## Channels with real content

### Hyphenate (`#cohost-hyphenate`)

- Nothing new on the rules beyond the workshop (see `../hyphenate-workshop.md`).
- A Hyphenate rep answered "how do we register for the track": participate normally, and the Devpost submission form asks you to select your track.
  So no separate sign-up is needed, but select the Hyphenate track at submission. [Rudraksh Awasthi, Hyphenate]
- Abdul, a Hyphenate founding engineer, said they will be judging as part of the Hyphenate team.
- The workshop recording (Fathom) and the slide PDF are pinned in the channel.

### Anthropic (`#cohost-anthropic`)

- Tyler Lacroix [Anthropic] said on Oct 20: "Yes all hackers will get $50 of Claude API credits".
  Reply thread: more info at the opening ceremony.
  A hacker asked whether the credits can be added to existing Claude Pro or Max plans, with no answer seen.
- A Cal Hacks director (Charlie) said on Oct 15 that sponsors were still being added to Slack.
  A hacker said Anthropic announced its credits at the opening ceremony last year (hacker report, not verified).
- No prize criteria for "Claude for Public Benefit" were posted here.

### CRS (`#spons-crs-credit-api`) - most relevant to Stochastic

- CRS describes itself as the credit data behind lending decisions, a certified credit reporting agency with access to all three bureaus, through one JSON API or an MCP server.
- It is also working on "the first agentic credit exchange, where AI agents represent borrowers and lenders and negotiate credit on their behalf" (self-reported, no details).
- Prizes: $1,500 cash plus interviews.
  Best Overall $1,000, Best Financial AI Agent $500, Best Identity / Fraud Innovation (interview for their forward-deployed engineer role), Most Unexpected Use of CRS (same interview).
- Rule: the project must use the CRS sandbox in a meaningful way and show it working live in the demo.
- Sandbox: `calhacks.crscreditapi.com` (enter an email for credentials, a Postman collection, and test cases), MCP at `mcp.crscreditapi.com`, usable from Claude, Claude Code, or any MCP client.
- Their engineers who built the APIs staff a booth all weekend.
- Consumer credit data is the wrong shape for corporate capital structuring, so the honest Stochastic angle is thin (see the Stochastic note below).

### Microsoft (`#spons-microsoft`, `#0-general`)

- Challenge: "Build a production-minded AI agent that solves a meaningful problem in finance, productivity, healthcare, or another high-impact domain."
- Judging text (from the `#0-general` repost): the solution should demonstrate customer understanding, end-to-end functionality, measurable usefulness, responsible design, and a credible path from prototype to production.
- Prizes: Grand Prize "Built for the Real World" is a Surface laptop for each member of the winning team, plus a remote FDE tech talk and 1:1 mentorship with senior FDEs (Microsoft Delta and Frontier Co.).
  Microsoft Customer Impact Award is the tech talk and mentorship, no cash.
- Events: networking social Friday 7 to 8pm at Gate 6, workshop "System Design for Deployed Agents" Saturday 10:00 to 10:45am at The Theatre.
- Finance is named as an example domain, and nothing in the post requires Microsoft products.
  Whether the prize requires them is still unconfirmed, so ask the booth.

### Coinbase (`#spons-coinbase`, `#0-general`)

- Two x402 tracks: Payment agent (give an agent a way to pay or earn, using the Coinbase MCP for Agents and x402) and Trading agents (agentic trading and portfolio management with Coinbase for Agents or the Coinbase Wallet MCP).
- Prize pool: $500 for each winning team member, per track, plus an exploratory call with a Coinbase recruiter.
  This matches the Hacker Guide figure and not the $2,000 Devpost figure.
- A link in the post holds the judging criteria, docs, and submission requirements (not opened).

### Fetch.ai (`#spons-fetch-ai`)

- ASI:One Agent Challenge "From Intent to Action": build an agent, register it on Agentverse, implement the Agent Chat Protocol, and make it discoverable and usable through ASI:One.
- Prize pool "$10,000": 1st $1,250 plus an internship interview, 2nd $750 plus interview, 3rd $500 plus interview, two special recognition prizes at $250.
  Discrepancy: `CalHacks/ideation/tracks.md` lists $1,500 / $1,000 / $500, so use the Slack amounts as newer, and confirm.
- Extras: fun ASI:One challenges with gadget prizes, a grand prize holiday trip, and surprise prizes at the opening ceremony.

### Creao (`#spons-creao-ai`)

- Prize tracks, $5,000 cash total: Best AI-First Disruptor $2,500, Best One-Person Company $1,500, Best Team Empowerment $1,000.
  Winners also join the CREAO Launchpad (1 year of Pro Max, mentorship, interview opportunities).
  Discrepancy: earlier docs list much larger "per placement" totals, which fold in non-cash value.
- To qualify: at least one CREAO agent (built on `agent.creao.ai`) does the core work, put the agent ID and a run share link in the Devpost README, and select the CREAO track.
- Starter pack with credits, docs, and judging criteria: `community.creao.ai/CalHacks2026`.
- A hacker reported the hacker guide link needs permission, and Creao asked the organizers to fix it.

### Bright Data (`#spons-bright-data`)

- Track: Best Use of Public Web Data in an App.
  The public web data must be essential, and the product should stop working if it is removed.
- Prizes: 1st $1,500 credits plus $500 Amazon gift card, 2nd $1,000 plus $350, 3rd $500 plus $250.
- Disqualified: scraping behind a login or paywall, non-public personal data, mocked or hardcoded demo data, or mentioning Bright Data only in the README.
- $300 credits via a promo link in the post, a "public data hackpack" on GitHub (`ScrapeAlchemist/public-data-hackpack`), and a DevRel person at the booth.
- Conflict with the Hyphenate brief: Hyphenate wants a seeded simulated company, and Bright Data forbids mocked data, so the two do not stack.

### Apify (`#spons-apify`)

- $5,000 in prizes: 1st $2,000, 2nd $1,000, 3rd $800, 4th $400, 5th $400, plus Best Actor built with AI Chat $400.
- The project must use Apify "in a meaningful way".
  $200 in credits with a promo code (already in `CalHacks/logistics.md`).
- Workshop Saturday 11:00am to 12:00pm Pacific, and the MCP server is at `mcp.apify.com`.

### Bitdeer AI (`#spons-bitdeer`)

- Prizes: 1st $500 credits plus four gaming mice, 2nd $200 credits plus a LEGO Technic set.
- Request token credits through a form, after registering for a Model Studio account.
- Workshop Saturday Oct 24, 1:00 to 2:00pm, Gate 4 Breakout 4.

### Atlassian (`#spons-atlassian`)

- Prizes: AirPods Max plus swag.
  Challenge details are in a Google doc linked in the channel.
- One ask: set up your Forge environment and demo site early (steps 1 to 4, about 15 minutes), because many people provisioning at once can leave teams waiting.

### Figma (`#spons-figma`)

- Workshop Friday Oct 23, 7 to 8pm, Gate 3 Breakout 3: "From Canvas to Shipped".
- Free Figma education access (including the new Figma Agent), and a "special activation" at Booth 35 on Saturday 10am to 2pm for people who show verification.
- A Figma track is being launched this year, with more details "soon".
  Prize details are not posted.

### Spacetime (`#cohost-spacetime`, `#0-announcements`)

- A pinned post links the workshop slides (a Figma deck, "Move fast and don't break things") and a startup program with up to $50,000 in Maincloud credits.
- A hacker asked whether the Scrabblebot Tournament can be entered solo alongside a main project, with no answer seen.
- The pre-event workshop ran on Oct 20 at UC Berkeley.

## Channels with only recruiting or logistics

- AfterQuery: head of talent posted, will be at their table Friday from 10am.
- Engramme: AI research lab building a "Large Memory Model", recruiting.
- Llama Ventures: early-stage AI fund ($300M+), writes $500K to $5M checks pre-seed to Series A, offers to bounce ideas.
- Fung Institute: UC Berkeley MEng and MAS-E recruiting.
- Listen Labs: two judges named (Hugo Berg, and Jason, a founding research scientist on human simulation).
- Runpod: asked about GPU credits, answer was to come to the booth Friday.
- Supercell: Clash Royale tournament, with a rumor of a branded AirPods Max prize.
  A hacker asked about registering after the 6pm Friday cutoff, with no answer seen.
- Jane Street: hackers asked about playing cards and a poker tournament.
- Wajo AI: promoting Fo, an AI action agent, and stickers at the booth, no prize.
- Cartesia: a Cartesia rep posted a promo code for first-time users (startup access), no prize details.
- Capital One: no track brief posted yet, as of Friday morning two hackers asked when it comes.
  A director said workshops and the tournament need no application.
- Visa: no track brief posted yet, one hacker asked when it comes, and another asked who represents Visa.
- Meta: Cal Hacks said Meta will not provide AR glasses (Oct 13).
- YC: afterparty Sun Oct 25, 6 to 9pm, Dogpatch, request a spot.
- Moss: only a bot notice that two Moss people joined.
- Partner channels `#partner-asus` and `#partner-redbull`: bot messages and a question about free Red Bull.

## Empty (no sponsor post yet)

a16z, Adobe, Annapurna Labs, Armadin, Canva, Citadel (only "interested in Citadel" replies), Context.dev, Convex, D.E.
Shaw, Decagon, Elastic, Factory, Greptile, Illumio, Mana, MoonPay, Notability, Opal Electronics, Savvy, Scale AI, SpaceXAI, The House Fund.

## General logistics found (`#0-general`, `#0-announcements`)

- Judging is Sunday 10:30am to 12:30pm.
  Winners are announced at the closing ceremony, not before, and some sponsors want to meet winning teams after, so plan to stay for it. [Sumin and Allison, Cal Hacks]
- The app has team matching (Airline Adventures tab) and a crash workaround ("check for updates"), already in `CalHacks/logistics.md`.
- A mentor ("George") posted a third-party "winning guide" with Claude Code skills and GitHub repos.
  Treat it as unvetted marketing, not an organizer resource.
- Microsoft, Bitdeer, Coinbase, Fetch.ai, and Bright Data reposted their blurbs in `#0-general`.
