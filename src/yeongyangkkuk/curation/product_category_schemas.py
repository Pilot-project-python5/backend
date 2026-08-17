"""제품 카테고리 공개 HTTP 스키마."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProductCategoryResponseItem(BaseModel):
    slug: str
    name: str


class ProductCategoryListResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {"slug": "all", "name": "전체"},
                        {"slug": "multivitamin", "name": "종합비타민"},
                        {"slug": "vitamin-b", "name": "비타민B군"},
                        {"slug": "vitamin-c", "name": "비타민C"},
                        {"slug": "omega-3", "name": "오메가3"},
                    ]
                }
            ]
        }
    )

    items: list[ProductCategoryResponseItem]
