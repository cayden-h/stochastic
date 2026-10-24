# Agent framework options for Stochastic (researched 2026-10-23)

Scope: the agent layer only.
Design under test: three small stateless agents (Mapper, Preparer, Reviewer) plus a human approver, one work item in and one typed result out per run, a Python FastAPI gateway as the only DB writer, deal math as code tools, and a 30 second demo with mostly hardcoded text.
Tags: VERIFIED means a source URL was fetched on 2026-10-23.
Fetches pass through a summarizing model, so exact signatures need a check against the installed package.
INFERRED means our own judgment.

## Short answer

1. The most important new fact is that Factory ships a Python Droid SDK, not only the TypeScript one.
   It has one-shot `run()`, Pydantic structured output, in-process custom tools, and an allowlist (`restrict_tools`).
   VERIFIED: https://docs.factory.com/sdk/python.md
   This removes the main reasons the TypeScript SDK looked awkward for a Python backend.
   The earlier note in `../sponsors/factory.md` said Python is "local subprocess only", which is still true, and that is fine for a demo laptop.
2. Factory's model catalog lists Claude, GPT, and Gemini families.
   VERIFIED: https://docs.factory.com/cli/user-guides/choosing-your-model.md
   Whether our own key sees them is still answered only by `list_models()`.
3. Cheapest honest path: write our own thin `run_agent(work_item) -> typed result` function in Python, with two interchangeable backends behind it (Anthropic API direct, and Droid Python SDK).
   The Droid backend lets us truthfully say "agents run on the Factory Droid SDK" for the prize, and the direct backend is the stage fallback.
   INFERRED.
4. We do not need A2A.
   We may use MCP, but only if a framework needs it to reach our gateway tools.

## What A2A and MCP are for

MCP (Model Context Protocol) is an open standard for connecting AI applications to external systems such as data sources, tools, and workflows.
VERIFIED: https://modelcontextprotocol.io/docs/getting-started/intro
In our design MCP is the way an agent calls a tool, for example `compute_irr` or `submit_result`.

A2A (Agent2Agent) is an open protocol for communication and interoperability between opaque agentic applications, originally from Google and donated to the Linux Foundation.
VERIFIED: https://a2a-protocol.org/latest/
The same page says MCP is for agent-to-tool communication and A2A is for agent-to-agent communication, and that the two are complementary.
VERIFIED: https://a2a-protocol.org/latest/

Do we need A2A?
No.
Our agents never talk to each other directly.
Each reads one work item from the gateway and writes one typed result back through the gateway, so the gateway is the only coordination point.
A2A solves discovery and delegation between separately owned agents, which we do not have.
INFERRED.
Possible pitch line if asked: "the work-item queue plays the role A2A plays between vendors, and we could expose an agent card later."
That is a roadmap statement, not something to build.

## Comparison table

| Option | Language | One-shot typed output | MCP tools | Claude models | Setup effort | Stage risk |
|---|---|---|---|---|---|---|
| 1a Factory Droid SDK, Python | Python 3.10+, asyncio | `run(prompt, output=PydanticModel)` | Yes, in-process `@tool` plus HTTP, SSE, stdio | Catalog lists Claude, check `list_models()` | Medium, about 2 to 3 hours | Medium |
| 1b Factory Droid SDK, TypeScript | TypeScript, Node 20+ | `outputFormat` JSON Schema, `structuredOutput` is `unknown` | Yes, `tool()` plus `createSdkMcpServer` | Same as 1a | Medium to high, needs a Node sidecar | Medium to high |
| 2 Google ADK | Python, plus TS, Go, Java, Kotlin | `output_schema` plus `include_contents='none'` | Yes, `McpToolset` | Yes via `LiteLlm("anthropic/...")` | Medium | Medium |
| 3a Anthropic API plus tool use | Python | `output_config.format` json_schema, or `messages.parse()` with Pydantic | Via MCP connector or our own tool defs | Native | Low, about 1 hour | Low |
| 3b Claude Agent SDK | Python, TypeScript | `output_format` json_schema, `ResultMessage.structured_output` | Yes, in-process `@tool` | Native | Medium, runs the Claude Code binary | Medium |
| 4 OpenAI Agents SDK | Python | `output_type=PydanticModel` | Yes, hosted, streamable HTTP, stdio | Only through beta LiteLLM or any-llm adapters | Low to medium | Medium for Claude, low for OpenAI models |
| 5 Hand-written loop | Python | Whatever we write, using option 3a's schema feature | Not needed | Native | Low, 1 to 2 hours | Lowest |

## Option 1: Factory Droid SDK

### Facts

- TypeScript: `npm install @factory/droid-sdk`, imports from `@factory/droid-sdk/node`, needs the `droid` CLI.
  VERIFIED: https://docs.factory.com/sdk/typescript.md and `../sponsors/factory.md`.
- Python: `pip install droid-sdk`, Python 3.10+, `droid` on PATH, and either an authenticated CLI or `FACTORY_API_KEY`.
  VERIFIED: https://docs.factory.com/sdk/python.md
- `run()` starts a session, runs one turn, and cleans up, and the result is a value with a `success` flag.
  VERIFIED: https://docs.factory.com/sdk/python.md
  The TypeScript docs say the same: `run()` creates a session, consumes the stream, returns the terminal result, and closes the session.
  VERIFIED: https://docs.factory.com/sdk/typescript.md
  This matches our stateless one-work-item-per-run design directly.
- Structured output, Python: pass a Pydantic `BaseModel` as `output=`, and "if output was requested, `RunSuccess` guarantees `result.output` is set".
  Raw JSON Schema is also accepted through `JsonSchema(...)`.
  VERIFIED: https://docs.factory.com/sdk/python.md
- Structured output, TypeScript: `outputFormat` with `OutputFormatType.JsonSchema`, read from `result.structuredOutput` (typed `unknown`, may be missing on success).
  Invalid output produces a failed result with subtype `error_structured_output`.
  VERIFIED: https://docs.factory.com/sdk/typescript.md
- Does it force structured output?
  The docs call it a requested output format with a failure subtype for invalid output, which implies validation after the fact.
  Whether it is constrained decoding or validate-and-retry is not stated.
  INFERRED.
  Always validate again in the gateway with our own Pydantic model.

### Custom tool that calls our REST gateway

Python, in-process, documented pattern (adapted, not compiled):

```python
import httpx
from droid_sdk import SessionConfig, run
from droid_sdk.mcp import create_sdk_mcp_server, tool

@tool("get_work_item", "Fetch one work item and its inputs from the gateway.")
async def get_work_item(item_id: str) -> str:
    async with httpx.AsyncClient(base_url=GATEWAY, headers=AUTH) as c:
        return (await c.get(f"/work-items/{item_id}")).text

@tool("compute_irr", "Deterministic IRR. The model must never do deal math.")
async def compute_irr(cashflows: list[float]) -> str:
    async with httpx.AsyncClient(base_url=GATEWAY, headers=AUTH) as c:
        return (await c.post("/tools/irr", json={"cashflows": cashflows})).text

server = create_sdk_mcp_server(name="stochastic", tools=[get_work_item, compute_irr])
result = await run(prompt, output=MapperResult,
                   config=SessionConfig(mcp_servers=[server], restrict_tools={...}))
```

- The `@tool` decorator "derives JSON Schema from type annotations", and tools may be sync or async.
  VERIFIED: https://docs.factory.com/sdk/python.md
- Install the extra with `pip install "droid-sdk[mcp]"`.
  VERIFIED: https://docs.factory.com/sdk/python.md
- External servers (for example a FastAPI MCP mount) also work through `HttpMcpServerConfig(name=..., url=...)`, with headers supported.
  VERIFIED: https://docs.factory.com/sdk/python.md
- TypeScript equivalent: `tool(name, description, zodShape, handler)` and `createSdkMcpServer({ name, tools })`, passed as `mcpServers: [server]`.
  Tool calls still follow autonomy and permission rules.
  VERIFIED: https://docs.factory.com/sdk/typescript.md
- The Python `restrict_tools` field is a real allowlist that never elevates permission.
  The TypeScript SDK has only subtractive `disabledToolIds` and "does not expose a restrictive allowlist".
  VERIFIED: https://docs.factory.com/sdk/python.md and https://docs.factory.com/sdk/typescript.md
  So for "agents can only call our tools", Python is the better binding.
- Python limits: asyncio only, local subprocess only, one turn at a time per session, hooks only through files.
  VERIFIED: https://docs.factory.com/sdk/python (also recorded in `../sponsors/factory.md`).
- Exact MCP tool ID strings for `restrict_tools` are not confirmed.
  The droid exec docs name MCP tools `MCP:<server>/<tool>`, but the Python SDK may differ.
  VERIFIED for the droid exec naming: `../sponsors/factory.md`.
  Check with a `list_tools()` probe in the first spike.

### Models

- Model IDs are plain strings, availability depends on account and organization policy, and `"auto"` picks a model per prompt.
  `list_models()` shows what a key can select.
  VERIFIED: https://docs.factory.com/sdk/python.md
- The Factory model guide lists Claude (including Sonnet 5.5, Opus 5.5, Haiku 5.5), GPT, Gemini, and xAI families, plus BYOK custom models.
  VERIFIED: https://docs.factory.com/cli/user-guides/choosing-your-model.md
  Whether the hackathon credits and our key can use the Claude models: not verified.
- This partly resolves the earlier note "whether sessions can run Claude models is unconfirmed" in `../sponsors/factory.md`, but only at the catalog level.

### Setup time

About 2 to 3 hours for one agent, from install to a typed result through our gateway tools.
INFERRED.
The Python SDK removes the Node sidecar, which the TypeScript route would have needed next to FastAPI.

### Risks on stage

- It spawns a subprocess of the `droid` CLI, so a CLI crash, auth expiry, or credit limit appears live.
  VERIFIED that it is a subprocess: https://docs.factory.com/sdk/python.md
  Mitigation: recorded run plus the direct-API backend flag (see recommendation).
- Latency of a full coding-agent harness per call is likely higher than a bare API call, and we have no measurement.
  INFERRED.
- API stability: the TypeScript README warns APIs are in flux, and Python SDK version is not stated in the docs.
  VERIFIED for TypeScript: `../sponsors/factory.md`.
  Pin versions and record the CLI version.
- Droid is a coding harness, so default prompts and tools are coding-flavored.
  Use `restrict_tools` and a replacing system prompt.
  INFERRED.
- Rate and credit windows may bite during a rehearsal-heavy weekend.
  VERIFIED that public plans use rolling windows: https://docs.factory.com/pricing.md (via `../sponsors/factory.md`).

### Prize and credit angle

- Prize: "Best Use of the Factory Droid SDK" ("Building with the Droid SDK"), $2,000 cash for the whole team, plus $200 in Factory credits and swag per member.
  Credits cover running the Droid agent, running apps with the agent SDK, and spinning up remote machines.
  Self-reported, Factory Slack post 2026-10-23, as recorded in `../sponsors/factory.md`.
  Not independently verified, and no rubric was posted.
- Does the Python SDK qualify as "the Droid SDK"?
  Not stated.
  The prize text names the SDK generically, but this must be asked.
  INFERRED.
- Truthful claim: if every agent run really goes through `droid_sdk.run()` with our tools, "our agents run on the Factory Droid SDK" is true.
  Do not claim it if the demo path used the fallback backend, or say so plainly.

## Option 2: Google ADK (Python)

- ADK is an open-source agent framework available in Python, TypeScript, Go, Java, and Kotlin.
  VERIFIED: https://adk.dev/
- Models: Gemini first, adapters for other providers.
  For Claude, wrap with `LiteLlm(model="anthropic/<model>")` and set `ANTHROPIC_API_KEY`.
  Needs `litellm>=1.84`.
  VERIFIED: https://adk.dev/agents/models/litellm/
  The same page carries a security advisory about malicious LiteLLM releases 1.82.7 and 1.82.8, so pin a clean version.
  VERIFIED: https://adk.dev/agents/models/litellm/
- Typed one-shot: `output_schema` accepts a Pydantic model, and `include_contents='none'` makes the agent see only its instruction and the current input, which suits stateless tasks.
  VERIFIED: https://adk.dev/agents/llm-agents/
- Catch: `output_schema` plus tools in one request is model-dependent.
  The docs say only specific models such as Gemini 3.0 support both together, and for others ADK uses a `set_model_response` tool that "may not work reliably".
  VERIFIED: https://adk.dev/agents/llm-agents/
  Our agents need tools (deal math) and typed output together, so this matters, especially with Claude through LiteLLM.
- MCP: `McpToolset` with stdio, streamable HTTP, or SSE, plus `tool_filter` to limit visible tools.
  VERIFIED: https://adk.dev/tools-custom/mcp-tools/
- A2A: ADK documents exposing and consuming A2A agents.
  VERIFIED: https://adk.dev/ (navigation only, body text not read).
- Setup: about 2 to 4 hours including Runner and session boilerplate, which is heavier than we need for stateless calls.
  INFERRED.
- Stage risk: medium.
  Extra moving parts (Runner, session service, LiteLLM) around a one-call job.
  INFERRED.
- Prize angle: nothing verified.
  A web search found no Cal Hacks 13.0 Google ADK or Gemini prize.
  The local `../../../CalHacks/ideation/tracks.md` lists only an MLH "Best Use of Gemini API" (MLH swag kits) at Cal Hacks 13.0 plus a Google Intelligent Eyewear overall placement.
  VERIFIED: local file `tracks.md` read 2026-10-23, which cites Devpost and the Hacker Guide.
  Using Gemini for one real call would qualify for the free MLH item per that file, but that does not require ADK.
  INFERRED.

## Option 3: Anthropic API with tool use, or the Claude Agent SDK

### 3a Plain Anthropic API (Python)

- Structured output: put a JSON Schema in `output_config.format` with `type: "json_schema"`, and the response text is valid JSON matching the schema.
  `client.messages.parse()` with a Pydantic `output_format` returns `parsed_output` and is the recommended method.
  VERIFIED: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Strict tool use: `strict: true` on a tool definition guarantees inputs match `input_schema`.
  The two features can be combined in one request.
  VERIFIED: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
  This directly removes the ADK problem above.
- Constraints: objects need `additionalProperties: false`, recursive schemas and numeric or length constraints are not supported in the raw API, refusal or max_tokens stops can break the schema, and the first request with a new schema has grammar compile latency (cached 24 hours).
  VERIFIED: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
  Warm every schema once before the demo.
  INFERRED.
- Tools: client tools run in our app, and the tool runner (beta) can drive the loop.
  Tool results go back as `tool_result` blocks.
  VERIFIED: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
- MCP: an MCP connector lets the Messages API reach remote MCP servers without a separate client.
  VERIFIED (named on the tool use overview): https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
  Not needed for us, since our tools are our own Python functions.
- Setup: about 1 hour.
  INFERRED.
- Stage risk: low, a single HTTPS call.
  INFERRED.
- Credit angle: Anthropic hackers get $50 of Claude API credits, and Anthropic is a presenting sponsor, but its only listed prize is "Claude for Public Benefit", a poor fit for Stochastic.
  VERIFIED as recorded: local `tracks.md` (self-reported, Anthropic staff).

### 3b Claude Agent SDK (Python)

- `pip install claude-agent-sdk`.
  `query()` starts a new session per call with no memory by default, which suits stateless runs.
  VERIFIED: https://code.claude.com/docs/en/agent-sdk/python
- Structured output: `output_format={"type": "json_schema", "schema": ...}`, result on `ResultMessage.structured_output`, with an `error_max_structured_output_retries` subtype.
  VERIFIED: https://code.claude.com/docs/en/agent-sdk/python
- Tools: `@tool` plus `create_sdk_mcp_server()`, passed through `mcp_servers`.
  `allowed_tools` only auto-approves and "does not restrict Claude to only these tools", so use `disallowed_tools` or permission settings to lock down.
  VERIFIED: https://code.claude.com/docs/en/agent-sdk/python
- It runs the Claude Code binary as a subprocess (the options include a path to the Claude Code CLI).
  VERIFIED: https://code.claude.com/docs/en/agent-sdk/overview
  Same shape of risk as Droid, with no sponsor prize for us.
- Auth: use API key authentication, and Anthropic does not allow claude.ai login in third-party products.
  VERIFIED: https://code.claude.com/docs/en/agent-sdk/overview
- Verdict: no advantage over 3a for three stateless agents, and it adds a subprocess.
  INFERRED.

## Option 4: OpenAI Agents SDK (Python)

- `pip install openai-agents`.
  VERIFIED: https://openai.github.io/openai-agents-python/
- Structured output: `output_type` accepts Pydantic, dataclasses, lists, TypedDict, and the result is read from `result.final_output` after `Runner.run`.
  VERIFIED: https://openai.github.io/openai-agents-python/agents/
- MCP: hosted tools, streamable HTTP (`MCPServerStreamableHttp`), and stdio, with SSE deprecated.
  VERIFIED: https://openai.github.io/openai-agents-python/mcp/
- Claude models: only through LiteLLM or any-llm adapters, both documented as best-effort beta.
  The docs warn to validate the exact backend if you depend on structured outputs or tool calling, because some providers accept JSON mode but not a given `json_schema`.
  VERIFIED: https://openai.github.io/openai-agents-python/models/
  Claude plus typed output plus tools through a beta adapter is the exact combination the docs warn about.
- Prize angle: none found for Cal Hacks 13.0, and the tracks file lists no OpenAI prize.
  VERIFIED by absence in local `tracks.md`, which is not proof that none exists.
- Verdict: fine only if we choose OpenAI models, which would leave the Anthropic ecosystem and win nothing.
  INFERRED.

## Option 5: Hand-written loop

- A loop is: send messages and tool definitions, run any `tool_use` blocks against our Python functions, append `tool_result`, repeat until `end_turn`, then validate the final JSON with Pydantic.
  The mechanics are documented in the tool use overview.
  VERIFIED: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
- Roughly 40 lines, no subprocess, and full control over audit logging into the gateway.
  INFERRED.
- Best fit for the "stateless, replicable, one work item in, one typed result out" design because the function is the contract.
  INFERRED.
- No prize angle by itself.

## Recommendation for a solo builder with a Python backend

1. Define the contract first: `run_agent(role, work_item) -> TypedResult`.
   Each of Mapper, Preparer, and Reviewer is a role (system prompt, tool list, Pydantic result type) plus a function.
   The gateway stores the result, and nothing else writes.
2. Build backend A on the plain Anthropic API with `messages.parse()` and tools as Python functions.
   This is the real, low-risk path, and it is the stage fallback.
3. Build backend B on the Factory Droid Python SDK behind the same function, with our gateway-calling `@tool` functions, `restrict_tools`, and `output=<same Pydantic model>`.
   Cap this at about 3 hours, matching the cap already set in `../sponsors/factory.md`.
   Pick one agent (the Reviewer or the Mapper) to run on B for the live moment, and keep the other two on A unless the spike goes smoothly.
4. Switch by an environment flag, `AGENT_BACKEND=droid|anthropic`, and keep a recorded run for the demo.
5. Say "built with the Factory Droid SDK" only about the agent runs that actually went through B.
   Ask Factory whether the Python SDK qualifies for the prize before spending the 3 hours.
6. Skip ADK and the OpenAI Agents SDK, since neither offers a verified prize or a native Claude path.
   Skip A2A, and use MCP only inside the Droid backend.

Why this is the cheapest truthful path: the direct-API backend is needed anyway for reliability, so the Droid backend costs only the adapter, and it is the only option with a verified sponsor prize connection (self-reported $2,000 and $200 per member).

Minimal code shape:

```python
async def run_agent(role: Role, item: WorkItem) -> BaseModel:
    backend = BACKENDS[os.environ.get("AGENT_BACKEND", "anthropic")]
    result = await backend(role.system, item.model_dump_json(), role.tools, role.result_type)
    return role.result_type.model_validate(result)   # gateway re-validates, then writes
```

## Open questions

1. For Factory at the 6pm Friday workshop, top question: does the Python `droid-sdk` qualify for "Building with the Droid SDK", and does a finance agent whose tools call our own gateway count, given that Droid is a coding harness?
2. Does our key's `list_models()` include Claude Sonnet and Haiku, and do the $200 credits cover them?
3. What are the exact MCP tool ID strings to pass to `restrict_tools`, and is the structured output constrained decoding or validate-and-retry?
4. What is typical latency for a one-turn `run()` with two tool calls, and how many concurrent `run()` calls can one key make?
5. For Cal Hacks organizers: is there a Google, Gemini, or ADK prize at 13.0 beyond the MLH "Best Use of Gemini API"?
   Not found in any source read today.

## Sources

- https://docs.factory.com/sdk/python.md
- https://docs.factory.com/sdk/typescript.md
- https://docs.factory.com/cli/user-guides/choosing-your-model.md
- https://adk.dev/
- https://adk.dev/agents/models/litellm/
- https://adk.dev/agents/llm-agents/
- https://adk.dev/tools-custom/mcp-tools/
- https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
- https://code.claude.com/docs/en/agent-sdk/python
- https://code.claude.com/docs/en/agent-sdk/overview
- https://openai.github.io/openai-agents-python/
- https://openai.github.io/openai-agents-python/agents/
- https://openai.github.io/openai-agents-python/mcp/
- https://openai.github.io/openai-agents-python/models/
- https://a2a-protocol.org/latest/
- https://modelcontextprotocol.io/docs/getting-started/intro
- Local: `../sponsors/factory.md`, `../sponsors/mana.md`, and `CalHacks/ideation/tracks.md`
