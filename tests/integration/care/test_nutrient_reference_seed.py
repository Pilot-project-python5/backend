from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from sqlalchemy import delete, func, select

from yeongyangkkuk.care.nutrient_reference_models import (
    NutrientReferenceValue,
    NutrientReferenceVersion,
)
from yeongyangkkuk.db.session import SessionFactory, engine
from yeongyangkkuk.seeding.runner import run_registered_seeds

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


def test_reference_seed_reuses_existing_version_natural_key() -> None:
    existing_id = UUID("36000000-0000-4000-8000-000000000001")
    with SessionFactory.begin() as session:
        version_ids = select(NutrientReferenceVersion.id).where(
            NutrientReferenceVersion.version == "KDRI-2025-20260316"
        )
        session.execute(
            delete(NutrientReferenceValue).where(
                NutrientReferenceValue.version_id.in_(version_ids)
            )
        )
        session.execute(
            delete(NutrientReferenceVersion).where(
                NutrientReferenceVersion.version == "KDRI-2025-20260316"
            )
        )
        session.add(
            NutrientReferenceVersion(
                id=existing_id,
                version="KDRI-2025-20260316",
                source_name="기존 로컬 기준 데이터",
                source_url="https://example.invalid/reference",
                published_on=date(2026, 3, 16),
                checksum="0" * 64,
                loaded_at=datetime(2026, 8, 14, tzinfo=UTC),
            )
        )

    run_registered_seeds(engine)

    with SessionFactory() as session:
        version = session.scalar(
            select(NutrientReferenceVersion).where(
                NutrientReferenceVersion.version == "KDRI-2025-20260316"
            )
        )
        assert version is not None
        assert version.id == existing_id
        assert (
            session.scalar(
                select(func.count())
                .select_from(NutrientReferenceValue)
                .where(NutrientReferenceValue.version_id == existing_id)
            )
            == 66
        )
