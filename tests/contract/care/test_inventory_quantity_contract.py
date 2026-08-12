from __future__ import annotations

import pytest

from allyakkkuk.core.config import Settings
from allyakkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-3.3")]


def test_registration_response_documents_server_owned_quantity_unit() -> None:
    schema = create_app(Settings(app_env="test")).openapi()
    operation = schema["paths"]["/api/v1/care/items"]["post"]
    request = schema["components"]["schemas"]["CareItemCreateRequest"]
    response = schema["components"]["schemas"]["CareItemResponse"]

    assert operation["operationId"] == "care_register_item"
    assert operation["security"] == [{"AccessCookieAuth": []}]
    assert set(operation["responses"]) >= {"201", "401", "404", "422", "503"}
    assert "quantity_unit" not in request["properties"]
    assert response["properties"]["quantity_unit"]["enum"] == [
        "TABLET",
        "CAPSULE",
        "SCOOP",
        "PACKET",
    ]
    assert "quantity_unit" in response["required"]
    assert "user_id" not in response["properties"]
