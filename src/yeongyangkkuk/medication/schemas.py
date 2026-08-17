"""의약품 목록·상세 HTTP 스키마."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DecimalString = Annotated[str, Field(pattern=r"^(?:0|[1-9]\d*)(?:\.\d+)?$")]
UnitForm = Literal["TABLET", "CAPSULE", "SCOOP", "PACKET"]
MedicationClassification = Literal["OTC", "PRESCRIPTION"]


class MedicationPackageResponse(BaseModel):
    unit_form: UnitForm
    units_per_package: DecimalString


class MedicationListItemResponse(BaseModel):
    id: UUID
    sku: str
    brand: str
    name: str
    image_url: str
    package: MedicationPackageResponse
    permit_code: str
    classification: MedicationClassification
    active_ingredients: str


class MedicationListResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": "22000000-0000-4000-8000-000000000010",
                            "sku": "LOCAL-MED-001",
                            "brand": "영양꾹 로컬 테스트",
                            "name": "복용 관리 예시 의약품 A",
                            "image_url": "/static/products/local-medication-a.svg",
                            "package": {
                                "unit_form": "TABLET",
                                "units_per_package": "20",
                            },
                            "permit_code": "LOCAL-MED-001",
                            "classification": "OTC",
                            "active_ingredients": "개발용 예시 성분 A",
                        }
                    ],
                    "page": 1,
                    "page_size": 20,
                    "total": 2,
                    "has_next": False,
                }
            ]
        }
    )

    items: list[MedicationListItemResponse]
    page: int
    page_size: int
    total: int
    has_next: bool


class MedicationSourceResponse(BaseModel):
    name: str
    url: str
    reviewed_on: date


class MedicationDetailResponse(MedicationListItemResponse):
    efficacy: str
    dosage_instructions: str
    precautions: str
    storage_instructions: str
    source: MedicationSourceResponse
