"""The Factory Droid backend: the agent runs as a droid session with only our tools.

Each role keeps one Droid session (stateful): the first call creates it, later calls resume it by session id, so
the agent carries its conversation across work items and deals. A resumed session keeps its model, reasoning
effort, system prompt, and tool restriction; only the in-process MCP server is passed again. [verified: probe on
2026-10-24, the resumed turn recalled a word from the first turn without a tool call and listed the same tools]
Tools are an in-process MCP server whose handlers call the gateway, and `restrict_tools` allows nothing but them.
The working directory is an empty folder per role (`DROID_WORKDIR/<role>`), because Droid is a coding agent that
reads files by default, and a resumed session must find the folder it started in. Droid groups sessions by folder,
so each role's sessions sit together. If a session cannot be resumed, a new one starts and the meta says why.
Structured output uses the role's Pydantic output type.

Rewind before a retry: when the gateway refuses a result, the job runner retries once and passes `rewind_to`, the
id of the user message that started the refused turn (returned in the meta as `turn_message_id`). The resumed
session is rewound to before that message, so the refused answer is not in the agent's memory, and the retry runs
on the successor. `Session.rewind(message_id)` keeps every message before `message_id` and drops it and everything
after; it works on a session reopened with `Session.resume`; and the successor has a new session id, which the meta
returns as `session_id` so the store keeps it. [verified: `scripts/droid_rewind_probe.py` on 2026-10-24, Haiku 5.5:
after rewinding to the second turn's prompt, the successor recalled PELICAN and not HERON, and its CLI session record
holds no HERON] A new session's first turn also streams a `context-...` user message, which is not the turn's start.
[verified: same probe] If the rewind fails, the retry runs in the same session and the meta sets `rewind_error`.
Only the Mapper is rewound today; it has no tools, so whether a successor keeps the in-process MCP server is untested.
[inferred]
Needs the `droid` CLI on PATH and FACTORY_API_KEY. Any failure raises, and the runner falls back.
"""
from __future__ import annotations

import asyncio
import glob
import hashlib
import json
import os
import re

from pydantic import BaseModel

from app.agents.roles import READER_TOOL_DESCRIPTIONS, Role
from app.agents.settings import role_model, role_reasoning
from app.tools.finance import TOOL_DESCRIPTIONS


def _build_server(role: Role, call_tool):
    from droid_sdk.mcp import create_sdk_mcp_server, tool

    droid_tools = []

    def make(name: str):
        def consolidate() -> str:
            return _call(name, {})

        def tie_out(run_id: str) -> str:
            return _call(name, {"run_id": run_id})

        def ebitda() -> str:
            return _call(name, {})

        def covenant_debt(naive: bool = False) -> str:
            return _call(name, {"naive": naive})

        def leverage(debt_run_id: str, ebitda_run_id: str) -> str:
            return _call(name, {"debt_run_id": debt_run_id, "ebitda_run_id": ebitda_run_id})

        def limit_test(leverage_run_id: str) -> str:
            return _call(name, {"leverage_run_id": leverage_run_id})

        def get_section(id: str) -> str:  # noqa: A002 - the tool's argument name
            return _call(name, {"id": id})

        def get_definition(term: str) -> str:
            return _call(name, {"term": term})

        return {"consolidate": consolidate, "tie_out": tie_out, "ebitda": ebitda, "covenant_debt": covenant_debt,
                "leverage": leverage, "limit_test": limit_test, "get_section": get_section,
                "get_definition": get_definition}[name]

    def _call(name: str, args: dict) -> str:
        try:
            run = call_tool(name, args)
            return json.dumps({"run_id": run.run_id, "outputs": run.outputs}, default=str)
        except Exception as error:
            return json.dumps({"error": str(error)})

    for name in role.tools:
        droid_tools.append(tool(name, {**TOOL_DESCRIPTIONS, **READER_TOOL_DESCRIPTIONS}[name], make(name)))
    return create_sdk_mcp_server(name="stochastic", tools=droid_tools), [t.name for t in droid_tools] if droid_tools else []


WORKDIR = os.getenv("DROID_WORKDIR", os.path.expanduser("~/.cache/stochastic/droid"))


def role_dir(role_name: str) -> str:
    """An empty folder that belongs to one role and stays put, so its sessions can be resumed."""
    path = os.path.join(WORKDIR, role_name)
    os.makedirs(path, exist_ok=True)
    return path


async def _turn(session, prompt: str, output, timeout: float):
    """Run one turn. Returns the result and the id of the user message that started the turn: the id a later
    rewind needs to drop this turn. A new session's first turn also streams a `context-...` user message
    before the prompt, which is not the turn's start."""
    starts: list[str] = []
    stream = session.stream(prompt, output=output, timeout=timeout)
    async with stream:
        async for item in stream:
            if type(item).__name__ == "UserMessage" and not str(item.id).startswith("context-"):
                starts.append(item.id)
    return stream.result, (starts[0] if starts else None)


def setup_key(role: Role, model: str | None, effort: str | None, restrict: list[str]) -> str:
    """A fingerprint of what a session was opened with. A resumed session keeps its system prompt, model, effort,
    and tool list, so a session opened with an older setup is not resumed."""
    body = json.dumps([role.system, model, effort, sorted(restrict)])
    return hashlib.sha256(body.encode()).hexdigest()[:16]


async def _rewind(session, message_id: str, role: Role):
    """Drop `message_id` and every message after it. Rewind forks: the successor has a new session id and the old
    session is left as it was. Returns (successor, old session id)."""
    old_id = session.id
    outcome = await session.rewind(message_id, title=f"{role.name}: rewound before a refused turn")
    try:
        await session.close()
    except Exception:  # the old session may already be replaced or closed by the rewind
        pass
    return outcome.session, old_id


async def _run(role: Role, inp: BaseModel, call_tool, session_id: str | None, session_key: str | None = None,
               rewind_to: str | None = None):
    from droid_sdk import Autonomy, DroidError, Session, SessionConfig

    server, names = _build_server(role, call_tool)
    allow = os.getenv("DROID_RESTRICT_TOOLS")
    restrict = allow.split(",") if allow else ([f"stochastic/{n}" for n in names] + [f"MCP:stochastic/{n}" for n in names] + names)
    config = SessionConfig(mcp_servers=[server] if names else [], restrict_tools=restrict or ["none"],
                           autonomy=Autonomy.HIGH, system_prompt=role.system)
    prompt = f"Work item input (JSON):\n{inp.model_dump_json()}\nReturn the typed result."
    timeout = float(os.getenv("DROID_TIMEOUT", "90"))  # measured Mapper runs take 47 to 64 s; a hang must not stall the stage
    model = role_model("DROID_MODEL", role.name)
    effort = role_reasoning("DROID", role.name)
    key = setup_key(role, model, effort, restrict)

    def fresh():
        kwargs = dict(cwd=role_dir(role.name), config=config)
        if model:
            kwargs["model"] = model
        if effort:
            kwargs["reasoning_effort"] = reasoning_enum(effort)
        return Session(**kwargs)

    session, resumed, resume_error = None, False, None
    if session_id and session_key != key:
        resume_error = "the role's prompt, model, effort, or tools changed since this session started"
    elif session_id:
        session = Session.resume(session_id, mcp_servers=[server] if names else [])
        try:
            await session.open()
            resumed = True
        except DroidError as error:  # the session is gone or cannot load: start a new one
            resume_error = f"{type(error).__name__}: {error}"[:200]
            await session.close()
    rewound, rewound_from, rewind_error = False, None, None
    if rewind_to and resumed:
        try:
            session, rewound_from = await _rewind(session, rewind_to, role)
            rewound = True
        except Exception as error:  # keep the resumed session: the retry still runs, and the meta says why
            rewind_error = f"{type(error).__name__}: {error}"[:200]
    elif rewind_to:
        rewind_error = "no resumed session to rewind" + (f" ({resume_error})" if resume_error else "")
    if not resumed:
        session = fresh()
    try:
        if not resumed:
            await session.open()
        result, turn_message_id = await _turn(session, prompt, role.output_type, timeout)
    finally:
        await session.close()
    if not result.success or result.output is None:
        raise RuntimeError(f"droid run failed: {getattr(result, 'error', None)} "
                           f"{getattr(result, 'structured_output_error', None) or getattr(result, 'output_validation_error', None)}")
    usage = getattr(result, "usage", None)
    cost = {}
    if usage is not None:
        for k in ("input_tokens", "output_tokens", "cache_creation_tokens", "cache_read_tokens", "thinking_tokens",
                  "factory_credits"):
            v = getattr(usage, k, None)
            if v is not None:
                cost[k] = v
    served = served_model(result.session_id)
    return result.output, {"session_id": result.session_id, "session_key": key, "resumed": resumed,
                           "resume_error": resume_error, "turn_message_id": turn_message_id,
                           "rewound": rewound, "rewound_from_session": rewound_from,
                           "rewound_to_message": rewind_to if rewound else None, "rewind_error": rewind_error,
                           "turns": result.turn_count,
                           "duration": getattr(result, "duration", None), "model_requested": model or "droid default",
                           "reasoning_effort_requested": effort,
                           "model_served": served.get("model"), "reasoning_effort_served": served.get("reasoning_effort"),
                           "model_confirmed": bool(model) and served.get("model") == model, "usage": cost}


def reasoning_enum(effort: str):
    """The SDK takes its ReasoningEffort enum, not a string; a bad value raises here, before any session is opened."""
    from droid_sdk import ReasoningEffort
    try:
        return ReasoningEffort(effort)
    except ValueError as error:
        raise ValueError(f"DROID_REASONING_EFFORT {effort!r} is not one of {[e.value for e in ReasoningEffort]}") from error


SESSIONS_DIR = os.getenv("FACTORY_SESSIONS_DIR", os.path.expanduser("~/.factory/sessions"))


def served_model(session_id: str | None, sessions_dir: str | None = None) -> dict:
    """What the droid CLI wrote into its own session record: the model id and reasoning effort on each assistant
    message. The run result carries neither, so this is how a Droid run confirms its model. The record is local
    (`~/.factory/sessions/<cwd>/<session id>.jsonl`). Returns {} when the record is missing or names several models."""
    if not session_id:
        return {}
    root = sessions_dir or SESSIONS_DIR
    paths = glob.glob(os.path.join(root, "*", f"{session_id}.jsonl"))
    if not paths:
        return {}
    try:
        text = open(paths[0], encoding="utf-8").read()
    except OSError:
        return {}
    models = sorted(set(re.findall(r'"modelId"\s*:\s*"([^"]*)"', text)))
    efforts = sorted(set(re.findall(r'"reasoningEffort"\s*:\s*"([^"]*)"', text)))
    out: dict = {"path": paths[0]}
    if len(models) == 1:
        out["model"] = models[0]
    elif models:
        out["models"] = models
    if len(efforts) == 1:
        out["reasoning_effort"] = efforts[0]
    return out


def run_droid(role: Role, inp: BaseModel, call_tool, session_id: str | None = None,
              session_key: str | None = None, rewind_to: str | None = None) -> tuple[BaseModel, dict]:
    """Synchronous wrapper. Runs the asyncio session in this thread. `rewind_to` is the message id that started a
    turn to drop from the resumed session before this turn runs."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    coro = _run(role, inp, call_tool, session_id, session_key, rewind_to)
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(asyncio.run, coro).result()
    return asyncio.run(coro)
