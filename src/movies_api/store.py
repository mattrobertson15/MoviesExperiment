from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .models import Actor, ActorMovie, Movie, Role

logger = logging.getLogger(__name__)


class Store:
    def __init__(self) -> None:
        self.movies: List[Movie] = []
        self.actors: List[Actor] = []
        self.genres: List[str] = []
        self._movies_by_id: Dict[str, Movie] = {}
        self._actors_by_id: Dict[str, Actor] = {}
        self.ready: bool = False

    def load(self, data_dir: str) -> None:
        base = Path(data_dir)

        ratings_raw = json.loads((base / "ratings.json").read_text(encoding="utf-8"))
        ratings_by_id: Dict[str, dict] = {r["movieId"]: r for r in ratings_raw}

        movies_raw = json.loads((base / "movies.json").read_text(encoding="utf-8"))
        self.movies = []
        for m in movies_raw:
            movie_id = m["movieId"]
            rating_info = ratings_by_id.get(movie_id, {})
            roles = [
                Role(
                    order=r["order"],
                    actorId=r["actorId"],
                    name=r["name"],
                    category=r["category"],
                    characters=r.get("characters"),
                    job=r.get("job"),
                )
                for r in m.get("roles", [])
            ]
            movie = Movie(
                id=movie_id,
                title=m["title"],
                year=m["year"],
                runtime=m.get("runtime"),
                genres=m.get("genres", []),
                roles=roles,
                rating=rating_info.get("rating"),
                votes=rating_info.get("votes"),
            )
            self.movies.append(movie)
            self._movies_by_id[movie_id] = movie

        genre_set: set = set()
        for movie in self.movies:
            genre_set.update(movie.genres)
        self.genres = sorted(genre_set)

        actors_raw = json.loads((base / "actors.json").read_text(encoding="utf-8"))
        self.actors = []
        for a in actors_raw:
            actor_id = a["actorId"]
            actor_movies = [
                ActorMovie(movieId=am["movieId"], title=am["title"])
                for am in a.get("movies", [])
            ]
            actor = Actor(
                id=actor_id,
                name=a["name"],
                birthYear=a.get("birthYear"),
                deathYear=a.get("deathYear"),
                profession=a.get("profession", []),
                movies=actor_movies,
            )
            self.actors.append(actor)
            self._actors_by_id[actor_id] = actor

        logger.info(
            "Data loaded",
            extra={"movies": len(self.movies), "actors": len(self.actors), "genres": len(self.genres)},
        )
        self.ready = True

    # --- lookups ---

    def get_movie(self, movie_id: str) -> Optional[Movie]:
        return self._movies_by_id.get(movie_id)

    def get_actor(self, actor_id: str) -> Optional[Actor]:
        return self._actors_by_id.get(actor_id)

    # --- filtered lists ---

    def list_movies(
        self,
        q: Optional[str] = None,
        genre: Optional[str] = None,
        year: Optional[int] = None,
        min_rating: Optional[float] = None,
        actor_id: Optional[str] = None,
    ) -> List[Movie]:
        results = self.movies

        if q:
            q_lower = q.lower()
            results = [m for m in results if q_lower in m.title.lower()]

        if genre:
            genre_lower = genre.lower()
            results = [m for m in results if any(g.lower() == genre_lower for g in m.genres)]

        if year is not None:
            results = [m for m in results if m.year == year]

        if min_rating is not None:
            results = [m for m in results if m.rating is not None and m.rating >= min_rating]

        if actor_id:
            results = [m for m in results if any(r.actorId == actor_id for r in m.roles)]

        # stable sort: year DESC, then title ASC
        results = sorted(results, key=lambda m: (-m.year, m.title))
        return results

    def list_actors(self, q: Optional[str] = None) -> List[Actor]:
        results = self.actors

        if q:
            q_lower = q.lower()
            results = [a for a in results if q_lower in a.name.lower()]

        results = sorted(results, key=lambda a: a.name)
        return results
