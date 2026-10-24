"""A live run must never replace the pinned replay; only `scripts/record_run.py` (RECORD_RUNS=force) writes it."""
from pydantic import BaseModel

from app.agents import recording


class Out(BaseModel):
    text: str


def test_live_run_writes_latest_and_force_writes_the_pinned_file(tmp_path, monkeypatch):
    monkeypatch.setattr(recording, "RECORDINGS", tmp_path)
    pinned = recording.record("mapper", Out(text="in"), Out(text="pinned"), "droid")
    live = recording.record("mapper", Out(text="in"), Out(text="live"), "droid", latest=True)

    assert pinned == tmp_path / "mapper.json"
    assert live == tmp_path / "latest" / "mapper.json"
    out, backend, matches = recording.load("mapper", Out, Out(text="in"))
    assert (out.text, backend, matches) == ("pinned", "droid", True)


def test_default_fallback_is_the_scripted_rules(monkeypatch):
    from app.agents import runner, settings

    monkeypatch.delenv("AGENT_FALLBACK", raising=False)
    assert runner.DEFAULT_FALLBACK == "scripted"
    assert settings.summary()["fallback"] == "scripted"
