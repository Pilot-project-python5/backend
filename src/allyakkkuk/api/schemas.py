"""공통 API 응답 스키마."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ErrorField(BaseModel):
    field: str
    code: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: list[ErrorField] = Field(default_factory=list)
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
