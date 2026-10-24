"""Agent settings, all from the environment. Documented in docs/agents.md.

Model choice per role: `<PREFIX>_<ROLE>` wins over `<PREFIX>`, for example `DROID_MODEL_MAPPER` over `DROID_MODEL`.
The default model is Claude Haiku 5.5 on both backends, to keep the weekend cheap. The Mapper is the role with
judgment in it; raise it to Sonnet 5.5 if a run misreads an exclusion.
"""
from __future__ import annotations

import os

DEFAULT_MODEL = "claude-haiku-5-5"


def role_model(prefix: str, role_name: str) -> str | None:
    """The model id for a role, or None to let the backend pick its own default."""
    return os.getenv(f"{prefix}_{role_name.upper()}") or os.getenv(prefix) or DEFAULT_MODEL


def summary() -> dict:
    """What the console shows under backend status."""
    return {
        "backend": os.getenv("AGENT_BACKEND", "scripted"),
        "fallback": os.getenv("AGENT_FALLBACK", "anthropic,scripted"),
        "models": {
            "anthropic": {r: role_model("ANTHROPIC_MODEL", r) for r in ("mapper", "preparer", "reviewer")},
            "droid": {r: role_model("DROID_MODEL", r) for r in ("mapper", "preparer", "reviewer")},
        },
        "record_runs": os.getenv("RECORD_RUNS", "1"),
        "droid_timeout_seconds": float(os.getenv("DROID_TIMEOUT", "240")),
    }
