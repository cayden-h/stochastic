# Microsoft (Cal Hacks 13.0)

## Status after the 2026-10-23 evening reframe

Stochastic is now a PE add-on integration tool.
It merges the books of a newly acquired company into the platform company's books, flags the few lines a human must decide, and checks the combined result against the lender's limit.
Three stateful agents do the work (Mapper, Preparer, Reviewer), code does all the math, and a controller approves. What the controller decides once, the agents keep.
The demo uses a real public deal: Kewaunee Scientific buying Nu Aire. [verified: `../STOCHASTIC.md` section 12]

### How Microsoft fits now

The fit is unchanged.
It is still a maybe, and it still depends on whether Microsoft products are required. [verified: `../STOCHASTIC.md` section 15]
Ask that question at kickoff or at the Microsoft workshop.
Do not add Microsoft tooling to the build just to qualify.

### Which old notes still apply

- The notes on the prize, the Frontier Co. team, and the workshop still apply.
- Notes that tie the fit to plan search, Monte Carlo, forks for what-if plans, the eight situations, or the clause reader describe the earlier framing.

---

- Prize at Cal Hacks 13.0: 1st "Built for the Real World" $3,800 plus Surface laptops and a tech talk and 1:1 mentorship with the Microsoft Delta / Frontier Co. FDE team; 2nd "Customer Impact Award" no cash
- Researched: 2026-10-15
## What they do
Microsoft is the cloud, productivity and developer-tools company behind Azure, GitHub, Copilot and Microsoft Foundry [inferred, general knowledge].
In July 2026 it announced Microsoft Frontier Co., a unit with a reported $2.5B budget and about 6,000 staff that embeds forward-deployed engineers inside enterprise customers [verified, https://www.marketscale.com/industries/software-and-technology/microsoft-launches-frontier-co-with-25b-and-6000-engineers-to-embed-ai-into-enterprise-operations].
Press names London Stock Exchange Group, Unilever, Land O'Lakes and Accenture as launch customers [verified, https://letsdatascience.com/news/microsoft-launches-frontier-company-to-deploy-ai-68a03cbe].
The name "Delta" was not found in any source; it may be an internal team name [not found].
## What they sell or ship that a hacker can touch
- Microsoft Foundry (formerly Azure AI Foundry): model catalog, agent building, and the "Best Use of Microsoft Foundry" category appeared at Microsoft's AI Dev Days hackathon [verified, https://developer.microsoft.com/en-us/reactor/events/26647/].
- Azure free account and student credits via Azure for Students [inferred, confirm at booth].
- GitHub Copilot and Copilot Studio [inferred].
- Microsoft 365 / Teams / Graph APIs for agents that act in a workplace [inferred].
- Exact Cal Hacks credit codes and signup flow: not found.
## Track brief and judging analysis

### Official prompt
The exact Devpost text for the Microsoft prizes was not retrievable: the Devpost page returned HTTP 403 and web search found nothing for "Built for the Real World" or "Customer Impact Award" [not found].
Prize names and rewards come from `../tracks.md`: 1st "Built for the Real World" ($3,800, Surface laptop, FDE tech talk and mentorship), 2nd "Customer Impact Award" (tech talk and mentorship, no cash) [verified: tracks.md, from Devpost 2026-10-15].
The organizers' email names the Delta / Frontier Co. FDE team as involved in the Customer Impact Award, and says Microsoft brings 12 engineers and 4 early-career recruiters plus a workshop on system design for deployed agents [verified: pre-event email, see tracks.md].
No judging criteria are published. Full criteria arrive on the Live Site at kickoff [verified: tracks.md].
"Delta" and any Delta Air Lines tie were not found in any public source [not found].

### How Microsoft wrote prompts and judged elsewhere
- AI Dev Days Hackathon (Reactor event 26647). Grand prizes: "Build AI Applications & Agents: Best overall solution with real-world impact and innovative use of Microsoft AI platform" and "Agentic DevOps: Best solution leveraging agentic DevOps to automate CI/CD, incident response, and reliability engineering". Categories: Best Use of Microsoft Foundry ("Demonstrates exceptional capabilities of Microsoft Foundry"), Best Enterprise Solution ("Greatest potential for enterprise adoption with security, responsible AI, governance, and scalability"), Best Multi-Agent System ("Most sophisticated multi-agent orchestration using Microsoft Agent Framework, A2A protocols, or MCP servers"), Best Azure Integration ("Most effective integration with Azure services (AI Services, Functions, AKS, or Azure Database)") [verified: https://developer.microsoft.com/en-us/reactor/events/26647/].
- Prizes there: Build 2026 tickets plus $10,000 split per category team, $20,000 per grand prize. Winners were not found; the full rules are at aka.ms/AIDevDaysHackathon/Rules, which we did not retrieve [verified: same URL, via search summary].
- Microsoft AI Hackathon at VSLive! (May 2026) judged architecture and design, security and safety, relevance to real business problems, user experience and execution, and practical use of Microsoft AI technologies [verified via search summary: https://devblogs.microsoft.com/visualstudio/?p=256267]. A different event, so only a hint.
- Microsoft and CCI Innovation Challenge winner was a George Mason team with a disaster-recovery resource finder, $10,000 (low relevance) [verified: techcommunity URL in Past winners].

### What Microsoft is pushing right now
- Frontier Co., announced 2026-07-02: about $2.5B budget and about 6,000 staff, embedding forward-deployed engineers at customers to design, deploy, and run AI systems (budget and headcount are Microsoft-reported, and unclear if new money) [verified: https://www.directionsonmicrosoft.com/microsoft-launches-its-own-forward-deployed-engineering-unit-the-frontier-company/ and the marketscale URL in Sources].
- Microsoft Foundry, Microsoft Agent Framework, A2A, MCP, GitHub, agentic DevOps [verified: Reactor URL above].
- Inference: the FDE team judges like customers, not like researchers. They ask who the customer is, what system of record the agent touches, what breaks in production, and how a human stays in control [inferred].

### Judging signals
- A named real customer or user with a concrete workflow and a measurable before and after [inferred from "Real World" and "Customer Impact" names].
- Enterprise readiness: security, governance, human approval, audit trail [verified as a category in Best Enterprise Solution, transferred by inference].
- Real use of the Microsoft stack, ideally Foundry or Azure, but not confirmed as required [inferred; eligibility is an open question].
- Deployed or deployable, with failure handling shown [inferred from the deployed-agents workshop].

### What a winning entry looks like
One narrow operational problem for one named type of customer, with the agent wired into a real system of record and a number on screen, such as hours saved or errors caught.
The demo shows a failure and the recovery, plus the human approval step.
The pitch sounds like an FDE engagement report: customer, integration, rollout risk, next step.
If the team can get a real person to say the workflow is real before Sunday, that beats any architecture slide.

### What loses
A general platform with no customer, a toy dataset, or a demo that only works on the happy path.
Impact claims with no baseline.
A chat agent with no integration into anything the customer already runs.
Using Microsoft tools only as a logo on the architecture diagram.

### Fit with our direction
Honest fit is weak-to-medium. "Built for the Real World" asks for customer impact, and a Git-based tool for small engineering teams has a real customer (small startups running Copilot, Claude Code, and humans together) but we do not have one yet [inferred].
A credible version: audit and attribution for teams using GitHub Copilot's coding agent alongside humans, with Foundry or Azure OpenAI behind the review agent, targeted at a small team that must show who or what wrote regulated code.
Do not force Foundry in if the product does not need it; judges at Microsoft will probe how it is used.
Sharp idea 1: "FDE for a 5-person dev shop". Interview one real small team before the event ends, measure review time and unattributed agent changes with and without our layer, and show the numbers.
Sharp idea 2: a compliance export that turns per-line attribution into an audit report (who or what wrote this line, who approved it), pitched at teams that sell software to enterprises asking about AI-written code.
### Fit with MatchaTalks (added 2026-10-18)
Fit is conditional. Real-world impact is easy to argue (networks drive job outcomes, a measurable match-to-meet rate), but the prize signals above are about customers: a named customer, a system of record, a before-and-after number, and human control [inferred]. A consumer app has no customer unless we name one.
Two ways to make it a customer story, both inferred:
- A campus deployment: a university student-affairs office or orientation team that wants new students to meet.
- A workplace deployment: a company with hybrid staff that wants cross-team coffee chats, like Donut but live and schedule-aware.
Real Microsoft-stack uses that the product needs anyway:
- Calendar free and busy through Microsoft Graph `getSchedule`. The official page confirms it returns free and busy availability for users. The least-privilege permission (reported as Calendars.ReadBasic, which should omit event details) comes from third-party guides and is unconfirmed, so test it. [verified for the endpoint, unverified for the permission]
- Azure Maps for venue search and walking ETA, as an alternative to Google Places or Apple Maps. The official pricing page shows a free monthly tier for Gen2 (map tiles listed: 5,000 base map). A third-party summary lists 5,000 search and 1,000 routing transactions a month free, so check the Azure pricing calculator. [secondary]
- Entra sign-in to verify that someone belongs to a school or company, which doubles as a safety feature. [inferred]
Do not force Foundry in. Judges at Microsoft will probe how it is used, and the language model for this build is meant to be the Meta Model API.
Revised 2026-10-18: Cayden says we can give real numbers from users recruited on the day, and we do not need to use Microsoft products, only make an impact.
That satisfies the customer-evidence part with real users and real numbers (sign-ups, matches, match-to-meet rate, minutes to meet), so the named-customer gate is replaced by the live pilot.
Using Microsoft products is now optional. Risk: whether the prize requires the Microsoft stack is unconfirmed [inferred from the sponsor docs]. Ask the Microsoft booth or the workshop once, and drop Microsoft if the answer is yes and we are not using it.
Graph free and busy and Azure Maps remain a low-cost option (estimated 3 to 5 hours) if we want them.
Reframe (2026-10-18): the app is for coffee chats and jobs, not loneliness. That makes the Microsoft recruiter or engineer a natural user on the supply side of a two-sided pool at the event. Our notes say Microsoft brings 12 engineers and 4 early-career recruiters (pre-event email, per the team). Ask them first and do not disrupt their booth shifts. This also makes the customer story concrete: an early-career recruiter who gets short, scheduled chats with students who opted in.
## Past hackathon winners using them
- Named winners for AI Dev Days: not found (event ran on Microsoft Innovation Studio, not Devpost).
- Microsoft and CCI Innovation Challenge winner ($10,000, George Mason University, disaster-recovery resource finder): https://techcommunity.microsoft.com/t5/azure/announcing-the-winner-of-the-microsoft-and-cci-innovation/m-p/4561704 (low relevance).
## Idea seeds
- Approval layer on Foundry agents: every agent tool call is written to a Git-backed ledger with attributed actor, diff and human approver.
- Per-action attribution for a small team using Copilot plus humans, rendered as a Git blame view for business actions.
- Finance agent that reconciles invoices against a ledger, proposes entries, and holds anything over a threshold for approval.
- FDE-in-a-box: an agent that onboards into a small business's spreadsheets and drafts the first automation with a customer-impact metric.
- Teams bot that turns an approved agent action into a signed audit record.
## Risks and open questions
- Confirm what "Delta" is and whether mentorship is team-wide or winner-only.
- Is Foundry or any Azure service required to be eligible?
- Surface laptops: one per member or per team?
- Azure quota and signup delays can eat hours; sign up before the event.
- Judging likely wants a customer story; line up a real user.
## Sources
- https://www.marketscale.com/industries/software-and-technology/microsoft-launches-frontier-co-with-25b-and-6000-engineers-to-embed-ai-into-enterprise-operations
- https://letsdatascience.com/news/microsoft-launches-frontier-company-to-deploy-ai-68a03cbe
- https://developer.microsoft.com/en-us/reactor/events/26647/
- https://techcommunity.microsoft.com/t5/azure/announcing-the-winner-of-the-microsoft-and-cci-innovation/m-p/4561704
- https://developer.microsoft.com/en-us/reactor/events/26647/ (categories and grand prize text)
- https://www.directionsonmicrosoft.com/microsoft-launches-its-own-forward-deployed-engineering-unit-the-frontier-company/
- https://devblogs.microsoft.com/visualstudio/?p=256267 (VSLive hackathon criteria, via search summary)
- https://cal-hacks-13-0.devpost.com/ (403 to our fetch on 2026-10-15)
