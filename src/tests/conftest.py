from __future__ import annotations

import os
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from movies_api.config import Config
from movies_api.main import create_app
from movies_api.store import Store

TEST_DATA_DIR = str(Path(__file__).parent / "data")


@pytest.fixture(scope="session")
def test_config() -> Config:
    return Config(
        data_dir=TEST_DATA_DIR,
        log_level="error",
        port=8080,
        version="0.0.1-test",
    )


@pytest.fixture(scope="session")
def test_store(test_config: Config) -> Store:
    s = Store()
    s.load(test_config.data_dir)
    return s


@pytest.fixture(scope="session")
def client(test_config: Config) -> TestClient:
    app = create_app(test_config)
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
