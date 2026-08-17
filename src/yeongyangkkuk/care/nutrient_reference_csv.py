"""영양소 섭취기준 CSV의 전체 파일 검증."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

HEADERS = (
    "version",
    "source_name",
    "source_url",
    "published_on",
    "nutrient_code",
    "gender",
    "age_min",
    "age_max",
    "reference_type",
    "reference_amount",
    "unit",
)
ALLOWED_GENDERS = {"MALE", "FEMALE"}
ALLOWED_REFERENCE_TYPES = {"RNI", "AI"}
ALLOWED_UNITS = {"MG", "G", "MCG", "IU"}


class NutrientReferenceCsvError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class NutrientReferenceCsvRow:
    nutrient_code: str
    gender: str
    age_min: int
    age_max: int
    reference_type: str
    reference_amount: Decimal
    unit: str


@dataclass(frozen=True, slots=True)
class NutrientReferenceCsvDocument:
    version: str
    source_name: str
    source_url: str
    published_on: date
    checksum: str
    rows: tuple[NutrientReferenceCsvRow, ...]


def load_reference_csv(path: Path) -> NutrientReferenceCsvDocument:
    raw = path.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != HEADERS:
            raise NutrientReferenceCsvError("CSV 열 계약이 일치하지 않습니다.")
        source_rows = list(reader)
    if not source_rows:
        raise NutrientReferenceCsvError("기준 데이터가 비어 있습니다.")

    metadata: tuple[str, str, str, date] | None = None
    rows: list[NutrientReferenceCsvRow] = []
    exact_keys: set[tuple[str, str, int, int, str]] = set()
    ranges: dict[tuple[str, str, str], list[tuple[int, int]]] = {}
    try:
        for number, source in enumerate(source_rows, start=2):
            current_metadata = (
                source["version"].strip(),
                source["source_name"].strip(),
                source["source_url"].strip(),
                date.fromisoformat(source["published_on"].strip()),
            )
            if not all(current_metadata[:3]) or not current_metadata[2].startswith(
                "https://"
            ):
                raise NutrientReferenceCsvError(
                    f"{number}행 메타데이터가 올바르지 않습니다."
                )
            if metadata is None:
                metadata = current_metadata
            elif metadata != current_metadata:
                raise NutrientReferenceCsvError("버전 메타데이터가 일관되지 않습니다.")

            code = source["nutrient_code"].strip()
            gender = source["gender"].strip()
            reference_type = source["reference_type"].strip()
            unit = source["unit"].strip()
            age_min = int(source["age_min"])
            age_max = int(source["age_max"])
            amount = Decimal(source["reference_amount"])
            if (
                not code
                or gender not in ALLOWED_GENDERS
                or reference_type not in ALLOWED_REFERENCE_TYPES
                or unit not in ALLOWED_UNITS
            ):
                raise NutrientReferenceCsvError(
                    f"{number}행의 허용 값이 올바르지 않습니다."
                )
            if not (0 <= age_min <= age_max <= 120) or amount <= 0:
                raise NutrientReferenceCsvError(
                    f"{number}행의 범위 또는 기준량이 올바르지 않습니다."
                )
            exact_key = (code, gender, age_min, age_max, reference_type)
            if exact_key in exact_keys:
                raise NutrientReferenceCsvError("중복 기준 행이 있습니다.")
            exact_keys.add(exact_key)
            range_key = (code, gender, reference_type)
            if any(
                age_min <= old_max and old_min <= age_max
                for old_min, old_max in ranges.setdefault(range_key, [])
            ):
                raise NutrientReferenceCsvError("겹치는 나이 구간이 있습니다.")
            ranges[range_key].append((age_min, age_max))
            rows.append(
                NutrientReferenceCsvRow(
                    code, gender, age_min, age_max, reference_type, amount, unit
                )
            )
    except (KeyError, ValueError, InvalidOperation) as exc:
        if isinstance(exc, NutrientReferenceCsvError):
            raise
        raise NutrientReferenceCsvError("CSV 값 형식이 올바르지 않습니다.") from exc

    assert metadata is not None
    return NutrientReferenceCsvDocument(*metadata, checksum, tuple(rows))
