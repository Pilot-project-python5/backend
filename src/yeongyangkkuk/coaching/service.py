from __future__ import annotations

import json
from datetime import date

from yeongyangkkuk.auth.current_user_service import AuthenticatedUser
from yeongyangkkuk.coaching.gateway import CoachingGateway, CoachingGatewayError
from yeongyangkkuk.coaching.repository import (
    CoachingContextError,
    CoachingContextRepository,
)
from yeongyangkkuk.coaching.schemas import CoachingChatRequest, CoachingChatResponse
from yeongyangkkuk.core.errors import AppError


class CoachingService:
    def __init__(
        self, repository: CoachingContextRepository, gateway: CoachingGateway
    ) -> None:
        self._repository = repository
        self._gateway = gateway

    def chat(
        self, request: CoachingChatRequest, user: AuthenticatedUser
    ) -> CoachingChatResponse:
        try:
            products = self._repository.active_product_names(user.user_id)
            result = self._gateway.chat(
                {
                    "user_profile": {
                        "age": _age(user.birth_date),
                        "gender": user.gender.value,
                        "height": float(user.height_cm),
                        "weight": float(user.weight_kg),
                        "current_supplements": list(products),
                    },
                    "db_context": json.dumps(
                        {"active_care_products": list(products)},
                        ensure_ascii=False,
                    ),
                    "user_message": request.message,
                    "chat_history": [
                        item.model_dump(mode="json") for item in request.chat_history
                    ],
                }
            )
        except (CoachingContextError, CoachingGatewayError) as exc:
            raise AppError(
                status_code=503,
                code="COACHING_UNAVAILABLE",
                message="AI 코칭 서비스에 연결할 수 없습니다.",
            ) from exc
        return CoachingChatResponse(
            reply=result.reply, suggested_questions=list(result.suggested_questions)
        )


def _age(birth_date: date) -> int:
    today = date.today()
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )
