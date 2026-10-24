"""Zero-copy forks of the Tiger Cloud service, through the Tiger CLI. Owner: Cayden (with `postgres.py`).

A fork is a full copy of the ledger at one moment, as its own service. The gateway uses one to hold a flag's
what-ifs outside the live record (`app/gateway/whatif.py`). The free plan allows two services, so with the main
service running there is room for one fork at a time; every fork this code makes is named with FORK_PREFIX, so
a fork left over by a crash can be found and deleted on the next start.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Protocol

FORK_PREFIX = "stochastic-whatif-"


class ForkError(RuntimeError):
    pass


@dataclass(frozen=True)
class Fork:
    service_id: str
    name: str
    dsn: str  # holds the fork's own password; never log it


class ForkClient(Protocol):
    def create(self, name: str) -> Fork: ...
    def delete(self, service_id: str) -> None: ...
    def leftovers(self) -> list[tuple[str, str]]: ...  # (service_id, name) of forks this code made


class TigerCliForks:
    """Forks through the `tiger` CLI, which holds the login. A fork of the demo service took 33 to 35 s on
    2026-10-24, so `create` blocks; call it from a background thread."""

    def __init__(self, source_service_id: str, binary: str = "tiger", timeout: float = 600.0) -> None:
        self.source = source_service_id
        self.binary = binary
        self.timeout = timeout

    def _run(self, *args: str) -> str:
        try:
            done = subprocess.run([self.binary, *args], capture_output=True, text=True, timeout=self.timeout)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ForkError(f"tiger {args[0]} {args[1]}: {type(error).__name__}") from error
        if done.returncode != 0:
            # The CLI's error line names the reason (for example the free plan's service limit); no secrets in it.
            raise ForkError((done.stderr or done.stdout).strip().splitlines()[-1][:300] if (done.stderr or done.stdout)
                            else f"tiger exited {done.returncode}")
        return done.stdout

    def create(self, name: str) -> Fork:
        out = json.loads(self._run("service", "fork", self.source, "--name", name, "--no-set-default",
                                   "--with-password", "-o", "json"))
        if out.get("status") != "READY" or not out.get("connection_string"):
            raise ForkError(f"fork {out.get('service_id')} is {out.get('status')}")
        return Fork(service_id=out["service_id"], name=out["name"], dsn=out["connection_string"])

    def delete(self, service_id: str) -> None:
        self._run("service", "delete", service_id, "--confirm")

    def leftovers(self) -> list[tuple[str, str]]:
        services = json.loads(self._run("service", "list", "-o", "json"))
        return [(s["service_id"], s["name"]) for s in services if s.get("name", "").startswith(FORK_PREFIX)]
