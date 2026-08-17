from __future__ import annotations

from pathlib import Path

import pytest

from yeongyangkkuk.care.nutrient_reference_csv import (
    NutrientReferenceCsvError,
    load_reference_csv,
)

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.6")]


def test_loads_checked_in_reference_csv() -> None:
    document = load_reference_csv(
        Path("data/reference/nutrient_reference_kdri_2025.csv")
    )
    assert document.version == "KDRI-2025-20260316"
    assert len(document.rows) == 66
    assert len(document.checksum) == 64


@pytest.mark.parametrize("mutation", ["duplicate", "overlap", "unit", "metadata"])
def test_rejects_invalid_reference_csv_before_loading(
    tmp_path: Path, mutation: str
) -> None:
    header = (
        "version,source_name,source_url,published_on,nutrient_code,gender,"
        "age_min,age_max,reference_type,reference_amount,unit\n"
    )
    row = "KDRI-2025-20260316,기준,https://example.com,2026-03-16,VITAMIN_C,FEMALE,19,29,RNI,100,MG\n"
    second = {
        "duplicate": row,
        "overlap": "KDRI-2025-20260316,기준,https://example.com,2026-03-16,VITAMIN_C,FEMALE,25,39,RNI,100,MG\n",
        "unit": "KDRI-2025-20260316,기준,https://example.com,2026-03-16,VITAMIN_C,MALE,19,29,RNI,100,KG\n",
        "metadata": "OTHER,기준,https://example.com,2026-03-16,VITAMIN_C,MALE,19,29,RNI,100,MG\n",
    }[mutation]
    path = tmp_path / "bad.csv"
    path.write_text(header + row + second, encoding="utf-8")

    with pytest.raises(NutrientReferenceCsvError):
        load_reference_csv(path)
