from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class CoachingGatewayError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class CoachingGatewayResponse:
    reply: str
    suggested_questions: tuple[str, ...]


class CoachingGateway(Protocol):
    def chat(self, payload: dict[str, Any]) -> CoachingGatewayResponse: ...


class HttpCoachingGateway:
    def __init__(self, *, base_url: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def chat(self, payload: dict[str, Any]) -> CoachingGatewayResponse:
        try:
            response = httpx.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            data = body.get("data", body)
            reply = data["reply"]
            questions = data.get("suggested_questions", [])
            if not isinstance(reply, str) or not isinstance(questions, list):
                raise ValueError("invalid AI response")
            return CoachingGatewayResponse(
                reply, tuple(str(item) for item in questions)
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise CoachingGatewayError from exc
