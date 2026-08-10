"""요청 상관관계 식별자 미들웨어."""

from __future__ import annotations

import re
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


async def request_id_middleware(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    candidate = request.headers.get(REQUEST_ID_HEADER, "")
    request_id = candidate if REQUEST_ID_PATTERN.fullmatch(candidate) else str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response
