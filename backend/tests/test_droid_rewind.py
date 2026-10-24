"""The Droid backend rewinds a resumed session before a turn when asked, and falls back honestly when it cannot.

The droid_sdk Session is faked, so no CLI and no credits are needed.
"""
import asyncio
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

droid_sdk = pytest.importorskip("droid_sdk")

from app.agents.backends import droid_backend  # noqa: E402
from app.agents.roles import MAPPER_ROLE  # noqa: E402
from app.core.models import MapperOutput  # noqa: E402


class UserMessage:  # the backend recognises the turn's start by this class name
    def __init__(self, id):
        self.id = id


class FakeStream:
    def __init__(self, session):
        self.session = session
        self.result = types.SimpleNamespace(success=True, output=MapperOutput(mappings=[], tags=[], flags=[]),
                                            session_id=session.id, turn_count=1, usage=None, duration=1.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __aiter__(self):
        async def gen():
            yield UserMessage(f"turn-start-on-{self.session.id}")
        return gen()


class FakeSession:
    rewind_raises = False
    log = []

    def __init__(self, id="S-new-fresh", **kwargs):
        self.id = id

    @classmethod
    def resume(cls, session_id, mcp_servers=()):
        return cls(session_id)

    async def open(self):
        FakeSession.log.append(("open", self.id))

    async def close(self):
        FakeSession.log.append(("close", self.id))

    async def rewind(self, message_id, *, title):
        FakeSession.log.append(("rewind", self.id, message_id))
        if FakeSession.rewind_raises:
            raise RuntimeError("rewind refused by the CLI")
        return types.SimpleNamespace(session=FakeSession("S-successor"))

    def stream(self, prompt, output=None, timeout=None):
        FakeSession.log.append(("turn", self.id))
        return FakeStream(self)


@pytest.fixture
def fake_sdk(monkeypatch):
    FakeSession.rewind_raises = False
    FakeSession.log = []
    monkeypatch.setattr(droid_sdk, "Session", FakeSession)
    monkeypatch.setattr(droid_backend, "served_model", lambda session_id: {})
    return FakeSession


def _run(session_id, rewind_to, key=None):
    inp = types.SimpleNamespace(model_dump_json=lambda: "{}")
    restrict = []  # the Mapper has no tools, so its fingerprint uses an empty list
    key = key or droid_backend.setup_key(MAPPER_ROLE, droid_backend.role_model("DROID_MODEL", "mapper"),
                                         droid_backend.role_reasoning("DROID", "mapper"), restrict)
    return asyncio.run(droid_backend._run(MAPPER_ROLE, inp, lambda *a: None, session_id, key, rewind_to))


def test_rewind_runs_the_turn_on_the_successor(fake_sdk):
    _, meta = _run("S-old", "m-bad")
    assert meta["rewound"] is True and meta["rewind_error"] is None
    assert meta["rewound_from_session"] == "S-old" and meta["rewound_to_message"] == "m-bad"
    assert meta["session_id"] == "S-successor"
    assert meta["turn_message_id"] == "turn-start-on-S-successor"
    assert ("rewind", "S-old", "m-bad") in fake_sdk.log and ("turn", "S-successor") in fake_sdk.log
    assert ("close", "S-old") in fake_sdk.log and ("close", "S-successor") in fake_sdk.log


def test_failed_rewind_keeps_the_resumed_session_and_says_why(fake_sdk):
    fake_sdk.rewind_raises = True
    _, meta = _run("S-old", "m-bad")
    assert meta["rewound"] is False and "rewind refused" in meta["rewind_error"]
    assert meta["session_id"] == "S-old" and meta["rewound_to_message"] is None
    assert ("turn", "S-old") in fake_sdk.log


def test_rewind_without_a_resumed_session_is_reported(fake_sdk):
    _, meta = _run(None, "m-bad")
    assert meta["rewound"] is False and meta["rewind_error"].startswith("no resumed session to rewind")
    assert meta["session_id"] == "S-new-fresh"
