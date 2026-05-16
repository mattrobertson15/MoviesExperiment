from __future__ import annotations

from starlette.testclient import TestClient


def test_list_actors_ok(client: TestClient):
    r = client.get("/api/actors")
    assert r.status_code == 200
    body = r.json()
    assert body["totalCount"] == 4
    assert body["pageNumber"] == 1
    assert body["pageSize"] == 25


def test_list_actors_sorted_by_name(client: TestClient):
    r = client.get("/api/actors")
    names = [a["name"] for a in r.json()["items"]]
    assert names == sorted(names)


def test_list_actors_q(client: TestClient):
    r = client.get("/api/actors?q=freeman")
    assert r.status_code == 200
    assert r.json()["totalCount"] == 1


def test_list_actors_pagination(client: TestClient):
    r = client.get("/api/actors?pageSize=2&pageNumber=1")
    assert r.status_code == 200
    assert len(r.json()["items"]) == 2


def test_list_actors_q_too_short(client: TestClient):
    r = client.get("/api/actors?q=x")
    assert r.status_code == 400


def test_list_actors_q_too_long(client: TestClient):
    r = client.get("/api/actors?q=" + "a" * 21)
    assert r.status_code == 400


def test_list_actors_page_number_zero(client: TestClient):
    r = client.get("/api/actors?pageNumber=0")
    assert r.status_code == 400


def test_list_actors_page_size_too_large(client: TestClient):
    r = client.get("/api/actors?pageSize=1001")
    assert r.status_code == 400


def test_get_actor_ok(client: TestClient):
    r = client.get("/api/actors/nm0000209")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "nm0000209"
    assert body["name"] == "Tim Robbins"
    assert body["birthYear"] == 1958
    assert "actor" in body["profession"]


def test_get_actor_not_found(client: TestClient):
    r = client.get("/api/actors/nm9999999")
    assert r.status_code == 404


def test_get_actor_bad_id_format(client: TestClient):
    r = client.get("/api/actors/badid")
    assert r.status_code == 400
