"""Score the Mapper's line mappings against the Note 2 answer key (evals/answer_key.csv).

    backend/.venv/bin/python evals/score_mapper.py                 # scripted backend, no key needed
    backend/.venv/bin/python evals/score_mapper.py --backend anthropic

Runs the Kewaunee deal in-process the way scripts/record_run.py does, but records nothing.
The Mapper is scored on what it proposed before any human answer, so a controller's choice does not count as the
Mapper's. The final mappings, after each flag takes its default answer, are shown where they differ.
Key rows with basis "none" have no answer in Note 2: they are listed with the Mapper's answer and not scored.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = Path(__file__).resolve().parent / "answer_key.csv"
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from app.agents.jobs import advance  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, TARGET, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402


def load_key() -> dict[tuple[str, str], dict]:
    with KEY.open(newline="") as f:
        return {(r["section"], r["target_line"]): r for r in csv.DictReader(f)}


def snapshot(store: MemoryStore) -> dict[tuple[str, str], dict]:
    """(section, target line) -> the Mapper's answer, for detail lines only (the key skips totals)."""
    lines = {l.id: l for l in store.lines(DEAL_ID, TARGET)}
    out = {}
    for m in store.deal_mappings(DEAL_ID):
        t = lines[m.target_line_id]
        if not t.is_total:
            out[(t.section, t.line)] = {"platform_line": m.platform_line or "", "confidence": m.confidence,
                                        "flagged": m.flagged, "reason": m.reason}
    return out


def run(backend: str) -> tuple[dict, dict, list[str]]:
    os.environ["RECORD_RUNS"] = "0"  # an eval run is not a recording
    os.environ["AGENT_FALLBACK"] = ""  # the score must come from the backend asked for
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    log = advance(gw, DEAL_ID, backend=backend)
    proposed = snapshot(store)
    for flag in gw.open_flags(DEAL_ID):
        gw.answer("human:controller", flag.id, flag.default or flag.options[0].id)
    log += advance(gw, DEAL_ID, backend=backend)
    return proposed, snapshot(store), log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default=os.getenv("AGENT_BACKEND", "scripted"))
    args = ap.parse_args()
    key = load_key()
    proposed, final, _ = run(args.backend)

    agree, disagree, uncovered = [], [], []
    for k, row in key.items():
        if k not in proposed:
            continue
        got = proposed[k]
        if row["basis"] == "none":
            uncovered.append((k, got))
        elif got["platform_line"] == row["platform_line"]:
            agree.append((k, row, got))
        else:
            disagree.append((k, row, got))
    missing_from_mapper = [k for k in key if k not in proposed]
    missing_from_key = [k for k in proposed if k not in key]

    print(f"backend: {args.backend}")
    print(f"answer key: {KEY.relative_to(ROOT)} ({len(key)} rows, preliminary, shape only)")
    for basis in ("note2", "note2_total"):
        n = sum(1 for _, r, _ in agree + disagree if r["basis"] == basis)
        a = sum(1 for _, r, _ in agree if r["basis"] == basis)
        print(f"  {basis:<12} {a}/{n} agree")
    scored = len(agree) + len(disagree)
    print(f"  {'all scored':<12} {len(agree)}/{scored} agree")

    print("\nagreements:")
    for (section, line), row, got in agree:
        flag = " [flagged]" if got["flagged"] else ""
        print(f"  {section:<16} {line} -> {row['platform_line']} ({got['confidence']:.2f}){flag}")
    print("\ndisagreements (key vs Mapper):")
    for (section, line), row, got in disagree or []:
        print(f"  {section:<16} {line}\n      key:    {row['platform_line'] or '(unmapped)'}  [{row['basis']}]"
              f"\n      mapper: {got['platform_line'] or '(unmapped)'} ({got['confidence']:.2f}) - {got['reason']}")
    if not disagree:
        print("  none")
    print("\nnot covered by Note 2 (not scored):")
    for (section, line), got in uncovered:
        flag = " [flagged]" if got["flagged"] else ""
        print(f"  {section:<16} {line} -> mapper: {got['platform_line'] or '(unmapped)'} ({got['confidence']:.2f}){flag}")
    print("\nin the key but not mapped by the Mapper:", [l for _, l in missing_from_mapper] or "none")
    print("mapped by the Mapper but not in the key:", [l for _, l in missing_from_key] or "none")

    changed = [(k, proposed[k], final[k]) for k in proposed if k in final and final[k]["platform_line"] != proposed[k]["platform_line"]]
    print("\nchanged by the default flag answers (not counted in the score):")
    for (section, line), before, after in changed:
        print(f"  {section:<16} {line}: {before['platform_line'] or '(unmapped)'} -> {after['platform_line'] or '(unmapped)'}")
    if not changed:
        print("  none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
