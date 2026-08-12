"""외부 구매 URL 안전 조건."""

from __future__ import annotations

from urllib.parse import urlsplit

MIN_PURCHASE_URL_LENGTH = 9
MAX_PURCHASE_URL_LENGTH = 2048


def validate_purchase_url(url: str) -> str:
    """안전한 외부 구매 URL이면 원문을 반환한다."""

    if not MIN_PURCHASE_URL_LENGTH <= len(url) <= MAX_PURCHASE_URL_LENGTH:
        raise ValueError("구매 URL 길이가 허용 범위를 벗어났습니다.")
    if any(
        character.isspace() or ord(character) < 32 or ord(character) == 127
        for character in url
    ):
        raise ValueError("구매 URL에 공백 또는 제어 문자를 사용할 수 없습니다.")
    if "#" in url:
        raise ValueError("구매 URL에 fragment를 사용할 수 없습니다.")

    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("구매 URL 형식이 올바르지 않습니다.") from exc

    if parsed.scheme != "https" or hostname is None:
        raise ValueError("구매 URL은 hostname이 있는 HTTPS 절대 URL이어야 합니다.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("구매 URL에 userinfo를 사용할 수 없습니다.")
    return url
