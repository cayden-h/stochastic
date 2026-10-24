"""Probe the Factory Droid Python SDK: which models our key can run, and one run() with structured output.

Run from the repo root with the backend venv:
    backend/.venv/bin/python scripts/droid_probe.py
Needs the `droid` CLI on PATH (curl -fsSL https://app.factory.ai/cli | sh) and FACTORY_API_KEY in .env.
It runs in an empty temp directory and allows no tools, so no finance data or files are exposed.
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Probe(BaseModel):
    greeting: str
    model_you_think_you_are: str


async def main() -> int:
    from droid_sdk import Autonomy, SessionConfig, list_models, run

    models = await list_models()
    print(f"{len(models)} models selectable by this key:")
    claude = []
    for m in models:
        line = f"  {getattr(m, 'id', m)}  {getattr(m, 'display_name', '')}  provider={getattr(m, 'provider', '')}"
        print(line)
        if "claude" in str(getattr(m, "id", m)).lower():
            claude.append(getattr(m, "id", m))
    print("\nCan Droid run Claude on this key:", "YES " + ", ".join(map(str, claude)) if claude else "NO")

    with tempfile.TemporaryDirectory(prefix="stochastic-probe-") as cwd:
        config = SessionConfig(restrict_tools=["none"], autonomy=Autonomy.HIGH,
                               system_prompt="Answer the question. Use no tools.")
        kwargs = dict(cwd=cwd, output=Probe, config=config, timeout=120)
        if os.getenv("DROID_MODEL"):
            kwargs["model"] = os.getenv("DROID_MODEL")
        result = await run("Say hello and name the model you are running as.", **kwargs)
    print("\nrun() success:", result.success, "session:", result.session_id, "turns:", result.turn_count)
    print("structured output:", result.output)
    if not result.success:
        print("error:", result.error, result.structured_output_error or result.output_validation_error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
