"""Settings read from the environment. No secrets are stored in code."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    store: str = os.getenv("STORE", "memory")  # memory or postgres; postgres needs DATABASE_URL
    db_schema: str = os.getenv("DB_SCHEMA", "stochastic")
    forks: str = os.getenv("FORKS", "off")  # tiger: hold a covenant flag's what-ifs in a Tiger fork (needs STORE=postgres)
    tiger_service_id: str = os.getenv("TIGER_SERVICE_ID", "")  # the service to fork, from `tiger service list`
    cors_origins: tuple[str, ...] = tuple(
        os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    )
    agent_backend: str = os.getenv("AGENT_BACKEND", "scripted")


settings = Settings()
