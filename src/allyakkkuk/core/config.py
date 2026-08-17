"""환경변수 기반 애플리케이션 설정."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """1차 로컬 MVP가 사용하는 설정 계약."""

    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "알약꾹 백엔드"
    app_version: str = "0.1.0"
    app_env: Literal["local", "test"] = "local"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_timezone: str = "Asia/Seoul"
    nutrient_reference_version: str = "KDRI-2025-20260316"
    api_prefix: str = "/api/v1"
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    database_url: str = (
        "postgresql+psycopg://allyakkkuk:allyakkkuk-local@localhost:5432/allyakkkuk_dev"
    )

    mail_host: str = "localhost"
    mail_port: int = Field(default=1025, ge=1, le=65535)
    mail_from_address: str = "no-reply@allyakkkuk.local"
    mail_from_name: str = "알약꾹"
    email_verification_secret: SecretStr = SecretStr(
        "local-only-email-verification-secret-change-me"
    )
    auth_token_secret: SecretStr = SecretStr(
        "local-only-auth-token-secret-change-before-deployment"
    )
    auth_cookie_secure: bool = False

    worker_poll_seconds: int = Field(default=60, ge=1, le=3600)

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/"):
            raise ValueError("api_prefix는 /로 시작하고 /로 끝나지 않아야 합니다")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("PostgreSQL psycopg 연결 문자열만 사용할 수 있습니다")
        return value

    @field_validator("app_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"알 수 없는 IANA 시간대입니다: {value}") from exc
        return value

    @field_validator("email_verification_secret")
    @classmethod
    def validate_email_verification_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("email_verification_secret은 32자 이상이어야 합니다")
        return value

    @field_validator("auth_token_secret")
    @classmethod
    def validate_auth_token_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("auth_token_secret은 32자 이상이어야 합니다")
        return value

    @property
    def allowed_cors_origins(self) -> tuple[str, ...]:
        return tuple(
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
