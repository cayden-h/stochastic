"""run_agent(role, item): one function, several backends, one typed result.

AGENT_BACKEND picks the backend: anthropic, droid, scripted, or replay. If the chosen backend fails, the runner
falls back along AGENT_FALLBACK (default "scripted") and says which backend produced the result, so the
pitch can be honest about it. Successful model runs are recorded to recordings/latest/ when RECORD_RUNS=1 (the default),
so a live run never replaces the pinned replay; `scripts/record_run.py` (RECORD_RUNS=force) writes the pinned one.
Agents are stateful: the runner loads the role's session from the gateway, passes it in, and updates it after.
`only(backend)` pins every run in the block to one backend with no fallback chain: the 15-second demo
(pace "demo") runs the scripted backend whatever AGENT_BACKEND says (app/agents/jobs.py).
"""
from __future__ import annotations

import contextlib
import contextvars
import os
import time
from dataclasses import dataclass, field

from pydantic import BaseModel

from app.agents import recording
from app.agents.backends.scripted import scripted_brief_reader, scripted_mapper, scripted_preparer, scripted_reviewer
from app.agents.roles import Role
from app.core.models import BriefReaderInput, MapperInput, PreparerInput, ReviewerInput

# The Anthropic backend has run on a teammate's key (recordings/anthropic-haiku-5-5), but the demo laptop has no
# key, so the default fallback is the deterministic rules. Add `anthropic` to AGENT_FALLBACK when a key is in .env.
DEFAULT_FALLBACK = "scripted"

# The one backend every run in an `only` block uses, with no fallback chain; None follows AGENT_BACKEND and the chain.
_only: contextvars.ContextVar[str | None] = contextvars.ContextVar("only_backend", default=None)


@contextlib.contextmanager
def only(backend: str | None):
    """Run the block on this backend alone, with no fallback (None: no pin)."""
    token = _only.set(backend)
    try:
        yield
    finally:
        _only.reset(token)


def pinned() -> str | None:
    """The backend an `only` block pins, or None."""
    return _only.get()


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
    if isinstance(inp, BriefReaderInput):
        return scripted_brief_reader(inp, call_tool)
    raise TypeError(f"no scripted agent for {type(inp).__name__}")


def _replay_note(about: dict, recorded_backend: str) -> str:
    who = about.get("model_label") or about.get("model") or "the recorded"
    return (f"Replay of the recorded {who} run on {recorded_backend} ({recording.folder().name}): the recorded tool "
            f"sequence, consolidate, ebitda, covenant_debt, leverage, re-run through the gateway, so every figure is a "
            f"fresh run")


def _attempt(backend: str, role: Role, inp: BaseModel, call_tool, session,
             rewind_to: str | None = None) -> tuple[BaseModel, dict]:
    if backend == "scripted":
        return _scripted(role, inp, call_tool), {}
    if backend == "replay":
        about = recording.info()
        meta = {"recording": recording.folder().name, "model": about.get("model"),
                "recorded_at": about.get("recorded_at"), "model_confirmed": about.get("model_confirmed")}
        if isinstance(inp, (PreparerInput, ReviewerInput)):
            # Tool-calling roles cannot replay stored numbers: run ids belong to the store that made them.
            # The replay re-runs the same deterministic tool sequence, so every number is a fresh gateway run.
            _, recorded_backend, _ = recording.load(role.name, role.output_type)
            out = _scripted(role, inp, call_tool)
            if isinstance(inp, PreparerInput):
                out = out.model_copy(update={"note": _replay_note(about, recorded_backend)})
            return out, {"recorded_backend": recorded_backend, "tools_rerun": True, **meta}
        out, recorded_backend, matches = recording.load(role.name, role.output_type, inp)
        if isinstance(inp, MapperInput) and recording.line_ids():
            from app.agents.demo_replay import translate
            out = translate(out, recording.line_ids())
            meta["line_ids_translated"] = True
        return out, {"recorded_backend": recorded_backend, "input_matches": matches, **meta}
    if backend == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        from app.agents.backends.anthropic_backend import run_anthropic
        return run_anthropic(role, inp, call_tool, session.transcript if session else None)
    if backend == "droid":
        if not os.getenv("FACTORY_API_KEY"):
            raise RuntimeError("FACTORY_API_KEY is not set")
        from app.agents.backends.droid_backend import run_droid
        extra = {"rewind_to": rewind_to} if rewind_to else {}  # only a retry after a refusal asks for a rewind
        return run_droid(role, inp, call_tool, session.session_id if session else None,
                         session.session_key if session else None, **extra)
    raise RuntimeError(f"unknown backend '{backend}'")


def _model_of(backend: str, role: Role, meta: dict) -> dict:
    """What produced the output, for the model card: the model id (None for the scripted rules) and whether it is a
    recorded run. A replay names the model of its recording; a live run the model it asked for (and was served, when
    the backend says)."""
    from app.agents import settings
    if backend == "replay":
        return {"model": meta.get("model"), "recorded": True, "recording": meta.get("recording"),
                "recorded_at": meta.get("recorded_at"), "recorded_backend": meta.get("recorded_backend")}
    if backend == "droid":
        return {"model": meta.get("model_served") or meta.get("model_requested") or settings.role_model("DROID_MODEL", role.name),
                "recorded": False}
    if backend == "anthropic":
        return {"model": settings.role_model("ANTHROPIC_MODEL", role.name), "recorded": False}
    return {"model": None, "recorded": False}


def run_agent(role: Role, inp: BaseModel, call_tool, session=None, backend: str | None = None,
              rewind_to: str | None = None) -> AgentRun:
    """Run one role on one work item. Returns the typed output and the backend that produced it.
    `rewind_to` asks the Droid backend to drop a turn from the resumed session first; other backends ignore it."""
    pin = _only.get()
    chosen = pin or backend or os.getenv("AGENT_BACKEND", "scripted")
    chain = [chosen] if pin else [chosen] + [b for b in os.getenv("AGENT_FALLBACK", DEFAULT_FALLBACK).split(",")
                                            if b and b != chosen]
    attempts: list[dict] = []
    start = time.time()
    for b in chain:
        t0 = time.time()
        try:
            out, meta = _attempt(b, role, inp, call_tool, session, rewind_to)
            out = role.output_type.model_validate(out.model_dump())
            attempts.append({"backend": b, "ok": True, "seconds": round(time.time() - t0, 2), **meta})
            rec = os.getenv("RECORD_RUNS", "1")
            if (b in ("anthropic", "droid") and rec == "1") or (rec == "force" and b != "replay"):
                try:
                    recording.record(role.name, inp, out, b, latest=rec != "force")
                except OSError:
                    pass
            run = AgentRun(output=out, backend=b, attempts=attempts, seconds=round(time.time() - start, 2))
            LAST_RUNS.append({"role": role.name, "backend": b, "asked": chosen, "attempts": attempts, "meta": meta,
                              "at": time.strftime("%H:%M:%S"), **_model_of(b, role, meta)})
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
