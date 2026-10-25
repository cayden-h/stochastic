"""The backend of the two demo paces: a replay of a real recorded Claude Haiku 5.5 run, when it fits the deal.

Pace "demo" (Run the demo, about 15 s) and pace "factory" (Upload then Begin, about 30 s) run with no live model call.
Before this, both ran the scripted rules. Now they replay the recorded Haiku 5.5 run of the demo deal
(backend/recordings/haiku-5-5-run2/, Droid, 2026-10-24; see its recording.json): the Mapper's typed output is the one
the model returned, and the Preparer and the Reviewer re-run the recorded tool sequence through the gateway, so every
figure is a fresh tool run. The gateway checks the replayed output like any other.

The recording applies only when it is honest to show it:
- The deal's lines must be the demo deal's lines (the same companies' roles, sections, line names, and amounts, by a
  content hash). That holds for the live demo deal and for an upload of the same Kewaunee and Nu Aire statements.
  The recorded line ids are translated to the deal's own ids by that content, since ids are given out by the store.
- No live policy learned on another deal (or on an earlier run of this one) may cover the deal: the recording was
  made with no memory, so replaying it would ask questions the agents have already learned to answer.
Otherwise the pace runs the scripted rules, and the run says so (`backend: "scripted"`, and a system note with the
reason), so the model card never calls scripted output a model's.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.agents import recording
from app.core.models import MapperOutput, SourceLine
from app.tools import finance

DEMO_RECORDING = "haiku-5-5-run2"
DEMO_PACES = ("demo", "factory")


@dataclass
class Plan:
    backend: str  # "replay" or "scripted"
    folder: Path | None = None
    ids: dict[str, str] = field(default_factory=dict)  # recorded line id -> this deal's line id
    reason: str = ""  # why the recording does not apply, when backend is "scripted"


def recording_folder() -> Path:
    return recording.RECORDINGS / DEMO_RECORDING


def _key(role: str, line: SourceLine) -> tuple:
    return (role, line.section, line.line.strip().casefold(), round(finance.to_thousands(line.amount, line.unit), 3),
            bool(line.is_total))


def _keyed(lines: list[SourceLine], platform: str) -> dict[tuple, str]:
    """Each line's content key, with its occurrence number so two equal lines stay apart, mapped to its id."""
    seen: Counter = Counter()
    out = {}
    for line in lines:
        role = "platform" if line.company.casefold() == platform.casefold() else "target"
        k = _key(role, line)
        seen[k] += 1
        out[(*k, seen[k])] = line.id
    return out


@lru_cache(maxsize=1)
def _recorded_lines() -> tuple[dict[tuple, str], str]:
    """The demo deal's lines as the recording saw them (a fresh store gives the same ids), keyed by content."""
    from app.db.fixtures import kewaunee
    from app.db.memory import MemoryStore
    keyed = _keyed(kewaunee.build_lines(MemoryStore()), kewaunee.PLATFORM)
    return keyed, _digest(keyed)


def _digest(keyed: dict[tuple, str]) -> str:
    return hashlib.sha256(repr(sorted(keyed)).encode()).hexdigest()[:16]


def content_digest(lines: list[SourceLine], platform: str) -> str:
    """The content hash of a deal's lines: role, section, name, amount in USD thousands, total or not."""
    return _digest(_keyed(lines, platform))


def plan(gw, deal_id: str) -> Plan:
    """Replay the recorded Haiku 5.5 run on this deal, or say why not."""
    store = gw.store
    deal = store.deals[deal_id]
    folder = recording_folder()
    if not (folder / "mapper.json").exists():
        return Plan("scripted", reason=f"the recording {DEMO_RECORDING} is missing")
    recorded, digest = _recorded_lines()
    mine = _keyed(store.lines(deal_id), deal.platform)
    if _digest(mine) != digest:
        return Plan("scripted", reason="this deal's statements are not the recorded Kewaunee and Nu Aire statements")
    own = {i.id for i in store.deal_items(deal_id)} | {e.id for e in store.deal_edits(deal_id)}
    covering = [p for p in gw.policies_for("agent:mapper", deal_id) if p.learned_from not in own]
    if covering:
        return Plan("scripted", reason=f"{len(covering)} learned polic{'y covers' if len(covering) == 1 else 'ies cover'} "
                                       f"this deal and the recording was made with no memory")
    return Plan("replay", folder=folder, ids={rid: mine[k] for k, rid in recorded.items()})


def translate(out: MapperOutput, ids: dict[str, str] | None) -> MapperOutput:
    """The recorded Mapper output with its line ids replaced by this deal's. An id the map does not know stays as it
    is, so the gateway refuses it by name."""
    if not ids:
        return out
    t = lambda i: ids.get(i, i)  # noqa: E731
    data = out.model_dump()
    for m in data["mappings"]:
        m["target_line_id"] = t(m["target_line_id"])
    for tag in data["tags"]:
        tag["line_id"] = t(tag["line_id"])
    for f in data["flags"]:
        f["line_ids"] = [t(i) for i in f["line_ids"]]
        for o in f["options"]:
            o["tags"] = {t(k): v for k, v in o["tags"].items()}
            o["mappings"] = {t(k): v for k, v in o["mappings"].items()}
    return MapperOutput.model_validate(data)
