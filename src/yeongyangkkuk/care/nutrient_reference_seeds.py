"""공식 영양소 기준 CSV의 검증·멱등 적재."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import Connection, delete, select
from sqlalchemy.dialects.postgresql import insert

from yeongyangkkuk.care.nutrient_reference_csv import load_reference_csv
from yeongyangkkuk.care.nutrient_reference_models import (
    NutrientReferenceValue,
    NutrientReferenceVersion,
)
from yeongyangkkuk.curation.models import Nutrient

REFERENCE_CSV_PATH = (
    Path(__file__).resolve().parents[3]
    / "data/reference/nutrient_reference_kdri_2025.csv"
)
REFERENCE_LOADED_AT = datetime(2026, 8, 14, tzinfo=UTC)


class NutrientReferenceSeedSet:
    name = "nutrient_references"

    def __init__(self, path: Path = REFERENCE_CSV_PATH) -> None:
        self._path = path

    def apply(self, connection: Connection) -> int:
        document = load_reference_csv(self._path)
        codes = {row.nutrient_code for row in document.rows}
        nutrients = {
            code: (nutrient_id, unit)
            for nutrient_id, code, unit in connection.execute(
                select(Nutrient.id, Nutrient.code, Nutrient.canonical_unit).where(
                    Nutrient.code.in_(codes)
                )
            )
        }
        if missing := sorted(codes - set(nutrients)):
            raise ValueError(f"기준 CSV에 필요한 성분이 없습니다: {missing}")
        if invalid := sorted(
            {
                row.nutrient_code
                for row in document.rows
                if nutrients[row.nutrient_code][1] != row.unit
            }
        ):
            raise ValueError(f"성분 기준 단위와 CSV 단위가 다릅니다: {invalid}")

        version_id = uuid5(
            NAMESPACE_URL, f"yeongyangkkuk:nutrient-reference:{document.version}"
        )
        statement = insert(NutrientReferenceVersion).values(
            id=version_id,
            version=document.version,
            source_name=document.source_name,
            source_url=document.source_url,
            published_on=document.published_on,
            checksum=document.checksum,
            loaded_at=REFERENCE_LOADED_AT,
        )
        persisted_version_id = connection.scalar(
            statement.on_conflict_do_update(
                index_elements=[NutrientReferenceVersion.version],
                set_={
                    "source_name": statement.excluded.source_name,
                    "source_url": statement.excluded.source_url,
                    "published_on": statement.excluded.published_on,
                    "checksum": statement.excluded.checksum,
                    "loaded_at": statement.excluded.loaded_at,
                },
            ).returning(NutrientReferenceVersion.id)
        )
        if persisted_version_id is None:
            raise ValueError("영양소 기준 버전 식별자를 확인할 수 없습니다.")
        connection.execute(
            delete(NutrientReferenceValue).where(
                NutrientReferenceValue.version_id == persisted_version_id
            )
        )
        connection.execute(
            insert(NutrientReferenceValue).values(
                [
                    {
                        "id": uuid5(
                            NAMESPACE_URL,
                            f"yeongyangkkuk:{document.version}:{row.nutrient_code}:{row.gender}:{row.age_min}:{row.age_max}:{row.reference_type}",
                        ),
                        "version_id": persisted_version_id,
                        "nutrient_id": nutrients[row.nutrient_code][0],
                        "gender": row.gender,
                        "age_min": row.age_min,
                        "age_max": row.age_max,
                        "reference_type": row.reference_type,
                        "reference_amount": row.reference_amount,
                        "unit": row.unit,
                    }
                    for row in document.rows
                ]
            )
        )
        return len(document.rows)
