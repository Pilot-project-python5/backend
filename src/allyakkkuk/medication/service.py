"""DB 시드 기반 의약품 카탈로그 애플리케이션 서비스."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from allyakkkuk.core.errors import AppError
from allyakkkuk.medication.repository import (
    MedicationPersistenceError,
    MedicationRepository,
    MedicationSummaryRecord,
)


@dataclass(frozen=True, slots=True)
class MedicationSummary:
    id: UUID
    sku: str
    brand: str
    name: str
    image_url: str
    unit_form: str
    units_per_package: Decimal
    permit_code: str
    classification: str
    active_ingredients: str


@dataclass(frozen=True, slots=True)
class MedicationDetail(MedicationSummary):
    efficacy: str
    dosage_instructions: str
    precautions: str
    storage_instructions: str
    source_name: str
    source_url: str
    source_reviewed_on: date


@dataclass(frozen=True, slots=True)
class MedicationPage:
    items: tuple[MedicationSummary, ...]
    page: int
    page_size: int
    total: int
    has_next: bool


class MedicationService:
    def __init__(self, repository: MedicationRepository) -> None:
        self._repository = repository

    def list_medications(self, *, page: int, page_size: int) -> MedicationPage:
        try:
            result = self._repository.list_published(page=page, page_size=page_size)
        except MedicationPersistenceError as exc:
            raise self._unavailable() from exc
        return MedicationPage(
            items=tuple(self._summary(item) for item in result.items),
            page=page,
            page_size=page_size,
            total=result.total,
            has_next=page * page_size < result.total,
        )

    def get_medication(self, product_id: UUID) -> MedicationDetail:
        try:
            result = self._repository.get_published(product_id)
        except MedicationPersistenceError as exc:
            raise self._unavailable() from exc
        if result is None:
            raise AppError(
                status_code=404,
                code="MEDICATION_NOT_FOUND",
                message="의약품을 찾을 수 없습니다.",
            )
        return MedicationDetail(
            id=result.id,
            sku=result.sku,
            brand=result.brand,
            name=result.name,
            image_url=result.image_url,
            unit_form=result.unit_form,
            units_per_package=result.units_per_package,
            permit_code=result.permit_code,
            classification=result.classification,
            active_ingredients=result.active_ingredients,
            efficacy=result.efficacy,
            dosage_instructions=result.dosage_instructions,
            precautions=result.precautions,
            storage_instructions=result.storage_instructions,
            source_name=result.source_name,
            source_url=result.source_url,
            source_reviewed_on=result.source_reviewed_on,
        )

    @staticmethod
    def _summary(item: MedicationSummaryRecord) -> MedicationSummary:
        return MedicationSummary(
            id=item.id,
            sku=item.sku,
            brand=item.brand,
            name=item.name,
            image_url=item.image_url,
            unit_form=item.unit_form,
            units_per_package=item.units_per_package,
            permit_code=item.permit_code,
            classification=item.classification,
            active_ingredients=item.active_ingredients,
        )

    @staticmethod
    def _unavailable() -> AppError:
        return AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="서비스가 아직 준비되지 않았습니다.",
        )
