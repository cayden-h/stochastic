"""The demo replays a real recorded Claude Haiku 5.5 run (backend/recordings/haiku-5-5-run2/) through the gateway.

The recording is the Mapper's typed output from the Droid run of 2026-10-24 evening (docs/agents.md, section 9).
The Preparer and the Reviewer re-run their tool sequence on replay, so every number is a fresh gateway run.
"""
import json
import os
from pathlib import Path

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

import pytest  # noqa: E402

from app.core.models import MAPPER, MapperOutput  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402

RUN2 = Path(__file__).resolve().parents[1] / "recordings" / "haiku-5-5-run2"


@pytest.fixture
def world():
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    return store, gw


def recorded_mapper() -> MapperOutput:
    return MapperOutput.model_validate(json.loads((RUN2 / "mapper.json").read_text())["output"])


def test_a_mapping_option_that_leaves_some_lines_unmapped_is_stated_without_a_crash(world):
    """The Haiku 5.5 run's mapping flag has options whose `mappings` hold None (leave a line unmapped). Stating the
    question once crashed on sorting None with the line names, after the mappings were written."""
    store, gw = world
    item = gw.create_item(DEAL_ID, "map_lines")
    gw.store_mapping(MAPPER, item.id, recorded_mapper())
    flag = next(f for f in gw.open_flags(DEAL_ID) if f.payload["kind"] == "mapping")
    q = next(m for m in gw.conversation(DEAL_ID) if m.kind == "question" and m.item_id == flag.id)
    assert "default_homes) Other accrued expenses, Other assets, Other income, net, Other non-current liabilities, " \
           "Prepaid expenses and other current assets; 1 line left unmapped;" in q.text, q.text
    assert "all_unmapped) Leave all six unmapped until the controller decides where each belongs. Debt" in q.text
    assert store.deals[DEAL_ID].stage == "awaiting_flag"
