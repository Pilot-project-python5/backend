"""기능 ID별 테스트 선택과 공통 pytest 설정."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--feature-id",
        action="store",
        default=None,
        help="지정한 Feature Packet ID와 연결된 테스트만 실행합니다.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    feature_id = config.getoption("--feature-id")
    if feature_id is None:
        return
    selected: list[pytest.Item] = []
    deselected: list[pytest.Item] = []
    for item in items:
        markers = list(item.iter_markers(name="feature"))
        if any(marker.args and marker.args[0] == feature_id for marker in markers):
            selected.append(item)
        else:
            deselected.append(item)
    config.hook.pytest_deselected(items=deselected)
    items[:] = selected
