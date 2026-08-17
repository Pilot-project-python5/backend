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
from yeongyangkkuk.medication.router import get_medication_service
from yeongyangkkuk.medication.service import (
    MedicationDetail,
    MedicationPage,
    MedicationService,
    MedicationSummary,
)

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-3.10")]

NOW = datetime(2026, 8, 14, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000310")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000010")


def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        USER_ID,
        "Medication310",
        "의약품 사용자",
        "medication310@example.com",
        UserStatus.ACTIVE,
        NOW,
        date(1990, 1, 1),
        Gender.FEMALE,
        Decimal("165"),
        Decimal("55"),
        NOW,
        NOW,
    )


def summary() -> MedicationSummary:
    return MedicationSummary(
        PRODUCT_ID,
        "LOCAL-MED-001",
        "영양꾹 로컬 테스트",
        "복용 관리 예시 의약품 A",
        "/static/products/local-medication-a.svg",
        "TABLET",
        Decimal("20.00"),
        "LOCAL-MED-001",
        "OTC",
        "개발용 예시 성분 A — 실사용 금지",
    )


def detail() -> MedicationDetail:
    item = summary()
    return MedicationDetail(
        item.id,
        item.sku,
        item.brand,
        item.name,
        item.image_url,
        item.unit_form,
        item.units_per_package,
        item.permit_code,
        item.classification,
        item.active_ingredients,
        "실제 의약품 정보가 아닌 로컬 테스트 문구입니다.",
        "실제 복용에 사용하지 마세요.",
        "API·UI 검증에만 사용하세요.",
        "로컬 테스트 데이터입니다.",
        "영양꾹 로컬 테스트 시드(실사용 금지)",
        "https://example.invalid/yeongyangkkuk/medications/local-med-001",
        date(2026, 8, 14),
    )


class StubMedicationService:
    def list_medications(self, *, page: int, page_size: int) -> MedicationPage:
        return MedicationPage((summary(),), page, page_size, 1, False)

    def get_medication(self, product_id: UUID) -> MedicationDetail:
        assert product_id == PRODUCT_ID
        return detail()


class ErrorMedicationService(StubMedicationService):
    def __init__(self, error: AppError) -> None:
        self.error = error

    def get_medication(self, product_id: UUID) -> MedicationDetail:
        raise self.error


def contract_client(service: object, *, authenticated: bool = True) -> TestClient:
    app = create_app(Settings(app_env="test"))
    if authenticated:
        app.dependency_overrides[require_current_user] = current_user
    app.dependency_overrides[get_medication_service] = lambda: cast(
        MedicationService, service
    )
    return TestClient(app)


def test_list_contract_serializes_decimal_and_private_headers() -> None:
    with contract_client(StubMedicationService()) as client:
        response = client.get("/api/v1/medications")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "items": [
            {
                "id": str(PRODUCT_ID),
                "sku": "LOCAL-MED-001",
                "brand": "영양꾹 로컬 테스트",
                "name": "복용 관리 예시 의약품 A",
                "image_url": "/static/products/local-medication-a.svg",
                "package": {"unit_form": "TABLET", "units_per_package": "20"},
                "permit_code": "LOCAL-MED-001",
                "classification": "OTC",
                "active_ingredients": "개발용 예시 성분 A — 실사용 금지",
            }
        ],
        "page": 1,
        "page_size": 20,
        "total": 1,
        "has_next": False,
    }


def test_detail_contract_includes_source_and_required_information() -> None:
    with contract_client(StubMedicationService()) as client:
        response = client.get(f"/api/v1/medications/{PRODUCT_ID}")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["efficacy"].startswith("실제 의약품 정보가 아닌")
    assert body["dosage_instructions"] == "실제 복용에 사용하지 마세요."
    assert body["source"] == {
        "name": "영양꾹 로컬 테스트 시드(실사용 금지)",
        "url": "https://example.invalid/yeongyangkkuk/medications/local-med-001",
        "reviewed_on": "2026-08-14",
    }


def test_list_requires_authentication() -> None:
    with contract_client(StubMedicationService(), authenticated=False) as client:
        response = client.get("/api/v1/medications")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (
            AppError(
                status_code=404,
                code="MEDICATION_NOT_FOUND",
                message="의약품을 찾을 수 없습니다.",
            ),
            404,
            "MEDICATION_NOT_FOUND",
        ),
        (
            AppError(
                status_code=503,
                code="SERVICE_UNAVAILABLE",
                message="서비스가 준비되지 않았습니다.",
            ),
            503,
            "SERVICE_UNAVAILABLE",
        ),
    ],
)
def test_detail_uses_common_error_contract(
    error: AppError, status: int, code: str
) -> None:
    with contract_client(ErrorMedicationService(error)) as client:
        response = client.get(f"/api/v1/medications/{PRODUCT_ID}")

    assert response.status_code == status
    assert response.json()["error"]["code"] == code


@pytest.mark.parametrize(
    "url",
    ["/api/v1/medications?page=0", "/api/v1/medications/not-a-uuid"],
)
def test_invalid_input_uses_validation_contract(url: str) -> None:
    with contract_client(StubMedicationService()) as client:
        response = client.get(url)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_openapi_documents_protected_medication_operations() -> None:
    schema = create_app(Settings(app_env="test")).openapi()
    listing = schema["paths"]["/api/v1/medications"]["get"]
    detail_operation = schema["paths"]["/api/v1/medications/{product_id}"]["get"]

    assert listing["operationId"] == "medication_list_catalog"
    assert detail_operation["operationId"] == "medication_get_catalog_item"
    assert listing["security"] == [{"AccessCookieAuth": []}]
    assert detail_operation["security"] == [{"AccessCookieAuth": []}]
    assert set(listing["responses"]) >= {"200", "401", "422", "503"}
    assert set(detail_operation["responses"]) >= {
        "200",
        "401",
        "404",
        "422",
        "503",
    }
