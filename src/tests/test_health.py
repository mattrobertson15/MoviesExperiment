from __future__ import annotations

from starlette.testclient import TestClient


def test_healthz(client: TestClient):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.text == "pass"


def test_readyz_ready(client: TestClient):
    # Fixture loads data, so app is ready
    r = client.get("/readyz")
    assert r.status_code == 200


def test_version(client: TestClient):
    r = client.get("/version")
    assert r.status_code == 200
    assert r.text == "0.0.1-test"
    assert r.headers["content-type"].startswith("text/plain")


def test_root_redirects(client: TestClient):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/swagger"


def test_swagger_ui(client: TestClient):
    r = client.get("/swagger")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_swagger_json(client: TestClient):
    r = client.get("/swagger/v1/swagger.json")
    assert r.status_code == 200
    body = r.json()
    assert body["openapi"].startswith("3.")
    assert "/api/movies" in body["paths"]
    assert "/api/actors" in body["paths"]
