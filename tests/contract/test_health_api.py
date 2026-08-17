from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from yeongyangkkuk.api.health import get_database_probe
from yeongyangkkuk.main import app

pytestmark = pytest.mark.contract


class HealthyProbe:
    def check(self) -> None:
        return None


class UnhealthyProbe:
    def check(self) -> None:
        raise RuntimeError("테스트용 연결 실패")


def test_liveness_does_not_require_database() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live", headers={"X-Request-ID": "contract-live"}
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"] == "contract-live"


def test_readiness_reports_database_success() -> None:
    app.dependency_overrides[get_database_probe] = HealthyProbe
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_uses_public_error_contract() -> None:
    app.dependency_overrides[get_database_probe] = UnhealthyProbe
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 503
    assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert body["error"]["request_id"]


def test_unknown_path_uses_public_error_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/not-found")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
