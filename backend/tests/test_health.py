from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def _all_ok_patches():
    return [
        patch("infrastructure.health._probe_postgres", new=AsyncMock(return_value=True)),
        patch("infrastructure.health._probe_mongodb", new=AsyncMock(return_value=True)),
        patch("infrastructure.health._probe_minio", new=AsyncMock(return_value=True)),
        patch("infrastructure.health._probe_mqtt", new=AsyncMock(return_value=True)),
    ]


def test_health_all_ok(client: TestClient):
    with (
        patch("infrastructure.health._probe_postgres", new=AsyncMock(return_value=True)),
        patch("infrastructure.health._probe_mongodb", new=AsyncMock(return_value=True)),
        patch("infrastructure.health._probe_minio", new=AsyncMock(return_value=True)),
        patch("infrastructure.health._probe_mqtt", new=AsyncMock(return_value=True)),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert all(v == "ok" for v in body["checks"].values())


def test_health_degraded_when_one_fails(client: TestClient):
    with (
        patch("infrastructure.health._probe_postgres", new=AsyncMock(return_value=True)),
        patch("infrastructure.health._probe_mongodb", new=AsyncMock(return_value=False)),
        patch("infrastructure.health._probe_minio", new=AsyncMock(return_value=True)),
        patch("infrastructure.health._probe_mqtt", new=AsyncMock(return_value=True)),
    ):
        response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["mongodb"] == "error"
    assert body["checks"]["postgres"] == "ok"
