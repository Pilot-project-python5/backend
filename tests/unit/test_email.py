from __future__ import annotations

from unittest.mock import patch

import pytest

from allyakkkuk.adapters.email import FakeEmailSender, SmtpEmailSender
from allyakkkuk.ports.email import OutboundEmail

pytestmark = pytest.mark.unit


def test_fake_email_sender_records_message_without_network() -> None:
    sender = FakeEmailSender()
    message = OutboundEmail(
        recipients=("fixture@example.test",),
        subject="로컬 검증",
        text_body="실제 이메일을 발송하지 않습니다.",
    )

    sender.send(message)

    assert sender.messages == [message]


def test_smtp_sender_builds_message_for_local_mailbox() -> None:
    sender = SmtpEmailSender(
        host="mail",
        port=1025,
        from_address="no-reply@allyakkkuk.local",
        from_name="알약꾹",
    )
    message = OutboundEmail(
        recipients=("fixture@example.test",),
        subject="인증번호",
        text_body="123456",
        html_body="<strong>123456</strong>",
    )

    with patch("allyakkkuk.adapters.email.smtplib.SMTP") as smtp_class:
        sender.send(message)

    smtp_class.assert_called_once_with("mail", 1025, timeout=10)
    sent = smtp_class.return_value.__enter__.return_value.send_message.call_args.args[0]
    assert sent["To"] == "fixture@example.test"
    assert sent["Subject"] == "인증번호"
    assert sent.is_multipart()
