"""Run the Mapper alone N times on the Anthropic backend and report how consistent it is. Records nothing.

    backend/.venv/bin/python evals/mapper_trials.py 10 /tmp/trials.json

Each trial seeds the demo deal and runs the job runner until the first stop (the Mapper's flags), the same way
the console does. It reports per trial: whether the gateway accepted the Mapper's result, the score against
evals/answer_key.csv, how many Mapper calls it took, and the tokens. Every trial spends real API credit
(about $0.01 per Mapper call on Claude Haiku 5.5 at $0.10 and $0.50 per million tokens).
Keys come from `.env` at the repo root, or from the file named by STOCHASTIC_ENV.
"""
from __future__ import annotations

import csv
import json
import os
import statistics
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.getenv("STOCHASTIC_ENV") or ROOT / ".env")
os.environ["RECORD_RUNS"] = "0"
os.environ["AGENT_FALLBACK"] = ""

from app.agents.backends import anthropic_backend as ab  # noqa: E402
from app.agents.jobs import advance  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402

PRICE_IN, PRICE_OUT = 0.10 / 1e6, 0.50 / 1e6  # Claude Haiku 5.5, prompts under 100K tokens

_calls: dict[int, list] = {}
_lock = threading.Lock()
_orig = ab.run_anthropic


def _wrapped(role, inp, call_tool, transcript=None):
    try:
        out, usage = _orig(role, inp, call_tool, transcript)
    except Exception as error:
        with _lock:
            _calls.setdefault(threading.get_ident(), []).append((role.name, None, getattr(error, "usage", None)))
        raise
    with _lock:
        _calls.setdefault(threading.get_ident(), []).append((role.name, out.model_dump(mode="json"), usage))
    return out, usage


ab.run_anthropic = _wrapped
KEY = {r["target_line"]: r["platform_line"] for r in csv.DictReader(open(ROOT / "evals" / "answer_key.csv"))
       if r["basis"] != "none"}


def _trial(i: int) -> dict:
    _calls.pop(threading.get_ident(), None)
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    lines = {l.id: l for l in store.source_lines.values()}
    rec: dict = {"trial": i}
    try:
        advance(gw, DEAL_ID, backend="anthropic")
        rec["ok"] = True
    except Exception as error:
        rec["ok"] = False
        rec["error"] = str(error)[-400:]
    calls = _calls.pop(threading.get_ident(), [])
    mapper = [c for c in calls if c[0] == "mapper"]
    rec["mapper_calls"] = len(mapper)
    rec["input_tokens"] = sum((c[2] or {}).get("input_tokens", 0) for c in calls)
    rec["output_tokens"] = sum((c[2] or {}).get("output_tokens", 0) for c in calls)
    rec["stage"] = store.deals[DEAL_ID].stage
    out = next((c[1] for c in reversed(mapper) if c[1]), None)
    if out:
        ids = {m["target_line_id"] for m in out["mappings"]}
        rec["platform_ids_as_target"] = sorted(t for t in ids if t in lines and lines[t].company != "Nu Aire")
        got = {lines[m["target_line_id"]].line: m["platform_line"] for m in out["mappings"] if m["target_line_id"] in lines}
        rec["agree"] = sum(got.get(t) == p for t, p in KEY.items())
        rec["scored"] = len(KEY)
        rec["misses"] = {t: got.get(t) for t, p in KEY.items() if got.get(t) != p}
        rec["flag_kinds"] = sorted(f["kind"] for f in out["flags"])
        rec["financing_unclear"] = sum(1 for t in out["tags"] if t["tag"] == "unclear"
                                       and "inancing liability" in lines.get(t["line_id"], lines["sl_001"]).line)
    return rec


def trial(i: int) -> dict:
    try:
        return _trial(i)
    except Exception as error:  # a broken trial must not lose the others
        return {"trial": i, "ok": False, "error": "SCRIPT " + repr(error)[:300]}


def main() -> int:
    n, out_path = int(sys.argv[1]), sys.argv[2]
    with ThreadPoolExecutor(max_workers=n) as ex:
        results = list(ex.map(trial, range(n)))
    Path(out_path).write_text(json.dumps(results, indent=1, default=str))
    for r in results:
        print(r["trial"], "OK  " if r["ok"] else "FAIL", "agree", r.get("agree"), "/", r.get("scored"),
              "mapper_calls", r.get("mapper_calls"), "flags", r.get("flag_kinds"), "| platform-as-target",
              r.get("platform_ids_as_target"), "|", (r.get("error") or "")[-160:].replace("\n", " "))
    scores = [r["agree"] for r in results if r.get("ok") and "agree" in r]
    cost = sum(r.get("input_tokens", 0) * PRICE_IN + r.get("output_tokens", 0) * PRICE_OUT for r in results)
    print(f"accepted {sum(r['ok'] for r in results)}/{n}; scores {sorted(scores)}; "
          f"median {statistics.median(scores) if scores else None}; mapper calls {sum(r.get('mapper_calls', 0) for r in results)}; "
          f"cost about ${cost:.3f} (Haiku 5.5 prices)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
