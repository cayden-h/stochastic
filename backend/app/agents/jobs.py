"""The job runner. Plain code, not a model. It moves work items from one agent to the next.

It reads the deal's state from the store, opens the next work item through the gateway, runs the agent for it,
and hands the typed result back to the gateway. It holds no state of its own: it can run again at any time and
will find the next thing to do.

With DEMO_PACE set, or a run's own pace ("demo", "human", "off"), it waits a little between steps on the scripted and
replay backends (app/agents/pace.py), so a demo run plays at a speed people can follow. The gateway's checks never
wait, and no wait holds the gateway's lock.

Pace "demo" (the 15-second "Run the demo") and pace "factory" (the 30-second Factory demo) never make a live call,
whatever AGENT_BACKEND says, unless the run names its own backend: they replay the recorded Claude Haiku 5.5 run when
it fits the deal (app/agents/demo_replay.py), and run the scripted rules otherwise, with no fallback chain either way.
"""
from __future__ import annotations

import contextlib
import os

from app.agents import demo_replay, pace, recording
from app.agents.roles import BRIEF_READER_ROLE, MAPPER_ROLE, PREPARER_ROLE, REVIEWER_ROLE, Role
from app.agents import runner
from app.agents.runner import run_agent
from app.core.models import VERIFIER, MapperInput, PreparerInput, ReviewerInput, State
from app.gateway.gateway import Gateway, Invalid


READ_TOOLS = ("get_section", "get_definition")  # the Brief Reader's read-only agreement tools


def _call_tool(gw: Gateway, actor: str, deal_id: str, pace_as: str | None = None):
    def call(name: str, inputs: dict):
        pace.pause("tool", pace_as)
        if name in READ_TOOLS:
            return gw.read_agreement(actor, deal_id, name, inputs)
        return gw.run_tool(actor, deal_id, name, inputs)
    return call


def _chosen(backend: str | None) -> str:
    return backend or os.getenv("AGENT_BACKEND", "scripted")


def _run(gw: Gateway, role: Role, inp, deal_id: str, item_id: str, backend: str | None,
         rewind_to: str | None = None, pace_as: str | None = None):
    """Run a role with its saved session, so a backend that can resume (Droid) continues the same conversation.
    `pace_as` is the backend the run was asked for: a scripted fallback after a live model's refusal is not paced."""
    pace_as = pace_as or _chosen(backend)
    pace.pause("turn", pace_as)
    extra = {"rewind_to": rewind_to} if rewind_to else {}  # only a retry after a refusal asks for a rewind
    return run_agent(role, inp, _call_tool(gw, role.actor, deal_id, pace_as), session=gw.store.sessions.get(role.name),
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
    asked = _chosen(backend)
    run = _run(gw, role, inp, deal_id, item_id, backend)
    try:
        return run, _stored(store_fn, run, asked)
    except Invalid as error:
        log.append(f"{role.name} result refused on {run.backend}: {error.message}")
        if retry_with_reason and run.backend != "scripted":
            # The agent forgets its refused answer (rewind) but still learns why it was refused (previous_refusal).
            rewind_to = _refused_turn(gw, role, run)
            inp = inp.model_copy(update={"previous_refusal": error.message})
            gw.note(deal_id, role.actor, f"Try once more on {run.backend}, with the gateway's reason", item_id=item_id)
            run = _run(gw, role, inp, deal_id, item_id, backend, rewind_to=rewind_to)
            ok = next((a for a in reversed(run.attempts) if a.get("ok")), {})
            if ok.get("rewound"):
                log.append(f"{role.name} session rewound before the retry: {ok.get('rewound_from_session')} "
                           f"-> {ok.get('session_id')}")
            elif rewind_to:
                log.append(f"{role.name} session not rewound: {ok.get('rewind_error') or 'the retry ran on ' + run.backend}")
            try:
                return run, _stored(store_fn, run, asked)
            except Invalid as again:
                log.append(f"{role.name} result refused again on {run.backend}: {again.message}")
        if run.backend == "scripted":
            raise
    gw.note(deal_id, role.actor, f"The {run.backend} result was refused; the scripted backend makes it under the same "
                                 f"checks", item_id=item_id)
    run = _run(gw, role, inp, deal_id, item_id, "scripted", pace_as=asked)
    log.append(f"{role.name} fell back to scripted after the refusal")
    return run, _stored(store_fn, run, asked)


def _stored(store_fn, run, asked: str):
    """Hand the result to the gateway, then wait the step's pace (off unless DEMO_PACE is set)."""
    out = store_fn(run)
    pace.pause("after", asked)
    return out


def _remember(gw: Gateway, role: Role, run, item_id: str, summary: str) -> None:
    """Record the turn on the role's session, with the backend session id when the backend returned one."""
    ok = next((a for a in reversed(run.attempts) if a.get("ok")), {})
    gw.update_session(role.name, run.backend, item_id, summary, ok.get("session_id"), ok.get("session_key"))


def advance(gw: Gateway, deal_id: str, backend: str | None = None, max_steps: int = 8,
            pace_name: str | None = None) -> list[str]:
    """Do every step that needs no human until the deal waits on a human or is posted. Returns what happened.

    `pace_name` ("demo", "factory", "human", "off") paces this run whatever DEMO_PACE says; None follows DEMO_PACE.
    Pace "demo" or "factory" with no `backend` pins every role to one backend with no fallback chain, so the demo never
    makes a live model call (a .env with AGENT_BACKEND=droid would otherwise take about 45 s and Factory credits): the
    replay of the recorded Claude Haiku 5.5 run when it fits the deal, else the scripted rules, with a note that says
    why. The Brief Reader has no Haiku recording, so a Brief step in a replayed run runs the scripted rules.
    A run that stops on an error marks the deal `run_failed` with a `run:failed` row before the error goes up, so
    the console offers Run again on the sync route too, not only after a background run."""
    try:
        pin, folder, ids = None, None, None
        if pace_name in demo_replay.DEMO_PACES and backend is None:
            plan = demo_replay.plan(gw, deal_id)
            pin, folder, ids = plan.backend, plan.folder, plan.ids
            if plan.reason and not gw.store.deal_items(deal_id, "map_lines"):
                gw.note(deal_id, MAPPER_ROLE.actor, f"Scripted rules for this run, not the recorded Claude Haiku 5.5 "
                                                    f"run: {plan.reason}")
        with pace.using(pace_name), runner.only(pin), recording.using(folder, ids):
            return _advance(gw, deal_id, pin or backend, max_steps)
    except Exception as error:
        if deal_id in gw.store.deals:  # the deal may have been reset meanwhile
            gw.note_run_failed(deal_id, f"{type(error).__name__}: {error}")
        raise


def _advance(gw: Gateway, deal_id: str, backend: str | None, max_steps: int) -> list[str]:
    log: list[str] = []
    store = gw.store
    for _ in range(max_steps):
        deal = store.deals[deal_id]
        if gw.needs_verification(deal_id):
            # The verifier checks the reader's draft before anyone is asked anything (D23): code, not a model, so it
            # runs the same on every backend. Its checks are paced like the mappings, outside the gateway lock.
            asked = _chosen(backend)
            n = gw.verification_size(deal_id)
            report = gw.verify_brief(VERIFIER, deal_id, progress=lambda step: pace.pause(step, asked, count=n))
            pace.pause("after", asked)
            log.append(f"verifier: {report.passed} of {len(report.checks)} checks passed"
                       + (", Brief auto-approved" if report.auto_approved else ""))
            continue
        if gw.open_flags(deal_id):
            log.append("waiting on a flag")
            break
        items = store.deal_items(deal_id)
        by_type = {}
        for i in items:
            by_type.setdefault(i.type, []).append(i)
        if deal.brief_status != "approved":
            # The Brief comes first (D20): the reader drafts it, the controller answers its flags and approves it.
            drafts = [i for i in by_type.get("draft_brief", []) if i.state not in (State.REJECTED, State.REVERSED)]
            live = drafts[-1] if drafts else None
            if live is None or live.state == State.NEW:
                item = live or gw.create_item(deal_id, "draft_brief")
                inp = gw.brief_reader_input(deal_id, item.id).model_copy(
                    update={"session": store.sessions.get(BRIEF_READER_ROLE.name)})
                # No Haiku recording exists for the Brief Reader: a replayed demo run reads the Brief with the rules.
                replayed = runner.pinned() == "replay"
                reader = "scripted" if replayed else backend
                pace.pause("read", reader or _chosen(backend))  # reading the agreement (D23)
                with runner.only("scripted") if replayed else contextlib.nullcontext():
                    run, _ = _store_or_fall_back(gw, BRIEF_READER_ROLE, inp, deal_id, item.id, reader,
                                                 lambda r: gw.store_brief(BRIEF_READER_ROLE.actor, item.id, r.output),
                                                 log, retry_with_reason=True)
                _remember(gw, BRIEF_READER_ROLE, run, item.id,
                          f"drafted the Brief: {len(run.output.citations)} citations, {len(run.output.flags)} flags")
                log.append(f"brief reader ran on {run.backend}")
                continue
            log.append("waiting on the controller to approve the Brief")
            break
        mapped = any(i.state in (State.POSTED, State.PROPOSED) for i in by_type.get("map_lines", []))
        if not mapped:
            item = gw.create_item(deal_id, "map_lines")
            inp = MapperInput(deal_id=deal_id, platform=deal.platform, target=deal.target,
                              target_lines=store.lines(deal_id, deal.target),
                              platform_lines=store.lines(deal_id, deal.platform), brief=deal.brief,
                              policies=gw.policies_for(MAPPER_ROLE.actor, deal_id),
                              session=store.sessions.get(MAPPER_ROLE.name))
            asked = _chosen(backend)

            def store_mapping(r):
                n = len(r.output.mappings)
                return gw.store_mapping(MAPPER_ROLE.actor, item.id, r.output,
                                        progress=lambda step: pace.pause(step, asked, count=n))
            run, _ = _store_or_fall_back(gw, MAPPER_ROLE, inp, deal_id, item.id, backend, store_mapping,
                                         log, retry_with_reason=True)
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
                                brief=deal.brief, adjustments=gw.adjustments_for(deal_id),
                                session=store.sessions.get(PREPARER_ROLE.name))
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
