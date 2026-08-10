from __future__ import annotations

import pytest

from allyakkkuk.auth.repository import LoginIdAvailabilityPersistenceError
from allyakkkuk.auth.service import LoginIdAvailabilityService
from allyakkkuk.core.errors import AppError

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-1.1.1")]


class FakeLoginIdAvailabilityRepository:
    def __init__(self, *, exists: bool = False, fails: bool = False) -> None:
        self.already_exists = exists
        self.fails = fails
        self.normalized_login_id: str | None = None

    def exists(self, normalized_login_id: str) -> bool:
        self.normalized_login_id = normalized_login_id
        if self.fails:
            raise LoginIdAvailabilityPersistenceError
        return self.already_exists


def test_availability_service_normalizes_login_id() -> None:
    repository = FakeLoginIdAvailabilityRepository(exists=True)
    service = LoginIdAvailabilityService(repository)

    result = service.check("User123")

    assert repository.normalized_login_id == "user123"
    assert result.login_id == "User123"
    assert result.available is False


def test_availability_service_converts_database_failure() -> None:
    repository = FakeLoginIdAvailabilityRepository(fails=True)
    service = LoginIdAvailabilityService(repository)

    with pytest.raises(AppError) as captured:
        service.check("User123")

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"
