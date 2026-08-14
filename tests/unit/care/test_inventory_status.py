from __future__ import annotations

import pytest

from allyakkkuk.care.inventory import inventory_status

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.8")]


@pytest.mark.parametrize(
    ("days_until_depletion", "expected"),
    [
        (6, "NORMAL"),
        (5, "LOW_STOCK"),
        (1, "LOW_STOCK"),
        (0, "LOW_STOCK"),
        (-1, "DEPLETED"),
    ],
)
def test_inventory_status_boundaries(
    days_until_depletion: int,
    expected: str,
) -> None:
    assert inventory_status(days_until_depletion) == expected
