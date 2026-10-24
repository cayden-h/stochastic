"""Record and replay agent outputs. The replay backend is the last fallback on stage.

A recording is the typed output of one role for one work-item input, with the backend that produced it.
Recordings live in backend/recordings/ and are committed, so the demo survives with no network.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from pydantic import BaseModel

RECORDINGS = Path(os.getenv("RECORDINGS_DIR", Path(__file__).resolve().parents[2] / "recordings"))


def input_key(role_name: str, inp: BaseModel) -> str:
    body = inp.model_dump(mode="json", exclude={"session", "policies"})
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:12]


def record(role_name: str, inp: BaseModel, out: BaseModel, backend: str) -> Path:
    RECORDINGS.mkdir(parents=True, exist_ok=True)
    path = RECORDINGS / f"{role_name}.json"
    data = {"role": role_name, "backend": backend, "input_key": input_key(role_name, inp),
            "output": out.model_dump(mode="json")}
    path.write_text(json.dumps(data, indent=2, default=str))
    return path


def load(role_name: str, output_type: type[BaseModel], inp: BaseModel | None = None) -> tuple[BaseModel, str, bool]:
    path = RECORDINGS / f"{role_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"no recording for {role_name} at {path}")
    data = json.loads(path.read_text())
    matches = inp is None or data.get("input_key") == input_key(role_name, inp)
    return output_type.model_validate(data["output"]), data.get("backend", "unknown"), matches
