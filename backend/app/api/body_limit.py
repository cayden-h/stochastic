"""Reject oversized request bodies before Starlette parses and spools them to disk.

Only requests that declare a content-length larger than the cap are refused here, without reading the body.
A request with no content-length (chunked) passes through; it is bounded by the per-file read in the route,
and a deployment should also cap request bodies in the reverse proxy.
"""
from __future__ import annotations

import json

from app.db.loader import MAX_BYTES

# Two files at the per-file cap, plus 1 MiB for the multipart form fields and boundaries.
MAX_BODY_BYTES = 2 * MAX_BYTES + 1024 * 1024


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes: int = MAX_BODY_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            for key, value in scope.get("headers", []):
                if key == b"content-length":
                    try:
                        too_big = int(value) > self.max_bytes
                    except ValueError:
                        too_big = False
                    if too_big:
                        body = json.dumps({"detail": f"request body is larger than {self.max_bytes // (1024 * 1024)} MB"}).encode()
                        await send({"type": "http.response.start", "status": 413,
                                    "headers": [(b"content-type", b"application/json"),
                                                (b"content-length", str(len(body)).encode())]})
                        await send({"type": "http.response.body", "body": body})
                        return
                    break
        await self.app(scope, receive, send)
