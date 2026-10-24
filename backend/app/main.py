"""App entry point. Run: uvicorn app.main:app --reload --port 8000"""
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parents[2] / ".env")  # keys stay in the repo-root .env, which git ignores

from app.api.body_limit import MAX_BODY_BYTES, BodyLimitMiddleware  # noqa: E402
from app.api.routes import build_router  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.fixtures.kewaunee import seed  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.gateway.gateway import Gateway  # noqa: E402


def create_app() -> FastAPI:
    store = MemoryStore()
    gateway = Gateway(store)
    seed(store, gateway)
    app = FastAPI(title="Stochastic gateway API", version="0.2.0")
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(BodyLimitMiddleware, max_bytes=MAX_BODY_BYTES)
    app.include_router(build_router(gateway))

    @app.post("/dev/reset")
    def reset(keep_memory: bool = True):
        """Demo helper: reseed the deal. Agent memory (policies, sessions) is kept unless keep_memory=false,
        so a second run shows the Mapper applying what the controller taught it."""
        store.reset_deals(keep_memory=keep_memory)
        seed(store, gateway)
        return {"ok": True, "policies": len(store.policies), "sessions": len(store.sessions)}

    return app


app = create_app()
