from __future__ import annotations

import pytest
from starlette.testclient import TestClient


def test_list_movies_ok(client: TestClient):
    r = client.get("/api/movies")
    assert r.status_code == 200
    body = r.json()
    assert body["pageNumber"] == 1
    assert body["pageSize"] == 25
    assert body["totalCount"] == 3
    assert len(body["items"]) == 3


def test_list_movies_content_type(client: TestClient):
    r = client.get("/api/movies")
    assert "application/json" in r.headers["content-type"]


def test_list_movies_pagination(client: TestClient):
    r = client.get("/api/movies?pageNumber=1&pageSize=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["totalCount"] == 3

    r2 = client.get("/api/movies?pageNumber=2&pageSize=2")
    assert r2.status_code == 200
    body2 = r2.json()
    assert len(body2["items"]) == 1


def test_list_movies_q(client: TestClient):
    r = client.get("/api/movies?q=godfather")
    assert r.status_code == 200
    assert r.json()["totalCount"] == 1


def test_list_movies_genre(client: TestClient):
    r = client.get("/api/movies?genre=Crime")
    assert r.status_code == 200
    assert r.json()["totalCount"] == 1


def test_list_movies_year(client: TestClient):
    r = client.get("/api/movies?year=1994")
    assert r.status_code == 200
    assert r.json()["totalCount"] == 1


def test_list_movies_rating(client: TestClient):
    r = client.get("/api/movies?rating=9.0")
    assert r.status_code == 200
    body = r.json()
    assert body["totalCount"] == 2


def test_list_movies_actor_id(client: TestClient):
    r = client.get("/api/movies?actorId=nm0000209")
    assert r.status_code == 200
    assert r.json()["totalCount"] == 1


# --- validation errors (400) ---

def test_list_movies_q_too_short(client: TestClient):
    r = client.get("/api/movies?q=a")
    assert r.status_code == 400


def test_list_movies_q_too_long(client: TestClient):
    r = client.get("/api/movies?q=" + "a" * 21)
    assert r.status_code == 400


def test_list_movies_page_number_zero(client: TestClient):
    r = client.get("/api/movies?pageNumber=0")
    assert r.status_code == 400


def test_list_movies_page_number_too_high(client: TestClient):
    r = client.get("/api/movies?pageNumber=10001")
    assert r.status_code == 400


def test_list_movies_page_size_zero(client: TestClient):
    r = client.get("/api/movies?pageSize=0")
    assert r.status_code == 400


def test_list_movies_page_size_too_high(client: TestClient):
    r = client.get("/api/movies?pageSize=1001")
    assert r.status_code == 400


def test_list_movies_invalid_actor_id(client: TestClient):
    r = client.get("/api/movies?actorId=invalid")
    assert r.status_code == 400


def test_get_movie_ok(client: TestClient):
    r = client.get("/api/movies/tt0111161")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "tt0111161"
    assert body["title"] == "The Shawshank Redemption"
    assert body["year"] == 1994
    assert "Drama" in body["genres"]
    assert body["rating"] == pytest.approx(9.3)


def test_get_movie_not_found(client: TestClient):
    r = client.get("/api/movies/tt9999999")
    assert r.status_code == 404


def test_get_movie_bad_id_format(client: TestClient):
    r = client.get("/api/movies/badid")
    assert r.status_code == 400
