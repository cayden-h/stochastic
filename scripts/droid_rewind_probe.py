"""Probe Droid's Session.rewind for the Mapper retry (docs/tasks/eric.md, Task A). Not app code.

    DROID_MODEL=claude-haiku-5-5 backend/.venv/bin/python scripts/droid_rewind_probe.py

Turn 1 asks the session to remember PELICAN. Turn 2 asks it to remember HERON. The session is closed and resumed,
then rewound to the message that started turn 2, and turn 3 asks for both codewords on the successor.
Expected if rewind drops turn 2: the successor knows PELICAN and not HERON.
Prints every streamed item's type and ids, so we can see which message id starts a turn.
Runs in an empty temp folder with no tools. Spends a few Factory credits.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


async def turn(session, prompt: str) -> tuple[str, list[tuple[str, str | None]]]:
    seen: list[tuple[str, str | None]] = []
    text = []
    stream = session.stream(prompt)
    async with stream:
        async for item in stream:
            mid = getattr(item, "id", None) or getattr(item, "message_id", None)
            seen.append((type(item).__name__, mid))
            if type(item).__name__ == "AssistantMessage":
                text.append(item.text)
    return " ".join(text).strip(), seen


def show(label: str, seen):
    kinds = []
    for kind, mid in seen:
        if not kinds or kinds[-1][0] != kind or kinds[-1][1] != mid:
            kinds.append((kind, mid))
    print(f"{label} stream:", [f"{k}:{m}" for k, m in kinds if k in ("UserMessage", "AssistantMessage")])


async def main() -> int:
    from droid_sdk import Autonomy, Session, SessionConfig

    cwd = tempfile.mkdtemp(prefix="rewind-probe-")
    config = SessionConfig(restrict_tools=["none"], autonomy=Autonomy.HIGH,
                           system_prompt="You are a test assistant. Answer in one short line. Use no tools.")
    model = os.getenv("DROID_MODEL", "claude-haiku-5-5")
    session = Session(cwd=cwd, config=config, model=model)
    await session.open()
    a1, s1 = await turn(session, "Remember the codeword PELICAN. Reply only: OK.")
    show("turn 1", s1)
    a2, s2 = await turn(session, "Also remember a second codeword, HERON. Reply only: OK.")
    show("turn 2", s2)
    sid = session.id
    await session.close()
    print("turn 1 reply:", a1, "| turn 2 reply:", a2, "| session:", sid)

    turn2_user = [m for k, m in s2 if k == "UserMessage"]
    turn1_assistant = [m for k, m in s1 if k == "AssistantMessage"]
    print("turn 2 user message ids:", turn2_user, "| turn 1 assistant ids:", turn1_assistant)

    # Q3: rewind a session reopened with Session.resume, from a new Session object
    resumed = Session.resume(sid)
    await resumed.open()
    target = turn2_user[0] if turn2_user else None
    print("rewinding resumed session to", target)
    try:
        outcome = await resumed.rewind(target, title="probe rewind")
    except Exception as error:
        print("REWIND FAILED:", type(error).__name__, str(error)[:300])
        await resumed.close()
        return 1
    successor = outcome.session
    print("successor id:", successor.id, "| old id:", sid, "| same:", successor.id == sid)
    a3, _ = await turn(successor, "List every codeword I asked you to remember, comma separated, nothing else.")
    print("turn 3 reply on successor:", a3)
    await successor.close()
    try:
        await resumed.close()
    except Exception:
        pass
    print("PELICAN kept:", "PELICAN" in a3.upper(), "| HERON dropped:", "HERON" not in a3.upper())
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
