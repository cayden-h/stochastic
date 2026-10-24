"""End-to-end check of the Mapper rewind through the real API server on Droid. Spends Factory credits.

    backend/.venv/bin/python scripts/droid_rewind_api_check.py

Starts the real FastAPI app with uvicorn on 127.0.0.1:8765 and drives it over HTTP, with the demo's models
(Mapper Claude Sonnet 5.5, Preparer and Reviewer Claude Haiku 5.5) and the in-memory store.
The Mapper's first result in phase 2 is made invalid from outside the app (this script wraps `jobs.run_agent`;
no app code changes), so the real gateway refuses a real model answer.

Phase 1  run the deal to its flags: the Mapper gets a saved Droid session S1.
Phase 2  reset (memory kept), run with the forced refusal: the retry rewinds S1 and runs on a successor S2.
         Answer the flags, run the Preparer and Reviewer, and approve: the deal must post.
Phase 3  reset (memory kept), run again with no forced refusal: the Mapper must resume S2, and the deal must post.
Then Factory's session records: S1 holds the refused turn, S2 does not, and S2 holds the phase 3 turn.
"""
from __future__ import annotations

import dataclasses
import glob
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
os.environ.update(AGENT_BACKEND="droid", AGENT_FALLBACK="", RECORD_RUNS="0", STORE="memory",
                  DROID_MODEL="claude-haiku-5-5", DROID_MODEL_MAPPER="claude-sonnet-5-5")
os.environ.setdefault("DROID_WORKDIR", tempfile.mkdtemp(prefix="rewind-api-"))

import httpx  # noqa: E402
import uvicorn  # noqa: E402

from app.agents import jobs  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID  # noqa: E402
from app.main import create_app  # noqa: E402

PORT = 8765
FORCE = {"left": 0}
MAPPER_CALLS: list[dict] = []
_real = jobs.run_agent


def _run_agent(role, inp, call_tool, session=None, backend=None, **kw):
    run = _real(role, inp, call_tool, session=session, backend=backend, **kw)
    if role.name != "mapper":
        return run
    ok = next((a for a in reversed(run.attempts) if a.get("ok")), {})
    MAPPER_CALLS.append({k: ok.get(k) for k in ("session_id", "resumed", "resume_error", "turn_message_id", "rewound",
                                                "rewound_from_session", "rewind_error", "model_served")}
                        | {"backend": run.backend, "rewind_to": kw.get("rewind_to")})
    if FORCE["left"] > 0 and run.backend == "droid":
        FORCE["left"] -= 1
        platform_id = next(l.id for l in inp.platform_lines)
        first = run.output.mappings[0].model_copy(update={"target_line_id": platform_id})
        run = dataclasses.replace(run, output=run.output.model_copy(update={"mappings": [first, *run.output.mappings[1:]]}))
    return run


jobs.run_agent = _run_agent


def record(session_id: str | None) -> str:
    paths = glob.glob(os.path.expanduser(f"~/.factory/sessions/*/{session_id}.jsonl")) if session_id else []
    return open(paths[0], encoding="utf-8").read() if paths else ""


def main() -> int:
    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=PORT, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    c = httpx.Client(base_url=f"http://127.0.0.1:{PORT}", timeout=1200)
    for _ in range(100):
        try:
            if c.get("/health").status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))
        print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)

    def run():
        t = time.time()
        r = c.post(f"/deals/{DEAL_ID}/run", json={"backend": "droid", "sync": True})
        body = r.json()
        print(f"  run {r.status_code} in {time.time() - t:.0f}s: {body.get('log')}", flush=True)
        return r.status_code, body

    def finish_deal(label):
        case = c.get(f"/deals/{DEAL_ID}/case").json()
        for f in case["open_flags"]:
            flag = next(x for x in case["flags"] if x["id"] == f["id"]) if isinstance(f, dict) and "id" in f else None
            fid = flag["id"] if flag else (f["id"] if isinstance(f, dict) else f)
            default = (flag or {}).get("default") or next(x for x in case["flags"] if x["id"] == fid)["default"]
            r = c.post(f"/work-items/{fid}/answer?auto_advance=false", json={"option_id": default})
            print(f"  answered {fid} with {default}: {r.status_code}", flush=True)
        if case["open_flags"]:
            run()
        case = c.get(f"/deals/{DEAL_ID}/case").json()
        v = case["verdict"] or {}
        check(f"{label}: Reviewer passed", (v.get("review") or {}).get("verdict") == "pass", str(v.get("review")))
        check(f"{label}: leverage computed", v.get("leverage") is not None, f"{v.get('leverage')}x, {v.get('verdict')}")
        r = c.post(f"/work-items/{v.get('approval_item')}/approve")
        case = c.get(f"/deals/{DEAL_ID}/case").json()
        check(f"{label}: controller approved and the deal posted", r.status_code == 200 and case["stage"] == "posted",
              case["stage"])
        check(f"{label}: audit chain valid", case["audit"]["chain_valid"])

    # Phase 1
    print("phase 1: first deal, to the flags", flush=True)
    c.post("/dev/reset", params={"keep_memory": "false"})
    status, _ = run()
    s1 = MAPPER_CALLS[-1]["session_id"]
    check("phase 1: Mapper ran on Droid and saved a session", status == 200 and MAPPER_CALLS[-1]["backend"] == "droid"
          and s1, f"S1={s1}, served={MAPPER_CALLS[-1]['model_served']}")

    # Phase 2
    print("phase 2: forced refusal, rewind, then the whole deal", flush=True)
    c.post("/dev/reset", params={"keep_memory": "true"})
    FORCE["left"] = 1
    n = len(MAPPER_CALLS)
    status, body = run()
    calls = MAPPER_CALLS[n:]
    log = " | ".join(body.get("log") or [])
    refused, retry = (calls + [{}, {}])[:2]
    s2 = retry.get("session_id")
    check("phase 2: the gateway refused the first Mapper result", "refused on droid" in log)
    check("phase 2: the refused turn ran in S1", refused.get("session_id") == s1 and refused.get("resumed"))
    check("phase 2: the retry was asked to rewind to the refused turn",
          retry.get("rewind_to") and retry.get("rewind_to") == refused.get("turn_message_id"))
    check("phase 2: the retry rewound S1 and ran on a successor",
          retry.get("rewound") and retry.get("rewound_from_session") == s1 and s2 and s2 != s1,
          f"S2={s2}, rewind_error={retry.get('rewind_error')}")
    check("phase 2: the retry stayed on Droid (no scripted fallback)", retry.get("backend") == "droid"
          and "fell back to scripted" not in log)
    mem = c.get("/agents/memory").json()
    saved = next((s for s in mem["sessions"] if s["role"] == "mapper"), {})
    check("phase 2: the API's agent memory shows S2 as the Mapper's session", saved.get("session_id") == s2)
    finish_deal("phase 2")

    # Phase 3
    print("phase 3: next deal resumes the successor", flush=True)
    c.post("/dev/reset", params={"keep_memory": "true"})
    n = len(MAPPER_CALLS)
    status, body = run()
    nxt = (MAPPER_CALLS[n:] + [{}])[0]
    check("phase 3: the Mapper resumed S2", nxt.get("resumed") and nxt.get("session_id") == s2,
          f"session={nxt.get('session_id')}, resume_error={nxt.get('resume_error')}")
    check("phase 3: no refusal and no rewind", not nxt.get("rewound") and "refused" not in " ".join(body.get("log") or []))
    finish_deal("phase 3")

    # Factory's own records
    bad = refused.get("turn_message_id")
    r1, r2 = record(s1), record(s2)
    check("records: S1 holds the refused turn", bad and bad in r1)
    check("records: S2 does not hold the refused turn", bad and r2 and bad not in r2)
    check("records: S2 holds the phase 3 turn", nxt.get("turn_message_id") and nxt["turn_message_id"] in r2)
    print("served models:", sorted({str(m.get("model_served")) for m in MAPPER_CALLS}))
    print(f"S1={s1}\nS2={s2}\nrefused turn={bad}\nphase 3 turn={nxt.get('turn_message_id')}")
    failed = [name for name, ok, _ in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed" + (f"; failed: {failed}" if failed else ""))
    server.should_exit = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
