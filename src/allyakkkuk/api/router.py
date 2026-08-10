"""버전 1 API 라우터."""

from fastapi import APIRouter

from allyakkkuk.api.health import router as health_router
from allyakkkuk.auth.router import router as auth_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
