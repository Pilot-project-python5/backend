from __future__ import annotations

import pytest

from yeongyangkkuk.core.config import Settings
from yeongyangkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-3.2")]


def test_snapshot_behavior_keeps_f_3_1_http_contract_compatible() -> None:
    schema = create_app(Settings(app_env="test")).openapi()
    operation = schema["paths"]["/api/v1/care/items"]["post"]
    request_properties = schema["components"]["schemas"]["CareItemCreateRequest"][
        "properties"
    ]
    response_properties = schema["components"]["schemas"]["CareItemResponse"][
        "properties"
    ]

    assert operation["operationId"] == "care_register_item"
    assert operation["security"] == [{"AccessCookieAuth": []}]
    assert set(operation["responses"]) >= {"201", "401", "404", "422", "503"}
    assert "nutrient_snapshots" not in request_properties
    assert "nutrient_snapshots" not in response_properties
    assert "user_id" not in request_properties
    assert "user_id" not in response_properties
