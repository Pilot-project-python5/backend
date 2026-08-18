from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from yeongyangkkuk.auth.current_user_dependencies import require_current_user
from yeongyangkkuk.auth.current_user_service import AuthenticatedUser
from yeongyangkkuk.auth.models import Gender, UserStatus
from yeongyangkkuk.coaching.router import get_coaching_service
from yeongyangkkuk.coaching.schemas import CoachingChatResponse
from yeongyangkkuk.main import app


class FakeCoachingService:
    def chat(self, request: object, user: object) -> CoachingChatResponse:
        return CoachingChatResponse(
            reply="비타민 D 섭취량을 먼저 확인해보세요.",
            suggested_questions=["언제 먹나요?", "권장량은 얼마인가요?"],
        )


def current_user() -> AuthenticatedUser:
    now = datetime.now(UTC)
    return AuthenticatedUser(
        user_id=uuid4(),
        login_id="coaching-user",
        name="코칭 사용자",
        email="coaching@example.com",
        status=UserStatus.ACTIVE,
        email_verified_at=now,
        birth_date=date(1995, 1, 1),
        gender=Gender.MALE,
        height_cm=Decimal("175"),
        weight_kg=Decimal("70"),
        access_token_expires_at=now + timedelta(minutes=15),
        refresh_token_expires_at=now + timedelta(days=7),
    )


def test_coaching_chat_contract() -> None:
    app.dependency_overrides[require_current_user] = current_user
    app.dependency_overrides[get_coaching_service] = FakeCoachingService
    try:
        response = TestClient(app).post(
            "/api/v1/coaching/chat",
            json={
                "client_request_id": str(uuid4()),
                "message": "비타민 D는 어떻게 먹나요?",
                "chat_history": [],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "reply": "비타민 D 섭취량을 먼저 확인해보세요.",
        "suggested_questions": ["언제 먹나요?", "권장량은 얼마인가요?"],
    }


def test_coaching_chat_openapi_contract() -> None:
    operation = app.openapi()["paths"]["/api/v1/coaching/chat"]["post"]
    assert operation["operationId"] == "coaching_chat"
    assert set(operation["responses"]) >= {"200", "401", "422", "503"}
