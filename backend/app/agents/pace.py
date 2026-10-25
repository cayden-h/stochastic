"""Demo pacing: short waits in the job runner, so a scripted or replayed run plays at a speed people can follow.

Two ways to turn it on:
- `DEMO_PACE` in the environment is a speed factor for every run. Unset, empty, or 0 means off (the default).
  `DEMO_PACE=1` is human speed (the `human` profile), about 21 s from Run to the controller's questions on the demo
  deal and about 13 s from the last answer to the approval. 0.5 halves every wait and 2 doubles it (capped at 5).
- `POST /deals/{id}/run` with `"pace"` sets it for that run only, and for the run that the controller's answer
  continues: `"demo"` (the 15-second demo, about 6 s to the question and 7 s from the answer to the approval),
  `"human"` (the DEMO_PACE=1 timings), or `"off"`. It overrides DEMO_PACE (`using`). A `"demo"` run with no backend
  of its own is always scripted, whatever AGENT_BACKEND says (app/agents/jobs.py, `advance`).

The waits sit in the job runner only: before an agent's turn, before each tool call an agent makes, while the
mappings are stored (a fixed time for the whole list in the `demo` profile, a fixed time per line in `human`), once
before the questions open, and after a result is stored. They are never inside the gateway's checks or under its
lock, and a live model backend (droid, anthropic) gets none, since its own run time is the real pace.
Under pytest the pace is off unless a test sets `ALLOW_IN_TESTS`, so a .env with DEMO_PACE=1 never slows the suite.
Tests replace `_sleep` with a fake clock, so a paced run is measured in virtual seconds and takes no real time.
"""
from __future__ import annotations

import contextlib
import contextvars
import math
import os
import time
from typing import Iterator, Literal

PACED_BACKENDS = ("scripted", "replay")
PaceName = Literal["demo", "human", "off"]

# Seconds per step, per profile. `human` is the DEMO_PACE=1 timing and is scaled by DEMO_PACE.
PROFILES: dict[str, dict[str, float]] = {
    "human": {
        "turn": 2.5,  # an agent picks up its work item
        "tool": 1.0,  # before each tool call an agent makes
        "mapping": 0.3,  # after each mapping the gateway accepts
        "verify": 0.3,  # after each Brief field the verifier checks (D23)
        "question": 1.5,  # before the questions to the controller open
        "after": 1.0,  # after an agent's result is stored, before the next hand-off
    },
    # The 15-second demo: about 6 s from Run to the question (the Mapper works 1.2 s, its mappings stream over 4 s,
    # the question opens 0.8 s later) and about 7 s from the answer to "Ready for your approval" (the Preparer
    # 1.2 + 4 tools x 0.6 + 0.6 = 4.2 s, the Reviewer 1.2 + 2 tools x 0.6 = 2.4 s, then the hand-off).
    "demo": {
        "turn": 1.2,
        "tool": 0.6,
        "mapping_total": 4.0,  # the whole list of mappings, spread evenly over the lines
        "verify_total": 2.0,  # the verifier's whole list of Brief checks, spread evenly over the checks (D23)
        "question": 0.8,
        "after": 0.6,
    },
}
STEPS = PROFILES["human"]  # kept for the callers and tests that read the human timings
MAX_FACTOR = 5.0

ALLOW_IN_TESTS = False  # a test that measures the pace sets this (monkeypatch) and replaces `_sleep`
_sleep = time.sleep

# The pace asked for on this run (POST /deals/{id}/run "pace"), or None to follow DEMO_PACE. A context variable, so
# two runs in two threads never see each other's pace.
_run_pace: contextvars.ContextVar[str | None] = contextvars.ContextVar("run_pace", default=None)


@contextlib.contextmanager
def using(name: str | None) -> Iterator[None]:
    """Run the block at this pace ("demo", "human", "off"), or at DEMO_PACE when name is None."""
    if name is not None and name not in (*PROFILES, "off"):
        raise ValueError(f"unknown pace '{name}': use demo, human, or off")
    token = _run_pace.set(name)
    try:
        yield
    finally:
        _run_pace.reset(token)


def current() -> str | None:
    """The pace this run asked for, or None when it follows DEMO_PACE."""
    return _run_pace.get()


def _env_factor() -> float:
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


def _profile() -> tuple[str, float]:
    """(profile name, speed factor) for this run; factor 0 means no pacing."""
    if os.getenv("PYTEST_CURRENT_TEST") and not ALLOW_IN_TESTS:
        return "human", 0.0
    name = _run_pace.get()
    if name == "off":
        return "human", 0.0
    if name in PROFILES:
        return name, 1.0
    return "human", _env_factor()


def factor() -> float:
    """The speed factor for this run, or 0 when pacing is off."""
    return _profile()[1]


def paced(backend: str | None) -> bool:
    """True when a run on this backend should be paced."""
    return factor() > 0 and (backend or os.getenv("AGENT_BACKEND", "scripted")) in PACED_BACKENDS


def seconds(step: str, count: int = 1) -> float:
    """The wait for one step at this run's pace, before the backend check. `count` is the number of mappings in the
    list being stored, for the `demo` profile's fixed total."""
    name, f = _profile()
    steps = PROFILES[name]
    if f"{step}_total" in steps:  # a list streamed in a fixed total time: the mappings, the Brief checks
        return f * steps[f"{step}_total"] / max(count, 1)
    return f * steps[step]


def pause(step: str, backend: str | None, count: int = 1) -> float:
    """Wait for one step when pacing is on for this backend. Returns the seconds waited (0 when off)."""
    if not paced(backend):
        return 0.0
    wait = seconds(step, count)
    _sleep(wait)
    return wait


def estimate(target_lines: int, questions: int, agent_tool_calls: int, turns: int) -> float:
    """Seconds a paced stretch of a run waits in total, for the docs and the tests. One question wait however many
    questions open, since they open together."""
    name, f = _profile()
    f = f or 1.0
    s = PROFILES[name]
    mapping = s["mapping_total"] if "mapping_total" in s else s["mapping"] * target_lines
    return f * (s["turn"] * turns + s["after"] * turns + (mapping if target_lines else 0)
                + (s["question"] if questions else 0) + s["tool"] * agent_tool_calls)
