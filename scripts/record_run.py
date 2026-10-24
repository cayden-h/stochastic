"""Run the demo deal end to end on one backend and save each agent's output for replay.

    backend/.venv/bin/python scripts/record_run.py --backend anthropic
    backend/.venv/bin/python scripts/record_run.py --backend droid
    backend/.venv/bin/python scripts/record_run.py --backend droid --agreement data/raw/8k_ex10-1.txt

With --agreement, only the Brief Reader runs: the demo deal is created from that agreement text instead of the
fixture Brief, the reader drafts the Brief, and the run stops on its flags. It writes recordings/brief_reader.json.

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
from app.core.models import CONTROLLER, Deal  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, EX101, PLATFORM, TARGET, build_lines, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default=os.getenv("AGENT_BACKEND", "scripted"))
    ap.add_argument("--answer", default=None, help="option id for every flag (default: the agent's default)")
    ap.add_argument("--agreement", default=None, help="record the Brief Reader on this agreement text (.txt)")
    args = ap.parse_args()
    os.environ["RECORD_RUNS"] = "force"  # record whichever backend ran, scripted included
    os.environ["AGENT_FALLBACK"] = ""  # a recording must come from the backend asked for
    store = MemoryStore()
    gw = Gateway(store)
    if args.agreement:
        return record_reader(gw, Path(args.agreement), args.backend)
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


def record_reader(gw: Gateway, path: Path, backend: str) -> int:
    from app.agents import runner

    deal = Deal(id=DEAL_ID, name="Kewaunee Scientific acquires Nu Aire", platform=PLATFORM, target=TARGET,
                brief=None, brief_status="none")
    gw.create_deal_from_agreement(CONTROLLER, deal, build_lines(gw.store), path.read_text(), EX101)
    print(advance(gw, DEAL_ID, backend=backend))
    run = next(r for r in reversed(runner.LAST_RUNS) if r.get("role") == "brief_reader")
    print("attempts:", run["attempts"])
    refused = [r.reason for r in gw.store.audit if r.action == "propose:draft_brief" and r.result == "DENIED"]
    print("refused drafts:", refused or "none")
    draft = gw.brief_draft(DEAL_ID)
    if draft:
        print(f"citations {len(draft.citations)}, flags {len(draft.flags)}")
        for fid in draft.flags:
            print("  flag:", gw.store.items[fid].payload["field"], "-", gw.store.items[fid].question)
        print(draft.brief.model_dump_json(indent=2))
    print("recordings in", recording.RECORDINGS, sorted(p.name for p in recording.RECORDINGS.glob('*.json')))
    return 0 if draft else 1


if __name__ == "__main__":
    sys.exit(main())
