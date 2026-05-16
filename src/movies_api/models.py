from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Role(BaseModel):
    order: int
    actorId: str
    name: str
    category: str
    characters: Optional[List[str]] = None
    job: Optional[str] = None


class Movie(BaseModel):
    id: str
    title: str
    year: int
    runtime: Optional[int] = None
    genres: List[str] = []
    roles: List[Role] = []
    rating: Optional[float] = None
    votes: Optional[int] = None


class ActorMovie(BaseModel):
    movieId: str
    title: str


class Actor(BaseModel):
    id: str
    name: str
    birthYear: Optional[int] = None
    deathYear: Optional[int] = None
    profession: List[str] = []
    movies: List[ActorMovie] = []


class Page(BaseModel, Generic[T]):
    pageNumber: int
    pageSize: int
    totalCount: int
    items: List[T]
