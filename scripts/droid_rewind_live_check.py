"""Live check for the Mapper rewind on the Droid backend (docs/tasks/eric.md, Task A). Spends Factory credits.

    backend/.venv/bin/python scripts/droid_rewind_live_check.py

1. Run the demo deal on Droid until the Mapper's flags, so the Mapper has a saved session (S1).
2. Reset the deal (memory kept) and run it again with the Mapper's first result forced invalid (Nu Aire's first line
   gets Kewaunee's line id), so the gateway refuses it. The refused turn was appended to S1.
3. The retry rewinds S1 to before the refused turn and runs on a successor (S2).
4. Read Factory's session records: S1 still holds the refused turn's prompt, S2 does not.
Sessions live in a scratch DROID_WORKDIR, so the demo's own sessions are not touched.
"""
from __future__ import annotations

import dataclasses
import glob
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
os.environ.update(RECORD_RUNS="0", AGENT_FALLBACK="", AGENT_BACKEND="droid", STORE="memory")
os.environ.setdefault("DROID_WORKDIR", tempfile.mkdtemp(prefix="rewind-live-"))

from app.agents import jobs  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402


def record(session_id: str) -> str:
    paths = glob.glob(os.path.expanduser(f"~/.factory/sessions/*/{session_id}.jsonl"))
    return open(paths[0], encoding="utf-8").read() if paths else ""


def main() -> int:
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    print("phase 1:", jobs.advance(gw, DEAL_ID, backend="droid"))
    s1 = store.sessions["mapper"].session_id
    print("saved Mapper session S1:", s1)

    store.reset_deals(keep_memory=True)
    seed(store, gw)
    real = jobs.run_agent
    seen = []

    def run_agent(role, inp, call_tool, session=None, backend=None, rewind_to=None):
        run = real(role, inp, call_tool, session=session, backend=backend, rewind_to=rewind_to)
        if role.name != "mapper":
            return run
        ok = next((a for a in reversed(run.attempts) if a.get("ok")), {})
        seen.append({k: ok.get(k) for k in ("session_id", "resumed", "turn_message_id", "rewound",
                                            "rewound_from_session", "rewound_to_message", "rewind_error")})
        if len(seen) == 1:  # force the gateway to refuse the first result
            deal = store.deals[DEAL_ID]
            first = run.output.mappings[0].model_copy(update={"target_line_id": store.lines(DEAL_ID, deal.platform)[0].id})
            run = dataclasses.replace(run, output=run.output.model_copy(update={"mappings": [first, *run.output.mappings[1:]]}))
        return run

    jobs.run_agent = run_agent
    try:
        print("phase 2:", jobs.advance(gw, DEAL_ID, backend="droid"))
    finally:
        jobs.run_agent = real
    for i, s in enumerate(seen, 1):
        print(f"mapper call {i}:", s)
    if len(seen) < 2:
        print("FAIL: no retry happened")
        return 1
    refused_msg = seen[0]["turn_message_id"]
    s2 = seen[1]["session_id"]
    print("refused turn message:", refused_msg, "| S1:", s1, "| S2:", s2, "| stored now:", store.sessions["mapper"].session_id)
    r1, r2 = record(s1), record(s2)
    print("S1 record holds the refused turn:", bool(refused_msg) and refused_msg in r1)
    print("S2 record holds the refused turn:", bool(refused_msg) and refused_msg in r2)
    print("S2 record holds the refusal reason (the retry's prompt):", "unknown target line" in r2)
    ok = (seen[1]["rewound"] and s2 != s1 and refused_msg and refused_msg in r1 and refused_msg not in r2
          and store.sessions["mapper"].session_id == s2)
    print("LIVE CHECK", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
