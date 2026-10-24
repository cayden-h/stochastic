"""One app-level handler for request validation errors (422).

FastAPI's default handler echoes each error's input, and a JSON body may carry NaN or an infinity (Python's JSON
reader accepts NaN, Infinity, and 1e999). A non-finite float cannot be written as JSON, so the default 422 would
become a 500. This handler returns the same 422 shape ({"detail": [{"loc", "msg", "type", ...}]}) with every
non-finite float replaced by the string "non-finite", so the field path and the message always reach the client
and a non-finite value is never echoed.
Owner: Tri (backend/app/api/).
"""
from __future__ import annotations

import math

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

NON_FINITE = "non-finite"


def finite_only(value):
    """A copy of value with every NaN or infinity (at any depth in dicts, lists, and tuples) replaced by "non-finite"."""
    if isinstance(value, float) and not math.isfinite(value):
        return NON_FINITE
    if isinstance(value, dict):
        return {k: finite_only(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite_only(v) for v in value]
    return value


async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": finite_only(jsonable_encoder(finite_only(exc.errors())))})


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_error)
