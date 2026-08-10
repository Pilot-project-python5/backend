"""버전 1 API 라우터."""

from fastapi import APIRouter

from allyakkkuk.api.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
