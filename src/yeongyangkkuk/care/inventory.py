"""예상 소진일까지 남은 날짜 기반 재고 상태."""

from __future__ import annotations

from typing import Literal

InventoryStatus = Literal["NORMAL", "LOW_STOCK", "DEPLETED"]


def inventory_status(days_until_depletion: int) -> InventoryStatus:
    if days_until_depletion < 0:
        return "DEPLETED"
    if days_until_depletion <= 5:
        return "LOW_STOCK"
    return "NORMAL"
