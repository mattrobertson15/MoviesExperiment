from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["ops"])


@router.get("/healthz", response_class=PlainTextResponse, include_in_schema=False)
async def healthz() -> str:
    return "pass"


@router.get("/readyz", response_class=PlainTextResponse, include_in_schema=False)
async def readyz(request: Request):
    if getattr(request.app.state, "ready", False):
        return PlainTextResponse("pass", status_code=200)
    return PlainTextResponse("fail", status_code=503)
