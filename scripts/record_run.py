"""Run the demo deal end to end on one backend and save each agent's output for replay.

    backend/.venv/bin/python scripts/record_run.py --backend anthropic
    backend/.venv/bin/python scripts/record_run.py --backend droid

Recordings land in backend/recordings/<role>.json. Replay them with AGENT_BACKEND=replay.
The scripted backend needs no key and is the default.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from app.agents import recording  # noqa: E402
from app.agents.jobs import advance  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default=os.getenv("AGENT_BACKEND", "scripted"))
    ap.add_argument("--answer", default=None, help="option id for every flag (default: the agent's default)")
    args = ap.parse_args()
    os.environ["RECORD_RUNS"] = "force"  # record whichever backend ran, scripted included
    os.environ["AGENT_FALLBACK"] = ""  # a recording must come from the backend asked for
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    print(advance(gw, DEAL_ID, backend=args.backend))
    for flag in gw.open_flags(DEAL_ID):
        print(f"flag {flag.id}: {flag.question}")
        for o in flag.options:
            print(f"   {o.id}: {o.label} -> {o.effect}")
        gw.answer("human:controller", flag.id, args.answer or flag.default or flag.options[0].id)
    print(advance(gw, DEAL_ID, backend=args.backend))
    result = store.latest_result(DEAL_ID)
    if result:
        print(f"leverage {result.leverage:.2f}x against {result.limit:.2f}x -> {result.verdict}, review {result.review}")
    print("recordings in", recording.RECORDINGS, sorted(p.name for p in recording.RECORDINGS.glob('*.json')))
    return 0


if __name__ == "__main__":
    sys.exit(main())
