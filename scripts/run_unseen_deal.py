"""Run the whole deal with an input no agent has seen: Kewaunee acquires the company in a QuickBooks trial balance.

For a judge who asks for a scenario of their own. The platform, the brief, and the lender's limit are the demo deal's;
the target is any QuickBooks Online trial balance with its Account List (.xlsx needs openpyxl, or save both as CSV).
It runs in memory, on the backend in AGENT_BACKEND (droid on the demo laptop), through the same gateway checks, and
prints the flags, the mappings, and the verdict. Nothing is written to Tiger.

    cd backend
    set -a; . ../.env; set +a
    STORE=memory FORKS=off RECORD_RUNS=0 .venv/bin/python ../scripts/run_unseen_deal.py \
        ../scripts/samples/qbo/trial_balance.xlsx ../scripts/samples/qbo/account_list.xlsx

It answers every flag with the agent's suggested option, so it stops at awaiting approval, like the console.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # load_lines
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))  # app

from load_lines import load_trial_balance  # noqa: E402

from app.agents import runner  # noqa: E402
from app.agents.jobs import advance  # noqa: E402
from app.core.models import CONTROLLER, Deal  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    trial_balance, account_list = Path(argv[0]), Path(argv[1])
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    base = store.deals[DEAL_ID]
    deal_id = "d_unseen"
    target, warnings = load_trial_balance(trial_balance, deal_id, store, account_list)
    for w in warnings:
        print(f"loader: {w}")
    if not any(l.section == "cash_flow" and "depreciation" in l.line.lower() for l in target):
        # The ebitda tool needs a D&A line per company; a company that books none gets one at zero, said here.
        target.append(target[0].model_copy(update={
            "id": store.next_id("sl"), "line": "Depreciation and amortization", "section": "cash_flow", "amount": 0.0,
            "is_total": False, "source_ref": "none in the trial balance; added at 0", "note": None}))
        print("loader: added Depreciation and amortization at 0")
    platform = [l.model_copy(update={"id": store.next_id("sl"), "deal_id": deal_id, "covenant_tag": "na",
                                     "covenant_note": None, "covenant_policy_id": None})
                for l in store.lines(DEAL_ID, base.platform)]
    deal = Deal(id=deal_id, name=f"{base.platform} acquires {target[0].company}", platform=base.platform,
                target=target[0].company, brief=base.brief)
    gw.create_deal(CONTROLLER, deal, platform + target)
    print(f"{deal.name}: {len(platform)} platform lines, {len(target)} target lines")

    start = time.time()
    for step in advance(gw, deal_id):
        print(f"  {step}")
    print(f"stopped after {time.time() - start:.0f} s")
    for flag in gw.open_flags(deal_id):
        print(f"\nFLAG ({flag.payload.get('kind')}): {flag.question}")
        for o in flag.options:
            mark = "*" if o.id == flag.default else " "
            print(f"  {mark} {o.label}\n      {o.effect} [{o.run_id or 'no run'}]")
        gw.answer(CONTROLLER, flag.id, flag.default or flag.options[0].id)

    print("\nMAPPINGS (target line -> platform line, confidence)")
    for m in store.deal_mappings(deal_id):
        print(f"  {m.target_line} -> {m.platform_line or 'unmapped'} ({m.confidence:.2f})")

    start = time.time()
    for step in advance(gw, deal_id):
        print(f"  {step}")
    result = store.latest_result(deal_id)
    if result:
        print(f"\nVERDICT: {result.leverage:.2f}x against {result.limit:.2f}x, {result.verdict}, "
              f"Reviewer {result.review.verdict if result.review else 'pending'}, backend {result.backend}, "
              f"{time.time() - start:.0f} s after the answers")
    denied = [r for r in store.audit if r.result == "DENIED"]
    print(f"gateway refusals: {len(denied)}; chain intact: {gw.verify_chain()}; "
          f"Factory credits: {runner.TOTALS['factory_credits']:.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
