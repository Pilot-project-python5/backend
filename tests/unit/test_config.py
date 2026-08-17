from __future__ import annotations

from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from allyakkkuk.core.config import Settings

pytestmark = pytest.mark.unit


def test_cors_origins_are_normalized() -> None:
    settings = Settings(
        cors_origins="http://localhost:3000, http://127.0.0.1:3000,",
    )

    assert settings.allowed_cors_origins == (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )


def test_default_cors_origins_include_local_vite_server() -> None:
    settings = Settings()

    assert "http://localhost:5173" in settings.allowed_cors_origins
    assert "http://127.0.0.1:5173" in settings.allowed_cors_origins


def test_non_postgresql_database_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///local.db")


def test_configured_timezone_is_an_iana_timezone() -> None:
    settings = Settings(app_timezone="Asia/Seoul")

    assert ZoneInfo(settings.app_timezone).key == "Asia/Seoul"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("api_prefix", "api/v1"),
        ("api_prefix", "/api/v1/"),
        ("app_timezone", "Invalid/Timezone"),
    ],
)
def test_invalid_application_boundary_settings_are_rejected(
    field: str, value: str
) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: value})  # type: ignore[arg-type]
