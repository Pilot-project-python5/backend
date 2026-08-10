"""공통 오류 계약을 FastAPI 응답으로 변환한다."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from allyakkkuk.api.schemas import ErrorDetail, ErrorField, ErrorResponse
from allyakkkuk.core.errors import AppError

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def _response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    fields: list[ErrorField] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            fields=fields or [],
            request_id=_request_id(request),
        )
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            fields=[
                ErrorField(field=item.field, code=item.code, message=item.message)
                for item in exc.fields
            ],
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = [
            ErrorField(
                field=".".join(str(part) for part in error["loc"]),
                code=str(error["type"]),
                message=str(error["msg"]),
            )
            for error in exc.errors()
        ]
        return _response(
            request,
            status_code=422,
            code="VALIDATION_FAILED",
            message="요청 값을 확인해주세요.",
            fields=fields,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        if exc.status_code == 404:
            return _response(
                request,
                status_code=404,
                code="RESOURCE_NOT_FOUND",
                message="요청한 리소스를 찾을 수 없습니다.",
            )
        return _response(
            request,
            status_code=exc.status_code,
            code="HTTP_ERROR",
            message="요청을 처리할 수 없습니다.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        context: dict[str, Any] = {"request_id": _request_id(request)}
        logger.exception("예상하지 못한 요청 처리 오류", extra=context)
        return _response(
            request,
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message="요청 처리 중 오류가 발생했습니다.",
        )
