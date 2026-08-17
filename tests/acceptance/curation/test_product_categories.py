from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from allyakkkuk.curation.models import ProductCategory
from allyakkkuk.curation.seeds import ProductCategorySeedSet
from allyakkkuk.db.session import SessionFactory, engine
from allyakkkuk.main import app

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-2.2")]


@pytest.fixture(autouse=True)
def seeded_categories() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(ProductCategory))
    with engine.begin() as connection:
        ProductCategorySeedSet().apply(connection)
    yield
    with SessionFactory.begin() as session:
        session.execute(delete(ProductCategory))


def test_public_category_list_matches_seeded_display_order() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/curation/categories")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"slug": "all", "name": "전체"},
            {"slug": "multivitamin", "name": "종합비타민"},
            {"slug": "vitamin-b", "name": "비타민B군"},
            {"slug": "vitamin-c", "name": "비타민C"},
            {"slug": "vitamin-d", "name": "비타민D"},
            {"slug": "protein-supplement", "name": "단백질 보충제"},
            {"slug": "pre-workout", "name": "부스터"},
            {"slug": "creatine", "name": "크레아틴"},
            {"slug": "probiotics", "name": "유산균"},
            {"slug": "omega-3", "name": "오메가3"},
            {"slug": "magnesium", "name": "마그네슘"},
            {"slug": "melatonin", "name": "멜라토닌"},
        ]
    }
