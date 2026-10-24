"""STORE=postgres with a database that cannot be reached still starts the API, in memory, and says why on /health."""
import dataclasses
import os

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402


def test_an_unreachable_database_falls_back_to_memory(monkeypatch):
    monkeypatch.setattr(main, "settings", dataclasses.replace(
        main.settings, store="postgres", database_url="postgresql://nobody@127.0.0.1:1/none?connect_timeout=2"))
    health = TestClient(main.create_app()).get("/health").json()
    assert health["store"]["kind"] == "memory"
    assert "OperationalError" in health["store"]["fallback_reason"]
    assert health["chain_valid"]


def test_the_default_store_is_memory():
    health = TestClient(main.create_app()).get("/health").json()
    assert health["store"] == {"kind": "memory", "fallback_reason": None}
