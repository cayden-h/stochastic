# Factory (Cal Hacks 13.0)
- Prize at Cal Hacks 13.0: Best Use of the Factory Droid SDK, $2,000 cash for the whole team, plus $200 in Factory credits and swag per team member (Factory Slack post, 2026-10-23, self-reported)
- Researched: 2026-10-15, Slack update 2026-10-23

## Update 2026-10-23 (Factory Slack post)

Track name in the post: "Building with the Droid SDK".
Cash is $2,000 for the whole team, not per member.
Credits are for running the Droid agent, for running apps with the agent SDK, and for spinning up remote machines to run agents in.
That fills the earlier gap "credit amount not found".
Opening keynote is by Eno, the CTO (Friday 4 to 6pm).
Workshop on the Droid SDK is Friday 6 to 7pm in the Theater.
The Hyphenate workshop follows at 7pm in the same room.
There is a booth for help getting started.
SDK link: `https://github.com/Factory-AI/droid-sdk-typescript`.
No rubric was posted, so the "Judging signals" below stay inferred.

### Fit for Stochastic (inferred, 2026-10-23)

Status is maybe, below Microsoft and Tiger Data.
Droid is a coding-agent harness, and Stochastic agents are finance agents, so the "why Factory?" question is real.
The honest answer is the approval gate and the tool boundary.

SDK pieces that map to the design (APIs verified in the sections above, the mapping is inferred):
- `permissionHandler` maps to the gateway as the only writer.
  A denied call becomes a logged denied action, and E1 to E6 route to the human reviewer.
- In-process tools from `createSdkMcpServer` hold the deterministic deal math, the clause quote validator, and the Monte Carlo run.
  The LLM calls them and never produces numbers.
- `fork()` and `rewind()` map to what-if structures, next to Tiger Data forks.
- The streamed `tool_call` and `tool_result` events feed the audit log and the reviewer console.
- Session IDs support "prove every step months later".

Weak points:
- The SDK repo warns that APIs are in flux, so pin a version.
- It needs the `droid` CLI, Node 18+, and a Factory API key.
- Whether the sessions can run Claude models is unconfirmed.
- A single `run()` call behind a chat box would lose.

Decision rule: ask the booth at the 6pm workshop whether non-coding use qualifies, whether Claude models are available, and what the rubric is.
Integrate only if each sub-agent (clause reader, structuring, risk, memo) can run as a droid session with our custom tools and `permissionHandler` can feed our escalation queue.
Cap the integration at about 3 hours.
If it does not fit, take the credits as free agent compute and drop the prize.
The credits are worth about $800 for four members (self-reported).

## What they do
Factory sells an agent-native software development platform whose agents are called droids.
Droids take whole engineering tasks (backlog work, PR review, tests, incident investigation) across CLI, desktop, web, Slack, Jira, Linear, and CI. [verified: https://factory.com/]
Products named on the site are Droid CLI, Missions (long-running multi-phase work), Automations, and a Public API. [verified: https://factory.com/]
The site also lists human approval checkpoints and multiple model providers. [verified: https://factory.com/]
## What they sell or ship that a hacker can touch
- TypeScript SDK: `npm install @factory/droid-sdk`, Node-specific APIs from `@factory/droid-sdk/node`.
  Needs Node 18+ and the `droid` CLI on PATH. [verified: https://docs.factory.com/sdk/typescript]
- Python SDK that runs a local droid subprocess, with one-shot runs, sessions, streaming. [verified: https://docs.factory.ai/sdk/python]
- Auth via `FACTORY_API_KEY` env var or an `apiKey` option. [verified]
- APIs: `run()`, `createSession()`, `resumeSession()`, `session.stream()`, `listModels()`, `listSessions()`, plus `fork()`, `compact()`, `rewind()`. [verified]
- Approval hooks: `permissionHandler` (ProceedOnce / ProceedAlways / Cancel), `askUserHandler`, `disabledToolIds`, autonomy levels Off/Low/Medium/High. [verified]
- Hooks are configured in `.factory/hooks.json` and the SDK streams hook events but cannot register hooks programmatically. [verified]
- Free tier, signup flow, and hackathon credit amounts: not found.
## Track brief and judging analysis

### Official prompt
The Cal Hacks 13.0 prompt text is not published anywhere we could reach.
The Devpost page returned HTTP 403 to fetch, and no search result quoted a Factory challenge.
The only official wording is the prize name, "Best Use of the Factory Droid SDK".
[verified: Devpost fetch blocked 2026-10-15; prize name from `CalHacks/ideation/tracks.md`]
Full criteria are due on the Live Site when hacking starts, so ask the Factory booth on day one for the rubric and the credit amount.
[verified: Hacker Guide note in `CalHacks/ideation/tracks.md`]

### How Factory frames and judges at other events
No Factory hackathon prompt, rubric, or winner list turned up in search (Devpost, Factory blog, general web).
[verified: searches 2026-10-15 returned only company coverage]
Factory's founders met at a hackathon in San Francisco, so the company knows the format, but that does not tell us its rubric.
[verified: https://www.latent.space/p/the-ai-coding-factory - podcast coverage]
Anything below about how Factory judges is [inferred] from the prize name and the SDK surface.

### What Factory sells and wants to showcase
The SDK is the same agent harness that powers the Droid CLI, desktop app, and web platform, exposed to your own code.
[verified: https://docs.factory.ai/sdk/typescript]
The surface that matters: `run()`, `createSession()`, `resumeSession()`, streaming messages (`tool_call`, `tool_result`, `assistant`), `fork()`, `compact()`, `rewind()`, `permissionHandler`, `askUserHandler`, autonomy levels, and in-process MCP tools made with `tool()` and `createSdkMcpServer()`.
[verified: https://docs.factory.com/sdk/typescript.md]
The repo ships 19 Node examples, and its README says a major overhaul is in progress and APIs may change.
[verified: https://docs.factory.com/sdk/typescript.md; GitHub README via search result]
Factory's strategic push is droids that take whole engineering tasks with human approval checkpoints, across many surfaces.
[verified: https://factory.com/]
So Factory wants to see third parties embed its harness as a component and build something that makes droids more trustworthy or more useful in a team.
[inferred]

### Judging signals
- Depth of SDK integration is the one signal the prize name states outright: "Use of the Droid SDK". [inferred]
- A demo moment where the SDK does something the CLI alone cannot do (programmatic permission gating, forked sessions, custom in-process tools, a UI around the stream) should read as "best use". [inferred]
- Novelty and business story are unstated.
  Factory sells to engineering orgs, so a believable team-workflow story probably helps. [inferred]
- Rubric weights: not published.
  Do not assume the Fetch.ai style percentages apply.

### What a winning entry looks like
It is a product whose core loop is driven by the Droid SDK from code, not a wrapper that shells out to `droid`.
Several droid sessions run in parallel, forked from one base session, with their tool calls and permission decisions streamed into a live UI.
A human approves or rejects at least one risky action live through `permissionHandler`, and the audit trail of that decision is visible afterward.
The team can say in one sentence what the SDK made possible, and they show a custom tool built with `createSdkMcpServer`.
[inferred]

### What loses
Using the Droid CLI only, or calling `run()` once behind a chat box.
Treating the SDK as interchangeable with the Claude Agent SDK, so a judge asks "why Factory?" and gets no answer.
Demos that depend on the SDK staying stable when the repo says APIs are in flux, with no pinned version and no recorded fallback.
[inferred]

### Honest fit with git for AI coding
This is our strongest fit of the six, and it is honest.
The SDK gives us the exact hooks a provenance layer needs: the permission handler sees each tool use before it runs, the stream records what ran, `DroidResult` carries `sessionId`, `turnCount`, and `tokenUsage` that can anchor a commit to a turn, and `fork()` models a branch of an agent conversation.
[verified: https://docs.factory.com/sdk/typescript.md for each API; the mapping to commits is inferred]
Gaps to plan around: the docs do not say whether results report which model ran when `modelId` is `auto`, fork and compact lineage is not exposed as metadata (we track parent and child ourselves), and observability events exclude prompts and tool inputs (we capture those from the stream).
[verified: https://docs.factory.com/sdk/typescript.md]
Anthropic's Scion is internal and monorepo-scale, so the small-team, per-line view is still open, and Factory is a coding-agent company that would plausibly care about it.
[inferred]

### Sharp ideas
1. Attribution-by-droid: wrap each droid session so every edit it makes lands as a Git commit whose trailer carries `sessionId`, turn number, model, and the approving human.
   A blame view shows "droid session 7, turn 3, approved by Ana" per line.
2. Fork-as-branch: map `fork()` to a Git branch, so two teammates each fork a shared droid session, and merging the branches merges the conversations and the code with the lineage kept.
## Past hackathon winners using them
None found.
A search for Factory Droid hackathon winners returned nothing relevant.
## Idea seeds
- Approval layer: a `permissionHandler` that routes every droid tool use to a human approval queue and writes each decision to a Git-backed audit log with per-action attribution.
- Droid PR-reviewer that commits a signed "who or what changed this" trailer per hunk, so agent and human edits are attributable in plain Git history.
- Multi-droid team board: small team assigns tasks, each droid session is forked per task, every session transcript is committed beside the diff.
- Finance agent: droid that reconciles a CSV ledger, proposes journal-entry fixes as patches, and blocks posting until a human approves.
- Spec-mode planner: use read-only spec mode output as a reviewable change request before any write is allowed.
- CI incident droid that opens a fix PR and attaches its full tool-use trace as the audit record.
## Risks and open questions
- SDK repo warns its APIs are in flux, and docs moved from docs.factory.ai to docs.factory.com. [verified by redirect and mirror README]
- Needs the `droid` CLI installed and a Factory account and API key; confirm hackathon credits and key distribution at the booth.
- Unknown whether "credits" cover model usage for the whole weekend.
- Confirm judging rubric and whether CLI-only use qualifies.
## Sources
- https://factory.com/
- https://docs.factory.com/sdk/typescript
- https://docs.factory.ai/sdk/python
- https://docs.factory.com/sdk/typescript.md (fetched 2026-10-15, SDK capabilities)
- https://www.latent.space/p/the-ai-coding-factory (founder background)

## Research 2026-10-23: Droid SDK integration

Sources fetched 2026-10-23: the TypeScript SDK reference and README, the Python SDK page, the droid exec page, and the pricing page.
SDK reference: `https://github.com/Factory-AI/droid-sdk-typescript` (README and `docs/typescript-sdk-reference.md`), `https://docs.factory.com/sdk/typescript.md`.
Docs moved to docs.factory.com, and docs.factory.ai now returns a 308 redirect. [verified: https://docs.factory.ai/pricing.md redirects to https://docs.factory.com/pricing.md]
Fetches go through a summarizing model, so exact wording and signatures need a check against the installed package types.

### What the SDK is (facts)

- Install: `npm install @factory/droid-sdk`, import Node APIs from `@factory/droid-sdk/node`.
  License Apache 2.0. [verified: https://github.com/Factory-AI/droid-sdk-typescript]
- Node 20+ is recommended.
  The package declares Node 18, but 0.10.0 needs global Web Crypto, which Node 18 lacks without `--experimental-global-webcrypto`. [verified: same README]
- Use SDK 0.10.0 or later. 0.9.1 and earlier can reject newer protocol messages.
  MCP tools need matching protocol versions in the npm package and the CLI. [verified: https://raw.githubusercontent.com/Factory-AI/droid-sdk-typescript/main/docs/typescript-sdk-reference.md, https://docs.factory.com/sdk/typescript.md]
- Sessions start the `droid` CLI from PATH (or `execPath`), so the CLI is required.
  Auth is `FACTORY_API_KEY` or an `apiKey` option. [verified: README]
- Zod 3 (`zod@^3.24.0`) is needed for structured output and SDK MCP tools. [verified: https://docs.factory.com/sdk/typescript.md]
- GitHub releases page says "There aren't any releases here", so release dates are not found.
  Version 0.10.0 is named in the docs.
  The repo had 2 open issues and 4 open PRs, contents not read. [verified: https://github.com/Factory-AI/droid-sdk-typescript/releases]
- `droid.unstable` APIs may change between releases.
  Earlier notes say the README warns of an overhaul, which this fetch did not re-confirm. [verified: reference doc for unstable; overhaul warning from 2026-10-15 notes above]
- Python SDK: `pip install droid-sdk`, Python 3.10+, asyncio only, local subprocess sessions only, one turn at a time per session, hooks via files only.
  Version not stated. [verified: https://docs.factory.com/sdk/python]
- Examples: folders `examples/node` and `examples/browser`.
  Only `daemon-session.ts` and `mission.ts` were named in the fetch.
  The 19-example count is not re-verified.
  Live examples use credits. [verified: README]

### API surface relevant to us

- `run(prompt, opts)` returns a result with `success`, `text`, `error`, and `structuredOutput`.
  `createSession()`, `resumeSession()`, and `session.stream()` give multi-turn work. [verified: README, https://docs.factory.com/sdk/typescript.md]
- `permissionHandler({ toolUses, options })` may be sync or async and returns `ProceedOnce`, `ProceedAlways`, or `Cancel`.
  Throwing, returning an unoffered value, or omitting the handler cancels the request.
  `autoRejectPermissionRequests` also exists. [verified: https://docs.factory.com/sdk/typescript.md]
- `askUserHandler({ questions })` returns answers, or `{ cancelled: true, answers: [] }`.
  With no handler, AskUser requests are declined. [verified: same]
- Autonomy: Off asks before every action, Low allows file edits and read-only commands, Medium allows reversible commands, High allows commands without prompts. [verified: same]
- `fork()`, `compact()`, `rewind()` each return a successor session, and the old wrapper then throws `SessionReplacedError`.
  Do not replace a session mid-stream. [verified: same]
- `tool(name, description, zodShape, handler)` and `createSdkMcpServer({ name, tools })`, passed as `mcpServers: [server]`.
  The SDK runs an authenticated loopback server and closes it with the session.
  Tool calls still follow autonomy and permission rules.
  Reattach the server on resume. [verified: same]
- `systemPrompt` as a string replaces Droid's default behavioral prompt.
  The preset `{ type: 'preset', preset: 'droid', append }` keeps the default. [verified: same]
- `outputFormat` with a JSON Schema gives `structuredOutput` typed `unknown`.
  It can be missing on success, and failure uses subtype `error_structured_output`. [verified: same]
- Hooks live in `.factory/hooks.json`, are streamed as `Hook` messages, and cannot be registered from code. [verified: reference doc]
- Observability events exclude prompts and tool inputs. [verified: reference doc]

### Models

- `modelId` is a string.
  Omitted means the Droid default.
  `auto` lets Factory pick per turn.
  `custom:<name>` uses a BYOK model from `~/.factory/settings.json`.
  `listModels()` shows the account catalog. [verified: https://docs.factory.com/sdk/typescript.md]
- No built-in model IDs are listed in the SDK docs, and the pricing page names no Claude, GPT, or Gemini models.
  Whether Claude or Gemini is available to our key: not found.
  `listModels()` answers it in one minute. [verified: https://docs.factory.com/pricing.md]
- BYOK accepts your own OpenAI or Anthropic keys, local models, and Bedrock routing.
  Keys stay local.
  Custom models appear only in the CLI.
  Whether BYOK works through the SDK is not confirmed beyond the `custom:` model ID. [verified: https://docs.factory.ai/model-independence/byok]
- Non-coding tasks: no rule found either way.
  The droid exec page shows non-coding examples (read-only analysis and reports), so general reasoning runs are normal use. [verified: https://docs.factory.com/cli/droid-exec/overview.md]
- Remote machines: the SDK reference shows REST helpers for machine templates and computers (create, list, restart) and `listRemoteSessions` only, with remote-session support listing only.
  No guide for running agents there.
  Python is local only. [verified: reference doc]
- Billing in the public plans: Standard Usage first, then a free Droid Core pool, then prepaid Extra Usage.
  SDK is included in Pro, Plus, and Max.
  Token multipliers per model are not published on that page.
  The hackathon credits are separate and self-reported. [verified: https://docs.factory.com/pricing.md]

### Can a session be restricted to only our tools? (question 2)

- TypeScript: only the subtractive `disabledToolIds` is documented, and the reference says there is no allowlist.
  Tool IDs named in the docs are `Execute`, `Create`, `ApplyPatch`.
  Edit, Read, Grep, Glob, WebSearch IDs are not confirmed in the SDK docs. [verified: reference doc]
- `session.listTools()` returns each tool with `id`, `allowed`, `source` (native, mcp, connector).
  Use it to build the disable list at runtime.
  A new built-in tool added later would slip through a deny list. [verified: https://docs.factory.com/sdk/typescript.md for the API; the slip-through risk is inferred]
- Python: `SessionConfig` has `enabled_tools`, `disabled_tools`, `restrict_tools`, and `additional_tools`.
  `restrict_tools` is an allowlist that never grants extra permission.
  This is the cleanest "only our tools" path. [verified: https://docs.factory.com/sdk/python]
- droid exec has `--only-tools` for an exact list, and MCP tools are named `MCP:<server>/<tool>`.
  `droid exec --list-tools` prints the set. [verified: https://docs.factory.com/cli/droid-exec/overview.md]
- Honest answer: pure reasoning agent with only our writes is plausible, but the safe version is defense in depth.
  Disable every tool `listTools()` reports except ours, set autonomy Off, and make `permissionHandler` cancel anything not from our server.
  Also give the DB role used by our tools the only write grant, so the model's other paths cannot write. [inferred]
- Even then, the gateway stays the real writer.
  The droid session never holds a DB credential, only our tool process does. [inferred]

### Integration patterns (question 3, hours are inferred estimates)

(a) Every sub-agent is a droid session with our MCP tools.
- Steps: spike one session with a `lookup` tool and structured output (1h), port clause reader (2h), then structuring, risk, memo (1.5h each), stream events into the reviewer console (2h), `permissionHandler` to escalation rows (1.5h).
  Total about 10 to 12h.
- Risk: highest.
  The master agent and the typed work-item loop would depend on a CLI subprocess per agent, on SDK APIs in flux, and on one account's rate limits.
  Concurrent sessions are not documented as supported or limited. [inferred]
- Upside: strongest "Best Use of the Droid SDK" story.

(b) Only clause reader and memo on Droid.
- Steps: build the two tools plus structured output schemas (3h), one session per task, stream to console (1.5h), fallback switch to our own LLM call (1h).
  Total about 5 to 6h.
- Risk: medium.
  The two agents are text-heavy and low in math, so a swap is cheap.
- Honest story: Droid reads long documents and drafts memos, our tools hold facts and numbers.

(c) One agent on Droid plus `permissionHandler` feeding the escalation queue.
- Steps: pick the clause reader, give it tools `search_clauses`, `quote_validate`, `propose_finding` (2h), handler writes a denied-action row and raises an E-level item (1.5h), console panel (1h), fallback (1h).
  Total about 4 to 5h.
- Risk: low to medium.
  Fits the 3-hour cap in this file only if the console panel is reused.
- Honest story: the handler is a second line of defense behind the gateway.

(d) Credits only.
- Steps: ask booth to confirm credits can be used outside Droid, or use Droid for dev work (reading EDGAR text, drafting tests). 0 to 1h.
- Risk: none.
  Forfeits the $2,000 prize.
  Value about $200 per member, self-reported.

Illustrative and unverified sketch for (a), adapted from the documented patterns, not compiled:

```ts
import { createSession, createSdkMcpServer, tool, ToolConfirmationOutcome } from '@factory/droid-sdk/node';
import { z } from 'zod';

const gw = createSdkMcpServer({ name: 'stochastic', tools: [
  tool('read_work_item', 'Read a typed work item', { id: z.string() }, ({ id }) => gateway.read(id)),
  tool('submit_result', 'Submit result via gateway', { id: z.string(), payload: z.any() },
    async (a) => JSON.stringify(await gateway.submit(a.id, a.payload))),
]});

const session = await createSession({
  mcpServers: [gw], autonomyLevel: 'Off', modelId: 'auto',
  disabledToolIds: (await probeNativeToolIds()).filter((id) => id !== 'MCP'), // names unverified
  systemPrompt: { type: 'preset', preset: 'droid', append: 'You are the clause reader. Use only stochastic tools.' },
  permissionHandler: async ({ toolUses, options }) => {
    for (const u of toolUses) {
      if (!String(u.toolName ?? u.details?.type).startsWith('stochastic')) {   // field names unverified
        await gateway.record({ type: 'denied_action', agent: 'clause_reader', detail: u });
        return ToolConfirmationOutcome.Cancel;
      }
    }
    return options.includes(ToolConfirmationOutcome.ProceedOnce) ? ToolConfirmationOutcome.ProceedOnce : ToolConfirmationOutcome.Cancel;
  },
});
for await (const m of session.stream('Work item WI-1')) audit.append(m);
```

- The enum import, the shape of `toolUses` entries, the autonomy value type, and MCP tool ID names are all unconfirmed.
  Verify with `listTools()` and the package types on Friday after 6pm.

### Hackathon rules, judging, winners (question 4)

- Rules and rubric: not found.
  Devpost was blocked earlier and searches on 2026-10-23 found no Factory hackathon rubric or winners.
  The only official wording is the prize name and the Slack post (self-reported).
- Stated preference about non-coding use: not found.
  Cayden plans to confirm that using Droid beside our own stack is allowed.

### Risks and how a judge sees it (question 5)

- "Why Factory for a finance agent?"
  Honest answer: Droid is a harness with a permission gate, a tool boundary, streamed tool events, and session IDs, and finance needs those properties.
  Do not claim Droid understands finance. [inferred]
- A judge may still read it as bolted on.
  Mitigation: show one live denied action in the reviewer console and the audit row, and say what the SDK made possible in one sentence. [inferred]
- API instability: pin the exact version in `package.json`, commit the lockfile, and record the CLI version. [inferred]
- Key distribution: one `FACTORY_API_KEY` on a shared machine or per-member keys.
  Never in git or the frontend.
  Needs booth answer on how hackathon credits attach to keys. [inferred]
- Credit expiry and limits: unknown.
  Public plans use rolling 5-hour, 7-day, and 30-day windows, so a heavy demo run could hit a limit mid-weekend. [verified: https://docs.factory.com/pricing.md for the windows; relevance to hackathon credits inferred]
- CLI fails live: keep a recorded run of the Droid-backed step, a config flag that routes the same work item to our own model call, and cached outputs for the demo deal.
  Rehearse the switch once.
  Tell the judges the switch exists. [inferred]
- Process fragility: subprocess exits raise `ProcessExitError`, and `ConcurrentStreamError` fires if a session streams twice.
  Wrap each call with retry then fallback. [verified: https://docs.factory.com/sdk/typescript.md for error names; the wrapper is inferred]

### Recommendation

Do pattern (c), growing to (b) only if the first spike works by hour 3.
Keep the gateway and deal math ours, run the clause reader on Droid with only our tools, and show `permissionHandler` writing a denied-action row into the escalation queue.
Skip (a): 10 or more hours for the highest risk, and it puts the deal manager on a subprocess.
Take the credits whatever happens, and drop the Factory prize if the spike fails.
Do not start project code before Friday about 6pm.

### Questions for Cayden to ask Factory at the workshop

1. Does a finance agent that uses Droid sessions beside our own Postgres gateway qualify for "Building with the Droid SDK", and is there a rubric or a rule that coding use is required?
2. Which models does our key list through `listModels()`, including Claude and Gemini, and does BYOK work through the SDK?
3. Is there a supported allowlist in the TypeScript SDK (like Python `restrict_tools`) to leave only our MCP tools, and what are the tool IDs for built-ins and for MCP tools?
4. How do the $200 credits attach to keys, do they cover SDK runs on remote machines, when do they expire, and what are the rate limits for four teammates running sessions at once?
5. Which SDK version and `droid` CLI version should we pin, and what is changing in the overhaul?
6. How many concurrent sessions can one key run, and is there a supported way to run the SDK on a remote machine for a demo?

## Update 2026-10-23 (evening): account, plan, and the build decision

Facts from Cayden (verified by the user's own statement, not by me):
- Cayden created a Factory account and has the Plus plan.
- The CLI install command from Factory is `curl -fsSL https://app.factory.ai/cli | sh`.
- Cayden will build the agent layer with the Droid SDK.
  The agent text in the Hyphenate demo will mostly be hardcoded.

What this changes:
- The Droid SDK needs the `droid` CLI on `PATH`.
  The SDK starts it as a subprocess, so the CLI install is a hard requirement for the build machine. [verified: https://github.com/Factory-AI/droid-sdk-typescript]
- The SDK reads `FACTORY_API_KEY`.
  Keep the key in `.env`, which is git-ignored.
  Never put it in git, the frontend, or a URL.
- The install command pipes a remote script into the shell.
  Read the script before you run it on a shared or demo machine. [inferred: general safe practice]
- The Plus plan limits are not in our notes.
  Whether the hackathon credits ($200 per member, self-reported) add to Plus or replace it is unknown.
  Ask at the workshop.

Open build choices (the agent-framework comparison is in `../research/agent-framework-options.md`):
- Use the Droid SDK only as the agent runner.
  Keep the gateway, the deal math, and the audit log in Python.
- Factory also ships a Python Droid SDK, so the whole backend can stay in one language.
  It has `run(prompt, output=PydanticModel)`, in-process `@tool` tools that can call our REST gateway, and a real allowlist (`restrict_tools`).
  The TypeScript SDK has no allowlist. [verified: https://docs.factory.com/sdk/python.md]
- Prefer the Python SDK over the TypeScript one.
  This replaces the earlier idea of a TypeScript runner that calls the Python gateway. [inferred]
- Write one `run_agent(role, item)` function with two backends, switched by `AGENT_BACKEND`.
  The Anthropic API is the real path and the stage fallback.
  The Droid SDK handles the agents that run through it.
  Claim "built with Droid" only for runs that went through it. [inferred, from the framework report]
- Run each agent once per work item.
  Agents are stateful (decided 2026-10-24): the backend keeps one Droid session per role and the gateway keeps the policies, so a session may be resumed. [inferred]
- Skip A2A.
  Agents pass work items through the gateway, and A2A adds a second path. [inferred]
- Keep a recorded output and a config flag that routes the same work item to a plain model call, in case the CLI fails live.

Still unconfirmed, ask at the 6pm Friday workshop:
1. Which models the key lists through `listModels()`, and whether Claude models are available.
2. Whether use beside our own stack qualifies for the Factory prize, and what the rubric is.
3. How the hackathon credits attach to a Plus account, when they expire, and what the rate limits are for four people.

## Update 2026-10-24: Factory's Cal Hacks deck

Source: https://factory-davidgu.github.io/calhacks13/ (a 12-slide intro by David G. of Factory, titled "Put an agent in your hack").
We read the deck's `slides.json`.
The deck is Factory's own material, so claims here are self-reported by Factory.

What the deck confirms:
- Setup has three steps: install the CLI with `curl -fsSL https://app.factory.ai/cli | sh`, add the SDK with `npm install @factory/droid-sdk`, and create a key at `app.factory.ai/settings/api-keys`.
  Node 20 or later is needed. [verified: deck slide 3]
- The SDK starts `droid` for you, so the CLI must be on `PATH`.
  The SDK reads `FACTORY_API_KEY` from the environment. [verified: deck slide 3]
- `run(prompt, options)` is a one-shot call, and `run()` closes its session.
  Our first Droid backend uses it per work item; per-role session resume is the next step. [verified: deck slide 4]
- Structured output works in the TypeScript SDK with `outputFormat` and a JSON Schema from Zod, and the result is in `result.structuredOutput`. [verified: deck slide 5]
- `createSession()` keeps context across prompts.
  We do not use it. [verified: deck slide 6]
- A daemon (`droid daemon --port 37643`) lets a web page run sessions through `connectToDaemon()`.
  We do not need it.
  The deck warns not to put a real API key in a public web page. [verified: deck slide 7]
- Factory lists "Multi-agent apps" as a use case: run several sessions at once and let one agent hand work to the others.
  This fits our replicable agents. [verified: deck slide 8]

Credits:
- The cover slide has a link to a Google Form to claim Factory credits: https://docs.google.com/forms/d/e/1FAIpQLSd90bta_Gj7szptt1sprHlO2mz_t-ZGeXHWO0e-p_rcuh2fgQ/viewform
- Each team member who wants credits must submit the form with their own details.
  We did not submit it. [verified: deck slide 1]
- The amount and the expiry are not in the deck.
  The earlier Slack post said $200 per member. [self-reported, Slack 2026-10-23]

What the deck does not say:
- It has no prize rules, no judging criteria, and no model list.
  The prize rubric is still unknown.
- It does not mention a tool allowlist.
  The framework report says the Python SDK has `restrict_tools` and the TypeScript SDK has none. [verified: `../research/agent-framework-options.md`]

Risks for us (inferred):
- Droid is a coding agent.
  The deck says it works in the current directory, reads files, and uses its tools.
  A finance agent must not get that access.
  Run each agent in an empty working directory, and allow only our tools.
- The deck teaches the TypeScript SDK, and the Factory prompt on slide 3 says "Use the typescript Factory Droid SDK".
  Our plan uses the Python SDK.
  If a judge expects TypeScript, say that the Python SDK is also from Factory.
- If the Python SDK fails to install or run, the fallback is a small TypeScript runner that the Python gateway calls.
  The `anthropic` backend remains the main fallback.

Updated to-do:
1. Each team member claims credits with the form, if they want them.
2. Cayden runs `list_models()` and tests one `run()` call with structured output, in an empty directory.
3. Cayden tests the tool allowlist (`restrict_tools`) before any finance data goes in.

## Update 2026-10-24, 03:30: the probe and the first Droid run

Cayden installed the `droid` CLI (0.249.0) and the agent ran `scripts/droid_probe.py` and `scripts/record_run.py --backend droid`. [verified: terminal output]

- `list_models()` on our key returns 60 or so models, including Claude: `claude-fable-5.1`, `claude-fable-5`, `claude-opus-5-5`, `claude-opus-5-5-fast`, `claude-opus-5`, `claude-opus-4-8`, `claude-opus-4-7`, `claude-opus-4-6`, `claude-sonnet-5-5`, `claude-sonnet-5`, `claude-sonnet-4-6`, `claude-haiku-5-5`, plus GPT-5.x, Gemini 3.x and 4, Mistral, GLM, Kimi, Qwen, DeepSeek, Grok.
  So Droid can run Claude on this key.
  The open question is closed.
- One `run()` with a Pydantic `output=` returned a typed result in one turn, in an empty temp directory with `restrict_tools=["none"]`.
- The whole deal ran on `AGENT_BACKEND=droid` with `DROID_MODEL=claude-sonnet-5-5`: the Mapper mapped the lines, the Preparer called `consolidate`, `ebitda`, `covenant_debt`, and `leverage` through our in-process MCP server, the Reviewer called `tie_out` and `limit_test`, and the verdict was 0.77x against 2.50x with Reviewer pass.
  The default `restrict_tools` guess (tool names with and without the `MCP:stochastic/` prefix) worked.
- First-run finding: the Mapper on Sonnet 5.5 decided the financing liability exclusions itself and raised six small flags (subtotals, short-term borrowings).
  The prompt now says exclusions are the controller's call and subtotals are never flagged.
  The second run is recorded in `backend/recordings/`.

What the SDK made possible, in one sentence for the pitch: one Droid session per role with only our gateway tools allowed (`restrict_tools`), a typed result per work item (`output=` Pydantic), and an empty working directory so a coding agent never sees a file.
