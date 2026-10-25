"""The Brief verifier (D23): code checks every Brief field against the agreement, fills the amounts the books give,
and on the demo deal approves a Brief whose every check passed. docs/architecture/brief-reader.md section 6a.

The agreement is the committed verbatim extract of Ex 10.1 (data/brief/kewaunee_ex101_extract.txt), the text the live
demo deal starts from.
"""
import os

import pytest

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

from app.agents import jobs  # noqa: E402
from app.agents.backends.scripted import kewaunee_quotes, scripted_brief_reader  # noqa: E402
from app.core import agreement as agr  # noqa: E402
from app.core import verifier as ver  # noqa: E402
from app.core.models import (  # noqa: E402
    BRIEF_READER, CONTROLLER, MAPPER, SYSTEM, VERIFIER, Adjustment, BriefFieldFlag, State,
)
from app.db.fixtures.kewaunee import (  # noqa: E402
    AGREEMENT_SOURCE, BOOK_AMOUNTS, BRIEF, DEAL_ID, agreement_text, seed, seed_demo,
)
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Denied, Gateway, IllegalTransition  # noqa: E402

TEXT = agreement_text()


@pytest.fixture
def world():
    store = MemoryStore()
    gw = Gateway(store)
    seed_demo(store, gw)
    return store, gw


def draft(gw, update=None):
    """Store the scripted reader's draft (optionally changed), without verifying it."""
    item = gw.create_item(DEAL_ID, "draft_brief")
    inp = gw.brief_reader_input(DEAL_ID, item.id)
    out = scripted_brief_reader(inp, lambda name, args: gw.read_agreement(BRIEF_READER, DEAL_ID, name, args))
    if update:
        out = update(out)
    gw.store_brief(BRIEF_READER, item.id, out)
    return gw.store.items[item.id]


def reader_brief():
    from app.agents.backends.scripted import _kewaunee_brief
    return _kewaunee_brief(kewaunee_quotes())


def cite(out, field, quote, section="Addendum I"):
    return [c.model_copy(update={"quote": quote, "section": section}) if c.field == field else c for c in out.citations]


# ---- the pure checks ------------------------------------------------------------------------------------------

def test_the_committed_extract_is_the_agreement_the_scripted_reader_knows():
    assert agr.agreement_sha256(TEXT) in kewaunee_quotes()["sha256"].values()
    assert set(agr.section_index(TEXT)) == {"preamble", "4.8", "4.8(a)", "4.8(b)", "Addendum I"}
    assert set(agr.definition_index(TEXT)) == {"EBITDA", "Senior Funded Bank Debt", "Subordinated Debt"}


def test_every_field_of_the_reader_draft_passes_on_the_extract():
    out = reader_brief()
    checks = ver.verify(out.brief, out.citations, TEXT, out.brief.agreement_ref)
    assert all(c.ok for c in checks), [(c.field, c.reason) for c in checks if not c.ok]
    fields = [c.field for c in checks]
    assert fields[:2] == ["lender", "limit"] and "test_period_note" in fields
    assert sum(f.endswith(".amount") for f in fields) == 5
    limit = next(c for c in checks if c.field == "limit")
    assert limit.section == "4.8(a)" and limit.checks == ["verbatim", "in_section", "number"]
    assert "2.50 in the quote" in limit.reason and "2.50 to 1.00" in limit.quote
    cap = next(c for c in checks if c.field == "ebitda_addbacks[2].cap")
    assert cap.checks == ["verbatim", "in_section", "number"] and "$4,000,000" in cap.reason
    assert next(c for c in checks if c.field == "debt_term").checks == ["verbatim", "in_section", "defined"]


@pytest.mark.parametrize("field, value, quote, section, reason", [
    ("lender", None, "PNC BANK, NATIONAL ASSOCIATION (the Lender), with an address", "preamble", "word for word"),
    ("lender", None, "ratio of Senior Funded Bank Debt to EBITDA of less than 2.50", "preamble", "not in section"),
    ("lender", None, "PNC BANK, NATIONAL ASSOCIATION (the \" Bank \"), with an address at", "9.9", "is not in the "
                                                                                                     "agreement"),
    ("limit", 3.0, None, None, "limit 3.00 is not in its quote"),
    ("ebitda_addbacks[2].cap", 5000.0, None, None, "cap 5,000K is not in its quote"),
    ("debt_excludes[0]", None, "noncash pension termination expense completed during the fiscal year", None,
     "not from the definition of 'Senior Funded Bank Debt'"),
    ("ebitda_addbacks[0].name", None, "but excluding (i) Subordinated Debt and (ii) any capitalized lease", None,
     "not from the definition of EBITDA"),
])
def test_a_field_that_does_not_match_the_agreement_fails_with_its_reason(field, value, quote, section, reason):
    out = reader_brief()
    brief = out.brief
    if field == "limit":
        brief = brief.model_copy(update={"limit": value})
    if field.endswith(".cap"):
        adds = [a.model_copy(update={"cap": value}) if i == 2 else a for i, a in enumerate(brief.ebitda_addbacks)]
        brief = brief.model_copy(update={"ebitda_addbacks": adds})
    cites = out.citations
    if quote:
        cites = cite(out, field, quote, section or "Addendum I")
    checks = {c.field: c for c in ver.verify(brief, cites, TEXT, brief.agreement_ref)}
    assert not checks[field].ok and reason in checks[field].reason, checks[field].reason


def test_an_undefined_debt_term_fails():
    out = reader_brief()
    brief = out.brief.model_copy(update={"debt_term": "Total Funded Debt"})
    check = next(c for c in ver.verify(brief, out.citations, TEXT, "x") if c.field == "debt_term")
    assert not check.ok and "'Total Funded Debt' is not a defined term" in check.reason


def test_an_amount_needs_a_source_outside_the_agreement_and_0_means_not_applied():
    ref = "8-K Ex 10.1, PNC Loan Agreement dated 2024-11-01"
    assert ver.check_amount("a", Adjustment(name="x", amount=0, source_ref=ref), ref).ok
    bad = ver.check_amount("a", Adjustment(name="x", amount=12, source_ref=ref), ref)
    assert not bad.ok and "no source outside the agreement" in bad.reason
    assert not ver.check_amount("a", Adjustment(name="x", amount=12, source_ref=""), ref).ok
    good = ver.check_amount("a", BOOK_AMOUNTS[0], ref)
    assert good.ok and good.value == "4,019" and good.quote.startswith("10-K FY2024")


def test_book_amounts_match_by_name_only():
    pension = Adjustment(name="noncash pension termination expense", amount=0, source_ref="x")
    assert ver.book_amount(pension, BOOK_AMOUNTS).amount == 4019
    capped = Adjustment(name="Transaction costs", amount=0, source_ref="x", cap=4000)
    assert ver.book_amount(capped, BOOK_AMOUNTS).name == "Transaction costs (capped)"
    assert ver.book_amount(Adjustment(name="Cash rental expense", amount=0, source_ref="x"), BOOK_AMOUNTS) is None


# ---- the demo deal: read, verify, auto-approve -----------------------------------------------------------------

def test_the_demo_deal_starts_from_the_agreement_and_the_verifier_approves_its_brief(world):
    store, gw = world
    deal = store.deals[DEAL_ID]
    assert deal.brief is None and deal.brief_status == "none" and deal.brief_auto_approve
    assert gw.agreement(DEAL_ID).source == AGREEMENT_SOURCE
    log = jobs.advance(gw, DEAL_ID, backend="scripted")
    assert log[:3] == ["brief reader ran on scripted", "verifier: 22 of 22 checks passed, Brief auto-approved",
                       "mapper ran on scripted"]
    deal = store.deals[DEAL_ID]
    assert deal.brief_status == "approved" and not gw._brief_flags(DEAL_ID, open_only=False)  # no Brief question
    report = gw.brief_verification(DEAL_ID)
    assert (report.passed, report.failed, report.auto_approved, report.escalated) == (22, 0, True, [])
    assert report.filled == [f"ebitda_addbacks[{i}].amount" for i in range(4)] + ["ebitda_deductions[0].amount"]
    assert len(report.scope_notes) == 1 and "Fixed Charge Coverage Ratio" in report.scope_notes[0]
    # The amounts are the books' amounts, each with its source; the math gets the same Brief as the fixture.
    for got, want in zip(deal.brief.ebitda_addbacks + deal.brief.ebitda_deductions, BOOK_AMOUNTS):
        assert (got.amount, got.source_ref, got.inferred) == (want.amount, want.source_ref, want.inferred)
    assert deal.brief.limit == BRIEF.limit and deal.brief.debt_excludes == BRIEF.debt_excludes


def test_every_check_is_a_message_and_an_audit_row_and_the_approval_says_why(world):
    store, gw = world
    jobs.advance(gw, DEAL_ID, backend="scripted")
    report = gw.brief_verification(DEAL_ID)
    rows = [r for r in store.audit if r.actor == VERIFIER]
    checks = [r for r in rows if r.action == "verify:brief_field"]
    assert [r.target for r in checks] == [c.field for c in report.checks] and all(r.result == "ALLOWED" for r in checks)
    amends = [r for r in rows if r.action == "brief:amend"]
    assert len(amends) == 5 and "4,019.000 from the books; source: 10-K FY2024" in amends[0].reason
    approve = next(r for r in store.audit if r.action == "approve_brief")
    assert approve.actor == VERIFIER and approve.result == "ALLOWED"
    assert approve.reason.startswith("auto-approved: all 22 checks passed; Brief locked: limit 2.50x")
    assert any(r.action == "verify:scope_note" for r in rows)
    msgs = gw.conversation(DEAL_ID)
    said = [m for m in msgs if m.sender == VERIFIER and m.kind == "check"]
    assert len(said) == 23 and said[-1].text == ("Brief verified: 22 of 22 checks passed; noted, not tested: 1 item "
                                                  "the Brief cannot hold")
    assert said[1].text.startswith("Verified limit = 2.50 in section 4.8(a)")
    # Nobody is asked anything before the Mapper: the first question is the Mapper's.
    first_q = next(m for m in msgs if m.kind == "question")
    assert first_q.sender == MAPPER
    assert gw.verify_chain()


def test_a_failed_check_escalates_and_blocks_the_auto_approval(world):
    store, gw = world

    def bad(out):  # a verbatim quote from the agreement, so the draft checks pass, but from the wrong definition
        return out.model_copy(update={"citations": cite(
            out, "debt_excludes[0]", "noncash pension termination expense completed during the fiscal year")})
    item = draft(gw, bad)
    assert store.deals[DEAL_ID].stage == "verifying_brief" and not gw._brief_flags(DEAL_ID)
    report = gw.verify_brief(VERIFIER, DEAL_ID)
    assert report.failed == 1 and not report.auto_approved and store.deals[DEAL_ID].brief_status == "draft"
    flags = gw._brief_flags(DEAL_ID)
    # The scope note stays a question too, since the Brief is not auto-approved: the controller sees every point.
    assert [f.payload["field"] for f in flags] == ["covenants", "debt_excludes[0]"]
    assert report.escalated == [f.id for f in flags] and report.scope_notes == []
    assert flags[1].proposed_by == VERIFIER and "The verifier could not confirm debt_excludes[0]" in flags[1].question
    assert next(r for r in store.audit if r.action == "verify:brief_field" and r.target == "debt_excludes[0]").result \
        == "DENIED"
    assert store.deals[DEAL_ID].stage == "awaiting_brief"
    with pytest.raises(Denied):
        gw._auto_approve_brief(VERIFIER, store.deals[DEAL_ID], item, report)
    for f in gw._brief_flags(DEAL_ID):  # the controller settles it and approves
        gw.answer(CONTROLLER, f.id, "confirm")
    gw.approve_brief(CONTROLLER, DEAL_ID)
    assert store.deals[DEAL_ID].brief_status == "approved"


def test_an_amount_the_books_do_not_give_is_asked(world):
    store, gw = world
    store.deals[DEAL_ID].book_amounts = [a for a in BOOK_AMOUNTS if a.name != "Stock-based compensation"]
    draft(gw)
    report = gw.verify_brief(VERIFIER, DEAL_ID)
    assert report.failed == 0 and not report.auto_approved
    assert [f.payload["field"] for f in gw._brief_flags(DEAL_ID)] == ["ebitda_addbacks[1].amount"]


def test_a_deal_without_auto_approval_waits_for_the_controller(world):
    store, gw = world
    store.deals[DEAL_ID].brief_auto_approve = False
    draft(gw)
    report = gw.verify_brief(VERIFIER, DEAL_ID)
    assert report.failed == 0 and not report.auto_approved and report.scope_notes == []
    flags = gw._brief_flags(DEAL_ID)
    assert [f.payload["field"] for f in flags] == ["covenants"]  # the second covenant is asked, not noted
    gw.answer(CONTROLLER, flags[0].id, "confirm")
    with pytest.raises(Denied):
        gw.approve_brief(VERIFIER, DEAL_ID)  # only the controller approves here
    gw.approve_brief(CONTROLLER, DEAL_ID)
    assert store.deals[DEAL_ID].brief_status == "approved"


def test_only_the_verifier_verifies_and_only_once(world):
    store, gw = world
    draft(gw)
    for actor in (BRIEF_READER, MAPPER, CONTROLLER, SYSTEM):
        with pytest.raises(Denied):
            gw.verify_brief(actor, DEAL_ID)
    gw.verify_brief(VERIFIER, DEAL_ID)
    with pytest.raises(IllegalTransition):
        gw.verify_brief(VERIFIER, DEAL_ID)


def test_a_draft_left_unverified_by_a_restart_is_verified_on_the_next_run(world):
    store, gw = world
    draft(gw)
    assert gw.needs_verification(DEAL_ID)
    log = jobs.advance(gw, DEAL_ID, backend="scripted")
    assert log[0] == "verifier: 22 of 22 checks passed, Brief auto-approved"


def test_the_fixture_seed_still_carries_the_approved_brief():
    store = MemoryStore()
    gw = Gateway(store)
    seed(store, gw)
    deal = store.deals[DEAL_ID]
    assert deal.brief_status == "approved" and not deal.brief_auto_approve and gw.agreement(DEAL_ID) is None


def test_a_reader_flag_on_a_field_still_reaches_the_controller(world):
    store, gw = world

    def unsure(out):
        return out.model_copy(update={"flags": [*out.flags, BriefFieldFlag(field="lender", question="Is it PNC?")]})
    draft(gw, unsure)
    report = gw.verify_brief(VERIFIER, DEAL_ID)
    assert not report.auto_approved and [f.payload["field"] for f in gw._brief_flags(DEAL_ID)] == ["lender"]
    assert store.items[report.escalated[0]].state == State.NEEDS_INFO
