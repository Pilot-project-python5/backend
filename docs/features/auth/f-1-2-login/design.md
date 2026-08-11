# F-1.2 설계

## API 계약

- 메서드와 경로: POST /api/v1/auth/login
- 인증: 불필요
- 요청: login_id, password
- 성공: 200과 user_id, login_id, name, status=ACTIVE, authenticated_at,
  access_token_expires_at, refresh_token_expires_at
- 성공 헤더: Cache-Control=no-store, Pragma=no-cache와 액세스·리프레시 Set-Cookie
- 오류: 401 AUTH_INVALID_CREDENTIALS, 403 AUTH_EMAIL_UNVERIFIED 또는
  AUTH_ACCOUNT_SUSPENDED, 422 VALIDATION_FAILED, 503 SERVICE_UNAVAILABLE

## 쿠키와 토큰 계약

- 액세스 쿠키: allyakkkuk_access_token, Path=/api/v1, HttpOnly,
  SameSite=Lax, Max-Age=900
- 리프레시 쿠키: allyakkkuk_refresh_token, Path=/api/v1/auth, HttpOnly,
  SameSite=Lax, Max-Age=1209600
- Secure는 AUTH_COOKIE_SECURE 설정으로 관리하고 로컬·테스트 기본값은 false다.
- 액세스 JWT는 HS256과 AUTH_TOKEN_SECRET을 사용하며 iss=allyakkkuk,
  aud=allyakkkuk-api, sub=user UUID, sid=refresh session UUID, type=access,
  jti·iat·exp를 포함한다.
- 리프레시 secret은 secrets.token_urlsafe(48)로 만들고 session UUID와 함께
  HMAC-SHA256 해시한다. F-1.3부터 원문은 selector·secret 형식으로 조합한다.
- 두 토큰은 응답 모델·오류·로그·DB 원문에 포함하지 않는다.

## 데이터 설계

- refresh_sessions: id PK, user_id FK, token_hash UNIQUE, expires_at,
  revoked_at, last_used_at, created_at
- users와 다대일이며 사용자 삭제 시 세션도 CASCADE 삭제한다.
- expires_at은 created_at 이후, revoked_at과 last_used_at은 값이 있으면 created_at
  이상이어야 한다.
- (user_id, created_at)과 expires_at 인덱스를 제공한다.
- 로그인 성공 시 revoked_at·last_used_at은 NULL이다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 논리 엔티티로만 있던 REFRESH_SESSIONS에 created_at, 제약·FK·인덱스를 확정한다.
- 기존 데이터 백필은 없으며 신규 테이블만 추가한다.
- 검증: 빈 PostgreSQL upgrade/downgrade/upgrade, make erd-check와 Alembic
  autogenerate 차이 검사를 실행한다.

## 애플리케이션 흐름

1. 요청 스키마가 로그인 아이디와 비밀번호 길이·형식을 검사한다.
2. 서비스가 로그인 아이디를 정규화해 사용자와 비밀번호 해시를 조회한다.
3. 사용자가 없으면 dummy Argon2id 해시를 검증하고, 있으면 저장된 해시를 검증한다.
4. 자격 증명 실패는 동일한 401로 변환한다.
5. 비밀번호 성공 후 이메일 인증과 상태를 검사한다.
6. 새 세션 UUID와 액세스 JWT·리프레시 토큰을 만들고 리프레시 해시만 저장한다.
7. 세션 커밋 성공 후 라우터가 두 토큰을 별도 HttpOnly 쿠키로 기록한다.

## 보안과 개인정보

- 비밀번호·토큰·해시와 자격 증명 요청 전체를 로그에서 제외한다.
- 미등록 아이디도 Argon2id 검증을 수행해 존재 여부에 따른 처리 시간 차이를 줄인다.
- 상태 오류는 올바른 비밀번호가 확인된 뒤에만 반환해 임의 계정 상태 열거를 줄인다.
- JWT 서명과 리프레시 HMAC은 이메일 인증과 분리된 AUTH_TOKEN_SECRET을 사용한다.
- SameSite=Lax는 1차 동일 사이트 웹 구성을 전제로 한다. 2차에서 프론트·API가
  교차 사이트가 되면 SameSite=None+Secure와 별도 CSRF 방어를 함께 설계해야 한다.

## 로컬 어댑터

- 데이터베이스: PostgreSQL 16, SQLAlchemy 동기 세션
- 시간: SystemClock, 테스트는 FakeClock
- 비밀번호: 기존 Argon2PasswordHasher
- 토큰: PyJWT HS256과 secrets 기반 리프레시 발급기

## 호환성

- OpenAPI: 신규 공개 POST API와 Set-Cookie·오류 계약 추가
- 기존 API·테이블 데이터는 변경하지 않는다.
- 롤백: 신규 라우트·서비스·토큰 설정과 refresh_sessions 테이블을 제거한다.
  이미 발급한 액세스 JWT는 서명 키가 유지되는 동안 만료 전까지 유효할 수 있다.
