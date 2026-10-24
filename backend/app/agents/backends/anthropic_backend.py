"""The Anthropic backend: Claude with tool use. The real model path and the stage fallback for Droid.

The agent gets the role's system prompt, the typed input as JSON, the role's tools (which call the gateway),
and one extra tool, `submit`, whose input schema is the role's output type. The loop ends when `submit` is called.
For the Mapper, `submit` is a strict tool built per work item: every line id is an enum of the ids in the input,
so the API cannot return a line id that does not belong (the gateway refused `sl_001`, a platform id, as a target).
The session transcript from the store is replayed first, so the agent keeps context across work items.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.agents.roles import READER_TOOL_DESCRIPTIONS, Role
from app.core.models import MapperInput
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
    "get_section": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"],
                    "additionalProperties": False},
    "get_definition": {"type": "object", "properties": {"term": {"type": "string"}}, "required": ["term"],
                       "additionalProperties": False},
}
DESCRIPTIONS = {**TOOL_DESCRIPTIONS, **READER_TOOL_DESCRIPTIONS}


def _obj(props: dict) -> dict:
    """A strict-mode object: every property required, no others allowed."""
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def _nullable(schema: dict) -> dict:
    return {"anyOf": [schema, {"type": "null"}]}


def mapper_submit_schema(inp: MapperInput) -> dict:
    """The Mapper's submit schema for one work item, in the form strict tool use accepts.

    It mirrors MapperOutput, with three changes: line ids and platform line names are enums from the input;
    optional fields are required but nullable; and FlagOption's dicts (which strict mode cannot express) are lists
    of pairs, turned back into dicts by `mapper_output_from_submit`. Confidence bounds are checked by pydantic.
    """
    target_ids = [l.id for l in inp.target_lines]
    deal_ids = target_ids + [l.id for l in inp.platform_lines]  # the gateway lets a tag name any line of the deal
    platform_names = list(dict.fromkeys(l.line for l in inp.platform_lines))
    tag = {"type": "string", "enum": ["debt", "not_debt", "unclear", "na"]}
    platform_line = _nullable({"$ref": "#/$defs/platform_line"})
    defs = {
        "target_line_id": {"type": "string", "enum": target_ids},
        "line_id": {"type": "string", "enum": deal_ids},
        "platform_line": {"type": "string", "enum": platform_names},
        "evidence": _obj({"quote": {"type": "string"}, "page": _nullable({"type": "integer"}),
                          "document_id": _nullable({"type": "string"})}),
        "option": _obj({
            "id": {"type": "string"}, "label": {"type": "string"},
            "tags": {"type": "array", "description": "For covenant_tag flags: the tag for each flagged line.",
                     "items": _obj({"line_id": {"$ref": "#/$defs/line_id"}, "tag": tag})},
            "platform_line": platform_line,
            "mappings": {"type": "array", "description": "For mapping flags over several lines: each target line's "
                                                          "platform line.",
                         "items": _obj({"target_line_id": {"$ref": "#/$defs/target_line_id"},
                                        "platform_line": platform_line})},
        }),
    }
    return {
        "$defs": defs,
        **_obj({
            "mappings": {"type": "array", "items": _obj({
                "target_line_id": {"$ref": "#/$defs/target_line_id"},
                "platform_line": platform_line,
                "confidence": {"type": "number", "description": "Between 0 and 1."},
                "reason": {"type": "string"},
                "policy_id": _nullable({"type": "string"}),
            })},
            "tags": {"type": "array", "items": _obj({
                "line_id": {"$ref": "#/$defs/line_id"}, "tag": tag, "note": {"type": "string"},
                "policy_id": _nullable({"type": "string"}),
            })},
            "flags": {"type": "array", "items": _obj({
                "kind": {"type": "string", "enum": ["covenant_tag", "mapping"]},
                "line_ids": {"type": "array", "items": {"$ref": "#/$defs/line_id"}},
                "question": {"type": "string"},
                "evidence": {"type": "array", "items": {"$ref": "#/$defs/evidence"}},
                "options": {"type": "array", "items": {"$ref": "#/$defs/option"}},
                "default": _nullable({"type": "string"}),
            })},
            "note": {"type": "string"},
        }),
    }


def mapper_output_from_submit(raw: dict) -> dict:
    """Turn the strict schema's lists of pairs back into FlagOption's dicts."""
    out = json.loads(json.dumps(raw))
    for flag in out.get("flags", []):
        for opt in flag.get("options", []):
            opt["tags"] = {t["line_id"]: t["tag"] for t in opt.get("tags") or []}
            opt["mappings"] = {m["target_line_id"]: m["platform_line"] for m in opt.get("mappings") or []}
    return out


def _tool_defs(role: Role, inp: BaseModel | None = None) -> list[dict]:
    defs = [{"name": n, "description": DESCRIPTIONS[n], "input_schema": TOOL_SCHEMAS[n]} for n in role.tools]
    submit = {"name": "submit", "description": f"Submit the final typed result ({role.output_type.__name__}). "
                                               "Call exactly once, when done."}
    if isinstance(inp, MapperInput):
        submit.update(input_schema=mapper_submit_schema(inp), strict=True)
    else:
        submit["input_schema"] = role.output_type.model_json_schema()
    defs.append(submit)
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
    tools = _tool_defs(role, inp)
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
                raw = mapper_output_from_submit(tu.input) if isinstance(inp, MapperInput) else tu.input
                out = role.output_type.model_validate(raw)
                return out, usage
            try:
                run = call_tool(tu.name, dict(tu.input))
                content = json.dumps({"run_id": run.run_id, "outputs": run.outputs}, default=str)
                results.append({"type": "tool_result", "tool_use_id": tu.id, "content": content})
            except Exception as error:  # the gateway's refusal goes back to the model as a tool error
                results.append({"type": "tool_result", "tool_use_id": tu.id, "content": f"error: {error}", "is_error": True})
        messages.append({"role": "user", "content": results})
    raise RuntimeError("anthropic backend did not submit within 12 turns")
