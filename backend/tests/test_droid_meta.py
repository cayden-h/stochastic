"""The Droid backend confirms its model from the CLI's own session record, and pins the reasoning effort."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.agents.backends.droid_backend import served_model  # noqa: E402
from app.agents.settings import role_reasoning  # noqa: E402


def _write_session(root, cwd_dir, session_id, rows):
    d = root / cwd_dir
    d.mkdir(parents=True)
    with open(d / f"{session_id}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def test_served_model_reads_the_cli_session_record(tmp_path):
    rows = [{"type": "session", "id": "s1"},
            {"type": "message", "message": {"role": "assistant", "modelId": "claude-haiku-5-5", "reasoningEffort": "high"}},
            {"type": "message", "message": {"role": "assistant", "modelId": "claude-haiku-5-5", "reasoningEffort": "high"}}]
    _write_session(tmp_path, "-tmp-stochastic-droid-abc", "s1", rows)
    out = served_model("s1", sessions_dir=str(tmp_path))
    assert out["model"] == "claude-haiku-5-5" and out["reasoning_effort"] == "high"


def test_served_model_is_empty_when_missing_or_mixed(tmp_path):
    assert served_model("nope", sessions_dir=str(tmp_path)) == {}
    assert served_model(None, sessions_dir=str(tmp_path)) == {}
    rows = [{"message": {"modelId": "claude-haiku-5-5"}}, {"message": {"modelId": "claude-sonnet-5-5"}}]
    _write_session(tmp_path, "-tmp-x", "s2", rows)
    out = served_model("s2", sessions_dir=str(tmp_path))
    assert "model" not in out and out["models"] == ["claude-haiku-5-5", "claude-sonnet-5-5"]


def test_reasoning_effort_is_explicit_per_role(monkeypatch):
    monkeypatch.delenv("DROID_REASONING_EFFORT", raising=False)
    monkeypatch.delenv("DROID_REASONING_EFFORT_MAPPER", raising=False)
    assert role_reasoning("DROID", "mapper") == "high"
    monkeypatch.setenv("DROID_REASONING_EFFORT", "medium")
    assert role_reasoning("DROID", "mapper") == "medium"
    monkeypatch.setenv("DROID_REASONING_EFFORT_MAPPER", "xhigh")
    assert role_reasoning("DROID", "mapper") == "xhigh" and role_reasoning("DROID", "reviewer") == "medium"
