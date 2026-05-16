from __future__ import annotations

from typing import List

from fastapi import APIRouter, Request

router = APIRouter(tags=["catalog"])


@router.get("/genres", response_model=List[str], summary="List all genres")
def list_genres(request: Request) -> List[str]:
    store = request.app.state.store
    return store.genres
