"""The phase 2 contract (D19 edits, D20 Brief Reader): the new models build and serialize, and the defaults leave
the fixture deal and the flag-answer policies as they were. No API call."""
import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.models import (  # noqa: E402
    BRIEF_READER,
    CONTROLLER,
    AgreementText,
    BriefCitation,
    BriefDraft,
    BriefFieldFlag,
    BriefReaderInput,
    BriefReaderOutput,
    Deal,
    Edit,
    LearnedAdjustment,
    Policy,
    ReasonChip,
)
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402


def _fixture_deal() -> Deal:
    store = MemoryStore()
    seed(store, Gateway(store))
    return store.deals[DEAL_ID]


def test_the_fixture_deal_is_unchanged():
    deal = _fixture_deal()
    assert deal.brief_status == "approved"
    assert deal.brief is not None and deal.brief.limit == 2.5
    assert Deal.model_validate_json(deal.model_dump_json()) == deal


def test_policy_scope_defaults_to_company():
    p = Policy(id="p_1", role="agent:mapper", kind="covenant_tag", pattern="term loan", decision="debt", reason="r",
               approved_by=CONTROLLER, learned_from="wi_002", deal_id=DEAL_ID, company="Nu Aire")
    assert p.scope == "company" and p.platform is None
    remap = p.model_copy(update={"kind": "mapping", "scope": "platform", "platform": "Kewaunee", "company": None})
    assert Policy.model_validate_json(remap.model_dump_json()).scope == "platform"
    with pytest.raises(ValidationError):
        Policy.model_validate({**p.model_dump(), "scope": "deal"})


def test_edit_and_learned_adjustment_round_trip():
    edit = Edit(id="e_1", deal_id=DEAL_ID, kind="amount", company="Nu Aire",
                line="Selling, general and administrative", section="income_statement",
                old_value=9812.0, new_value=9312.0)
    assert edit.status == "needs_reason" and edit.remember is True and edit.actor == CONTROLLER
    assert edit.run_ids == [] and edit.policy_id is None and edit.adjustment_id is None
    assert Edit.model_validate_json(edit.model_dump_json()) == edit
    remap = Edit(id="e_2", deal_id=DEAL_ID, kind="remap", company="Nu Aire", line="Short-term investments",
                 section="balance_sheet", old_platform_line="Cash and cash equivalents",
                 new_platform_line="Short-term investments", status="reasoned", reason_chip=0,
                 reason_text="Not a cash equivalent (over 90 days)", policy_id="p_9")
    assert remap.model_dump(mode="json")["status"] == "reasoned"
    with pytest.raises(ValidationError):
        Edit.model_validate({**edit.model_dump(), "kind": "delete"})

    adj = LearnedAdjustment(id="a_1", deal_id=DEAL_ID, company="Nu Aire", line=edit.line, amount=9312.0,
                            reason="One-time acquisition cost, an allowed add-back", edit_id=edit.id)
    assert adj.status == "applied"
    assert LearnedAdjustment.model_validate_json(adj.model_dump_json()) == adj


def test_reason_chip_ids_are_0_to_2():
    assert ReasonChip(id=2, label="Correcting a typo in the source").id == 2
    with pytest.raises(ValidationError):
        ReasonChip(id=3, label="x")


def test_brief_reader_types_build_and_serialize():
    brief = _fixture_deal().brief
    assert BRIEF_READER == "agent:brief_reader"
    text = AgreementText(id="ag_1", deal_id=DEAL_ID, text="...", sha256="0" * 64, source="8-K Ex 10.1")
    cite = BriefCitation(field="limit", quote="shall not exceed 2.50 to 1.00", section="4.8(a)", confidence=0.9)
    flag = BriefFieldFlag(field="ebitda_addbacks[0].amount", question="Enter the amount from the books.")
    assert flag.kind == "brief_field"
    inp = BriefReaderInput(deal_id=DEAL_ID, item_id="wi_1", agreement_id=text.id, sha256=text.sha256,
                           section_index={"4.8": "Financial Covenants"}, excerpts={"4.8": "..."})
    out = BriefReaderOutput(brief=brief, citations=[cite], flags=[flag])
    draft = BriefDraft(item_id="wi_1", agreement_id=text.id, sha256=text.sha256, brief=brief, citations=[cite])
    for model in (text, cite, flag, inp, out, draft):
        assert type(model).model_validate_json(model.model_dump_json()) == model
    with pytest.raises(ValidationError):
        BriefCitation(field="limit", quote="q", section="s", confidence=1.5)
    assert Deal.model_validate({**_fixture_deal().model_dump(), "brief": None, "brief_status": "none"}).brief is None
