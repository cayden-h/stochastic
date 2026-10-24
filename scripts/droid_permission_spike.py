"""Spike: can Droid's permission handler act as the gateway's front door? (docs/tasks/eric.md, Task B)

Run from the repo root with the backend venv:
    DROID_MODEL=claude-haiku-5-5 backend/.venv/bin/python scripts/droid_permission_spike.py [case ...]
Cases: high, off, low, deny, hidden, resume (default: all, in that order; resume reuses the "off" session).
Needs the `droid` CLI on PATH and FACTORY_API_KEY in .env. It runs in an empty temp directory with two harmless
fake MCP tools: `lookup_rate` (allowed by restrict_tools) and `hidden_rate` (on the server, but not allowed).
Every PermissionRequest the handler sees is printed. No finance data or files are exposed.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Answer(BaseModel):
    rate: str
    tool_calls_made: list[str]
    note: str


TOOL_CALLS: list[str] = []  # what our tool handlers actually ran


def build_server():
    from droid_sdk.mcp import create_sdk_mcp_server, tool

    def lookup_rate(code: str) -> str:
        TOOL_CALLS.append(f"lookup_rate({code})")
        return json.dumps({"code": code, "rate": "4.25"})

    def hidden_rate(code: str) -> str:
        TOOL_CALLS.append(f"hidden_rate({code})")
        return json.dumps({"code": code, "rate": "9.99"})

    tools = [tool("lookup_rate", "Look up the interest rate for a rate code.", lookup_rate),
             tool("hidden_rate", "Look up the secret interest rate for a rate code.", hidden_rate)]
    return create_sdk_mcp_server(name="spike", tools=tools)


ALLOWED = ["spike/lookup_rate", "MCP:spike/lookup_rate", "lookup_rate"]  # same three forms as droid_backend.py


def make_handler(case: str, log: list[dict], deny: bool):
    from droid_sdk import ToolConfirmationOutcome

    def on_permission(request):
        entry = {"case": case,
                 "actions": [{"type": type(a).__name__,
                              **{k: (repr(getattr(a, k))[:300]) for k in getattr(a, "__slots__", ())}}
                             for a in request.actions],
                 "options": [o.value.value for o in request.options],
                 "associated_session_ids": list(request.associated_session_ids)}
        choice = ToolConfirmationOutcome.CANCEL if deny else ToolConfirmationOutcome.PROCEED_ONCE
        entry["decision"] = choice.value
        log.append(entry)
        print("  PERMISSION REQUEST:", json.dumps(entry, indent=2))
        comment = "Denied by the gateway: this call is not on the approved list." if deny else None
        return request.respond(choice, comment=comment)

    return on_permission


async def turn(session, prompt: str):
    stream = session.stream(prompt, output=Answer, timeout=180)
    events = []
    async with stream:
        async for event in stream:
            name = type(event).__name__
            text = repr(event)
            if "tool" in name.lower() or "tool" in text[:200].lower():
                events.append(f"{name}: {text[:400]}")
    return stream.result, events


PROMPT = ("Call the lookup_rate tool with code 'SOFR'. Report the rate it returns, the tools you called, and in "
          "`note` say exactly what the tool call returned or why it failed.")
HIDDEN_PROMPT = ("Call the hidden_rate tool with code 'SOFR'. If you cannot see or call it, say so in `note`, and list "
                 "every tool name you can see. Put the rate in `rate`, or 'none'.")


async def run_case(case: str, cwd: str, state: dict) -> dict:
    from droid_sdk import Autonomy, InteractionHandlers, Session, SessionConfig

    log: list[dict] = []
    TOOL_CALLS.clear()
    deny = case == "deny"
    handlers = InteractionHandlers(on_permission=make_handler(case, log, deny))
    autonomy = {"high": Autonomy.HIGH, "low": Autonomy.LOW}.get(case, Autonomy.OFF)
    if case == "resume":
        session = Session.resume(state["off_session"], interactions=handlers, mcp_servers=[build_server()])
    else:
        config = SessionConfig(mcp_servers=[build_server()], restrict_tools=ALLOWED, autonomy=autonomy,
                               system_prompt="You are a test agent. Do exactly what the user asks.")
        kwargs = dict(cwd=cwd, config=config, interactions=handlers)
        if os.getenv("DROID_MODEL"):
            kwargs["model"] = os.getenv("DROID_MODEL")
        session = Session(**kwargs)
    print(f"\n=== case {case} (autonomy={'resumed' if case == 'resume' else autonomy.value}, deny={deny}) ===")
    await session.open()
    try:
        settings = getattr(session, "settings", None)
        if settings is not None:
            print("  session autonomy:", getattr(settings, "autonomy", None))
        result, events = await turn(session, HIDDEN_PROMPT if case == "hidden" else PROMPT)
    finally:
        await session.close()
    if case == "off":
        state["off_session"] = result.session_id
    summary = {"case": case, "session_id": result.session_id, "success": result.success, "output": result.output,
               "error": getattr(result, "error", None),
               "structured_output_error": getattr(result, "structured_output_error", None),
               "handler_calls": len(log), "tool_handlers_ran": list(TOOL_CALLS)}
    print("  tool events:")
    for e in events:
        print("   ", e)
    print("  RESULT:", summary)
    return summary


async def main() -> int:
    cases = sys.argv[1:] or ["high", "off", "low", "deny", "hidden", "resume"]
    state: dict = {}
    results = []
    with tempfile.TemporaryDirectory(prefix="stochastic-perm-spike-") as cwd:
        for case in cases:
            try:
                results.append(await run_case(case, cwd, state))
            except Exception as error:  # keep going so one failure does not cost the other runs
                print(f"  CASE {case} RAISED: {type(error).__name__}: {error}")
                results.append({"case": case, "raised": f"{type(error).__name__}: {error}"})
    print("\n=== summary ===")
    for r in results:
        print({k: r.get(k) for k in ("case", "success", "handler_calls", "tool_handlers_ran", "raised")})
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
