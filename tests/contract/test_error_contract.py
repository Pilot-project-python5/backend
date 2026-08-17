from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yeongyangkkuk.core.config import Settings
from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.main import create_app

pytestmark = pytest.mark.contract


def error_test_app() -> FastAPI:
    application = create_app(Settings(app_env="test"))

    @application.get("/test/validation")
    def validation_route(value: int) -> dict[str, int]:
        return {"value": value}

    @application.get("/test/app-error")
    def app_error_route() -> None:
        raise AppError(status_code=409, code="FIXTURE_CONFLICT", message="충돌")

    @application.get("/test/unexpected")
    def unexpected_route() -> None:
        raise RuntimeError("응답에 노출되면 안 되는 내부 오류")

    return application


def test_validation_error_uses_field_contract() -> None:
    with TestClient(error_test_app()) as client:
        response = client.get("/test/validation", params={"value": "invalid"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"
    assert response.json()["error"]["fields"][0]["field"] == "query.value"


def test_application_error_is_serialized() -> None:
    with TestClient(error_test_app()) as client:
        response = client.get("/test/app-error")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "FIXTURE_CONFLICT"


def test_non_404_http_error_does_not_expose_framework_detail() -> None:
    with TestClient(error_test_app()) as client:
        response = client.post("/test/validation")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "HTTP_ERROR"


def test_unexpected_error_does_not_expose_exception() -> None:
    with TestClient(error_test_app(), raise_server_exceptions=False) as client:
        response = client.get("/test/unexpected")

    body = response.json()
    assert response.status_code == 500
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "내부 오류" not in body["error"]["message"]
