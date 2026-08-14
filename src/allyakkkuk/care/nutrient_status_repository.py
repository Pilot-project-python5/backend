"""영양성분 현황 프로필과 기준량 조회."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.auth.models import HealthProfile
from allyakkkuk.care.nutrient_reference_models import (
    NutrientReferenceValue,
    NutrientReferenceVersion,
)
from allyakkkuk.curation.models import Nutrient


class NutrientStatusPersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class NutrientStatusProfile:
    birth_date: date
    gender: str


@dataclass(frozen=True, slots=True)
class NutrientReferenceVersionRecord:
    id: UUID
    version: str
    source_name: str
    source_url: str


@dataclass(frozen=True, slots=True)
class NutrientReferenceRecord:
    nutrient_id: UUID
    nutrient_code: str
    reference_type: str
    reference_amount: Decimal
    unit: str


class NutrientStatusRepository(Protocol):
    def get_profile(self, *, user_id: UUID) -> NutrientStatusProfile: ...
    def get_reference_version(
        self, *, version: str
    ) -> NutrientReferenceVersionRecord | None: ...
    def list_reference_values(
        self, *, version_id: UUID, gender: str, age: int
    ) -> tuple[NutrientReferenceRecord, ...]: ...


class SQLAlchemyNutrientStatusRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_profile(self, *, user_id: UUID) -> NutrientStatusProfile:
        try:
            profile = self._session.get(HealthProfile, user_id)
            if profile is None:
                raise NutrientStatusPersistenceError
            return NutrientStatusProfile(profile.birth_date, profile.gender)
        except SQLAlchemyError as exc:
            raise NutrientStatusPersistenceError from exc

    def get_reference_version(
        self, *, version: str
    ) -> NutrientReferenceVersionRecord | None:
        try:
            row = self._session.scalar(
                select(NutrientReferenceVersion).where(
                    NutrientReferenceVersion.version == version
                )
            )
            return (
                None
                if row is None
                else NutrientReferenceVersionRecord(
                    row.id, row.version, row.source_name, row.source_url
                )
            )
        except SQLAlchemyError as exc:
            raise NutrientStatusPersistenceError from exc

    def list_reference_values(
        self, *, version_id: UUID, gender: str, age: int
    ) -> tuple[NutrientReferenceRecord, ...]:
        try:
            rows = self._session.execute(
                select(NutrientReferenceValue, Nutrient.code)
                .join(Nutrient, Nutrient.id == NutrientReferenceValue.nutrient_id)
                .where(
                    NutrientReferenceValue.version_id == version_id,
                    NutrientReferenceValue.gender == gender,
                    NutrientReferenceValue.age_min <= age,
                    NutrientReferenceValue.age_max >= age,
                )
                .order_by(Nutrient.code, NutrientReferenceValue.reference_type)
            )
            return tuple(
                NutrientReferenceRecord(
                    value.nutrient_id,
                    code,
                    value.reference_type,
                    value.reference_amount,
                    value.unit,
                )
                for value, code in rows
            )
        except SQLAlchemyError as exc:
            raise NutrientStatusPersistenceError from exc
