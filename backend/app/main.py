"""App entry point. Run: uvicorn app.main:app --reload --port 8000"""
import logging
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parents[2] / ".env")  # keys stay in the repo-root .env, which git ignores

from app.api.body_limit import MAX_BODY_BYTES, BodyLimitMiddleware  # noqa: E402
from app.api.routes import build_router  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.fixtures.kewaunee import seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402


log = logging.getLogger("stochastic")


def open_store() -> MemoryStore:
    """STORE=postgres writes through to Tiger Cloud. If the database cannot be reached, the API still starts
    in memory and says so on /health, so the demo is never blocked by the network."""
    if settings.store != "postgres":
        return MemoryStore()
    if not settings.database_url:
        raise RuntimeError("STORE=postgres needs DATABASE_URL in .env")
    from app.db.postgres import PostgresStore
    try:
        return PostgresStore(settings.database_url, schema=settings.db_schema)
    except Exception as error:  # noqa: BLE001 - any connect or schema failure falls back the same way
        log.error("Postgres store unavailable, running in memory: %s", error)
        store = MemoryStore()
        store.fallback_reason = f"{type(error).__name__}: {error}"
        return store


def create_app() -> FastAPI:
    store = open_store()
    gateway = Gateway(store)
    if settings.forks == "tiger" and store.kind == "postgres" and settings.tiger_service_id:
        from app.db.forks import TigerCliForks
        from app.gateway.whatif import WhatIfForks
        binary = os.getenv("TIGER_BIN") or shutil.which("tiger") or os.path.expanduser("~/.local/bin/tiger")
        gateway.forks = WhatIfForks(gateway, TigerCliForks(settings.tiger_service_id, binary=binary),
                                    schema=settings.db_schema)
        gateway.forks.clean_leftovers()
    if not store.deals:  # a Postgres store that loaded a ledger keeps it
        seed(store, gateway)
    app = FastAPI(title="Stochastic gateway API", version="0.2.0")
    app.add_middleware(BodyLimitMiddleware, max_bytes=MAX_BODY_BYTES)
    # CORS is added last so it is outermost and a 413 still carries CORS headers
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_methods=["*"], allow_headers=["*"])
    app.include_router(build_router(gateway))
    app.state.gateway = gateway

    @app.post("/dev/reset")
    def reset(keep_memory: bool = True):
        """Demo helper: reseed the deal. Agent memory (policies, sessions) is kept unless keep_memory=false,
        so a second run shows the Mapper applying what the controller taught it. Between judges, use
        keep_memory=false so the next judge sees the flag. Refused while a run is in flight, because the run
        would keep writing into the new deal; the fork slot is freed."""
        if gateway.running:
            raise HTTPException(409, "a run is in progress; wait for it to finish, then reset")
        with gateway.lock:
            store.reset_deals(keep_memory=keep_memory)
            seed(store, gateway)
            if gateway.forks:
                gateway.forks.reset()
        return {"ok": True, "keep_memory": keep_memory, "policies": len(store.policies),
                "sessions": len(store.sessions)}

    return app


app = create_app()
