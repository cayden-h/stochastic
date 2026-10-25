"""Demo pacing: short waits in the job runner, so a scripted or replayed run plays at a speed people can follow.

`DEMO_PACE` is a speed factor. Unset, empty, or 0 means off (the default): no wait at all. `DEMO_PACE=1` is
human-readable speed, about 23 s from Run to the controller's questions on the demo deal and about 13 s from the
last answer to the approval. 0.5 halves every wait and 2 doubles it; the factor is capped at 5.

The waits sit in the job runner only: before an agent's turn, before each tool call an agent makes, after each
mapping the gateway accepts, and before each question opens. They are never inside the gateway's checks, and a
live model backend (droid, anthropic) gets none, since its own run time is the real pace.
Under pytest the pace is off unless a test sets `ALLOW_IN_TESTS`, so a .env with DEMO_PACE=1 never slows the suite.
"""
from __future__ import annotations

import math
import os
import time

PACED_BACKENDS = ("scripted", "replay")

# Seconds at DEMO_PACE=1, per step.
STEPS: dict[str, float] = {
    "turn": 2.5,  # an agent picks up its work item
    "tool": 1.0,  # before each tool call an agent makes
    "mapping": 0.3,  # after each mapping the gateway accepts
    "question": 1.5,  # before each question to the controller opens
    "after": 1.0,  # after an agent's result is stored, before the next hand-off
}
MAX_FACTOR = 5.0

ALLOW_IN_TESTS = False  # a test that measures the pace sets this (monkeypatch) and replaces `_sleep`
_sleep = time.sleep


def factor() -> float:
    """The speed factor from DEMO_PACE, or 0 when pacing is off."""
    if os.getenv("PYTEST_CURRENT_TEST") and not ALLOW_IN_TESTS:
        return 0.0
    raw = (os.getenv("DEMO_PACE") or "").strip().lower()
    if raw in ("", "0", "off", "false", "no"):
        return 0.0
    if raw in ("on", "true", "yes"):
        return 1.0
    try:
        value = float(raw)
    except ValueError:
        return 0.0
    if not math.isfinite(value) or value <= 0:
        return 0.0
    return min(value, MAX_FACTOR)


def paced(backend: str | None) -> bool:
    """True when a run on this backend should be paced."""
    return factor() > 0 and (backend or os.getenv("AGENT_BACKEND", "scripted")) in PACED_BACKENDS


def pause(step: str, backend: str | None) -> float:
    """Wait for one step when pacing is on for this backend. Returns the seconds waited (0 when off)."""
    if not paced(backend):
        return 0.0
    seconds = STEPS[step] * factor()
    _sleep(seconds)
    return seconds


def estimate(target_lines: int, questions: int, agent_tool_calls: int, turns: int) -> float:
    """Seconds a paced stretch of a run waits in total, for the docs and the tests."""
    f = factor() or 1.0
    return f * (STEPS["turn"] * turns + STEPS["after"] * turns + STEPS["mapping"] * target_lines
                + STEPS["question"] * questions + STEPS["tool"] * agent_tool_calls)
