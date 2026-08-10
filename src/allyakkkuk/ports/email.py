"""이메일 발송 포트."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class OutboundEmail:
    recipients: tuple[str, ...]
    subject: str
    text_body: str
    html_body: str | None = None


class EmailSender(Protocol):
    def send(self, message: OutboundEmail) -> None: ...
