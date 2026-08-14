"""영양성분 현황 HTTP 스키마."""

from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from allyakkkuk.care.care_item_schemas import DecimalString
from allyakkkuk.care.daily_intake_schemas import NutrientUnit


class NutrientStatusItemResponse(BaseModel):
    nutrient_id: UUID
    nutrient_code: str
    nutrient_name: str
    daily_amount: DecimalString
    unit: NutrientUnit
    reference_available: bool
    reference_amount: DecimalString | None
    reference_type: Literal["RNI", "AI"] | None
    achievement_rate_percent: DecimalString | None


class NutrientStatusResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "등록된 보충제 복용 계획이 총 식이 기준량에서 차지하는 비교이며 "
                "실제 식사량·임상 판정이 아닙니다."
            )
        }
    )
    as_of_date: date
    age: int
    gender: Literal["MALE", "FEMALE"]
    reference_version: str
    reference_source_name: str
    reference_source_url: str
    nutrients: list[NutrientStatusItemResponse]
