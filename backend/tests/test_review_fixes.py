"""One test per finding of the final backend review (2026-10-25)."""
import os

import pytest

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

from app.agents import jobs  # noqa: E402
from app.core import agreement as agr  # noqa: E402
from app.core.models import BRIEF_READER, CONTROLLER, SYSTEM, VERIFIER, BriefFieldFlag, Evidence, State  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import EDIT_TOOLS, Denied, Gateway, Invalid  # noqa: E402
from app.tools import finance  # noqa: E402
from tests.test_brief_reader_gateway import EXCERPT, answer_kewaunee, new_deal, reader_output  # noqa: E402
from tests.test_edits import _recompute_without_edits, amount_edit, run_to_approval  # noqa: E402


@pytest.fixture
def world():
    store = MemoryStore()
    return store, Gateway(store)


@pytest.fixture
def demo(world):
    store, gw = world
    seed(store, gw)
    return store, gw


def denied(store, action):
    return [r for r in store.audit if r.action == action and r.result == "DENIED"]


# ---- 1. a reader flag never lets an unquoted value through ---------------------------------------------------

def test_a_flag_cannot_carry_a_limit_that_has_no_quote(world):
    """The repro: limit 9.0, its citation dropped, a flag "Please confirm the limit"; the controller keeps it."""
    store, gw = world
    new_deal(store, gw)
    item, out = reader_output(gw)
    bad = out.model_copy(update={
        "brief": out.brief.model_copy(update={"limit": 9.0}),
        "citations": [c for c in out.citations if c.field != "limit"],
        "flags": [*out.flags, BriefFieldFlag(field="limit", question="Please confirm the limit")]})
    with pytest.raises(Invalid, match="limit has no verified quote, so it must stay empty"):
        gw.store_brief(BRIEF_READER, item.id, bad)
    # Whenever limit_wording is set, the limit must be the number in it: a "missing" limit of 0 beside a wording
    # that says 2.50 is refused too.
    zero = bad.model_copy(update={"brief": bad.brief.model_copy(update={"limit": 0.0}),
                                  "flags": [*out.flags, BriefFieldFlag(field="limit",
                                                                       question="The limit was not found in sections 4.8")]})
    with pytest.raises(Invalid, match="limit 0.0 is not in limit_wording"):
        gw.store_brief(BRIEF_READER, item.id, zero)
    assert store.deals[DEAL_ID].brief is None


def test_a_flagged_cap_holds_a_value_only_if_its_evidence_shows_it(world):
    store, gw = world
    new_deal(store, gw)
    item, out = reader_output(gw)
    no_quote = [c for c in out.citations if c.field != "ebitda_addbacks[2].cap"]
    shown = "Closing Date Acquisition, but not exceeding $4,000,000 in the aggregate"
    for evidence, ok in (([], False), ([Evidence(quote="not exceeding $4,000,000 per the model")], False),
                         ([Evidence(quote=shown)], True)):
        flag = BriefFieldFlag(field="ebitda_addbacks[2].cap", question="Is the cap right?", evidence=evidence)
        draft = out.model_copy(update={"citations": no_quote, "flags": [*out.flags, flag]})
        if ok:
            gw.store_brief(BRIEF_READER, item.id, draft)
        else:
            with pytest.raises(Invalid, match="must stay empty"):
                gw.store_brief(BRIEF_READER, item.id, draft)
    assert store.deals[DEAL_ID].brief.ebitda_addbacks[2].cap == 4000.0


def test_a_flagged_text_field_with_no_quote_must_be_empty(world):
    store, gw = world
    new_deal(store, gw)
    item, out = reader_output(gw)
    draft = out.model_copy(update={"citations": [c for c in out.citations if c.field != "lender"],
                                   "flags": [*out.flags, BriefFieldFlag(field="lender", question="Lender?")]})
    with pytest.raises(Invalid, match="lender has no verified quote, so it must stay empty"):
        gw.store_brief(BRIEF_READER, item.id, draft)


# ---- 2. a crash in a recompute or a tool is refused and rolled back ------------------------------------------

def _broken(tool):
    def fn(*args, edits=None, **kwargs):
        raise KeyError("rows")
    return fn


def test_a_tool_crash_during_apply_edit_is_a_422_and_nothing_is_kept(demo, monkeypatch):
    store, gw = demo
    approval = run_to_approval(gw)
    for name in EDIT_TOOLS:
        monkeypatch.setitem(finance.TOOLS, name, _broken(finance.TOOLS[name]))
    with pytest.raises(Invalid) as error:
        amount_edit(gw)
    assert error.value.status == 422 and "KeyError" in error.value.message
    assert not store.edits and approval.state == State.PROPOSED
    assert "edit not applied" in denied(store, "edit:apply")[-1].reason
    assert any(r.action == "tool:consolidate" and "KeyError" in (r.reason or "") for r in store.audit)


def test_a_crash_during_revert_keeps_the_edit_live(demo, monkeypatch):
    store, gw = demo
    monkeypatch.setattr(Gateway, "_recompute", _recompute_without_edits)
    run_to_approval(gw)
    edit = amount_edit(gw)["edit"]

    def crash(self, deal_id, edit_ids):
        raise RuntimeError("tool process died")
    monkeypatch.setattr(Gateway, "_recompute", crash)
    with pytest.raises(Invalid, match="edit not reverted: the recompute failed .RuntimeError"):
        gw.revert_edit(CONTROLLER, edit.id)
    assert store.edits[edit.id].status == "needs_reason" and denied(store, "edit:revert")


def test_run_tool_turns_any_tool_exception_into_an_audited_refusal(demo, monkeypatch):
    store, gw = demo
    monkeypatch.setitem(finance.TOOLS, "leverage", lambda debt, ebitda_value: {}["missing"])
    with pytest.raises(Invalid, match="leverage failed: KeyError"):
        gw.run_tool(SYSTEM, DEAL_ID, "leverage", {"debt": 1.0, "ebitda": 2.0})
    assert "KeyError" in store.audit[-1].reason


# ---- 3 is in test_edits.py: test_the_gateway_refuses_an_offer_it_would_not_make ------------------------------

# ---- 8. headings with "Section" and without a trailing dot -----------------------------------------------------

def test_section_headings_in_other_styles():
    text = ("Preamble.\nSection 7.1 Leverage Ratio\nkeep it low.\nSECTION 7.2.\ncoverage.\n7.3 Fixed Charges\n"
            "fixed.\nas set forth in\nSection 5.8 .\nsection 7.4 of this Agreement says so.\n1.\nnot a heading.\n")
    assert agr.section_index(text) == {"preamble": "Preamble", "7.1": "Leverage Ratio", "7.2": "Section 7.2",
                                       "7.3": "Fixed Charges"}
    assert "keep it low" in agr.section_text(text, "7.1")
    assert agr.section_index(EXCERPT).keys() >= {"preamble", "4.8", "4.8(a)", "4.8(b)", "Addendum I"}


# ---- 9. the Brief is the controller's, and the reader is its maker --------------------------------------------

def test_only_the_controller_amends_or_approves_and_the_reader_is_the_maker(world):
    store, gw = world
    new_deal(store, gw)
    jobs.advance(gw, DEAL_ID)
    assert store.deal_items(DEAL_ID, "draft_brief")[-1].proposed_by == BRIEF_READER
    answer_kewaunee(gw)
    for call in (lambda: gw.approve_brief("human:intern", DEAL_ID),
                 lambda: gw.amend_brief("human:intern", DEAL_ID, "lender", "Someone")):
        with pytest.raises(Denied, match="only human:controller"):
            call()
    gw.approve_brief(CONTROLLER, DEAL_ID)
    assert store.deals[DEAL_ID].brief_status == "approved"


# ---- 11 and 12. counters and approved Briefs survive a reset with memory ----------------------------------------

def test_edit_and_work_item_counters_and_approved_briefs_survive_a_reset(world):
    store, gw = world
    new_deal(store, gw)
    jobs.advance(gw, DEAL_ID)
    answer_kewaunee(gw)
    gw.approve_brief(CONTROLLER, DEAL_ID)
    store.next_id("e")
    seq = dict(store._seq)
    store.reset_deals(keep_memory=True)
    assert store.next_id("wi") == f"wi_{seq['wi'] + 1:03d}" and store.next_id("e") == f"e_{seq['e'] + 1:03d}"
    again = new_deal(store, gw)  # the same agreement after the reset: the approved Brief is reused
    assert again.brief_status == "approved" and any(r.action == "brief:reuse" for r in store.audit)
    store.reset_deals(keep_memory=False)
    assert not store.approved_briefs and store.next_id("wi") == "wi_001"


# ---- 13. a reader flag's evidence is verified -------------------------------------------------------------------

def test_reader_flag_evidence_not_in_the_agreement_is_kept_apart(world):
    store, gw = world
    new_deal(store, gw)
    item, out = reader_output(gw)
    real = Evidence(quote="a Fixed Charge Coverage Ratio of at least 1.20 to 1", document_id="4.8(b)")
    made_up = Evidence(quote="the lender waived every covenant last year", document_id="4.8(b)")
    flag = BriefFieldFlag(field="lender", question="Is the lender PNC?", evidence=[real, made_up])
    gw.store_brief(BRIEF_READER, item.id, out.model_copy(update={"flags": [flag]}))
    gw.verify_brief(VERIFIER, DEAL_ID)  # the questions open once the verifier has checked the draft (D23)
    opened = next(f for f in gw._brief_flags(DEAL_ID) if f.payload["field"] == "lender")
    assert [e.quote for e in opened.evidence] == [real.quote]
    assert [e["quote"] for e in opened.payload["unverified_evidence"]] == [made_up.quote]


# ---- 5. the chips for /case ---------------------------------------------------------------------------------------

def test_reason_chips_for_case(world):
    _, gw = world
    chips = gw.reason_chips(DEAL_ID)
    assert set(chips) == {"amount", "remap"} and len(chips["amount"]) == len(chips["remap"]) == 3
