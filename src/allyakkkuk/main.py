"""FastAPI 애플리케이션 팩터리."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from allyakkkuk.api.error_handlers import register_error_handlers
from allyakkkuk.api.middleware import request_id_middleware
from allyakkkuk.api.router import api_router
from allyakkkuk.core.config import Settings, get_settings
from allyakkkuk.core.logging import configure_logging

STATIC_DIRECTORY = Path(__file__).resolve().parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    configure_logging(debug=resolved.app_debug)

    application = FastAPI(
        title=resolved.app_name,
        version=resolved.app_version,
        description="알약꾹 1차 로컬 MVP 백엔드 API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    application.middleware("http")(request_id_middleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.allowed_cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(application)
    application.include_router(api_router, prefix=resolved.api_prefix)
    application.mount(
        "/static",
        StaticFiles(directory=STATIC_DIRECTORY),
        name="static",
    )
    return application


app = create_app()
