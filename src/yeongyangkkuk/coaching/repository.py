from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from yeongyangkkuk.care.models import CareItem
from yeongyangkkuk.curation.models import Product


class CoachingContextError(Exception):
    pass


class CoachingContextRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def active_product_names(self, user_id: UUID) -> tuple[str, ...]:
        try:
            return tuple(
                self._session.scalars(
                    select(Product.name)
                    .join(CareItem, CareItem.product_id == Product.id)
                    .where(CareItem.user_id == user_id, CareItem.deleted_at.is_(None))
                    .order_by(CareItem.created_at.desc())
                )
            )
        except SQLAlchemyError as exc:
            raise CoachingContextError from exc
