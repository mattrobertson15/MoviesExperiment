from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ..models import Actor, Page

router = APIRouter(tags=["catalog"])

_ACTOR_ID_RE = re.compile(r"^nm\d{5,9}$")


@router.get(
    "/actors",
    response_model=Page[Actor],
    summary="List actors",
)
def list_actors(
    request: Request,
    q: Optional[str] = Query(None, min_length=2, max_length=20, description="Search name (contains, case-insensitive)"),
    pageNumber: int = Query(1, ge=1, le=10000, description="Page number (1-based)"),
    pageSize: int = Query(25, ge=1, le=1000, description="Items per page"),
) -> Page[Actor]:
    store = request.app.state.store
    results = store.list_actors(q=q)

    total = len(results)
    offset = (pageNumber - 1) * pageSize
    page_items = results[offset : offset + pageSize]

    return Page(
        pageNumber=pageNumber,
        pageSize=pageSize,
        totalCount=total,
        items=page_items,
    )


@router.get(
    "/actors/{actor_id}",
    response_model=Actor,
    summary="Get actor by ID",
    responses={404: {"description": "Actor not found"}},
)
def get_actor(actor_id: str, request: Request) -> Actor:
    if not _ACTOR_ID_RE.match(actor_id):
        raise HTTPException(status_code=400, detail="actor_id must match ^nm\\d{5,9}$")

    store = request.app.state.store
    actor = store.get_actor(actor_id)
    if actor is None:
        raise HTTPException(status_code=404, detail=f"Actor '{actor_id}' not found")
    return actor
