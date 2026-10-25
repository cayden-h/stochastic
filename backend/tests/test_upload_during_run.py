"""An upload while a paced run holds the gateway lock waits in a worker thread, not on the event loop.

Found on 2026-10-24 in the final review: POST /deals is async and called the gateway under its lock on the event
loop, so an upload during a paced Mapper (which holds the lock for seconds) froze every stream until the lock was free.
"""
import asyncio
import json
import os
import threading
import time

os.environ["AGENT_BACKEND"] = "scripted"
os.environ["AGENT_FALLBACK"] = "scripted"

import httpx  # noqa: E402

from app.main import create_app  # noqa: E402
from tests.test_api import BRIEF, TARGET_CSV, platform_csv  # noqa: E402

HOLD_S = 1.5  # how long the stand-in for a paced Mapper holds the gateway lock


async def _upload_while_locked(app) -> tuple[float, int]:
    """Hold the gateway lock in another thread, upload, and measure the longest gap between event-loop ticks."""
    gw = app.state.gateway
    locked, release = threading.Event(), threading.Event()

    def mapper():
        with gw.lock:
            locked.set()
            release.wait(HOLD_S)

    holder = threading.Thread(target=mapper)
    holder.start()
    locked.wait(5)
    gaps, stop = [], asyncio.Event()

    async def ticker():
        last = time.monotonic()
        while not stop.is_set():
            await asyncio.sleep(0.02)
            t = time.monotonic()
            gaps.append(t - last)
            last = t
        gaps.append(time.monotonic() - last)  # a loop blocked for the whole upload never ticked inside the while

    tick = asyncio.create_task(ticker())
    await asyncio.sleep(0.1)  # the ticker is running before the upload starts
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"platform_csv": ("platform.csv", platform_csv(), "text/csv"),
                 "target_csv": ("target.csv", TARGET_CSV, "text/csv")}
        data = {"name": "Acme", "platform": "Acme", "target": "Bolt", "brief": json.dumps(BRIEF)}
        r = await client.post("/deals", files=files, data=data)
    stop.set()
    await tick
    holder.join()
    return max(gaps), r.status_code


def test_an_upload_during_a_paced_run_does_not_block_the_event_loop():
    app = create_app()
    started = time.monotonic()
    worst, status = asyncio.run(_upload_while_locked(app))
    assert status == 201
    assert time.monotonic() - started >= HOLD_S * 0.9  # the upload did wait for the lock
    assert worst < 0.5, f"the event loop stalled for {worst:.2f} s during the upload"
