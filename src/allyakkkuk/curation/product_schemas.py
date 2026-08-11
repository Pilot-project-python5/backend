"""추천 제품 목록 HTTP 스키마."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
                            "id": "22000000-0000-4000-8000-000000000001",
                            "sku": "LIFE-TWO-PER-DAY",
                            "product_type": "SUPPLEMENT",
                            "brand": "Life Extension",
                            "name": "라이프익스텐션 투퍼데이",
                            "image_url": (
                                "/static/products/life-extension-two-per-day.svg"
                            ),
                            "display_price": 28400,
                            "currency": "KRW",
                            "category_slugs": ["vitamin"],
                        }
                    ],
                    "page": 1,
                    "page_size": 20,
                    "total": 3,
                    "has_next": False,
                }
            ]
        }
    )

    items: list[ProductListItemResponse]
    page: int
    page_size: int
    total: int
    has_next: bool
