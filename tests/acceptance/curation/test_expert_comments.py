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

PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000001")


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
            "id": "24000000-0000-4000-8000-000000000001",
            "author_label": "MJ's COMMENT",
            "content": (
                "비타민 B군의 함량 구성이 안정적인 개발용 추천 제품입니다. "
                "개인별 건강 상태에 따라 선택 기준은 달라질 수 있습니다."
            ),
        }
    ]
