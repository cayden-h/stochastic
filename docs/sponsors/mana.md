# Mana (Cal Hacks 13.0)

## Status after the 2026-10-23 evening reframe

Stochastic is now a PE add-on integration tool.
It merges the books of a newly acquired company into the platform company's books, flags the few lines a human must decide, and checks the combined result against the lender's limit.
Three small stateless agents do the work (Mapper, Preparer, Reviewer), code does all the math, and a controller approves.
The demo uses a real public deal: Kewaunee Scientific buying Nu Aire. [verified: `../STOCHASTIC.md` section 12]

### How Mana fits now

The advice is to skip it.
Stochastic is not built inside Mana, and the prize wording is "built with Mana".
The fit needs the founders' confirmation that it counts. [verified: `../STOCHASTIC.md` section 15]
Do not spend build time on it.

### Which old notes still apply

- The notes on what Mana is, the credits, and the prize wording still apply.
- Notes that tie the fit to plan search, Monte Carlo, forks for what-if plans, the eight situations, or the clause reader describe the earlier framing.

---

- Prize at Cal Hacks 13.0: best project wins $5,000, and every team using Mana gets 3 months of Pro, described as equivalent to Claude Max (source: pre-event email #3, 2026-10-22)
- Researched: 2026-10-22, from the email text only, no web research yet
## What they do
Mana describes itself as the fastest way to build a project: visualize ideas, test prototypes, build the real version, with no setup, API keys, or deploys. [self-reported, email #3]
It works inside Mana or alongside your own stack on GitHub. [verified: email #3]
## Update 2026-10-23 (Mana Slack post, from founder Behzad, self-reported)

The post says $5,000 for the best hack built with Mana, and every hacker gets $150 in credits.
This is Mana's first public release.
Mana is described as Notion plus Claude Code: a workspace where apps are built inside it, the apps can call AI agents (research, analyze data, take actions), and everything is multiplayer.
The post says you can start in a shared workspace to brainstorm and prototype, then build on your own stack, push to GitHub, and deploy on Vercel.
Starter pack and access code: `https://mana.space/a/calhacks`.
Two founders, Behzad and Shayan, are in the channel all weekend.
The email's "3 months of Pro" is not repeated in the post, so treat the credits as $150 per hacker.

The prize wording is "built with Mana", which is stricter than the email's "inside Mana or alongside your own stack".
No judging criteria were posted.

## Open questions
- What must a team do with Mana to be eligible for the $5,000? Does a prototype in Mana, then a build on our own stack, count?
- Are judging criteria published? Ask in the channel or at the booth.
- Is $150 per hacker usable for model calls in our own stack?

## Fit for Stochastic (inferred, 2026-10-23)

Status is maybe, leaning skip as a prize target.
Stochastic needs the gateway, Postgres with an audit log, and deterministic deal math under our control.
That is a custom stack, and Mana's no-setup model works against it.
The honest cheap use is brainstorming, research, and a throwaway prototype of the reviewer console, with the real build on our own stack.
That may not count as "built with Mana".
Claim the credits, and do not change the architecture for the prize.
No project code before Friday Oct 23, about 6pm, so check that Mana prototyping does not break that rule (the rule is in `../../logistics.md`).


## Research 2026-10-23: alongside-stack fit

Method note: mana.space is a client-rendered app, so WebFetch returned only the title "Mana" for every page, and WebSearch found no launch post, docs, blog, funding, or press for it.
The only public text found is in the site's own JavaScript bundle (https://mana.space/assets/index-BpVNh6jy.js, build time 2026-10-23T21:26Z, which includes the terms, privacy text, plan table, and runtime helper names), plus robots.txt and sitemap.xml.
Bundle findings describe what the client code references, not documented or supported features, so tag them as inferred in practice.
Do not confuse this with mana.am (an iPhone app-builder, GitHub org mana-am) or withmana.com, which are different products. [verified: https://github.com/mana-am/agent-presence never mentions mana.space]

### 1. What Mana is (public evidence)

- Self-description in page metadata: "Mana is your personal AI assistant and workspace. Research, organize knowledge, and build tools that remember your context and evolve with you." [verified: https://mana.space/assets/index-BpVNh6jy.js] (self-reported)
- Terms call it "a persistence-first, AI-powered workspace" that stores content, runs tasks through an AI assistant, generates interactive content, and optionally connects third-party services. [verified: same bundle]
- Sitemap lists only /landing, /privacy-policy, /terms-of-service, /support. No docs, blog, or API pages are public. [verified: https://mana.space/sitemap.xml]
- Plans in the client code: Free $0 (5 credits), Pro $50/month (50 credits), Max $200/month with an "Alpha" price of $150. [verified: bundle] (self-reported)
  The "$150 in credits" in the founders' post may map to that Max alpha price. [inferred]
- Settings search terms list integrations: Google, Gmail, Calendar, Notion, GitHub, Slack, Granola, Microsoft, iMessage, Anthropic, OpenAI, "API Keys & Variables", "Mana API Keys", and bring-your-own-key providers. [verified: bundle] Whether the GitHub integration pushes code is not documented. [inferred: the string is a settings keyword only]
- Runtime helpers exposed to in-Mana apps include a credential-aware `fetch`, `connectors`, OAuth helpers, `uploadFile`, Firebase and Yjs sync (multiplayer), and in-browser Python (Pyodide). [verified: bundle] A Mana server API at server-prod.mana.space exists, and this is the likely route for external calls. [inferred]
- Not found: public API docs, webhooks, a documented GitHub export, a Vercel deploy flow, founders' bios (Behzad and Shayan), funding, hackathon rules, judging criteria, and past winners. The bundle names a Vercel project owner (behzadhaghgoos), which only suggests Behzad is a founder. [inferred]

### 2. Hackathon rules and "built with Mana"

- Nothing public. No prior Mana hackathon, no rules page, no winners found. [not found]
- The only wording is the email ("inside Mana or alongside your own stack") and the Slack post ("best hack built with Mana"), both already recorded above.
- "Alongside" is the team's belief and Cayden will confirm. Until then treat eligibility as unconfirmed.

### 3. Alongside patterns

Pattern A: Reviewer console prototype in Mana, calling our gateway.
- Steps: (1) stand up one read-only gateway endpoint over a public tunnel or Vercel URL with a demo token. (2) In Mana, build a page that lists work items and shows an approve and reject button. (3) Approve and reject POST to our gateway, which stays the only writer and enforces limits. (4) Keep the real console in our repo as the fallback.
- Hours: 3 to 5 if Mana's fetch can reach an external HTTPS URL (unverified), plus 2 for the tunnel and token.
- Risks: unknown egress rules, CORS, and credential handling. Mana apps may hold the token client side, so use a scoped demo token only. Console logic must stay thin, since limits and audit live in the gateway.
- Core impact: none if the gateway is the only writer. Our console can ship without Mana.

Pattern B: Deal-room workspace (read-only view plus comments).
- Steps: (1) export a deal snapshot (clauses, simulation summary, audit rows) as JSON or Markdown from our backend. (2) Load it into a shared Mana workspace for reviewers to annotate. (3) Paste decisions back by hand, or through the gateway.
- Hours: 2 to 3.
- Risks: a second place for human decisions splits the audit trail. Only the gateway write counts as the decision.
- Impact: low. Weak as a "built with Mana" claim because Mana holds notes, not behavior.

Pattern C: Team research notes and the answer key.
- Steps: put Organogenesis clause notes, the trap list, and the answer-key draft in a Mana workspace, then export to our repo as JSON.
- Hours: 1 to 2 (account setup, import).
- Risks: weakest claim for the prize. Export format is unknown (not found). The answer key must live in our repo as the source of truth.
- Impact: none. This is the cheapest honest use.

Pattern D: A Mana agent as an extra reader of the demo output (for example, summarizing the memo for the reviewer).
- Hours: 3 to 4. Risk: adds a non-deterministic model on the approval path. Not recommended for the core flow.

### 4. Risks

- First public release, so expect bugs and rate limits. The client has "monthly_credits_exhausted" and a weekly "advanced" query limit, and the free plan is only 5 credits. [verified: bundle]
- Privacy: the terms grant Mana a license to host and use Your Content "to operate, provide, secure, maintain, and improve the Services". The privacy text says providers do not train on data and that Google user data is not used for model training. [verified: bundle, self-reported] Public SEC filings are fine. Put no credentials, private emails, or `funding/` material into Mana.
- Lock-in: no documented export of apps or code. Mana apps seem to run on Mana's runtime (Firebase, Pyodide, in-browser JavaScript). Mana-generated code may not run on our stack without rework. [inferred]
- Reliability on demo day: console depending on Mana plus a tunnel is two points of failure. Keep the repo console as fallback.
- Rule check: logistics.md bars project code before Friday 6pm. Mana prototyping of the console would count as project work, so wait until the window opens. Research and notes are fine.

### 5. Fit with Hyphenate judging

- Hyphenate wants a system of work: a gateway as the only writer, limits enforced in code, an append-only audit trail, and real approval moments. [verified: ../Stochastic/README.md]
- A Mana-built console helps only if it is a thin client that calls the gateway, so the approval is a recorded, denied-or-allowed transition. It hurts if Mana holds logic, state, or the approval record, because that moves limits and audit outside our code.
- It does not help "real enough" or "would you hire it". Judges see the loop, not the tool that drew the buttons. A Mana console is neutral to slightly risky for the Hyphenate score and a possible plus for the Mana prize. [inferred]

### Recommendation

Claim the credits and make a free account now.
Do the cheapest honest pattern: C (notes and answer-key draft), then A only after the code window opens and only if Mana confirms external calls work.
Do not move any logic into Mana, and do not change the architecture for the $5,000.
Pitch Mana honestly as the prototype and review surface, never as the engine.
If the founders say "built with Mana" requires the core inside Mana, skip the prize.

### Questions for the Mana founders

1. Does "built with Mana" count if the backend, database, and agents run on our own stack and Mana is used for the reviewer console or shared workspace?
2. Is there a minimum amount of the project that must live in Mana, and how do judges check it?
3. Can a Mana app call an external HTTPS API with a bearer token? Any CORS, egress, or secret-storage limits?
4. Can Mana apps receive webhooks or run server-side code, or are they client-only?
5. How does export to GitHub work, and is the output runnable code or a Mana-runtime bundle? Can we run it on Vercel without Mana?
6. What do the $150 credits cover (model calls only?), do they expire, and can they power calls from our own stack?
7. What are the rate and usage limits during the hackathon, and which plan do we get?
8. Is a shared workspace limited to team members, and can a judge view it read-only?
9. What are the judging criteria and who judges the Mana prize?
10. What happens to our content in a workspace after the event, and can we delete it?
