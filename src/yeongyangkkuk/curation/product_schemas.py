"""추천 제품 목록과 상세 HTTP 스키마."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DecimalString = Annotated[str, Field(pattern=r"^(?:0|[1-9]\d*)(?:\.\d+)?$")]
UnitForm = Literal["TABLET", "CAPSULE", "SCOOP", "PACKET"]
NutrientUnit = Literal["MG", "G", "MCG", "IU"]


def decimal_string(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


class ProductListItemResponse(BaseModel):
    id: UUID
    sku: str
    product_type: str
    brand: str
    name: str
    image_url: str
    display_price: int
    currency: Literal["KRW"] = "KRW"
    category_slugs: list[str]


class ProductListResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": "22000000-0000-4000-8000-000000000101",
                            "sku": "KORYO-EUNDAN-MULTIVITAMIN-ALL-IN-ONE",
                            "product_type": "SUPPLEMENT",
                            "brand": "고려은단",
                            "name": "고려은단 멀티비타민 올인원",
                            "image_url": (
                                "/static/products/"
                                "koryo-eundan-multivitamin-all-in-one.webp"
                            ),
                            "display_price": 0,
                            "currency": "KRW",
                            "category_slugs": ["multivitamin"],
                        }
                    ],
                    "page": 1,
                    "page_size": 20,
                    "total": 32,
                    "has_next": True,
                }
            ]
        }
    )

    items: list[ProductListItemResponse]
    page: int
    page_size: int
    total: int
    has_next: bool


class ProductPackageResponse(BaseModel):
    unit_form: UnitForm
    units_per_package: DecimalString


class ProductNutrientResponse(BaseModel):
    code: str
    name: str
    amount_per_unit: DecimalString
    unit: NutrientUnit


class ExpertCommentResponse(BaseModel):
    id: UUID
    author_label: str
    content: str


class ProductDetailResponse(ProductListItemResponse):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "22000000-0000-4000-8000-000000000101",
                    "sku": "KORYO-EUNDAN-MULTIVITAMIN-ALL-IN-ONE",
                    "product_type": "SUPPLEMENT",
                    "brand": "고려은단",
                    "name": "고려은단 멀티비타민 올인원",
                    "image_url": (
                        "/static/products/koryo-eundan-multivitamin-all-in-one.webp"
                    ),
                    "display_price": 0,
                    "currency": "KRW",
                    "category_slugs": ["multivitamin"],
                    "package": {
                        "unit_form": "TABLET",
                        "units_per_package": "60",
                    },
                    "nutrients": [
                        {
                            "code": "VITAMIN_C",
                            "name": "비타민 C",
                            "amount_per_unit": "100",
                            "unit": "MG",
                        }
                    ],
                    "expert_comments": [
                        {
                            "id": "24000000-0000-4000-8000-000000000101",
                            "author_label": "MJ's COMMENT",
                            "content": "종합비타민 카테고리 안내와 섭취 주의사항",
                        }
                    ],
                }
            ]
        }
    )

    package: ProductPackageResponse
    nutrients: list[ProductNutrientResponse]
    expert_comments: list[ExpertCommentResponse]
