from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from yeongyangkkuk.auth.current_user_dependencies import require_current_user
from yeongyangkkuk.auth.current_user_service import AuthenticatedUser
from yeongyangkkuk.auth.models import Gender, UserStatus
from yeongyangkkuk.core.config import Settings
from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.main import create_app
from yeongyangkkuk.notification.router import get_notification_service
from yeongyangkkuk.notification.service import (
    NotificationListItem,
    NotificationListResult,
    NotificationReadResult,
    NotificationService,
)

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-3.9")]

NOW = datetime(2026, 8, 14, 0, 30, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000391")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000391")
NOTIFICATION_ID = UUID("41000000-0000-4000-8000-000000000391")


def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=USER_ID,
        login_id="Notification391",
        name="화면 알림 계약 사용자",
        email="notification-391@example.com",
        status=UserStatus.ACTIVE,
        email_verified_at=NOW,
        birth_date=date(1995, 5, 20),
        gender=Gender.FEMALE,
        height_cm=Decimal("165"),
        weight_kg=Decimal("55"),
        access_token_expires_at=NOW,
        refresh_token_expires_at=NOW,
    )


class StubNotificationService:
    def __init__(self, error: AppError | None = None) -> None:
        self.error = error
        self.list_calls: list[tuple[UUID, int, int]] = []
        self.read_calls: list[tuple[UUID, UUID]] = []

    def list_notifications(
        self, *, user_id: UUID, page: int, page_size: int
    ) -> NotificationListResult:
        self.list_calls.append((user_id, page, page_size))
        if self.error is not None:
            raise self.error
        return NotificationListResult(
            items=(
                NotificationListItem(
                    id=NOTIFICATION_ID,
                    care_item_id=ITEM_ID,
                    product_name="화면 알림 제품",
                    notification_type="REPURCHASE",
                    reference_date=date(2026, 8, 19),
                    trigger_days_before=5,
                    scheduled_at=datetime(2026, 8, 14, 0, 0, tzinfo=UTC),
                    created_at=NOW,
                    read_at=None,
                    is_read=False,
                ),
            ),
            page=page,
            page_size=page_size,
            total=1,
            has_next=False,
        )

    def mark_read(
        self, *, user_id: UUID, notification_id: UUID
    ) -> NotificationReadResult:
        self.read_calls.append((user_id, notification_id))
        if self.error is not None:
            raise self.error
        return NotificationReadResult(id=notification_id, read_at=NOW)


def contract_client(
    service: StubNotificationService, *, authenticated: bool = True
) -> TestClient:
    application = create_app(Settings(app_env="test"))
    application.dependency_overrides[get_notification_service] = lambda: cast(
        NotificationService, service
    )
    if authenticated:
        application.dependency_overrides[require_current_user] = current_user
    return TestClient(application)


def test_list_contract_returns_private_notification_page() -> None:
    service = StubNotificationService()

    with contract_client(service) as client:
        response = client.get("/api/v1/notifications")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "items": [
            {
                "id": str(NOTIFICATION_ID),
                "care_item_id": str(ITEM_ID),
                "product_name": "화면 알림 제품",
                "notification_type": "REPURCHASE",
                "reference_date": "2026-08-19",
                "trigger_days_before": 5,
                "scheduled_at": "2026-08-14T00:00:00Z",
                "created_at": "2026-08-14T00:30:00Z",
                "read_at": None,
                "is_read": False,
            }
        ],
        "page": 1,
        "page_size": 20,
        "total": 1,
        "has_next": False,
    }
    assert service.list_calls == [(USER_ID, 1, 20)]
    assert "user_id" not in response.text


def test_read_contract_is_bodyless_and_returns_read_time() -> None:
    service = StubNotificationService()

    with contract_client(service) as client:
        response = client.put(f"/api/v1/notifications/{NOTIFICATION_ID}/read")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "id": str(NOTIFICATION_ID),
        "read_at": "2026-08-14T00:30:00Z",
    }
    assert service.read_calls == [(USER_ID, NOTIFICATION_ID)]


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 0}, {"page_size": 101}])
def test_list_rejects_invalid_pagination(params: dict[str, int]) -> None:
    with contract_client(StubNotificationService()) as client:
        response = client.get("/api/v1/notifications", params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_notification_apis_require_authentication() -> None:
    with contract_client(StubNotificationService(), authenticated=False) as client:
        listed = client.get("/api/v1/notifications")
        read = client.put(f"/api/v1/notifications/{NOTIFICATION_ID}/read")

    assert listed.status_code == read.status_code == 401
    assert listed.json()["error"]["code"] == "AUTH_REQUIRED"
    assert read.json()["error"]["code"] == "AUTH_REQUIRED"


def test_list_exposes_safe_service_unavailable_contract() -> None:
    service = StubNotificationService(
        AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="서비스가 아직 준비되지 않았습니다.",
        )
    )

    with contract_client(service) as client:
        response = client.get("/api/v1/notifications")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_read_exposes_not_found_without_ownership_detail() -> None:
    service = StubNotificationService(
        AppError(
            status_code=404,
            code="NOTIFICATION_NOT_FOUND",
            message="알림을 찾을 수 없습니다.",
        )
    )

    with contract_client(service) as client:
        response = client.put(f"/api/v1/notifications/{NOTIFICATION_ID}/read")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"
