"""복용 제품 등록 애플리케이션 서비스."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from allyakkkuk.care.care_item_repository import (
    CareItemCreateData,
    CareItemListRecord,
    CareItemManagementRepository,
    CareItemPersistenceError,
    CareItemRepository,
)
from allyakkkuk.care.depletion import (
    calculate_days_until_depletion,
    calculate_expected_depletion_date,
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
    expected_depletion_date: date
    total_quantity: Decimal
    quantity_unit: str
    dose_per_intake: Decimal
    intakes_per_day: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CareItemListItem:
    id: UUID
    product_id: UUID
    product_type: str
    brand: str
    name: str
    image_url: str
    purchase_date: date
    intake_start_date: date
    expected_depletion_date: date
    total_quantity: Decimal
    quantity_unit: str
    dose_per_intake: Decimal
    intakes_per_day: int
    days_until_depletion: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CareItemListResult:
    items: tuple[CareItemListItem, ...]
    page: int
    page_size: int
    total: int
    has_next: bool


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
            expected_depletion_date = calculate_expected_depletion_date(
                intake_start_date=command.intake_start_date,
                total_quantity=command.total_quantity,
                dose_per_intake=command.dose_per_intake,
                intakes_per_day=command.intakes_per_day,
            )
        except (OverflowError, ValueError) as exc:
            raise _validation_error(
                field="body.total_quantity",
                code="depletion_date_out_of_range",
                message="예상 소진일을 지원하는 날짜 범위에서 계산할 수 없습니다.",
            ) from exc

        try:
            result = self._repository.create(
                CareItemCreateData(
                    user_id=user_id,
                    product_id=command.product_id,
                    purchase_date=command.purchase_date,
                    intake_start_date=command.intake_start_date,
                    expected_depletion_date=expected_depletion_date,
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
            expected_depletion_date=result.expected_depletion_date,
            total_quantity=result.total_quantity,
            quantity_unit=result.quantity_unit,
            dose_per_intake=result.dose_per_intake,
            intakes_per_day=result.intakes_per_day,
            created_at=result.created_at,
        )


class CareItemManagementService:
    def __init__(
        self,
        repository: CareItemManagementRepository,
        clock: Clock,
        time_zone: ZoneInfo,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._time_zone = time_zone

    def list_items(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
    ) -> CareItemListResult:
        try:
            result = self._repository.list_active(
                user_id=user_id,
                page=page,
                page_size=page_size,
            )
        except CareItemPersistenceError as exc:
            raise _service_unavailable() from exc

        today = self._clock.now().astimezone(self._time_zone).date()
        return CareItemListResult(
            items=tuple(_list_item(item, today=today) for item in result.items),
            page=page,
            page_size=page_size,
            total=result.total,
            has_next=page * page_size < result.total,
        )

    def delete_item(self, *, user_id: UUID, care_item_id: UUID) -> None:
        try:
            deleted = self._repository.soft_delete(
                user_id=user_id,
                care_item_id=care_item_id,
                deleted_at=self._clock.now(),
            )
        except CareItemPersistenceError as exc:
            raise _service_unavailable() from exc

        if not deleted:
            raise AppError(
                status_code=404,
                code="CARE_ITEM_NOT_FOUND",
                message="복용 항목을 찾을 수 없습니다.",
            )


def _list_item(item: CareItemListRecord, *, today: date) -> CareItemListItem:
    return CareItemListItem(
        id=item.id,
        product_id=item.product_id,
        product_type=item.product_type,
        brand=item.brand,
        name=item.name,
        image_url=item.image_url,
        purchase_date=item.purchase_date,
        intake_start_date=item.intake_start_date,
        expected_depletion_date=item.expected_depletion_date,
        total_quantity=item.total_quantity,
        quantity_unit=item.quantity_unit,
        dose_per_intake=item.dose_per_intake,
        intakes_per_day=item.intakes_per_day,
        days_until_depletion=calculate_days_until_depletion(
            expected_depletion_date=item.expected_depletion_date,
            today=today,
        ),
        created_at=item.created_at,
    )


def _service_unavailable() -> AppError:
    return AppError(
        status_code=503,
        code="SERVICE_UNAVAILABLE",
        message="서비스가 아직 준비되지 않았습니다.",
    )


def _validation_error(*, field: str, code: str, message: str) -> AppError:
    return AppError(
        status_code=422,
        code="VALIDATION_FAILED",
        message="요청 값을 확인해주세요.",
        fields=(ErrorFieldData(field=field, code=code, message=message),),
    )
