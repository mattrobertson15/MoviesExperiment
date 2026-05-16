from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from ..models import Movie, Page

router = APIRouter(tags=["catalog"])

_ACTOR_ID_RE = re.compile(r"^nm\d{5,9}$")
_MOVIE_ID_RE = re.compile(r"^tt\d{5,9}$")


@router.get(
    "/movies",
    response_model=Page[Movie],
    summary="List movies",
)
def list_movies(
    request: Request,
    q: Optional[str] = Query(None, min_length=2, max_length=20, description="Search title (contains, case-insensitive)"),
    genre: Optional[str] = Query(None, description="Filter by genre (exact, case-insensitive)"),
    year: Optional[int] = Query(None, ge=1888, le=2100, description="Filter by release year"),
    rating: Optional[float] = Query(None, ge=0.0, le=10.0, description="Minimum rating (inclusive)"),
    actorId: Optional[str] = Query(None, description="Filter to movies featuring this actor"),
    pageNumber: int = Query(1, ge=1, le=10000, description="Page number (1-based)"),
    pageSize: int = Query(25, ge=1, le=1000, description="Items per page"),
) -> Page[Movie]:
    if actorId is not None and not _ACTOR_ID_RE.match(actorId):
        raise HTTPException(status_code=400, detail="actorId must match ^nm\\d{5,9}$")

    store = request.app.state.store
    results = store.list_movies(
        q=q,
        genre=genre,
        year=year,
        min_rating=rating,
        actor_id=actorId,
    )

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
    "/movies/{movie_id}",
    response_model=Movie,
    summary="Get movie by ID",
    responses={404: {"description": "Movie not found"}},
)
def get_movie(movie_id: str, request: Request) -> Movie:
    if not _MOVIE_ID_RE.match(movie_id):
        raise HTTPException(status_code=400, detail="movie_id must match ^tt\\d{5,9}$")

    store = request.app.state.store
    movie = store.get_movie(movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail=f"Movie '{movie_id}' not found")
    return movie
