"""App entry point. Run: uvicorn app.main:app --reload --port 8000"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import build_router
from app.core.config import settings
from app.db.fixtures.demo import seed_demo
from app.db.memory import MemoryStore
from app.gateway.gateway import Gateway


def create_app() -> FastAPI:
    store = MemoryStore()
    gateway = Gateway(store)
    seed_demo(store, gateway)
    app = FastAPI(title="Stochastic gateway API", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_methods=["*"], allow_headers=["*"])
    app.include_router(build_router(gateway))

    @app.post("/dev/reset")
    def reset():
        """Demo helper: reseed the in-memory store."""
        store.__init__()
        seed_demo(store, gateway)
        return {"ok": True}

    return app


app = create_app()
