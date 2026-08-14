from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest

from allyakkkuk.notification.email_repository import EmailDeliveryClaim
from allyakkkuk.notification.email_service import render_reminder_email

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.12")]


@pytest.mark.parametrize(
    ("notification_type", "expected_phrase", "date_label"),
    [
        ("REPURCHASE", "재구매가 3일 남았습니다", "예상 소진일"),
        ("EXPIRATION", "유통기한이 3일 남았습니다", "유통기한"),
    ],
)
def test_renders_safe_plain_text_reminder(
    notification_type: str,
    expected_phrase: str,
    date_label: str,
) -> None:
    delivery_id = UUID("51000000-0000-4000-8000-000000000413")
    notification_id = UUID("41000000-0000-4000-8000-000000000413")
    message = render_reminder_email(
        EmailDeliveryClaim(
            id=delivery_id,
            notification_id=notification_id,
            recipient_email="template-413@example.com",
            notification_type=notification_type,
            product_name="테스트\n제품",
            reference_date=date(2026, 8, 17),
            trigger_days_before=3,
            attempt_count=1,
        )
    )

    assert message.recipients == ("template-413@example.com",)
    assert expected_phrase in message.subject
    assert "\n" not in message.subject
    assert date_label in message.text_body
    assert "2026-08-17" in message.text_body
    assert str(delivery_id) not in message.text_body
    assert str(notification_id) not in message.text_body
    assert message.html_body is None
