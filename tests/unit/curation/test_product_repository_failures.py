from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.curation.product_repository import (
    ProductPersistenceError,
    SQLAlchemyProductRepository,
)

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-2.3")]


def test_repository_converts_query_execution_failure() -> None:
    session = MagicMock(spec=Session)
    session.execute.side_effect = SQLAlchemyError("쿼리 실행 실패")

    with pytest.raises(ProductPersistenceError):
        SQLAlchemyProductRepository(session).list_published(
            category_slug=None,
            page=1,
            page_size=20,
        )


def test_repository_converts_failure_while_reading_category_result() -> None:
    session = MagicMock(spec=Session)
    session.scalar.side_effect = SQLAlchemyError("결과 읽기 실패")

    with pytest.raises(ProductPersistenceError):
        SQLAlchemyProductRepository(session).category_is_active("vitamin")
