"""SMTP와 결정적 가짜 이메일 발신기."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from allyakkkuk.ports.email import EmailSender, OutboundEmail


class SmtpEmailSender(EmailSender):
    def __init__(
        self,
        *,
        host: str,
        port: int,
        from_address: str,
        from_name: str,
    ) -> None:
        self._host = host
        self._port = port
        self._from_address = from_address
        self._from_name = from_name

    def send(self, message: OutboundEmail) -> None:
        email = EmailMessage()
        email["From"] = f"{self._from_name} <{self._from_address}>"
        email["To"] = ", ".join(message.recipients)
        email["Subject"] = message.subject
        email.set_content(message.text_body)
        if message.html_body is not None:
            email.add_alternative(message.html_body, subtype="html")
        with smtplib.SMTP(self._host, self._port, timeout=10) as smtp:
            smtp.send_message(email)


class FakeEmailSender(EmailSender):
    def __init__(self) -> None:
        self.messages: list[OutboundEmail] = []

    def send(self, message: OutboundEmail) -> None:
        self.messages.append(message)
