from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["ops"])


@router.get("/version", response_class=PlainTextResponse, include_in_schema=False)
async def version(request: Request) -> str:
    return getattr(request.app.state, "version", "1.0.0")
