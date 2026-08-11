"""보호 API가 재사용하는 access cookie 인증 의존성."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from allyakkkuk.auth.cookies import ACCESS_COOKIE_NAME
from allyakkkuk.auth.current_user_repository import SQLAlchemyCurrentUserRepository
from allyakkkuk.auth.current_user_service import AuthenticatedUser, CurrentUserService
from allyakkkuk.auth.tokens import JwtSessionTokenIssuer
from allyakkkuk.core.config import get_settings
from allyakkkuk.db.session import get_db_session
from allyakkkuk.ports.clock import SystemClock

_settings = get_settings()
_clock = SystemClock()
_token_verifier = JwtSessionTokenIssuer(_settings.auth_token_secret.get_secret_value())
_access_cookie = APIKeyCookie(
    name=ACCESS_COOKIE_NAME,
    scheme_name="AccessCookieAuth",
    description="HttpOnly access JWT 쿠키",
    auto_error=False,
)


def get_current_user_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> CurrentUserService:
    return CurrentUserService(
        repository=SQLAlchemyCurrentUserRepository(session),
        token_verifier=_token_verifier,
        clock=_clock,
    )


def require_current_user(
    service: Annotated[CurrentUserService, Depends(get_current_user_service)],
    access_token: Annotated[str | None, Security(_access_cookie)] = None,
) -> AuthenticatedUser:
    return service.authenticate(access_token)
