"""복용 제품 등록 HTTP 스키마."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MAX_QUANTITY = Decimal("999999999.999")
QuantityUnit = Literal["TABLET", "CAPSULE", "SCOOP", "PACKET"]
ProductType = Literal["SUPPLEMENT", "MEDICATION"]
DecimalString = Annotated[str, Field(pattern=r"^(?:0|[1-9]\d*)(?:\.\d+)?$")]
ExpirationStatus = Literal["NORMAL", "EXPIRING_SOON", "EXPIRED"]
InventoryStatus = Literal["NORMAL", "LOW_STOCK", "DEPLETED"]


def decimal_string(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


class CareItemCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "product_id": "22000000-0000-4000-8000-000000000001",
                    "purchase_date": "2026-08-10",
                    "intake_start_date": "2026-08-12",
                    "total_quantity": "60",
                    "dose_per_intake": "1",
                    "intakes_per_day": 2,
                }
            ]
        }
    )

    product_id: UUID
    purchase_date: date
    intake_start_date: date
    total_quantity: Decimal = Field(
        gt=0,
        le=MAX_QUANTITY,
        max_digits=12,
        decimal_places=3,
    )
    dose_per_intake: Decimal = Field(
        gt=0,
        le=MAX_QUANTITY,
        max_digits=12,
        decimal_places=3,
    )
    intakes_per_day: int = Field(ge=1, le=24)
    expiration_date: date | None = None


class CareItemResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "31000000-0000-4000-8000-000000000001",
                    "product_id": "22000000-0000-4000-8000-000000000001",
                    "purchase_date": "2026-08-10",
                    "intake_start_date": "2026-08-12",
                    "expected_depletion_date": "2026-09-10",
                    "total_quantity": "60",
                    "quantity_unit": "CAPSULE",
                    "dose_per_intake": "1",
                    "intakes_per_day": 2,
                    "created_at": "2026-08-12T09:00:00Z",
                }
            ]
        }
    )

    id: UUID
    product_id: UUID
    purchase_date: date
    intake_start_date: date
    expected_depletion_date: date
    total_quantity: Decimal
    quantity_unit: QuantityUnit
    dose_per_intake: Decimal
    intakes_per_day: int
    created_at: datetime
    expiration_date: date | None


class CareItemListItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_type: ProductType
    brand: str
    name: str
    image_url: str
    purchase_date: date
    intake_start_date: date
    expected_depletion_date: date
    total_quantity: DecimalString
    quantity_unit: QuantityUnit
    dose_per_intake: DecimalString
    intakes_per_day: int
    days_until_depletion: int
    inventory_status: InventoryStatus
    created_at: datetime
    expiration_date: date | None
    days_until_expiration: int | None
    expiration_status: ExpirationStatus | None


class CareItemListResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": "31000000-0000-4000-8000-000000000001",
                            "product_id": "22000000-0000-4000-8000-000000000001",
                            "product_type": "SUPPLEMENT",
                            "brand": "Life Extension",
                            "name": "라이프익스텐션 투퍼데이",
                            "image_url": (
                                "/static/products/life-extension-two-per-day.svg"
                            ),
                            "purchase_date": "2026-08-10",
                            "intake_start_date": "2026-08-12",
                            "expected_depletion_date": "2026-09-10",
                            "total_quantity": "60",
                            "quantity_unit": "CAPSULE",
                            "dose_per_intake": "1",
                            "intakes_per_day": 2,
                            "days_until_depletion": 28,
                            "created_at": "2026-08-13T09:00:00Z",
                        }
                    ],
                    "page": 1,
                    "page_size": 20,
                    "total": 1,
                    "has_next": False,
                }
            ]
        }
    )

    items: list[CareItemListItemResponse]
    page: int
    page_size: int
    total: int
    has_next: bool


class CareItemExpirationUpdateRequest(BaseModel):
    expiration_date: date


class CareItemExpirationResponse(BaseModel):
    care_item_id: UUID
    expiration_date: date
