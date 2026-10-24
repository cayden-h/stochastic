"""The Factory Droid backend: the agent runs as a droid session with only our tools.

Each role keeps one Droid session (stateful): the first call creates it, later calls resume it by session id, so
the agent carries context across work items. Tools are an in-process MCP server whose handlers call the gateway,
`restrict_tools` allows nothing but them, and the working directory is an empty temp folder, because Droid is a
coding agent that reads files by default. Structured output uses the role's Pydantic output type.
Needs the `droid` CLI on PATH and FACTORY_API_KEY. Any failure raises, and the runner falls back.
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile

from pydantic import BaseModel

from app.agents.roles import Role
from app.agents.settings import role_model
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

        return {"consolidate": consolidate, "tie_out": tie_out, "ebitda": ebitda, "covenant_debt": covenant_debt,
                "leverage": leverage, "limit_test": limit_test}[name]

    def _call(name: str, args: dict) -> str:
        try:
            run = call_tool(name, args)
            return json.dumps({"run_id": run.run_id, "outputs": run.outputs}, default=str)
        except Exception as error:
            return json.dumps({"error": str(error)})

    for name in role.tools:
        droid_tools.append(tool(name, TOOL_DESCRIPTIONS[name], make(name)))
    return create_sdk_mcp_server(name="stochastic", tools=droid_tools), [t.name for t in droid_tools] if droid_tools else []


async def _run(role: Role, inp: BaseModel, call_tool, session_id: str | None):
    from droid_sdk import Autonomy, SessionConfig, run

    server, names = _build_server(role, call_tool)
    allow = os.getenv("DROID_RESTRICT_TOOLS")
    restrict = allow.split(",") if allow else ([f"stochastic/{n}" for n in names] + [f"MCP:stochastic/{n}" for n in names] + names)
    config = SessionConfig(mcp_servers=[server] if names else [], restrict_tools=restrict or ["none"],
                           autonomy=Autonomy.HIGH, system_prompt=role.system)
    prompt = f"Work item input (JSON):\n{inp.model_dump_json()}\nReturn the typed result."
    with tempfile.TemporaryDirectory(prefix="stochastic-droid-") as cwd:
        kwargs = dict(cwd=cwd, output=role.output_type, config=config,
                      timeout=float(os.getenv("DROID_TIMEOUT", "240")))
        model = role_model("DROID_MODEL", role.name)
        if model:
            kwargs["model"] = model
        result = await run(prompt, **kwargs)
    if not result.success or result.output is None:
        raise RuntimeError(f"droid run failed: {getattr(result, 'error', None)} "
                           f"{getattr(result, 'structured_output_error', None) or getattr(result, 'output_validation_error', None)}")
    return result.output, {"session_id": result.session_id, "turns": result.turn_count,
                           "duration": getattr(result, "duration", None)}


def run_droid(role: Role, inp: BaseModel, call_tool, session_id: str | None = None) -> tuple[BaseModel, dict]:
    """Synchronous wrapper. Runs the asyncio session in this thread."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    coro = _run(role, inp, call_tool, session_id)
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(asyncio.run, coro).result()
    return asyncio.run(coro)
