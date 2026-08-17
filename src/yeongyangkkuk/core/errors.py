"""애플리케이션 계층의 공개 오류."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ErrorFieldData:
    field: str
    code: str
    message: str


class AppError(Exception):
    """HTTP 응답으로 안전하게 변환할 수 있는 예상 오류."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        fields: Sequence[ErrorFieldData] = (),
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = tuple(fields)
