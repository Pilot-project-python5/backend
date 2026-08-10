"""기능 스키마를 추가하기 전 마이그레이션 기준점을 만든다.

Revision ID: 20260810_0001
Revises:
Create Date: 2026-08-10
"""

from collections.abc import Sequence

revision: str = "20260810_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """제품 기능 테이블은 승인된 기능 PR에서 추가한다."""


def downgrade() -> None:
    """기준점에는 되돌릴 제품 스키마가 없다."""
