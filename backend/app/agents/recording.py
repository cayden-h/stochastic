"""Record and replay agent outputs. The replay backend is the last fallback on stage, and the backend of the two demo
paces (app/agents/demo_replay.py).

A recording is the typed output of one role for one work-item input, with the backend that produced it.
Recordings live in backend/recordings/ and are committed, so the demo survives with no network.
The pinned recording (backend/recordings/<role>.json) is what replay reads by default. A folder of recordings
(backend/recordings/<name>/) may carry a `recording.json` that says which model made it, on which backend, and when;
`using(folder)` makes replay read that folder for the block (the demo paces read haiku-5-5-run2).
Live runs write to recordings/latest/, so a run from the console never replaces a pinned one; promote a run by
copying it up after scoring it.
"""
from __future__ import annotations

import contextlib
import contextvars
import hashlib
import json
import os
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel

RECORDINGS = Path(os.getenv("RECORDINGS_DIR", Path(__file__).resolve().parents[2] / "recordings"))

# The folder replay reads in this block and the line id translation for the deal being run, or None (RECORDINGS).
_folder: contextvars.ContextVar[Path | None] = contextvars.ContextVar("recording_folder", default=None)
_ids: contextvars.ContextVar[dict[str, str] | None] = contextvars.ContextVar("recording_ids", default=None)


@contextlib.contextmanager
def using(folder: Path | None, ids: dict[str, str] | None = None) -> Iterator[None]:
    """Replay from this folder in the block. `ids` maps the recording's line ids to this deal's line ids."""
    t1, t2 = _folder.set(folder), _ids.set(ids)
    try:
        yield
    finally:
        _folder.reset(t1)
        _ids.reset(t2)


def folder() -> Path:
    return _folder.get() or RECORDINGS


def line_ids() -> dict[str, str] | None:
    """The recording-to-deal line id translation of this block, or None to use the recorded ids as they are."""
    return _ids.get()


def info(path: Path | None = None) -> dict:
    """What a recording folder says about itself (recording.json): model, backend, recorded_at, source. Empty when
    the folder has no such file (the root pin and the older folders)."""
    p = (path or folder()) / "recording.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def input_key(role_name: str, inp: BaseModel) -> str:
    body = inp.model_dump(mode="json", exclude={"session", "policies", "previous_refusal"})
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:12]


def record(role_name: str, inp: BaseModel, out: BaseModel, backend: str, latest: bool = False) -> Path:
    base = RECORDINGS / "latest" if latest else RECORDINGS
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{role_name}.json"
    data = {"role": role_name, "backend": backend, "input_key": input_key(role_name, inp),
            "output": out.model_dump(mode="json")}
    path.write_text(json.dumps(data, indent=2, default=str))
    return path


def load(role_name: str, output_type: type[BaseModel], inp: BaseModel | None = None) -> tuple[BaseModel, str, bool]:
    path = folder() / f"{role_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"no recording for {role_name} at {path}")
    data = json.loads(path.read_text())
    matches = inp is None or data.get("input_key") == input_key(role_name, inp)
    return output_type.model_validate(data["output"]), data.get("backend", "unknown"), matches
