"""The job runner. Plain code, not a model. It moves work items from one agent to the next.

It reads the deal's state from the store, opens the next work item through the gateway, runs the agent for it,
and hands the typed result back to the gateway. It holds no state of its own: it can run again at any time and
will find the next thing to do.
"""
from __future__ import annotations

from app.agents.roles import MAPPER_ROLE, PREPARER_ROLE, REVIEWER_ROLE, Role
from app.agents.runner import run_agent
from app.core.models import MapperInput, PreparerInput, ReviewerInput, State
from app.gateway.gateway import Gateway, Invalid


def _call_tool(gw: Gateway, actor: str, deal_id: str):
    def call(name: str, inputs: dict):
        return gw.run_tool(actor, deal_id, name, inputs)
    return call


def _run(gw: Gateway, role: Role, inp, deal_id: str, item_id: str, backend: str | None):
    session = gw.session(role.name, backend or "auto")
    run = run_agent(role, inp, _call_tool(gw, role.actor, deal_id), session=session, backend=backend)
    return run


def advance(gw: Gateway, deal_id: str, backend: str | None = None, max_steps: int = 6) -> list[str]:
    """Do every step that needs no human until the deal waits on a human or is posted. Returns what happened."""
    log: list[str] = []
    store = gw.store
    for _ in range(max_steps):
        deal = store.deals[deal_id]
        if gw.open_flags(deal_id):
            log.append("waiting on a flag")
            break
        items = store.deal_items(deal_id)
        by_type = {}
        for i in items:
            by_type.setdefault(i.type, []).append(i)
        mapped = any(i.state in (State.POSTED, State.PROPOSED) for i in by_type.get("map_lines", []))
        if not mapped:
            item = gw.create_item(deal_id, "map_lines")
            inp = MapperInput(deal_id=deal_id, platform=deal.platform, target=deal.target,
                              target_lines=store.lines(deal_id, deal.target),
                              platform_lines=store.lines(deal_id, deal.platform), brief=deal.brief,
                              policies=store.role_policies(MAPPER_ROLE.actor),
                              session=store.sessions.get(MAPPER_ROLE.name))
            run = _run(gw, MAPPER_ROLE, inp, deal_id, item.id, backend)
            try:
                gw.store_mapping(MAPPER_ROLE.actor, item.id, run.output)
            except Invalid as error:  # the gateway logged the refusal; one retry with the reason, then fail as before
                log.append(f"mapper result refused on {run.backend}: {error.message}")
                inp = inp.model_copy(update={"previous_refusal": error.message})
                run = _run(gw, MAPPER_ROLE, inp, deal_id, item.id, backend)
                gw.store_mapping(MAPPER_ROLE.actor, item.id, run.output)
            gw.update_session(MAPPER_ROLE.name, run.backend, item.id,
                              f"mapped {len(run.output.mappings)} lines, {len(run.output.flags)} flags",
                              next((a.get("session_id") for a in run.attempts if a.get("session_id")), None))
            log.append(f"mapper ran on {run.backend}")
            continue
        prep = [i for i in by_type.get("prepare_result", []) if i.state not in (State.REJECTED, State.REVERSED)]
        live_prep = prep[-1] if prep else None
        if live_prep is None or live_prep.state == State.NEW:
            item = live_prep or gw.create_item(deal_id, "prepare_result")
            inp = PreparerInput(deal_id=deal_id, item_id=item.id, platform_lines=store.lines(deal_id, deal.platform),
                                target_lines=store.lines(deal_id, deal.target),
                                mappings=[m for m in store.deal_mappings(deal_id) if not m.flagged or m.approved_by],
                                brief=deal.brief, session=store.sessions.get(PREPARER_ROLE.name))
            run = _run(gw, PREPARER_ROLE, inp, deal_id, item.id, backend)
            result = gw.store_result(PREPARER_ROLE.actor, item.id, run.output, backend=run.backend)
            gw.update_session(PREPARER_ROLE.name, run.backend, item.id,
                              f"result {result.id}: leverage {result.leverage:.2f}x")
            log.append(f"preparer ran on {run.backend}: leverage {result.leverage:.2f}x")
            continue
        result_id = live_prep.payload.get("result_id")
        reviews = [i for i in by_type.get("review_result", []) if i.payload.get("result_id") == result_id]
        if not reviews or reviews[-1].state == State.NEW:
            item = reviews[-1] if reviews else gw.create_item(deal_id, "review_result", payload={"result_id": result_id})
            result = store.results[result_id]
            inp = ReviewerInput(deal_id=deal_id, item_id=item.id, result_id=result.id, rows=result.rows,
                                ebitda=result.ebitda, debt=result.debt, leverage=result.leverage, limit=result.limit,
                                run_ids=result.run_ids, consolidate_run_id=result.run_ids_by_tool.get("consolidate"),
                                leverage_run_id=result.run_ids_by_tool.get("leverage"),
                                session=store.sessions.get(REVIEWER_ROLE.name))
            run = _run(gw, REVIEWER_ROLE, inp, deal_id, item.id, backend)
            gw.store_review(REVIEWER_ROLE.actor, item.id, run.output)
            gw.update_session(REVIEWER_ROLE.name, run.backend, item.id, f"{run.output.verdict} on {result.id}")
            log.append(f"reviewer ran on {run.backend}: {run.output.verdict}")
            continue
        log.append(f"waiting on the controller ({deal.stage})")
        break
    return log
