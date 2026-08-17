from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from yeongyangkkuk.curation.product_category_repository import (
    ProductCategoryPersistenceError,
    SQLAlchemyProductCategoryRepository,
)

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-2.2")]


def test_repository_converts_failure_while_fetching_rows() -> None:
    session = MagicMock(spec=Session)
    scalar_result = session.execute.return_value.scalars.return_value
    scalar_result.__iter__.side_effect = SQLAlchemyError("결과 읽기 실패")

    with pytest.raises(ProductCategoryPersistenceError):
        SQLAlchemyProductCategoryRepository(session).list_active()
