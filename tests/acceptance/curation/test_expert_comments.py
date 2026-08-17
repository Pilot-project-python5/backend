from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from allyakkkuk.curation.expert_comment_seeds import ExpertCommentSeedSet
from allyakkkuk.curation.models import (
    ExpertComment,
    Product,
    ProductCategory,
    ProductCategoryMapping,
)
from allyakkkuk.curation.product_seeds import ProductSeedSet
from allyakkkuk.curation.seeds import ProductCategorySeedSet
from allyakkkuk.db.session import SessionFactory, engine
from allyakkkuk.main import app

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-2.4.1")]

PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000101")


@pytest.fixture(autouse=True)
def seeded_comments() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(ExpertComment))
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))
    with engine.begin() as connection:
        ProductCategorySeedSet().apply(connection)
        ProductSeedSet().apply(connection)
        ExpertCommentSeedSet().apply(connection)
    yield
    with SessionFactory.begin() as session:
        session.execute(delete(ExpertComment))
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))


def test_visitor_reads_seeded_expert_comment_in_product_detail() -> None:
    with TestClient(app) as client:
        response = client.get(f"/api/v1/curation/products/{PRODUCT_ID}")

    assert response.status_code == 200
    assert response.json()["expert_comments"] == [
        {
            "id": "24000000-0000-4000-8000-000000000101",
            "author_label": "MJ's COMMENT",
            "content": (
                "전반적인 일상 컨디션 유지와 식사로 부족한 여러 비타민·미네랄 "
                "보충을 돕습니다. 다른 비타민 제품과 함께 섭취할 때 같은 영양소의 "
                "중복과 과다 섭취를 확인하세요."
            ),
        }
    ]
