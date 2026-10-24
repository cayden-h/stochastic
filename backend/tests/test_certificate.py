"""Draft compliance certificate: GET /deals/{id}/certificate. Figures are hand-computed in test_demo_run.py."""
import os

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.certificate import render_html  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, PLATFORM, TARGET  # noqa: E402
from app.main import create_app  # noqa: E402

URL = f"/deals/{DEAL_ID}/certificate"
GATE = "certificate is available after the controller approves the result"


def case(c):
    return c.get(f"/deals/{DEAL_ID}/case").json()


def run_to_proposed(c):
    assert c.post(f"/deals/{DEAL_ID}/run").json()["stage"] == "awaiting_flag"
    for f in case(c)["flags"]:
        assert c.post(f"/work-items/{f['id']}/answer?auto_advance=false", json={"option_id": f["default"]}).status_code == 200
    assert c.post(f"/deals/{DEAL_ID}/run").json()["stage"] == "awaiting_approval"


def run_to_posted(c):
    run_to_proposed(c)
    item = case(c)["verdict"]["approval_item"]
    assert c.post(f"/work-items/{item}/approve").json()["state"] == "POSTED"


@pytest.fixture
def client():
    return TestClient(create_app())


def test_404_for_unknown_deal(client):
    assert client.get("/deals/nope/certificate").status_code == 404


def test_409_before_any_run(client):
    r = client.get(URL)
    assert r.status_code == 409 and r.json()["detail"] == GATE


def test_409_after_proposed_before_approval(client):
    run_to_proposed(client)
    for fmt in ("md", "html", "json"):
        r = client.get(f"{URL}?format={fmt}")
        assert r.status_code == 409 and r.json()["detail"] == GATE


def test_bad_format_is_422(client):
    run_to_posted(client)
    assert client.get(f"{URL}?format=pdf").status_code == 422


def test_after_approval_all_formats(client):
    run_to_posted(client)
    md = client.get(URL)
    assert md.status_code == 200 and md.headers["content-type"] == "text/markdown; charset=utf-8"
    html_r = client.get(f"{URL}?format=html")
    assert html_r.status_code == 200 and html_r.headers["content-type"].startswith("text/html")
    js = client.get(f"{URL}?format=json")
    assert js.status_code == 200
    cert = js.json()
    h = cert["header"]
    assert h["draft"] is True and h["backend"] == "scripted" and h["unit"] == "USD thousands"
    assert h["limit_section"] == "Section 4.8(a)" and h["debt_term"] == "Senior Funded Bank Debt"
    periods = cert["test_period"]["periods"]
    assert set(periods) == {PLATFORM, TARGET}
    for p in periods.values():
        assert set(p) == {"income_statement", "balance_sheet"} and p["income_statement"] and p["balance_sheet"]
    assert cert["companies"] == {"platform": PLATFORM, "target": TARGET}
    # Hand-computed figures (test_demo_run.py): EBITDA 28,378.845, debt 21,633, leverage 0.762, capacity 49,314.113.
    assert cert["ebitda"]["ebitda"] == pytest.approx(28378.845, abs=0.001)
    assert cert["debt"]["debt"] == pytest.approx(21633.0, abs=0.001)
    assert cert["leverage"]["leverage"] == pytest.approx(0.762, abs=0.0005)
    assert cert["limit_test"]["debt_capacity"] == pytest.approx(49314.113, abs=0.001)
    assert cert["limit_test"]["verdict"] == "ok" and cert["limit_test"]["limit"] == 2.5
    assert "naive_flip_addback" not in cert["limit_test"]  # the Reviewer's run carries no sensitivity; that is a separate gateway run on /case
    assert cert["tie_out"]["ok"] is True and cert["tie_out"]["run_id"]
    assert len(cert["decisions"]) == 2 and all(d["state"] == "POSTED" and d["option_id"] for d in cert["decisions"])
    fin = next(d for d in cert["decisions"] if "Financing liability" in d["question"])
    assert fin["option_id"] == "b" and fin["effect"].startswith("Senior Funded Bank Debt 21,633K")
    assert cert["approval"]["state"] == "POSTED"
    audit = client.get(f"/deals/{DEAL_ID}/audit").json()["rows"]
    assert cert["approval"]["audit"]["chain_valid"] is True and cert["approval"]["audit"]["denied"] == 0
    assert cert["approval"]["audit"]["rows"] == len(audit)
    assert cert["mappings"]["count"] == len(client.get(f"/deals/{DEAL_ID}/mappings").json())
    assert cert["mappings"]["from_policy"] == 0  # first run: no policy learned yet


def test_every_figure_matches_its_run(client):
    run_to_posted(client)
    cert = client.get(f"{URL}?format=json").json()
    expected_tool = {"ebitda": "ebitda", "debt": "covenant_debt", "leverage": "leverage", "limit_test": "limit_test"}
    for section, tool in expected_tool.items():
        block = cert[section]
        run = client.get(f"/runs/{block['run_id']}").json()
        assert run["tool"] == tool
        for key, value in block.items():
            if key == "run_id":
                continue
            assert key in run["outputs"], f"{section}.{key} is not a {tool} output"
            assert value == run["outputs"][key], f"{section}.{key} differs from run {block['run_id']}"
    tie = client.get(f"/runs/{cert['tie_out']['run_id']}").json()
    assert tie["tool"] == "tie_out" and tie["outputs"]["ok"] is cert["tie_out"]["ok"]
    for d in cert["decisions"]:
        if d["run_id"]:  # covenant flags carry a limit_test run; mapping flags have none
            assert client.get(f"/runs/{d['run_id']}").json()["tool"] == "limit_test"
    result = case(client)["result"]
    assert cert["ebitda"]["run_id"] == result["run_ids_by_tool"]["ebitda"]
    assert cert["limit_test"]["run_id"] in result["review"]["run_ids"]


def test_markdown_carries_the_figures_and_run_ids(client):
    run_to_posted(client)
    cert = client.get(f"{URL}?format=json").json()
    md = client.get(URL).text
    assert md.startswith("# Draft compliance certificate")
    assert "Draft. Not signed." in md
    assert f"28,378.845 [{cert['ebitda']['run_id']}]" in md
    assert f"21,633.000 [{cert['debt']['run_id']}]" in md
    assert f"0.762 [{cert['leverage']['run_id']}]" in md
    assert f"49,314.113 [{cert['limit_test']['run_id']}]" in md
    assert "1,970.000" in md  # the Statesville rent deduction
    assert "scripted backend" in md and "the audit log are real" in md
    assert f"{PLATFORM}: net income" in md and f"{TARGET}: net income" in md
    assert "platform: net income" not in md and "target: net income" not in md
    assert f"{PLATFORM} income statement periods:" in md and f"{TARGET} balance sheet dates:" in md
    assert "no run" not in md
    mapping = next(d for d in cert["decisions"] if d["kind"] == "mapping")
    assert f"[from source line {', '.join(mapping['line_ids'])}]" in md
    titles = [line[3:] for line in md.splitlines() if line.startswith("## ")]
    assert titles == ["Header", "Test period", "EBITDA", "Debt", "Leverage", "Limit test", "Tie-out", "Decisions",
                      "Edits in review", "Approval", "Mappings"]


def test_html_escapes_strings(client):
    run_to_posted(client)
    cert = client.get(f"{URL}?format=json").json()
    cert["decisions"][0]["question"] = "Is <b>this</b> debt & more?"
    page = render_html(cert)
    assert "<b>this</b>" not in page and "&lt;b&gt;this&lt;/b&gt; debt &amp; more?" in page
    assert client.get(f"{URL}?format=html").text.count("<li>") > 10


def test_gateway_rejects_naive_debt_run_that_is_not_covenant_debt(client):
    run_to_posted(client)
    by_tool = case(client)["result"]["run_ids_by_tool"]
    r = client.post("/tools/limit_test", headers={"X-Actor": "system:gateway"},
                    json={"deal_id": DEAL_ID, "inputs": {"leverage_run_id": by_tool["leverage"],
                                                         "naive_debt_run_id": by_tool["ebitda"]}})
    assert r.status_code == 422, r.text
    assert "naive_debt_run_id must name a covenant_debt run" in r.json()["detail"]
