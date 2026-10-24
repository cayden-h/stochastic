"""run_agent(role, item): one function, several backends, one typed result.

AGENT_BACKEND picks the backend: anthropic, droid, scripted, or replay. If the chosen backend fails, the runner
falls back along AGENT_FALLBACK (default "scripted") and says which backend produced the result, so the
pitch can be honest about it. Successful model runs are recorded to recordings/latest/ when RECORD_RUNS=1 (the default),
so a live run never replaces the pinned replay; `scripts/record_run.py` (RECORD_RUNS=force) writes the pinned one.
Agents are stateful: the runner loads the role's session from the gateway, passes it in, and updates it after.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from pydantic import BaseModel

from app.agents import recording
from app.agents.backends.scripted import scripted_mapper, scripted_preparer, scripted_reviewer
from app.agents.roles import Role
from app.core.models import MapperInput, PreparerInput, ReviewerInput

# No Anthropic key is on the team, so the default fallback is the deterministic rules. Add `anthropic` back in
# AGENT_FALLBACK when a key is in .env.
DEFAULT_FALLBACK = "scripted"

LAST_RUNS: list[dict] = []  # what the console shows as "backend status"
TOTALS: dict[str, float] = {"runs": 0, "factory_credits": 0.0, "input_tokens": 0, "output_tokens": 0}  # this process


@dataclass
class AgentRun:
    output: BaseModel
    backend: str
    attempts: list[dict] = field(default_factory=list)
    seconds: float = 0.0


def _scripted(role: Role, inp: BaseModel, call_tool) -> BaseModel:
    if isinstance(inp, MapperInput):
        return scripted_mapper(inp)
    if isinstance(inp, PreparerInput):
        return scripted_preparer(inp, call_tool)
    if isinstance(inp, ReviewerInput):
        return scripted_reviewer(inp, call_tool)
    raise TypeError(f"no scripted agent for {type(inp).__name__}")


def _attempt(backend: str, role: Role, inp: BaseModel, call_tool, session) -> tuple[BaseModel, dict]:
    if backend == "scripted":
        return _scripted(role, inp, call_tool), {}
    if backend == "replay":
        if isinstance(inp, (PreparerInput, ReviewerInput)):
            # Tool-calling roles cannot replay stored numbers: run ids belong to the store that made them.
            # The replay re-runs the same deterministic tool sequence, so every number is a fresh gateway run.
            _, recorded_backend, _ = recording.load(role.name, role.output_type)
            return _scripted(role, inp, call_tool), {"recorded_backend": recorded_backend, "tools_rerun": True}
        out, recorded_backend, matches = recording.load(role.name, role.output_type, inp)
        return out, {"recorded_backend": recorded_backend, "input_matches": matches}
    if backend == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        from app.agents.backends.anthropic_backend import run_anthropic
        return run_anthropic(role, inp, call_tool, session.transcript if session else None)
    if backend == "droid":
        if not os.getenv("FACTORY_API_KEY"):
            raise RuntimeError("FACTORY_API_KEY is not set")
        from app.agents.backends.droid_backend import run_droid
        return run_droid(role, inp, call_tool, session.session_id if session else None,
                         session.session_key if session else None)
    raise RuntimeError(f"unknown backend '{backend}'")


def run_agent(role: Role, inp: BaseModel, call_tool, session=None, backend: str | None = None) -> AgentRun:
    """Run one role on one work item. Returns the typed output and the backend that produced it."""
    chosen = backend or os.getenv("AGENT_BACKEND", "scripted")
    chain = [chosen] + [b for b in os.getenv("AGENT_FALLBACK", DEFAULT_FALLBACK).split(",") if b and b != chosen]
    attempts: list[dict] = []
    start = time.time()
    for b in chain:
        t0 = time.time()
        try:
            out, meta = _attempt(b, role, inp, call_tool, session)
            out = role.output_type.model_validate(out.model_dump())
            attempts.append({"backend": b, "ok": True, "seconds": round(time.time() - t0, 2), **meta})
            rec = os.getenv("RECORD_RUNS", "1")
            if (b in ("anthropic", "droid") and rec == "1") or (rec == "force" and b != "replay"):
                try:
                    recording.record(role.name, inp, out, b, latest=rec != "force")
                except OSError:
                    pass
            run = AgentRun(output=out, backend=b, attempts=attempts, seconds=round(time.time() - start, 2))
            LAST_RUNS.append({"role": role.name, "backend": b, "attempts": attempts, "meta": meta,
                              "at": time.strftime("%H:%M:%S")})
            TOTALS["runs"] += 1
            usage = meta.get("usage", meta) if isinstance(meta, dict) else {}
            for k in ("factory_credits", "input_tokens", "output_tokens"):
                if isinstance(usage.get(k), (int, float)):
                    TOTALS[k] += usage[k]
            del LAST_RUNS[:-30]
            return run
        except Exception as error:  # fall back and keep the reason
            attempts.append({"backend": b, "ok": False, "seconds": round(time.time() - t0, 2), "error": str(error)[:300]})
    raise RuntimeError(f"every backend failed for {role.name}: {attempts}")
