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


def _run(gw: Gateway, role: Role, inp, deal_id: str, item_id: str, backend: str | None,
         rewind_to: str | None = None):
    """Run a role with its saved session, so a backend that can resume (Droid) continues the same conversation."""
    extra = {"rewind_to": rewind_to} if rewind_to else {}  # only a retry after a refusal asks for a rewind
    return run_agent(role, inp, _call_tool(gw, role.actor, deal_id), session=gw.store.sessions.get(role.name),
                     backend=backend, **extra)


def _refused_turn(gw: Gateway, role: Role, run) -> str | None:
    """The message id that started a refused turn, when that turn was added to the role's saved session.
    The retry rewinds the session to before it, so the refused answer never becomes the agent's memory.
    A turn that ran in a new session needs no rewind: `_remember` was not called, so that session is not kept."""
    ok = next((a for a in reversed(run.attempts) if a.get("ok")), {})
    saved = gw.store.sessions.get(role.name)
    if ok.get("resumed") and saved and ok.get("session_id") == saved.session_id:
        return ok.get("turn_message_id")
    return None


def _store_or_fall_back(gw: Gateway, role: Role, inp, deal_id: str, item_id: str, backend: str | None, store_fn,
                        log: list[str], retry_with_reason: bool = False):
    """Run the role and hand its result to the gateway. If the gateway refuses it, the refusal is already in the
    audit log; the Mapper first retries once with the reason, then the scripted backend makes the result, so a
    refused model result costs one more run instead of failing the deal on stage. The scripted result goes
    through the same checks."""
    run = _run(gw, role, inp, deal_id, item_id, backend)
    try:
        return run, store_fn(run)
    except Invalid as error:
        log.append(f"{role.name} result refused on {run.backend}: {error.message}")
        if retry_with_reason and run.backend != "scripted":
            # The agent forgets its refused answer (rewind) but still learns why it was refused (previous_refusal).
            rewind_to = _refused_turn(gw, role, run)
            inp = inp.model_copy(update={"previous_refusal": error.message})
            run = _run(gw, role, inp, deal_id, item_id, backend, rewind_to=rewind_to)
            ok = next((a for a in reversed(run.attempts) if a.get("ok")), {})
            if ok.get("rewound"):
                log.append(f"{role.name} session rewound before the retry: {ok.get('rewound_from_session')} "
                           f"-> {ok.get('session_id')}")
            elif rewind_to:
                log.append(f"{role.name} session not rewound: {ok.get('rewind_error') or 'the retry ran on ' + run.backend}")
            try:
                return run, store_fn(run)
            except Invalid as again:
                log.append(f"{role.name} result refused again on {run.backend}: {again.message}")
        if run.backend == "scripted":
            raise
    run = _run(gw, role, inp, deal_id, item_id, "scripted")
    log.append(f"{role.name} fell back to scripted after the refusal")
    return run, store_fn(run)


def _remember(gw: Gateway, role: Role, run, item_id: str, summary: str) -> None:
    """Record the turn on the role's session, with the backend session id when the backend returned one."""
    ok = next((a for a in reversed(run.attempts) if a.get("ok")), {})
    gw.update_session(role.name, run.backend, item_id, summary, ok.get("session_id"), ok.get("session_key"))


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
            run, _ = _store_or_fall_back(gw, MAPPER_ROLE, inp, deal_id, item.id, backend,
                                         lambda r: gw.store_mapping(MAPPER_ROLE.actor, item.id, r.output), log,
                                         retry_with_reason=True)
            _remember(gw, MAPPER_ROLE, run, item.id,
                      f"mapped {len(run.output.mappings)} lines, {len(run.output.flags)} flags")
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
            run, result = _store_or_fall_back(
                gw, PREPARER_ROLE, inp, deal_id, item.id, backend,
                lambda r: gw.store_result(PREPARER_ROLE.actor, item.id, r.output, backend=r.backend), log)
            _remember(gw, PREPARER_ROLE, run, item.id, f"result {result.id}: leverage {result.leverage:.2f}x")
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
            run, _ = _store_or_fall_back(gw, REVIEWER_ROLE, inp, deal_id, item.id, backend,
                                         lambda r: gw.store_review(REVIEWER_ROLE.actor, item.id, r.output), log)
            _remember(gw, REVIEWER_ROLE, run, item.id, f"{run.output.verdict} on {result.id}")
            log.append(f"reviewer ran on {run.backend}: {run.output.verdict}")
            continue
        log.append(f"waiting on the controller ({deal.stage})")
        break
    return log
