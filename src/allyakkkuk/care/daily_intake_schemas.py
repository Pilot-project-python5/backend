"""일일 예정 섭취량 HTTP 스키마."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from allyakkkuk.care.care_item_schemas import DecimalString

NutrientUnit = Literal["MG", "G", "MCG", "IU"]


class DailyIntakeNutrientResponse(BaseModel):
    nutrient_id: UUID
    nutrient_code: str
    nutrient_name: str
    daily_amount: DecimalString
    unit: NutrientUnit


class DailyIntakeResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "nutrients": [
                        {
                            "nutrient_id": ("23000000-0000-4000-8000-000000000001"),
                            "nutrient_code": "VITAMIN_C",
                            "nutrient_name": "비타민 C",
                            "daily_amount": "470",
                            "unit": "MG",
                        }
                    ]
                }
            ]
        }
    )

    nutrients: list[DailyIntakeNutrientResponse]
