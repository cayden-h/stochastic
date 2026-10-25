"""Simulated GL detail: every detail line's accounts sum exactly to the filed amount, the same lines give the same
accounts, subtotals get none, and GET /deals/{id}/gl returns the shape the console reads."""
import os

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.fixtures.kewaunee import DEAL_ID, build_lines  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.main import create_app  # noqa: E402
from app.tools.gl_detail import NOTE, gl_detail  # noqa: E402


def test_demo_lines_sum_exactly_and_are_deterministic():
    lines = build_lines(MemoryStore())
    first, second = gl_detail(lines), gl_detail(build_lines(MemoryStore()))
    for line in lines:
        if line.is_total:
            assert line.id not in first
            continue
        accounts = first[line.id]
        assert sum(a.amount for a in accounts) == line.amount, line.line
        assert (len(accounts) == 2) if line.amount == 0 else (4 <= len(accounts) <= 8), line.line
        assert all(a.amount == int(a.amount) for a in accounts)
        assert all(a.last_posted[:7] in line.period or line.period.endswith("2024-09-30") for a in accounts)
    assert [[a.model_dump() for a in v] for v in first.values()] == [[a.model_dump() for a in v] for v in second.values()]
    for line in lines:  # account numbers are unique within a company
        nums = [a.account for l in lines if l.company == line.company and not l.is_total for a in first[l.id]]
        assert len(nums) == len(set(nums))


def test_gl_route_shape_and_every_seeded_case_sums():
    c = TestClient(create_app())
    assert c.get("/deals/nope/gl").status_code == 404
    deals = c.get("/deals").json()
    for deal_id in [d["id"] for d in deals]:
        body = c.get(f"/deals/{deal_id}/gl").json()
        assert body["simulated"] is True and body["note"] == NOTE
        lines = c.get(f"/deals/{deal_id}/source-lines").json()
        detail = [l for l in lines if not l["is_total"]]
        assert set(body["lines"]) == {l["id"] for l in detail}
        for l in detail:
            accounts = body["lines"][l["id"]]
            assert abs(sum(a["amount"] for a in accounts) - l["amount"]) < 1e-6, (deal_id, l["line"])
            for a in accounts:
                assert set(a) == {"account", "name", "amount", "prior", "entries", "last_posted"}
                assert isinstance(a["account"], str) and isinstance(a["entries"], int)
    assert DEAL_ID in [d["id"] for d in deals]
