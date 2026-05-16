from __future__ import annotations

import pytest

from movies_api.store import Store


def test_load_counts(test_store: Store):
    assert len(test_store.movies) == 3
    assert len(test_store.actors) == 4
    assert test_store.ready is True


def test_genres_sorted(test_store: Store):
    assert test_store.genres == sorted(test_store.genres)
    assert "Drama" in test_store.genres
    assert "Crime" in test_store.genres
    assert "Fantasy" in test_store.genres


def test_ratings_merged(test_store: Store):
    shawshank = test_store.get_movie("tt0111161")
    assert shawshank is not None
    assert shawshank.rating == pytest.approx(9.3)
    assert shawshank.votes == 2700000


def test_get_movie_known(test_store: Store):
    movie = test_store.get_movie("tt0111161")
    assert movie is not None
    assert movie.title == "The Shawshank Redemption"
    assert movie.year == 1994


def test_get_movie_unknown(test_store: Store):
    assert test_store.get_movie("tt9999999") is None


def test_get_actor_known(test_store: Store):
    actor = test_store.get_actor("nm0000209")
    assert actor is not None
    assert actor.name == "Tim Robbins"


def test_get_actor_unknown(test_store: Store):
    assert test_store.get_actor("nm9999999") is None


def test_list_movies_no_filter(test_store: Store):
    results = test_store.list_movies()
    assert len(results) == 3
    # sorted year DESC
    assert results[0].year >= results[1].year >= results[2].year


def test_list_movies_q(test_store: Store):
    results = test_store.list_movies(q="godfather")
    assert len(results) == 1
    assert results[0].title == "The Godfather"


def test_list_movies_q_case_insensitive(test_store: Store):
    results = test_store.list_movies(q="SHAWSHANK")
    assert len(results) == 1


def test_list_movies_genre(test_store: Store):
    results = test_store.list_movies(genre="Crime")
    assert all("Crime" in m.genres for m in results)


def test_list_movies_genre_case_insensitive(test_store: Store):
    upper = test_store.list_movies(genre="DRAMA")
    lower = test_store.list_movies(genre="drama")
    assert {m.id for m in upper} == {m.id for m in lower}


def test_list_movies_year(test_store: Store):
    results = test_store.list_movies(year=1994)
    assert len(results) == 1
    assert results[0].title == "The Shawshank Redemption"


def test_list_movies_min_rating(test_store: Store):
    results = test_store.list_movies(min_rating=9.0)
    assert all(m.rating is not None and m.rating >= 9.0 for m in results)
    assert len(results) == 2


def test_list_movies_actor_id(test_store: Store):
    results = test_store.list_movies(actor_id="nm0000209")
    assert len(results) == 1
    assert results[0].id == "tt0111161"


def test_list_movies_filters_combine_and(test_store: Store):
    # Drama + year=1994 → only Shawshank
    results = test_store.list_movies(genre="Drama", year=1994)
    assert len(results) == 1
    assert results[0].id == "tt0111161"


def test_list_actors_no_filter(test_store: Store):
    results = test_store.list_actors()
    assert len(results) == 4
    names = [a.name for a in results]
    assert names == sorted(names)


def test_list_actors_q(test_store: Store):
    results = test_store.list_actors(q="freeman")
    assert len(results) == 1
    assert results[0].name == "Morgan Freeman"
