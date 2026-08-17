from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select

from yeongyangkkuk.curation.models import Product
from yeongyangkkuk.db.session import SessionFactory, engine
from yeongyangkkuk.medication.models import MedicationDetail
from yeongyangkkuk.medication.seeds import MEDICATION_SEED_ROWS, MedicationSeedSet

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.10")]


def test_medication_seed_is_deterministic_idempotent_and_has_local_images() -> None:
    seed_set = MedicationSeedSet()
    with engine.begin() as connection:
        assert seed_set.apply(connection) == 2
        assert seed_set.apply(connection) == 2

    seed_ids = tuple(row.id for row in MEDICATION_SEED_ROWS)
    with SessionFactory() as session:
        products = tuple(
            session.execute(
                select(Product)
                .where(Product.id.in_(seed_ids))
                .order_by(Product.sort_order)
            ).scalars()
        )
        details = tuple(
            session.execute(
                select(MedicationDetail).where(
                    MedicationDetail.product_id.in_(seed_ids)
                )
            ).scalars()
        )
        count = session.scalar(
            select(func.count())
            .select_from(MedicationDetail)
            .where(MedicationDetail.product_id.in_(seed_ids))
        )

    assert len(products) == len(details) == count == 2
    assert all(product.product_type == "MEDICATION" for product in products)
    assert {detail.classification for detail in details} == {"OTC", "PRESCRIPTION"}
    static_root = Path("src/yeongyangkkuk/static")
    assert all(
        (static_root / row.image_url.removeprefix("/static/")).is_file()
        for row in MEDICATION_SEED_ROWS
    )
