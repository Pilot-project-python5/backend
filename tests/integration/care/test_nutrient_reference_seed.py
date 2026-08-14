from __future__ import annotations

import pytest
from sqlalchemy import func, select

from allyakkkuk.care.nutrient_reference_models import (
    NutrientReferenceValue,
    NutrientReferenceVersion,
)
from allyakkkuk.db.session import SessionFactory, engine
from allyakkkuk.seeding.runner import run_registered_seeds

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.6")]


def test_reference_seed_is_complete_and_idempotent() -> None:
    run_registered_seeds(engine)
    run_registered_seeds(engine)

    with SessionFactory() as session:
        version = session.scalar(
            select(NutrientReferenceVersion).where(
                NutrientReferenceVersion.version == "KDRI-2025-20260316"
            )
        )
        assert version is not None
        assert len(version.checksum) == 64
        assert (
            session.scalar(
                select(func.count())
                .select_from(NutrientReferenceValue)
                .where(NutrientReferenceValue.version_id == version.id)
            )
            == 66
        )
