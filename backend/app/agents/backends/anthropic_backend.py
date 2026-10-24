"""The Anthropic backend: Claude with tool use. The real model path and the stage fallback for Droid.

The agent gets the role's system prompt, the typed input as JSON, the role's tools (which call the gateway),
and one extra tool, `submit`, whose input schema is the role's output type. The loop ends when `submit` is called.
The session transcript from the store is replayed first, so the agent keeps context across work items.
"""
from __future__ import annotations

import json
import os
from typing import Any

from pydantic import BaseModel

from app.agents.roles import Role
from app.agents.settings import role_model
from app.tools.finance import TOOL_DESCRIPTIONS

TOOL_SCHEMAS: dict[str, dict] = {
    "consolidate": {"type": "object", "properties": {}, "additionalProperties": False},
    "tie_out": {"type": "object", "properties": {"run_id": {"type": "string"}}, "required": ["run_id"],
                "additionalProperties": False},
    "ebitda": {"type": "object", "properties": {}, "additionalProperties": False},
    "covenant_debt": {"type": "object", "properties": {"naive": {"type": "boolean"}}, "additionalProperties": False},
    "leverage": {"type": "object", "properties": {"debt_run_id": {"type": "string"}, "ebitda_run_id": {"type": "string"}},
                 "required": ["debt_run_id", "ebitda_run_id"], "additionalProperties": False},
    "limit_test": {"type": "object", "properties": {"leverage_run_id": {"type": "string"}},
                   "required": ["leverage_run_id"], "additionalProperties": False},
}


def _tool_defs(role: Role) -> list[dict]:
    defs = [{"name": n, "description": TOOL_DESCRIPTIONS[n], "input_schema": TOOL_SCHEMAS[n]} for n in role.tools]
    schema = role.output_type.model_json_schema()
    defs.append({"name": "submit", "description": f"Submit the final typed result ({role.output_type.__name__}). "
                                                  "Call exactly once, when done.", "input_schema": schema})
    return defs


def run_anthropic(role: Role, inp: BaseModel, call_tool, transcript: list[dict] | None = None) -> tuple[BaseModel, dict]:
    import anthropic  # imported here so the scripted backend works without the package

    client = anthropic.Anthropic()
    model = role_model("ANTHROPIC_MODEL", role.name) or "claude-haiku-5-5"
    memory = ""
    if transcript:
        memory = "\n\nYour earlier turns (most recent last):\n" + "\n".join(
            f"- {t.get('item')}: {t.get('summary')}" for t in transcript[-10:])
    messages: list[dict[str, Any]] = [{"role": "user", "content": f"Work item input (JSON):\n{inp.model_dump_json()}{memory}"}]
    tools = _tool_defs(role)
    usage = {"input_tokens": 0, "output_tokens": 0, "turns": 0, "model_requested": model, "model_confirmed": True}
    for _ in range(12):
        # The Mapper's typed result (every line's mapping and covenant tag) passed 16K output tokens on Haiku 5.5
        # and came back truncated. Streaming lets the cap go to 64K without an HTTP timeout.
        with client.messages.stream(model=model, max_tokens=64000, system=role.system, tools=tools,
                                    messages=messages) as stream:
            resp = stream.get_final_message()
        usage["input_tokens"] += resp.usage.input_tokens
        usage["output_tokens"] += resp.usage.output_tokens
        usage["turns"] += 1
        if resp.stop_reason == "max_tokens":
            raise RuntimeError(f"anthropic output hit max_tokens after {resp.usage.output_tokens} tokens; the result was cut off")
        messages.append({"role": "assistant", "content": resp.content})
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            if resp.stop_reason == "end_turn":
                messages.append({"role": "user", "content": "Call the submit tool with the typed result."})
                continue
            raise RuntimeError(f"anthropic stop_reason {resp.stop_reason} without a tool call")
        results = []
        for tu in tool_uses:
            if tu.name == "submit":
                out = role.output_type.model_validate(tu.input)
                return out, usage
            try:
                run = call_tool(tu.name, dict(tu.input))
                content = json.dumps({"run_id": run.run_id, "outputs": run.outputs}, default=str)
                results.append({"type": "tool_result", "tool_use_id": tu.id, "content": content})
            except Exception as error:  # the gateway's refusal goes back to the model as a tool error
                results.append({"type": "tool_result", "tool_use_id": tu.id, "content": f"error: {error}", "is_error": True})
        messages.append({"role": "user", "content": results})
    raise RuntimeError("anthropic backend did not submit within 12 turns")
