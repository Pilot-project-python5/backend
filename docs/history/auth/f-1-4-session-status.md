---
feature_id: "F-1.4"
title: "세션 상태 확인"
requirement_id: "FR-1"
domain: "auth"
status: "implemented"
completed_on: "2026-08-11"
feature_packet: "docs/features/auth/f-1-4-session-status"
pull_request: "https://github.com/Pilot-project-python5/backend/pull/8"
commit: null
---

# F-1.4 세션 상태 확인 구현 이력

## 구현 요약

로그인 사용자는 GET /api/v1/auth/me에서 현재 계정·건강 프로필과 access·refresh 만료
시각을 조회할 수 있다. 보호 요청은 access JWT의 서명·필수 claim뿐 아니라 서버의
refresh 세션과 계정 상태까지 확인하므로 로그아웃·세션 만료·계정 정지가 남은 JWT
수명보다 우선해 즉시 반영된다.

## 구현 범위

### 포함

- `yeongyangkkuk_access_token` cookie 기반 Access JWT verifier
- 사용자·건강 프로필·refresh 세션 읽기 저장소와 인증 서비스
- 이후 보호 API가 재사용할 `require_current_user` FastAPI 의존성
- GET /api/v1/auth/me의 현재 사용자·세션 만료 응답
- AccessCookieAuth OpenAPI security scheme과 인증 문서
- 단위·계약·PostgreSQL 인수 테스트

### 제외

- access token 자동 refresh와 refresh token 검증은 /me에서 수행하지 않는다.
- 프로필 수정, 비밀번호 변경·재설정, 전체 기기 로그아웃과 세션 목록은 제외했다.
- 역할·관리자 권한, 운영 JWT 키 회전, AWS와 AI 연동은 제외했다.

## 주요 구현 내용

- `JwtSessionTokenIssuer.verify_access_token`이 HS256, issuer, audience, access type과
  sub·sid·jti·iat·exp 필수 claim의 UUID·시간 경계를 검증한다.
- `SQLAlchemyCurrentUserRepository`가 JWT 사용자와 세션 ID로 users,
  health_profiles, refresh_sessions를 한 번에 읽고 소유 관계를 제한한다.
- `CurrentUserService`가 ACTIVE·이메일 인증 계정과 미폐기·고정 만료 전 세션만
  `AuthenticatedUser`로 변환한다.
- `APIKeyCookie` 기반 `require_current_user`가 인증 로직을 보호 API 공통 경계로
  제공한다.
- 라우터는 내부 해시·정규화 식별자·token을 제외하고 공개 필드만 중첩 응답으로
  반환하며 성공 응답 캐시를 금지한다.

## API 변경

- `GET /api/v1/auth/me`
  - 인증: `AccessCookieAuth`, cookie name `yeongyangkkuk_access_token`
  - 요청 본문·쿼리: 없음
  - 200: authenticated=true, user 기본·건강 정보,
    session.access_token_expires_at·refresh_token_expires_at
  - 401 AUTH_REQUIRED: 쿠키 누락, JWT·claim 오류, 만료, 사용자·세션·계정 상태 무효
  - 503 SERVICE_UNAVAILABLE: PostgreSQL 조회 실패
- /me는 성공·실패 모두 token을 발급하거나 Set-Cookie를 변경하지 않는다.
- 성공 응답은 Cache-Control=no-store와 Pragma=no-cache를 사용한다.

## 데이터·ERD·마이그레이션

- users, health_profiles, refresh_sessions를 읽기만 하며 엔티티·관계·컬럼·제약·
  인덱스를 변경하지 않았다.
- 신규 Alembic 마이그레이션과 백필·시드 변경은 없다.
- `alembic check`는 신규 upgrade 작업이 없음을 확인했고 ERD 검증은 기존 19개 필수
  엔티티와 20개 관계를 그대로 통과했다.

## 보안과 개인정보

- JWT sub와 users.id, JWT sid와 refresh_sessions.id·user_id가 함께 일치해야 한다.
- 모든 보호 요청에서 revoked_at과 expires_at을 확인해 logout을 즉시 반영한다.
- 인증 실패 사유와 사용자·세션 존재 여부는 같은 401 AUTH_REQUIRED로 통합한다.
- password_hash, normalized_login_id, normalized_email, token_hash와 token 원문을
  조회 응답·오류·로그에 노출하지 않는다.
- DB 장애는 인증 실패로 숨기지 않고 503으로 구분한다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-1.4-001~007을 단위·계약·PostgreSQL 인수 테스트에 연결 | 7개 조건 모두 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-1.4` | 38개 통과 |
| 전체 로컬 검증 | `make verify` | 200개 통과, 커버리지 94.64% |
| 정적 검사 | `ruff format --check .`, `ruff check .`, `mypy` | 모두 통과 |
| 데이터·ERD | ERD validator, `alembic upgrade head`, `alembic check`, 시드 2회 | 모두 통과, 스키마 차이 없음 |
| API 계약 | OpenAPI 생성 후 `python -m scripts.check_openapi` | `openapi.json` 일치 |

## 주요 결정과 근거

- 로그아웃 뒤 access JWT를 최대 15분 더 허용하지 않도록 stateless 검증만 하지 않고
  refresh_sessions를 매 보호 요청 읽는다.
- 프론트엔드가 상태를 예측하기 쉽도록 /me는 자동 refresh하지 않는다. 401 뒤 F-1.3
  refresh를 명시적으로 호출한다.
- FastAPI `APIKeyCookie`를 사용해 실제 HttpOnly cookie 인증을 Swagger 보안 정의와
  동일하게 표현한다.
- 숫자 나이는 저장하거나 응답하지 않고 birth_date를 반환해 기준일 계산 원칙을
  유지한다.

## 알려진 제약

- 강한 즉시 폐기 보장 때문에 보호 요청마다 PostgreSQL 읽기가 한 번 발생한다.
- /me의 401은 access 만료와 완전한 로그아웃을 구분하지 않으므로 프론트엔드가
  refresh 결과로 다음 화면을 결정해야 한다.
- 여러 요청이 동시에 401이면 클라이언트가 refresh를 직렬화해야 F-1.3 이전 token
  재사용 탐지로 세션이 폐기되지 않는다.

## 후속 작업

- F-2·F-3의 로그인 전용 API는 구현할 때 `require_current_user`를 재사용한다.
- 2차 운영에서는 DB 부하를 측정하고 즉시 폐기 보장을 유지하는 캐시·키 회전 전략을
  별도 설계한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/auth/f-1-4-session-status
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
