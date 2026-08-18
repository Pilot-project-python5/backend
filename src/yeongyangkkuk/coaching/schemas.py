from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRole(StrEnum):
    USER = "USER"
    CHATBOT = "CHATBOT"


class ChatHistoryItem(BaseModel):
    role: ChatRole
    message: str = Field(min_length=1, max_length=4000)


class CoachingChatRequest(BaseModel):
    client_request_id: UUID
    message: str = Field(min_length=1, max_length=4000)
    chat_history: list[ChatHistoryItem] = Field(default_factory=list, max_length=40)


class CoachingChatResponse(BaseModel):
    reply: str
    suggested_questions: list[str]
