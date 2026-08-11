"""버전 1 API 라우터."""

from fastapi import APIRouter

from allyakkkuk.api.health import router as health_router
from allyakkkuk.auth.email_verification_router import (
    router as email_verification_router,
)
from allyakkkuk.auth.login_router import router as login_router
from allyakkkuk.auth.router import router as auth_router
from allyakkkuk.auth.session_router import router as session_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(email_verification_router)
api_router.include_router(login_router)
api_router.include_router(session_router)
