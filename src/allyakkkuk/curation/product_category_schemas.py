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
                        {"slug": "vitamin", "name": "비타민"},
                        {"slug": "protein", "name": "단백질"},
                        {"slug": "omega-3", "name": "오메가3"},
                    ]
                }
            ]
        }
    )

    items: list[ProductCategoryResponseItem]
