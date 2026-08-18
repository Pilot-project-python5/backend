from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from yeongyangkkuk.auth.current_user_dependencies import require_current_user
from yeongyangkkuk.auth.current_user_service import AuthenticatedUser
from yeongyangkkuk.coaching.gateway import HttpCoachingGateway
from yeongyangkkuk.coaching.repository import CoachingContextRepository
from yeongyangkkuk.coaching.schemas import CoachingChatRequest, CoachingChatResponse
from yeongyangkkuk.coaching.service import CoachingService
from yeongyangkkuk.core.config import get_settings
from yeongyangkkuk.db.session import get_db_session

router = APIRouter(prefix="/coaching", tags=["AI 코칭"])


def get_coaching_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> CoachingService:
    settings = get_settings()
    return CoachingService(
        CoachingContextRepository(session),
        HttpCoachingGateway(
            base_url=settings.ai_server_base_url,
            timeout_seconds=settings.ai_server_timeout_seconds,
        ),
    )


@router.post(
    "/chat",
    response_model=CoachingChatResponse,
    responses={
        401: {"description": "로그인 필요"},
        422: {"description": "요청 형식 오류"},
        503: {"description": "AI 또는 DB 연결 실패"},
    },
    summary="AI 코칭 대화",
    operation_id="coaching_chat",
)
def coaching_chat(
    request: CoachingChatRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[CoachingService, Depends(get_coaching_service)],
) -> CoachingChatResponse:
    return service.chat(request, user)
