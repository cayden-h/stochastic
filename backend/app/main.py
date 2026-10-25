"""App entry point. Run: uvicorn app.main:app --reload --port 8000"""
import logging
import os
import sys
import shutil
import threading
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parents[2] / ".env")  # keys stay in the repo-root .env, which git ignores

from app.api.body_limit import MAX_BODY_BYTES, BodyLimitMiddleware  # noqa: E402
from app.api.errors import install_error_handlers  # noqa: E402
from app.api.routes import build_router  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.fixtures.kewaunee import DEAL_ID, seed  # noqa: E402
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


def demo_cases_wanted() -> bool:
    """DEMO_CASES (default on) seeds the Dashboard's four cases after startup. Under pytest it is off unless a test
    asks (create_app(demo_cases=True)), so the suite's deal ids and counters stay as they were. The module-level `app`
    is built while pytest collects, before PYTEST_CURRENT_TEST is set, so a loaded pytest counts too: its background
    seeding thread used to run the cases' scripted agents into the middle of a later test's `last_runs`."""
    if os.getenv("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
        return False
    return (os.getenv("DEMO_CASES") or "1").strip().lower() not in ("0", "off", "false", "no")


def demo_from_agreement_wanted() -> bool:
    """DEMO_FROM_AGREEMENT (default on) starts the live demo deal from the agreement text (D23): the Brief Reader, the
    verifier, then the controller's one-click Brief approval. Under pytest it is off unless a test asks
    (create_app(demo_from_agreement=True)), so the suite's flows that start at the Mapper stay as they were."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    return (os.getenv("DEMO_FROM_AGREEMENT") or "1").strip().lower() not in ("0", "off", "false", "no")


def start_demo_cases(gateway: Gateway, background: bool = True) -> threading.Thread | None:
    """Seed the cases through the real pipeline (scripted backend, no pace). In a background thread, so /health
    answers at once; a case already in the store (a Postgres ledger that loaded it) is never touched."""
    from app.db.fixtures.cases import seed_cases

    def run():
        try:
            seeded = seed_cases(gateway)
            if seeded:
                log.info("seeded the Dashboard cases: %s", ", ".join(seeded))
        except Exception:  # noqa: BLE001 - the demo deal must work whatever happens to the cases
            log.exception("seeding the Dashboard cases failed")

    if not background:
        run()
        return None
    t = threading.Thread(target=run, name="stochastic-demo-cases", daemon=True)
    t.start()
    return t


def create_app(demo_cases: bool | None = None, demo_cases_background: bool = True,
               demo_from_agreement: bool | None = None) -> FastAPI:
    store = open_store()
    gateway = Gateway(store)
    from_agreement = demo_from_agreement if demo_from_agreement is not None else demo_from_agreement_wanted()

    def seed_demo_deal() -> None:
        seed(store, gateway, from_agreement=from_agreement)
    if settings.forks == "tiger" and store.kind == "postgres" and settings.tiger_service_id:
        from app.db.forks import TigerCliForks
        from app.gateway.whatif import WhatIfForks
        binary = os.getenv("TIGER_BIN") or shutil.which("tiger") or os.path.expanduser("~/.local/bin/tiger")
        gateway.forks = WhatIfForks(gateway, TigerCliForks(settings.tiger_service_id, binary=binary),
                                    schema=settings.db_schema)
        gateway.forks.clean_leftovers()
    if not store.deals:  # a Postgres store that loaded a ledger keeps it
        seed_demo_deal()
    stuck = gateway.recover_interrupted_runs()  # no job survives a restart; a deal left mid-run gets Run again
    if stuck:
        log.warning("deals left mid-run by the last process, now run_failed: %s", ", ".join(stuck))
    app = FastAPI(title="Stochastic gateway API", version="0.2.0")
    app.add_middleware(BodyLimitMiddleware, max_bytes=MAX_BODY_BYTES)
    # CORS is added last so it is outermost and a 413 still carries CORS headers
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_methods=["*"], allow_headers=["*"])
    app.include_router(build_router(gateway))
    install_error_handlers(app)
    app.state.gateway = gateway
    from app.db.fixtures import cases as _cases  # noqa: F401 - registers the cases' scripted plans and reason chips
    app.state.cases_thread = None
    if demo_cases if demo_cases is not None else demo_cases_wanted():
        app.state.cases_thread = start_demo_cases(gateway, background=demo_cases_background)

    FRESH_DEMO_REASON = "fresh demo: clear memory for the demo deal"

    @app.post("/dev/reset")
    def reset(keep_memory: bool = True):
        """Demo helper: reseed the live demo deal. Agent memory (policies, sessions) is kept unless keep_memory=false,
        so a second run shows the Mapper applying what the controller taught it. Between judges, use
        keep_memory=false so the next judge sees the flag. Every other deal (the Dashboard's seeded cases, uploads)
        keeps its whole record, its audit rows, and the memory learned on it, in both modes, except that
        keep_memory=false retires (D18) every live policy that covers the demo deal's companies or platform, whatever
        deal it was learned on, so the next demo run asks both questions again. Refused while a run of
        the demo deal is in flight, because the run would keep writing into the new deal; the fork slot is freed."""
        # The running check and the reset hold the lock a run's claim takes (routes.claim), so a Run clicked at the
        # same moment either claims first and the reset is refused, or waits and starts on the new deal.
        with gateway.running_lock:
            if DEAL_ID in gateway.running:
                raise HTTPException(409, "a run is in progress; wait for it to finish, then reset")
            with gateway.lock:
                keep = {d for d in store.deals if d != DEAL_ID}
                store.reset_deals(keep_memory=keep_memory, keep_deals=keep, rechain=gateway.rechain)
                gateway.run_pace.pop(DEAL_ID, None)
                seed_demo_deal()
                if not keep_memory:  # memory learned on other deals that covers the demo deal's companies, too
                    gateway.retire_policies_covering(DEAL_ID, FRESH_DEMO_REASON)
                if gateway.forks:
                    gateway.forks.reset()
        demo = store.deals[DEAL_ID]
        return {"ok": True, "keep_memory": keep_memory,
                "policies": len([p for p in store.policies.values() if gateway._policy_applies(p, DEAL_ID, demo.platform)
                                 or gateway._policy_applies(p, DEAL_ID, demo.target)]),
                "sessions": len(store.sessions), "kept_deals": sorted(keep)}

    return app


app = create_app()
