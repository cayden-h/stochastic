"""The Anthropic Mapper's submit tool is strict, and its line ids are enums of the work item's own ids. No API call."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.agents.backends.anthropic_backend import _tool_defs, mapper_output_from_submit, mapper_submit_schema  # noqa: E402
from app.agents.roles import MAPPER_ROLE, PREPARER_ROLE  # noqa: E402
from app.core.models import MapperInput, MapperOutput  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402


def _mapper_input() -> MapperInput:
    store = MemoryStore()
    seed(store, Gateway(store))
    deal = store.deals[DEAL_ID]
    return MapperInput(deal_id=DEAL_ID, platform=deal.platform, target=deal.target,
                       target_lines=store.lines(DEAL_ID, deal.target),
                       platform_lines=store.lines(DEAL_ID, deal.platform), brief=deal.brief)


def _objects(node):
    if isinstance(node, dict):
        if node.get("type") == "object":
            yield node
        for v in node.values():
            yield from _objects(v)
    elif isinstance(node, list):
        for v in node:
            yield from _objects(v)


def test_mapper_enums_are_exactly_the_work_items_ids():
    inp = _mapper_input()
    defs = mapper_submit_schema(inp)["$defs"]
    target_ids = {l.id for l in inp.target_lines}
    platform_ids = {l.id for l in inp.platform_lines}
    assert set(defs["target_line_id"]["enum"]) == target_ids
    assert len(defs["target_line_id"]["enum"]) == len(target_ids)
    assert set(defs["line_id"]["enum"]) == target_ids | platform_ids
    assert set(defs["platform_line"]["enum"]) == {l.line for l in inp.platform_lines}
    assert "sl_055" in target_ids and "sl_001" not in defs["target_line_id"]["enum"]  # the id the model once copied


def test_mapper_submit_is_strict_and_every_object_is_closed():
    inp = _mapper_input()
    submit = next(d for d in _tool_defs(MAPPER_ROLE, inp) if d["name"] == "submit")
    assert submit["strict"] is True
    schema = submit["input_schema"]
    for obj in _objects(schema):
        assert obj["additionalProperties"] is False
        assert set(obj["required"]) == set(obj["properties"])
    text = json.dumps(schema)
    for unsupported in ('"minimum"', '"maximum"', '"default": ""', '"default": null', '"default": []',
                        '"default": {}', '"additionalProperties": {'):
        assert unsupported not in text
    assert text.count('"anyOf"') <= 16  # the API's limit on parameters with union types


def test_other_roles_keep_the_pydantic_schema():
    submit = next(d for d in _tool_defs(PREPARER_ROLE) if d["name"] == "submit")
    assert "strict" not in submit
    assert submit["input_schema"] == PREPARER_ROLE.output_type.model_json_schema()


def test_submit_pairs_turn_back_into_flag_option_dicts():
    raw = {"mappings": [{"target_line_id": "sl_055", "platform_line": "Cash and cash equivalents",
                         "confidence": 0.95, "reason": "same line", "policy_id": None}],
           "tags": [{"line_id": "sl_055", "tag": "na", "note": "", "policy_id": None}],
           "flags": [{"kind": "covenant_tag", "line_ids": ["sl_070"], "question": "Is it debt?",
                      "evidence": [{"quote": "q", "page": None, "document_id": None}],
                      "options": [{"id": "a", "label": "debt", "tags": [{"line_id": "sl_070", "tag": "debt"}],
                                   "platform_line": None, "mappings": []}],
                      "default": "a"}],
           "note": ""}
    out = MapperOutput.model_validate(mapper_output_from_submit(raw))
    assert out.flags[0].options[0].tags == {"sl_070": "debt"}
    assert out.flags[0].options[0].mappings == {}
    assert raw["flags"][0]["options"][0]["tags"] == [{"line_id": "sl_070", "tag": "debt"}]  # input left unchanged
