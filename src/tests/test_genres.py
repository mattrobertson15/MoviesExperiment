from __future__ import annotations

from starlette.testclient import TestClient


def test_list_genres_ok(client: TestClient):
    r = client.get("/api/genres")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert "Drama" in body
    assert "Crime" in body
    assert "Fantasy" in body


def test_list_genres_sorted(client: TestClient):
    r = client.get("/api/genres")
    genres = r.json()
    assert genres == sorted(genres)


def test_list_genres_content_type(client: TestClient):
    r = client.get("/api/genres")
    assert "application/json" in r.headers["content-type"]
