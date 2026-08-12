"""복용 제품 등록 HTTP 스키마."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MAX_QUANTITY = Decimal("999999999.999")
QuantityUnit = Literal["TABLET", "CAPSULE", "SCOOP", "PACKET"]


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


class CareItemResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "31000000-0000-4000-8000-000000000001",
                    "product_id": "22000000-0000-4000-8000-000000000001",
                    "purchase_date": "2026-08-10",
                    "intake_start_date": "2026-08-12",
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
    total_quantity: Decimal
    quantity_unit: QuantityUnit
    dose_per_intake: Decimal
    intakes_per_day: int
    created_at: datetime
