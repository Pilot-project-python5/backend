"""복용 제품 등록 애플리케이션 서비스."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from allyakkkuk.care.care_item_repository import (
    CareItemCreateData,
    CareItemPersistenceError,
    CareItemRepository,
)
from allyakkkuk.core.errors import AppError, ErrorFieldData
from allyakkkuk.ports.clock import Clock


@dataclass(frozen=True, slots=True)
class CareItemRegistrationCommand:
    product_id: UUID
    purchase_date: date
    intake_start_date: date
    total_quantity: Decimal
    dose_per_intake: Decimal
    intakes_per_day: int


@dataclass(frozen=True, slots=True)
class CareItemRegistrationResult:
    id: UUID
    product_id: UUID
    purchase_date: date
    intake_start_date: date
    total_quantity: Decimal
    quantity_unit: str
    dose_per_intake: Decimal
    intakes_per_day: int
    created_at: datetime


class CareItemService:
    def __init__(
        self,
        repository: CareItemRepository,
        clock: Clock,
        time_zone: ZoneInfo,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._time_zone = time_zone

    def register(
        self,
        *,
        user_id: UUID,
        command: CareItemRegistrationCommand,
    ) -> CareItemRegistrationResult:
        now = self._clock.now()
        if command.purchase_date > now.astimezone(self._time_zone).date():
            raise _validation_error(
                field="body.purchase_date",
                code="purchase_date_future",
                message="구매일은 미래일 수 없습니다.",
            )
        if command.intake_start_date < command.purchase_date:
            raise _validation_error(
                field="body.intake_start_date",
                code="intake_start_before_purchase",
                message="복용 시작일은 구매일보다 빠를 수 없습니다.",
            )
        if command.dose_per_intake > command.total_quantity:
            raise _validation_error(
                field="body.dose_per_intake",
                code="dose_exceeds_total_quantity",
                message="1회 복용량은 총수량을 초과할 수 없습니다.",
            )

        try:
            result = self._repository.create(
                CareItemCreateData(
                    user_id=user_id,
                    product_id=command.product_id,
                    purchase_date=command.purchase_date,
                    intake_start_date=command.intake_start_date,
                    total_quantity=command.total_quantity,
                    dose_per_intake=command.dose_per_intake,
                    intakes_per_day=command.intakes_per_day,
                    created_at=now,
                )
            )
        except CareItemPersistenceError as exc:
            raise AppError(
                status_code=503,
                code="SERVICE_UNAVAILABLE",
                message="서비스가 아직 준비되지 않았습니다.",
            ) from exc

        if result is None:
            raise AppError(
                status_code=404,
                code="PRODUCT_NOT_FOUND",
                message="제품을 찾을 수 없습니다.",
            )

        return CareItemRegistrationResult(
            id=result.id,
            product_id=result.product_id,
            purchase_date=result.purchase_date,
            intake_start_date=result.intake_start_date,
            total_quantity=result.total_quantity,
            quantity_unit=result.quantity_unit,
            dose_per_intake=result.dose_per_intake,
            intakes_per_day=result.intakes_per_day,
            created_at=result.created_at,
        )


def _validation_error(*, field: str, code: str, message: str) -> AppError:
    return AppError(
        status_code=422,
        code="VALIDATION_FAILED",
        message="요청 값을 확인해주세요.",
        fields=(ErrorFieldData(field=field, code=code, message=message),),
    )
