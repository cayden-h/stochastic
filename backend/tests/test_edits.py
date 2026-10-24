"""Review edits in the gateway (D19, design/review-companion.md): apply, reason, revert, and what the agents learn.

Tests that need recomputed figures skip until Tri's edit-aware tools (T1) are installed, and then run by themselves.
Flow tests that only need a recompute to have happened replace `Gateway._recompute` with the same tool chain run
without edits; no figure test does that.
"""
import inspect
import math
import os

import pytest

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

from app.agents.backends.scripted import scripted_mapper  # noqa: E402
from app.agents.jobs import advance  # noqa: E402
from app.core.models import (  # noqa: E402
    CONTROLLER, MAPPER, PREPARER, REVIEWER, SYSTEM, Deal, Edit, MapperInput, Policy, State,
)
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import (  # noqa: E402
    EDIT_TOOLS, T1_MISSING, Denied, Gateway, IllegalTransition, Invalid, NotReady,
)
from app.tools import finance  # noqa: E402

T1_READY = all("edits" in inspect.signature(finance.TOOLS[n]).parameters for n in EDIT_TOOLS)
needs_t1 = pytest.mark.skipif(not T1_READY, reason="needs T1 edit-aware tools")

TARGET, PLATFORM = "Nu Aire", "Kewaunee"
AMOUNT_LINE = "General and Administrative"  # Nu Aire income statement, $6,162,806 filed, 6,162.806 in thousands
REMAP_LINE = "Certificates of Deposit"  # mapped to cash by the Mapper's flag; the filing does not say they are cash
REMAP_TO = "Prepaid expenses and other current assets"
AMOUNT_CHIPS = ["One-time acquisition cost, an allowed add-back", "Auditor's late adjustment",
                "Correcting a typo in the source"]
REMAP_CHIPS = ["Not a cash equivalent (over 90 days)", "Matches how the platform reports it",
               "Auditor's reclassification"]


def _recompute_without_edits(self, deal_id, edit_ids):
    """Flow tests only: the same six runs as the system, without edits, so the flow can be tested before T1."""
    cons = self.run_tool(SYSTEM, deal_id, "consolidate", {})
    eb = self.run_tool(SYSTEM, deal_id, "ebitda", {})
    debt = self.run_tool(SYSTEM, deal_id, "covenant_debt", {"naive": False})
    lev = self.run_tool(SYSTEM, deal_id, "leverage", {"debt_run_id": debt.run_id, "ebitda_run_id": eb.run_id})
    tie = self.run_tool(SYSTEM, deal_id, "tie_out", {"run_id": cons.run_id})
    test = self.run_tool(SYSTEM, deal_id, "limit_test", {"leverage_run_id": lev.run_id})
    return {"consolidate": cons, "ebitda": eb, "covenant_debt": debt, "leverage": lev, "tie_out": tie,
            "limit_test": test}


@pytest.fixture
def world():
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    return store, gw


@pytest.fixture
def flow(monkeypatch, world):
    monkeypatch.setattr(Gateway, "_recompute", _recompute_without_edits)
    return world


def run_to_approval(gw, deal_id=DEAL_ID):
    advance(gw, deal_id)
    for flag in gw.open_flags(deal_id):
        gw.answer(CONTROLLER, flag.id, flag.default or flag.options[0].id)
    advance(gw, deal_id)
    approval = gw.store.deal_items(deal_id, "approve_result")[-1]
    assert approval.state == State.PROPOSED
    return approval


def amount_edit(gw, value=5662.806, actor=CONTROLLER, deal_id=DEAL_ID):
    return gw.apply_edit(actor, deal_id, "amount", TARGET, AMOUNT_LINE, value=value)


def remap_edit(gw, actor=CONTROLLER, deal_id=DEAL_ID):
    return gw.apply_edit(actor, deal_id, "remap", TARGET, REMAP_LINE, platform_line=REMAP_TO)


def rows(store, action, result=None):
    return [r for r in store.audit if r.action == action and (result is None or r.result == result)]


def next_deal(store, gw, deal_id="d_kequ_second", target="Acme Labs", platform=PLATFORM):
    """A later add-on of the same platform: the demo deal's lines, with the target renamed (and the platform, if asked)."""
    first = store.deals[DEAL_ID]
    lines = []
    for line in store.lines(DEAL_ID):
        company = target if line.company == TARGET else platform
        lines.append(line.model_copy(update={"id": f"{deal_id}_{line.id}", "deal_id": deal_id, "company": company,
                                             "covenant_tag": "na", "covenant_note": None,
                                             "covenant_policy_id": None}))
    deal = Deal(id=deal_id, name=f"{platform} acquires {target}", platform=platform, target=target, brief=first.brief)
    gw.create_deal(CONTROLLER, deal, lines)
    return deal


def mapping_of(store, deal_id, line_name):
    return next(m for m in store.deal_mappings(deal_id) if m.target_line.lower() == line_name.lower())


# ---- who may edit, and when ----------------------------------------------------------------------------------

def test_an_edit_by_an_agent_is_refused(world):
    store, gw = world
    approval = run_to_approval(gw)
    for actor in (MAPPER, PREPARER, REVIEWER, SYSTEM, "human:intern"):
        with pytest.raises(Denied):
            amount_edit(gw, actor=actor)
        with pytest.raises(Denied):
            remap_edit(gw, actor=actor)
    denied = rows(store, "edit:apply", "DENIED")
    assert {r.actor for r in denied} == {MAPPER, PREPARER, REVIEWER, SYSTEM, "human:intern"}
    assert all("only human:controller" in r.reason for r in denied)
    assert not store.edits and approval.state == State.PROPOSED
    assert gw.verify_chain()


def test_agents_cannot_reason_or_revert_an_edit(flow):
    store, gw = flow
    run_to_approval(gw)
    edit = amount_edit(gw)["edit"]
    for actor in (MAPPER, PREPARER, REVIEWER):
        with pytest.raises(Denied):
            gw.reason_edit(actor, edit.id, chip=0)
        with pytest.raises(Denied):
            gw.revert_edit(actor, edit.id)
    assert edit.status == "needs_reason"
    assert len(rows(store, "edit:reason", "DENIED")) == 3 and len(rows(store, "edit:revert", "DENIED")) == 3


def test_an_edit_is_refused_before_the_agents_finish_and_after_approval(flow):
    store, gw = flow
    advance(gw, DEAL_ID)  # waiting on the flags: no result yet
    with pytest.raises(IllegalTransition):
        amount_edit(gw)
    for flag in gw.open_flags(DEAL_ID):
        gw.answer(CONTROLLER, flag.id, flag.default)
    advance(gw, DEAL_ID)
    approval = store.deal_items(DEAL_ID, "approve_result")[-1]
    gw.approve(CONTROLLER, approval.id)
    with pytest.raises(IllegalTransition):
        amount_edit(gw)
    assert not store.edits
    assert all("only while the result is PROPOSED" in r.reason for r in rows(store, "edit:apply", "DENIED"))


@pytest.mark.skipif(T1_READY, reason="T1 is installed; this checks the refusal before it")
def test_without_t1_an_edit_is_refused_and_nothing_is_kept(world):
    store, gw = world
    approval = run_to_approval(gw)
    results = len(store.results)
    with pytest.raises(NotReady) as error:
        amount_edit(gw)
    assert T1_MISSING in error.value.message
    assert not store.edits and len(store.results) == results and approval.state == State.PROPOSED
    assert T1_MISSING in rows(store, "edit:apply", "DENIED")[-1].reason


def test_bad_edits_are_refused_and_name_the_problem(world):
    store, gw = world
    run_to_approval(gw)
    cases = [
        (dict(kind="amount", company=TARGET, line="No such line", value=1.0), "has no line"),
        (dict(kind="amount", company=TARGET, line="Net Income", value=1.0), "subtotal"),
        (dict(kind="amount", company="Someone else", line=AMOUNT_LINE, value=1.0), "company must be"),
        (dict(kind="amount", company=TARGET, line=AMOUNT_LINE, value=6162.806), "already"),
        (dict(kind="amount", company=TARGET, line=AMOUNT_LINE, value=math.nan), "finite"),
        (dict(kind="amount", company=TARGET, line=AMOUNT_LINE, value="12"), "finite"),
        (dict(kind="amount", company=TARGET, line=AMOUNT_LINE), "finite"),
        (dict(kind="remap", company=PLATFORM, line="Inventories", platform_line="Inventories"), "platform"),
        (dict(kind="remap", company=TARGET, line=REMAP_LINE, platform_line="Bitcoin"), "is not a Kewaunee line"),
        (dict(kind="remap", company=TARGET, line=REMAP_LINE, platform_line="Cash and cash equivalents"), "already"),
        (dict(kind="split", company=TARGET, line=AMOUNT_LINE, value=1.0), "kind must be"),
    ]
    for fields, words in cases:
        with pytest.raises((Invalid, IllegalTransition)) as error:
            gw.apply_edit(CONTROLLER, DEAL_ID, **fields)
        assert words in error.value.message, (fields, error.value.message)
    assert not store.edits
    assert len(rows(store, "edit:apply", "DENIED")) == len(cases)


def test_tool_runs_take_edits_from_the_gateway_only(world):
    store, gw = world
    run_to_approval(gw)
    with pytest.raises(Invalid, match="only the gateway"):
        gw.run_tool(PREPARER, DEAL_ID, "consolidate", {"edit_ids": []})
    with pytest.raises(Invalid, match="takes no edits"):
        gw.run_tool(SYSTEM, DEAL_ID, "leverage", {"edit_ids": [], "debt": 1.0, "ebitda": 2.0})
    cons = gw.run_tool(SYSTEM, DEAL_ID, "consolidate", {})
    with pytest.raises(Invalid, match="takes no edits"):  # its rows already carry the edits
        gw.run_tool(SYSTEM, DEAL_ID, "tie_out", {"edit_ids": [], "run_id": cons.run_id})
    if not T1_READY:
        with pytest.raises(Invalid, match=r"T1"):
            gw.run_tool(SYSTEM, DEAL_ID, "consolidate", {"edit_ids": []})
    else:
        with pytest.raises(Invalid, match="not found"):
            gw.run_tool(SYSTEM, DEAL_ID, "consolidate", {"edit_ids": ["e_999"]})


# ---- the approval gate and the superseded item -----------------------------------------------------------------

def test_approval_is_refused_while_an_edit_needs_a_reason(flow):
    store, gw = flow
    old = run_to_approval(gw)
    out = amount_edit(gw)
    edit, new = out["edit"], out["approval"]
    assert edit.status == "needs_reason" and edit.old_value == 6162.806 and edit.new_value == 5662.806
    assert old.state == State.SUPERSEDED and old.id in store.items  # stays in the log
    assert new.state == State.PROPOSED and new.payload["edit_id"] == edit.id and new.payload["supersedes"] == old.id
    assert new.proposed_by == SYSTEM  # the gateway's recompute proposes it; the controller approves it below
    with pytest.raises(Denied) as error:
        gw.approve(CONTROLLER, new.id)
    assert edit.id in error.value.message
    denied = rows(store, "approve", "DENIED")[-1]
    assert denied.target == new.id and edit.id in denied.reason
    with pytest.raises(IllegalTransition):
        gw.approve(CONTROLLER, old.id)  # a superseded item is never approved
    gw.reason_edit(CONTROLLER, edit.id, chip=0)
    gw.approve(CONTROLLER, new.id)
    assert store.items[new.id].state == State.POSTED and store.deals[DEAL_ID].stage == "posted"


def test_a_second_edit_supersedes_again_and_a_reverted_edit_does_not_block_approval(flow):
    store, gw = flow
    first = run_to_approval(gw)
    a = amount_edit(gw)
    b = remap_edit(gw)
    approvals = store.deal_items(DEAL_ID, "approve_result")
    assert [i.state for i in approvals] == [State.SUPERSEDED, State.SUPERSEDED, State.PROPOSED]
    assert approvals[0].id == first.id
    assert store.results[b["result"].id].supersedes == a["result"].id
    with pytest.raises(IllegalTransition, match="already changes this line"):
        amount_edit(gw, value=1.0)
    gw.reason_edit(CONTROLLER, a["edit"].id, chip=1)
    after = gw.revert_edit(CONTROLLER, b["edit"].id)
    assert after["edit"].status == "reverted"
    gw.approve(CONTROLLER, after["approval"].id)
    assert store.deals[DEAL_ID].stage == "posted"


def test_reason_needs_one_chip_or_text_and_the_chips_are_hardcoded(flow):
    store, gw = flow
    run_to_approval(gw)
    out = amount_edit(gw)
    assert [c.label for c in out["reasons"]] == AMOUNT_CHIPS
    assert [c.label for c in gw.reason_chips(DEAL_ID, "remap")] == REMAP_CHIPS
    assert [c.label for c in gw.reason_chips("d_other", "amount")] == AMOUNT_CHIPS  # the demo list is the default
    edit = out["edit"]
    for kwargs in (dict(), dict(chip=0, text="both"), dict(chip=3), dict(chip=True), dict(text="   "),
                   dict(text="x" * 501)):
        with pytest.raises(Invalid):
            gw.reason_edit(CONTROLLER, edit.id, **kwargs)
    assert edit.status == "needs_reason"
    gw.reason_edit(CONTROLLER, edit.id, text="Bonus accrual booked twice", remember=False)
    assert edit.status == "reasoned" and edit.reason_text == "Bonus accrual booked twice" and edit.reason_chip is None
    assert edit.adjustment_id is None and not store.adjustments  # not remembered
    with pytest.raises(IllegalTransition):
        gw.reason_edit(CONTROLLER, edit.id, chip=0)


# ---- what the agents learn ----------------------------------------------------------------------------------

def test_a_reasoned_amount_edit_becomes_a_logged_adjustment(flow):
    store, gw = flow
    run_to_approval(gw)
    edit = amount_edit(gw)["edit"]
    gw.reason_edit(CONTROLLER, edit.id, chip=0)
    adj = store.adjustments[edit.adjustment_id]
    assert (adj.status, adj.company, adj.line, adj.amount, adj.edit_id) == ("applied", TARGET, AMOUNT_LINE,
                                                                           -500.0, edit.id)  # the change, not the value
    assert adj.reason == AMOUNT_CHIPS[0]
    learn = rows(store, "policy:learn")[-1]
    assert learn.target == adj.id and learn.reason.startswith(f"source: edit {edit.id}")
    assert "never applied silently" in learn.reason


def test_a_reasoned_remap_makes_a_platform_policy_that_the_mapper_applies_on_the_next_deal(flow):
    store, gw = flow
    run_to_approval(gw)
    assert mapping_of(store, DEAL_ID, REMAP_LINE).platform_line == "Cash and cash equivalents"
    out = remap_edit(gw)
    edit = out["edit"]
    assert (edit.old_platform_line, edit.new_platform_line) == ("Cash and cash equivalents", REMAP_TO)
    assert mapping_of(store, DEAL_ID, REMAP_LINE).platform_line == "Cash and cash equivalents"  # on top, not over
    assert [c.label for c in out["reasons"]] == REMAP_CHIPS
    gw.reason_edit(CONTROLLER, edit.id, chip=0, remember=True)
    policy = store.policies[edit.policy_id]
    assert (policy.kind, policy.scope, policy.platform, policy.company) == ("mapping", "platform", PLATFORM, None)
    assert (policy.pattern, policy.decision, policy.reason) == (REMAP_LINE.lower(), REMAP_TO, REMAP_CHIPS[0])
    assert policy.learned_from == edit.id and policy.approved_by == CONTROLLER and policy.role == MAPPER
    learn = rows(store, "policy:learn")[-1]
    assert learn.target == policy.id and learn.reason.startswith(f"source: edit {edit.id}")

    second = next_deal(store, gw)
    assert policy in gw.policies_for(MAPPER, second.id)
    advance(gw, second.id)
    m = mapping_of(store, second.id, REMAP_LINE)
    assert m.platform_line == REMAP_TO and m.policy_id == policy.id  # the console's Learned chip
    assert policy.id in m.reason and REMAP_CHIPS[0] in m.reason
    assert not any(REMAP_LINE in (f.question or "") for f in gw.open_flags(second.id))  # not asked again
    applied = [r for r in rows(store, "policy:apply") if r.deal_id == second.id and r.target == policy.id]
    assert applied and policy.times_applied == 1


def test_a_platform_policy_stays_on_its_platform(flow):
    store, gw = flow
    run_to_approval(gw)
    edit = remap_edit(gw)["edit"]
    gw.reason_edit(CONTROLLER, edit.id, chip=0)
    policy = store.policies[edit.policy_id]
    other = next_deal(store, gw, deal_id="d_other_platform", target="Acme Labs", platform="Other Platform")
    assert policy not in gw.policies_for(MAPPER, other.id)
    # Even if a model cites it, the gateway does not mark the line as learned on another platform.
    line = next(sl for sl in store.lines(other.id, "Acme Labs") if sl.line == REMAP_LINE)
    assert gw._cited_policy(policy.id, "mapping", REMAP_TO, line) is None
    # Nor on the platform's own lines: a platform policy covers the add-on's lines.
    own = next(sl for sl in store.lines(DEAL_ID, PLATFORM) if sl.section == "balance_sheet")
    assert gw._cited_policy(policy.id, "mapping", REMAP_TO, own.model_copy(update={"line": REMAP_LINE})) is None


def test_a_platform_policy_never_settles_a_not_debt_tag(world):
    """D18: only a policy learned on that company's line may exclude debt. A platform policy is never one."""
    store, gw = world
    advance(gw, DEAL_ID)
    fin = next(sl for sl in store.lines(DEAL_ID, PLATFORM) if sl.line == "Current portion of financing liability")
    rogue = Policy(id="p_rogue", role=MAPPER, kind="covenant_tag", pattern=fin.line.lower(), decision="not_debt",
                   reason="r", approved_by=CONTROLLER, learned_from="e_x", deal_id=DEAL_ID, scope="platform",
                   platform=PLATFORM)
    anyone = Policy(id="p_anyone", role=MAPPER, kind="covenant_tag", pattern=fin.line.lower(), decision="not_debt",
                    reason="r", approved_by=CONTROLLER, learned_from="wi_x", deal_id=DEAL_ID, company=None)
    store.policies.update({rogue.id: rogue, anyone.id: anyone})
    for pid in (rogue.id, anyone.id):
        assert gw._cited_policy(pid, "covenant_tag", "not_debt", fin) is None
    # The Mapper does not apply them either, so it still flags the line.
    deal = store.deals[DEAL_ID]
    inp = MapperInput(deal_id=DEAL_ID, platform=deal.platform, target=deal.target,
                      target_lines=store.lines(DEAL_ID, deal.target), platform_lines=store.lines(DEAL_ID, deal.platform),
                      brief=deal.brief, policies=[rogue, anyone])
    tag = next(t for t in scripted_mapper(inp).tags if t.line_id == fin.id)
    assert tag.tag == "unclear" and tag.policy_id is None
    assert rogue not in gw.policies_for(MAPPER, DEAL_ID) and anyone not in gw.policies_for(MAPPER, DEAL_ID)


def test_company_policies_reach_only_their_company(world):
    store, gw = world
    run_to_approval(gw)
    learned = [p for p in store.role_policies(MAPPER) if p.company == TARGET]
    assert learned  # the mapping flag on Nu Aire's certificates of deposit taught one
    other = next_deal(store, gw, deal_id="d_kequ_acme", target="Acme Labs")
    shown = gw.policies_for(MAPPER, other.id)
    assert not any(p.company == TARGET for p in shown)
    assert any(p.company == PLATFORM for p in shown)  # the platform company's own answers still apply


# ---- revert -------------------------------------------------------------------------------------------------

def test_a_revert_retires_the_policy_and_the_next_deal_is_asked_again(flow):
    store, gw = flow
    run_to_approval(gw)
    edit = remap_edit(gw)["edit"]
    gw.reason_edit(CONTROLLER, edit.id, chip=0)
    policy = store.policies[edit.policy_id]
    out = gw.revert_edit(CONTROLLER, edit.id)
    assert out["edit"].status == "reverted" and policy.retired_by == edit.id
    assert out["approval"].state == State.PROPOSED and out["result"].edit_ids == []
    retire = rows(store, "policy:retire")[-1]
    assert retire.target == policy.id and edit.id in retire.reason
    assert policy not in store.role_policies(MAPPER)
    with pytest.raises(IllegalTransition):
        gw.revert_edit(CONTROLLER, edit.id)
    second = next_deal(store, gw)
    advance(gw, second.id)
    m = mapping_of(store, second.id, REMAP_LINE)
    assert m.policy_id != policy.id and m.platform_line != REMAP_TO


def test_a_revert_retires_the_adjustment(flow):
    store, gw = flow
    run_to_approval(gw)
    edit = amount_edit(gw)["edit"]
    gw.reason_edit(CONTROLLER, edit.id, chip=0)
    gw.revert_edit(CONTROLLER, edit.id)
    assert store.adjustments[edit.adjustment_id].status == "retired"
    assert rows(store, "policy:retire")[-1].target == edit.adjustment_id


def test_the_audit_rows_of_an_edit(flow):
    store, gw = flow
    run_to_approval(gw)
    edit = remap_edit(gw)["edit"]
    gw.reason_edit(CONTROLLER, edit.id, chip=1)
    gw.revert_edit(CONTROLLER, edit.id)
    mine = [r for r in store.audit if r.target in (edit.id, edit.policy_id)]
    assert [(r.actor, r.action) for r in mine] == [
        (CONTROLLER, "edit:apply"), (CONTROLLER, "edit:reason"), (SYSTEM, "policy:learn"),
        (CONTROLLER, "edit:revert"), (SYSTEM, "policy:retire")]
    assert all(r.result == "ALLOWED" for r in mine)
    assert "source: edit" in mine[2].reason
    assert len(rows(store, "supersede")) == 2
    assert gw.verify_chain()


# ---- the figures (T1) ---------------------------------------------------------------------------------------

@needs_t1
def test_every_recompute_figure_equals_its_tool_run(world):
    store, gw = world
    approval = run_to_approval(gw)
    old = store.results[approval.payload["result_id"]]
    before = set(store.tool_runs)
    out = amount_edit(gw)
    edit, result = out["edit"], out["result"]
    runs = {t: store.tool_runs[rid] for t, rid in result.run_ids_by_tool.items()}
    assert set(runs) == {"consolidate", "ebitda", "covenant_debt", "leverage", "tie_out", "limit_test",
                         "naive_covenant_debt", "naive_ebitda", "naive_leverage"}
    assert not before & set(result.run_ids) and edit.run_ids == result.run_ids  # every run is new
    assert all(r.actor == SYSTEM for r in runs.values())
    for tool in EDIT_TOOLS:
        assert runs[tool].inputs["edit_ids"] == [edit.id]
    assert "edit_ids" not in runs["tie_out"].inputs  # the edited rows, not the edits again
    assert runs["consolidate"].outputs["edits_applied"] == [edit.id]
    assert runs["ebitda"].outputs["edits_applied"] == [edit.id]
    assert set(runs["covenant_debt"].outputs["edits_applied"]) <= {edit.id}
    assert result.ebitda == runs["ebitda"].outputs["ebitda"]
    assert result.debt == runs["covenant_debt"].outputs["debt"]
    assert result.leverage == runs["leverage"].outputs["leverage"]
    assert runs["leverage"].inputs == {"debt_run_id": runs["covenant_debt"].run_id,
                                       "ebitda_run_id": runs["ebitda"].run_id}
    assert runs["tie_out"].inputs["run_id"] == runs["consolidate"].run_id
    assert runs["limit_test"].inputs["leverage_run_id"] == runs["leverage"].run_id
    assert result.verdict == runs["limit_test"].outputs["verdict"]
    assert result.headroom_turns == runs["limit_test"].outputs["headroom_turns"]
    assert result.tie_out_ok == runs["tie_out"].outputs["ok"]
    expected = runs["consolidate"].outputs["rows"]
    assert len(result.rows) == len(expected)
    for row, e in zip(result.rows, expected):
        assert (row.line, row.section, row.platform, row.target, row.combined, row.run_id) == (
            e["line"], e["section"], e["platform"], e["target"], e["combined"], runs["consolidate"].run_id)
    assert result.supersedes == old.id and result.edit_ids == [edit.id]
    # (500) of G&A is 500 less cost: EBITDA rises by exactly 500, debt does not move.
    assert math.isclose(result.ebitda - old.ebitda, 500.0, abs_tol=1e-3)
    assert result.debt == old.debt
    assert math.isclose(result.leverage, result.debt / result.ebitda, abs_tol=5e-4)
    assert out["verdict"]["leverage"] == result.leverage
    # The whole-line what-if is run again on the edited books, and the flag's tags are restored afterwards.
    naive_debt, naive_eb = runs["naive_covenant_debt"], runs["naive_ebitda"]
    assert naive_debt.inputs["naive"] and naive_eb.inputs["as_filed"] and naive_debt.inputs["edit_ids"] == [edit.id]
    assert runs["naive_leverage"].inputs["debt_run_id"] == naive_debt.run_id
    flag = next(i for i in store.deal_items(DEAL_ID, "flag") if i.payload.get("kind") == "covenant_tag")
    whole = next(o for o in flag.options if o.basis == "as_filed")
    flag_lev = store.tool_runs[store.tool_runs[whole.run_id].inputs["leverage_run_id"]]
    assert naive_debt.outputs["debt"] == store.tool_runs[flag_lev.inputs["debt_run_id"]].outputs["debt"]
    assert math.isclose(naive_eb.outputs["ebitda"] - flag_lev.outputs["ebitda"], 500.0, abs_tol=1e-3)
    assert all(store.source_lines[lid].covenant_tag != "unclear" for lid in flag.payload["line_ids"])
    assert [store.source_lines[lid].covenant_tag for lid in flag.payload["line_ids"]] == [
        flag.payload["option_actions"][flag.answer]["tags"][lid] for lid in flag.payload["line_ids"]]


@needs_t1
def test_a_revert_restores_the_agents_value(world):
    store, gw = world
    approval = run_to_approval(gw)
    agents = store.results[approval.payload["result_id"]]
    edit = amount_edit(gw)["edit"]
    restored = gw.revert_edit(CONTROLLER, edit.id)["result"]
    assert (restored.ebitda, restored.debt, restored.leverage, restored.verdict) == (
        agents.ebitda, agents.debt, agents.leverage, agents.verdict)
    assert [r.model_dump(exclude={"run_id"}) for r in restored.rows] == [
        r.model_dump(exclude={"run_id"}) for r in agents.rows]


@needs_t1
def test_a_remap_revert_restores_every_figure_exactly(world):
    store, gw = world
    approval = run_to_approval(gw)
    agents = store.results[approval.payload["result_id"]]
    edit = remap_edit(gw)["edit"]
    restored = gw.revert_edit(CONTROLLER, edit.id)["result"]
    for field in ("ebitda", "debt", "leverage", "verdict", "headroom_turns", "tie_out_ok"):
        assert getattr(restored, field) == getattr(agents, field), field
    assert [r.model_dump(exclude={"run_id"}) for r in restored.rows] == [
        r.model_dump(exclude={"run_id"}) for r in agents.rows]


@needs_t1
def test_a_remap_moves_the_line_and_the_books_still_tie_out(world):
    store, gw = world
    run_to_approval(gw)
    result = remap_edit(gw)["result"]
    cash = next(r for r in result.rows if r.line == "Cash and cash equivalents")
    other = next(r for r in result.rows if r.line == REMAP_TO)
    agents = store.results[result.supersedes]
    cash0 = next(r for r in agents.rows if r.line == "Cash and cash equivalents")
    other0 = next(r for r in agents.rows if r.line == REMAP_TO)
    moved = finance.to_thousands(991082, "USD")
    assert math.isclose(cash0.target - cash.target, moved, abs_tol=1e-3)
    assert math.isclose(other.target - other0.target, moved, abs_tol=1e-3)
    assert result.tie_out_ok is True


@needs_t1
def test_the_demo_beat(world):
    """design/review-companion.md section 9, through the gateway: edit a target amount, the verdict moves, press
    the add-back chip, approve. The HTTP version is Tri's (T2)."""
    store, gw = world
    approval = run_to_approval(gw)
    before = store.results[approval.payload["result_id"]]
    out = amount_edit(gw)
    assert out["verdict"]["leverage"] != before.leverage and out["verdict"]["verdict"] == "ok"
    assert out["edit"].status == "needs_reason" and out["reasons"][0].label == AMOUNT_CHIPS[0]
    edit = gw.reason_edit(CONTROLLER, out["edit"].id, chip=0, remember=True)
    assert store.adjustments[edit.adjustment_id].reason == AMOUNT_CHIPS[0]
    gw.approve(CONTROLLER, out["approval"].id)
    assert store.deals[DEAL_ID].stage == "posted"
    actions = [r.action for r in store.audit if r.result == "ALLOWED"]
    for action in ("edit:apply", "edit:reason", "policy:learn", "approve"):
        assert action in actions
    assert gw.verify_chain()


def test_edit_model_round_trips_through_the_store(flow):
    """The store keeps edits with the deal record and adjustments with agent memory across a reset."""
    store, gw = flow
    run_to_approval(gw)
    edit = amount_edit(gw)["edit"]
    gw.reason_edit(CONTROLLER, edit.id, chip=0)
    assert Edit.model_validate_json(edit.model_dump_json()) == edit
    store.reset_deals(keep_memory=True)
    assert not store.edits and edit.adjustment_id in store.adjustments
    assert store.next_id("a") == "a_002"
    store.reset_deals(keep_memory=False)
    assert not store.adjustments


# ---- learned adjustments offered on a later deal ---------------------------------------------------------------

def learn_adjustment(gw):
    """On the demo deal: the add-back edit with its reason, remembered, then approved."""
    run_to_approval(gw)
    out = amount_edit(gw)
    gw.reason_edit(CONTROLLER, out["edit"].id, chip=0, remember=True)
    gw.approve(CONTROLLER, out["approval"].id)
    return gw.store.adjustments[out["edit"].adjustment_id]


def adjustment_flag(gw, deal_id):
    flags = gw.open_adjustment_flags(deal_id)
    assert len(flags) == 1
    return flags[0]


def test_a_learned_adjustment_is_offered_as_a_flag_on_the_next_deal_and_never_applied(flow):
    store, gw = flow
    adj = learn_adjustment(gw)
    assert adj.platform == PLATFORM and adj.status == "applied"
    assert adj not in gw.adjustments_for(DEAL_ID)  # not on the deal it was learned on
    second = next_deal(store, gw)
    approval = run_to_approval(gw, second.id)  # the offer does not block the Preparer or the Reviewer
    flag = adjustment_flag(gw, second.id)
    assert flag.proposed_by == PREPARER and flag.payload["adjustment_id"] == adj.id
    assert [o.id for o in flag.options] == ["apply", "skip"] and flag.default == "skip"
    line = store.source_lines[flag.payload["line_ids"][0]]
    assert (line.company, line.line) == ("Acme Labs", AMOUNT_LINE) and line.amount == 6162806
    assert f"(500) to Acme Labs's {AMOUNT_LINE}" in flag.question and adj.id not in flag.question
    assert "from 6,163K to 5,663K" in flag.question
    assert next(o for o in flag.options if o.id == "apply").label == f"Apply it: (500) to Acme Labs, {AMOUNT_LINE}"
    assert adj.status == "proposed" and not store.deal_edits(second.id)  # never applied silently
    assert [r.target for r in rows(store, "adjustment:propose")] == [adj.id]
    assert any(r.actor == PREPARER and r.target == flag.id for r in rows(store, "ask:flag"))
    with pytest.raises(Denied, match=flag.id):
        gw.approve(CONTROLLER, approval.id)
    assert flag.id in rows(store, "approve", "DENIED")[-1].reason


def test_skipping_the_offer_leaves_the_books_as_the_agents_made_them(flow):
    store, gw = flow
    adj = learn_adjustment(gw)
    second = next_deal(store, gw)
    approval = run_to_approval(gw, second.id)
    flag = adjustment_flag(gw, second.id)
    gw.answer(CONTROLLER, flag.id, "skip")
    assert store.items[flag.id].state == State.POSTED and store.items[flag.id].answer == "skip"
    assert not store.deal_edits(second.id) and approval.state == State.PROPOSED
    assert adj.status == "applied" and adj not in gw.adjustments_for(second.id)  # kept, not asked twice here
    assert rows(store, "adjustment:skip")[-1].target == adj.id
    gw.approve(CONTROLLER, approval.id)
    assert store.deals[second.id].stage == "posted"


def test_applying_the_offer_makes_a_reasoned_edit_through_the_recompute(flow):
    store, gw = flow
    adj = learn_adjustment(gw)
    second = next_deal(store, gw)
    acme = next(sl for sl in store.lines(second.id, "Acme Labs") if sl.line == AMOUNT_LINE)
    acme.amount = 7000000.0  # another company's own figure: the change carries, the old value does not
    old = run_to_approval(gw, second.id)
    flag = adjustment_flag(gw, second.id)
    assert "from 7,000K to 6,500K" in flag.question
    gw.answer(CONTROLLER, flag.id, "apply")
    edit = store.edits[store.items[flag.id].payload["edit_id"]]
    assert (edit.deal_id, edit.company, edit.line) == (second.id, "Acme Labs", AMOUNT_LINE)
    assert (edit.old_value, edit.new_value) == (7000.0, 6500.0)  # this deal's agent value plus the change
    assert edit.status == "reasoned" and edit.reason_text == adj.reason and edit.from_adjustment_id == adj.id
    assert edit.adjustment_id is None and len(store.adjustments) == 1  # it does not teach itself again
    assert old.state == State.SUPERSEDED and adj.status == "applied"
    assert rows(store, "adjustment:apply")[-1].target == adj.id
    assert [r.action for r in store.audit if r.target == edit.id] == ["edit:apply", "edit:reason"]
    new = store.deal_items(second.id, "approve_result")[-1]
    gw.approve(CONTROLLER, new.id)
    assert store.deals[second.id].stage == "posted" and gw.verify_chain()


@pytest.mark.skipif(T1_READY, reason="T1 is installed; this checks the refusal before it")
def test_without_t1_applying_the_offer_is_refused_and_the_flag_stays_open(world):
    store, gw = world
    run_to_approval(gw)
    # Learn one by hand: before T1 no edit can be applied, so write the memory the way reason_edit would.
    from app.core.models import LearnedAdjustment
    store.adjustments["a_001"] = LearnedAdjustment(id="a_001", deal_id="d_earlier", company=TARGET, platform=PLATFORM,
                                                   line=AMOUNT_LINE, amount=-500.0, reason=AMOUNT_CHIPS[0],
                                                   edit_id="e_earlier")
    second = next_deal(store, gw)
    run_to_approval(gw, second.id)
    flag = adjustment_flag(gw, second.id)
    with pytest.raises(NotReady):
        gw.answer(CONTROLLER, flag.id, "apply")
    assert store.items[flag.id].state == State.NEEDS_INFO and store.adjustments["a_001"].status == "proposed"
    assert not store.deal_edits(second.id)


def test_adjustments_stay_on_their_platform_and_retired_ones_are_not_offered(flow):
    store, gw = flow
    adj = learn_adjustment(gw)
    other = next_deal(store, gw, deal_id="d_other_platform", target="Acme Labs", platform="Other Platform")
    assert adj not in gw.adjustments_for(other.id)
    same_company = next_deal(store, gw, deal_id="d_nuaire_again", target=TARGET, platform="Other Platform")
    assert adj in gw.adjustments_for(same_company.id)  # the same company's line, under any platform
    adj.status = "retired"
    assert adj not in gw.adjustments_for(same_company.id) and adj not in gw.adjustments_for(next_deal(store, gw).id)


def test_after_a_demo_reset_the_reseeded_deal_is_offered_the_adjustment(flow):
    store, gw = flow
    adj = learn_adjustment(gw)
    with gw.lock:
        store.reset_deals(keep_memory=True)
        seed(store, gw)
    run_to_approval(gw)
    assert adjustment_flag(gw, DEAL_ID).payload["adjustment_id"] == adj.id


def test_the_gateway_refuses_an_offer_it_would_not_make(flow):
    from app.agents.backends.scripted import scripted_preparer
    from app.core.models import AdjustmentProposal, PreparerInput
    store, gw = flow
    adj = learn_adjustment(gw)
    second = next_deal(store, gw)
    advance(gw, second.id)
    for f in gw.open_flags(second.id):
        gw.answer(CONTROLLER, f.id, f.default)
    item = gw.create_item(second.id, "prepare_result")
    deal = store.deals[second.id]
    inp = PreparerInput(deal_id=deal.id, item_id=item.id, platform_lines=store.lines(deal.id, deal.platform),
                        target_lines=store.lines(deal.id, deal.target), mappings=store.deal_mappings(deal.id),
                        brief=deal.brief, adjustments=gw.adjustments_for(deal.id))
    out = scripted_preparer(inp, lambda n, i: gw.run_tool(PREPARER, deal.id, n, i))
    good = out.adjustment_flags[0]
    wrong_line = next(sl for sl in store.lines(deal.id, "Acme Labs") if sl.line == "Selling Expense")
    for bad in ([AdjustmentProposal(adjustment_id="a_999", line_id=good.line_id, question="q")],
                [good.model_copy(update={"line_id": wrong_line.id})],
                [good, good]):
        with pytest.raises(Invalid):
            gw.store_result(PREPARER, item.id, out.model_copy(update={"adjustment_flags": bad}))
    assert not gw.open_adjustment_flags(second.id) and adj.status == "applied"
    gw.store_result(PREPARER, item.id, out)
    assert gw.open_adjustment_flags(second.id)


@needs_t1
def test_an_applied_offer_moves_the_figures_through_its_tool_runs(world):
    store, gw = world
    adj = learn_adjustment(gw)
    second = next_deal(store, gw)
    old = store.results[run_to_approval(gw, second.id).payload["result_id"]]
    gw.answer(CONTROLLER, adjustment_flag(gw, second.id).id, "apply")
    result = store.latest_result(second.id)
    edit = store.edits[result.edit_ids[0]]
    assert edit.from_adjustment_id == adj.id
    assert result.ebitda == store.tool_runs[result.run_ids_by_tool["ebitda"]].outputs["ebitda"] != old.ebitda
    assert result.leverage == store.tool_runs[result.run_ids_by_tool["leverage"]].outputs["leverage"]


# ---- the T1 output contract, newest-wins policies, and names ---------------------------------------------------

def _edit_aware(tool, applied):
    """A stand-in edit-aware tool that ignores the edits and reports `applied(edits)` as edits_applied."""
    def fn(*args, edits=None, **kwargs):
        out = tool(*args, **kwargs)
        out["edits_applied"] = applied(edits or [])
        return out
    return fn


@pytest.mark.parametrize("tool, applied, words", [
    ("consolidate", lambda edits: [], "did not apply"),
    ("ebitda", lambda edits: ["e_999"], "not given"),
    ("covenant_debt", lambda edits: None, "did not return edits_applied"),
])
def test_a_recompute_is_refused_when_a_tool_misreports_its_edits(world, monkeypatch, tool, applied, words):
    store, gw = world
    approval = run_to_approval(gw)
    for name in EDIT_TOOLS:
        right = (lambda edits: [e.id for e in edits])
        monkeypatch.setitem(finance.TOOLS, name, _edit_aware(finance.TOOLS[name], applied if name == tool else right))
    with pytest.raises(Invalid, match=words):
        amount_edit(gw)
    assert not store.edits and approval.state == State.PROPOSED
    denied = rows(store, "edit:apply", "DENIED")[-1]
    assert "edit not applied" in denied.reason and words in denied.reason


def test_the_newest_platform_policy_wins_and_a_revert_brings_the_older_back(flow):
    store, gw = flow
    run_to_approval(gw)
    first = remap_edit(gw)["edit"]
    gw.reason_edit(CONTROLLER, first.id, chip=0)
    gw.approve(CONTROLLER, store.deal_items(DEAL_ID, "approve_result")[-1].id)
    older = store.policies[first.policy_id]
    second = next_deal(store, gw)
    run_to_approval(gw, second.id)
    assert mapping_of(store, second.id, REMAP_LINE).policy_id == older.id
    later = gw.apply_edit(CONTROLLER, second.id, "remap", "Acme Labs", REMAP_LINE, platform_line="Other assets")["edit"]
    gw.reason_edit(CONTROLLER, later.id, chip=1)
    newer = store.policies[later.policy_id]
    assert newer.id != older.id and older.retired_by is None and older.decision == REMAP_TO  # not updated in place
    assert not rows(store, "policy:update")
    third = next_deal(store, gw, deal_id="d_third", target="Beta Labs")
    line = next(sl for sl in store.lines(third.id, "Beta Labs") if sl.line == REMAP_LINE)
    assert gw._cited_policy(older.id, "mapping", REMAP_TO, line) is None  # a replaced answer cannot be cited
    assert gw._cited_policy(newer.id, "mapping", "Other assets", line) == newer.id
    gw.revert_edit(CONTROLLER, later.id)
    assert newer.retired_by == later.id and older.retired_by is None
    assert gw._cited_policy(older.id, "mapping", REMAP_TO, line) == older.id
    advance(gw, third.id)
    m = mapping_of(store, third.id, REMAP_LINE)
    assert (m.platform_line, m.policy_id) == (REMAP_TO, older.id)


def test_platform_and_company_names_match_casefolded(flow):
    from app.core.policies import policy_applies
    store, gw = flow
    p = Policy(id="p_x", role=MAPPER, kind="mapping", pattern="x", decision="y", reason="r", approved_by=CONTROLLER,
               learned_from="e_x", deal_id=DEAL_ID, scope="platform", platform=" kewaunee ")
    assert policy_applies(p, "ACME LABS", "Kewaunee", "Acme Labs")
    assert not policy_applies(p, "Kewaunee", "Kewaunee", "Acme Labs")  # the platform's own lines
    c = Policy(id="p_y", role=MAPPER, kind="mapping", pattern="x", decision="y", reason="r", approved_by=CONTROLLER,
               learned_from="wi_x", deal_id=DEAL_ID, company="nu aire")
    assert policy_applies(c, "Nu Aire ", "Kewaunee", "Nu Aire") and not policy_applies(c, "Nu", "Kewaunee", "Nu Aire")
    adj = learn_adjustment(gw)
    shouty = next_deal(store, gw, deal_id="d_shouty", target="Acme Labs", platform="KEWAUNEE")
    assert adj in gw.adjustments_for(shouty.id)
