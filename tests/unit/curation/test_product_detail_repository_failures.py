from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from yeongyangkkuk.curation.product_detail_repository import (
    ProductDetailPersistenceError,
    SQLAlchemyProductDetailRepository,
)

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-2.4")]


def test_repository_converts_detail_query_failure() -> None:
    session = MagicMock(spec=Session)
    session.execute.side_effect = SQLAlchemyError("상세 쿼리 실패")

    with pytest.raises(ProductDetailPersistenceError):
        SQLAlchemyProductDetailRepository(session).get_published(
            UUID("22000000-0000-4000-8000-000000000001")
        )
