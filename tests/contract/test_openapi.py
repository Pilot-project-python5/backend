from __future__ import annotations

import json
from pathlib import Path

import pytest

from yeongyangkkuk.main import app

pytestmark = pytest.mark.contract


def test_openapi_contains_versioned_health_contracts() -> None:
    schema = app.openapi()

    assert "/api/v1/health/live" in schema["paths"]
    assert "/api/v1/health/ready" in schema["paths"]
    assert schema["paths"]["/api/v1/health/live"]["get"]["operationId"] == (
        "system_liveness"
    )


def test_committed_openapi_is_valid_json() -> None:
    document = json.loads(Path("openapi.json").read_text(encoding="utf-8"))

    assert document["info"]["title"] == "영양꾹 백엔드"
