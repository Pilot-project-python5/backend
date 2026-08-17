from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import delete, select, update

from yeongyangkkuk.care.nutrient_reference_models import NutrientReferenceVersion
from yeongyangkkuk.curation.models import (
    Nutrient,
    Product,
    ProductCategory,
    ProductCategoryMapping,
    ProductNutrient,
)
from yeongyangkkuk.curation.product_nutrient_seeds import (
    NUTRIENT_SEED_ROWS,
    PRODUCT_NUTRIENT_SEED_ROWS,
    ProductNutrientSeedSet,
)
from yeongyangkkuk.curation.product_seeds import ProductSeedSet
from yeongyangkkuk.curation.seeds import ProductCategorySeedSet
from yeongyangkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-2.4")]


@pytest.fixture(autouse=True)
def clean_catalog() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(NutrientReferenceVersion))
        session.execute(delete(ProductNutrient))
        session.execute(delete(Nutrient))
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))
    yield
    with SessionFactory.begin() as session:
        session.execute(delete(NutrientReferenceVersion))
        session.execute(delete(ProductNutrient))
        session.execute(delete(Nutrient))
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))


def test_nutrient_seed_is_deterministic_idempotent_and_restores_mappings() -> None:
    with engine.begin() as connection:
        ProductCategorySeedSet().apply(connection)
        ProductSeedSet().apply(connection)
        seed = ProductNutrientSeedSet()
        assert seed.apply(connection) == len(NUTRIENT_SEED_ROWS)
        connection.execute(
            update(Nutrient)
            .where(Nutrient.code == NUTRIENT_SEED_ROWS[0].code)
            .values(name="변경됨", canonical_unit="IU", is_active=False)
        )
        connection.execute(delete(ProductNutrient))
        assert seed.apply(connection) == len(NUTRIENT_SEED_ROWS)
        assert seed.apply(connection) == len(NUTRIENT_SEED_ROWS)

    with SessionFactory() as session:
        stored_nutrients = tuple(
            session.execute(select(Nutrient).order_by(Nutrient.code)).scalars()
        )
        stored_mappings = tuple(
            session.execute(
                select(
                    Product.sku,
                    Nutrient.code,
                    ProductNutrient.amount_per_unit,
                    ProductNutrient.unit,
                    ProductNutrient.sort_order,
                )
                .join(ProductNutrient, ProductNutrient.product_id == Product.id)
                .join(Nutrient, Nutrient.id == ProductNutrient.nutrient_id)
                .order_by(Product.sku, ProductNutrient.sort_order, Nutrient.code)
            )
        )

    assert [
        (item.id, item.code, item.name, item.canonical_unit, item.is_active)
        for item in stored_nutrients
    ] == [
        (row.id, row.code, row.name, row.canonical_unit, True)
        for row in sorted(NUTRIENT_SEED_ROWS, key=lambda value: value.code)
    ]
    assert stored_mappings == tuple(
        (
            row.product_sku,
            row.nutrient_code,
            row.amount_per_unit,
            row.unit,
            row.sort_order,
        )
        for row in sorted(
            PRODUCT_NUTRIENT_SEED_ROWS,
            key=lambda value: (
                value.product_sku,
                value.sort_order,
                value.nutrient_code,
            ),
        )
    )
