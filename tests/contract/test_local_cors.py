from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from allyakkkuk.core.config import Settings
from allyakkkuk.main import create_app

pytestmark = pytest.mark.contract


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
)
def test_local_vite_origin_can_preflight_json_request(origin: str) -> None:
    app = create_app(
        Settings(
            cors_origins=(
                "http://localhost:5173,http://127.0.0.1:5173"
            )
        )
    )

    with TestClient(app) as client:
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
