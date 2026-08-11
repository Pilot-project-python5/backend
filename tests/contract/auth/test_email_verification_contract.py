from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from allyakkkuk.auth.email_verification_router import get_email_verification_service
from allyakkkuk.auth.email_verification_service import (
    EmailVerificationIssueResult,
    EmailVerificationService,
    EmailVerificationSuccessResult,
)
from allyakkkuk.auth.models import UserStatus
from allyakkkuk.core.config import Settings
from allyakkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-1.1.3")]

USER_ID = UUID("11111111-1111-4111-8111-111111111111")
VERIFICATION_ID = UUID("22222222-2222-4222-8222-222222222222")


class StubEmailVerificationService:
    def issue(self, user_id: UUID) -> EmailVerificationIssueResult:
        assert user_id == USER_ID
        return EmailVerificationIssueResult(
            verification_id=VERIFICATION_ID,
            expires_at=datetime(2026, 8, 11, 9, 10, tzinfo=UTC),
            resend_available_at=datetime(2026, 8, 11, 9, 1, tzinfo=UTC),
        )

    def resend(self, user_id: UUID) -> EmailVerificationIssueResult:
        return self.issue(user_id)

    def confirm(
        self, verification_id: UUID, code: str
    ) -> EmailVerificationSuccessResult:
        assert verification_id == VERIFICATION_ID
        assert code == "123456"
        return EmailVerificationSuccessResult(
            user_id=USER_ID,
            status=UserStatus.ACTIVE,
            email_verified_at=datetime(2026, 8, 11, 9, 0, tzinfo=UTC),
        )


def contract_client() -> TestClient:
    application = create_app(Settings(app_env="test"))
    stub = cast(EmailVerificationService, StubEmailVerificationService())
    application.dependency_overrides[get_email_verification_service] = lambda: stub
    return TestClient(application)


def test_issue_and_resend_success_contracts() -> None:
    for path in ("/email-verifications", "/email-verifications/resend"):
        with contract_client() as client:
            response = client.post(
                f"/api/v1/auth{path}", json={"user_id": str(USER_ID)}
            )

        assert response.status_code == 201
        assert response.json() == {
            "verification_id": str(VERIFICATION_ID),
            "expires_at": "2026-08-11T09:10:00Z",
            "resend_available_at": "2026-08-11T09:01:00Z",
        }


def test_confirm_success_contract() -> None:
    with contract_client() as client:
        response = client.post(
            "/api/v1/auth/email-verifications/confirm",
            json={"verification_id": str(VERIFICATION_ID), "code": "123456"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(USER_ID),
        "status": "ACTIVE",
        "email_verified_at": "2026-08-11T09:00:00Z",
    }


@pytest.mark.parametrize(
    "code",
    ["12345", "1234567", "abcdef", "\uff11\uff12\uff13\uff14\uff15\uff16"],
)
def test_confirm_rejects_non_ascii_six_digit_code(code: str) -> None:
    with contract_client() as client:
        response = client.post(
            "/api/v1/auth/email-verifications/confirm",
            json={"verification_id": str(VERIFICATION_ID), "code": code},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_openapi_documents_email_verification_contract_and_errors() -> None:
    application = create_app(Settings(app_env="test"))
    paths = application.openapi()["paths"]

    issue = paths["/api/v1/auth/email-verifications"]["post"]
    resend = paths["/api/v1/auth/email-verifications/resend"]["post"]
    confirm = paths["/api/v1/auth/email-verifications/confirm"]["post"]

    assert issue["operationId"] == "auth_issue_email_verification"
    assert resend["operationId"] == "auth_resend_email_verification"
    assert confirm["operationId"] == "auth_confirm_email_verification"
    assert set(issue["responses"]) >= {"201", "404", "409", "429", "422", "503"}
    assert set(confirm["responses"]) >= {
        "200",
        "400",
        "404",
        "409",
        "410",
        "429",
        "422",
        "503",
    }
