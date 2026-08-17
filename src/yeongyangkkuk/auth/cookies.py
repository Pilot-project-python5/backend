"""인증 세션 쿠키의 공통 이름·속성·설정과 삭제 정책."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from fastapi import Response

ACCESS_COOKIE_NAME = "yeongyangkkuk_access_token"
REFRESH_COOKIE_NAME = "yeongyangkkuk_refresh_token"


@dataclass(frozen=True, slots=True)
class SessionCookiePolicy:
    secure: bool
    same_site: Literal["lax", "strict", "none"] = "lax"
    access_path: str = "/api/v1"
    refresh_path: str = "/api/v1/auth"


def set_no_store_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    authenticated_at: datetime,
    access_token_expires_at: datetime,
    refresh_token_expires_at: datetime,
    policy: SessionCookiePolicy,
) -> None:
    access_max_age = max(
        int((access_token_expires_at - authenticated_at).total_seconds()),
        0,
    )
    refresh_max_age = max(
        int((refresh_token_expires_at - authenticated_at).total_seconds()),
        0,
    )
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=access_max_age,
        expires=access_token_expires_at,
        path=policy.access_path,
        secure=policy.secure,
        httponly=True,
        samesite=policy.same_site,
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=refresh_max_age,
        expires=refresh_token_expires_at,
        path=policy.refresh_path,
        secure=policy.secure,
        httponly=True,
        samesite=policy.same_site,
    )


def clear_auth_cookies(response: Response, policy: SessionCookiePolicy) -> None:
    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
        path=policy.access_path,
        secure=policy.secure,
        httponly=True,
        samesite=policy.same_site,
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=policy.refresh_path,
        secure=policy.secure,
        httponly=True,
        samesite=policy.same_site,
    )
