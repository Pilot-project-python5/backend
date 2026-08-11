# F-1.4 설계

## API 계약

- 메서드와 경로: GET /api/v1/auth/me
- 인증: OpenAPI `AccessCookieAuth` API key cookie scheme으로 표현한
  `allyakkkuk_access_token` HttpOnly 쿠키
- 요청: 본문과 쿼리 없음
- 성공 응답: 200, authenticated=true, user(id, login_id, name, email, status,
  email_verified_at, birth_date, gender, height_cm, weight_kg),
  session(access_token_expires_at, refresh_token_expires_at)
- 오류 응답: 401 AUTH_REQUIRED, 503 SERVICE_UNAVAILABLE
- 멱등성: 읽기 전용 GET이며 같은 인증·DB 상태에서 반복 호출 결과가 같다.
- 캐시: 성공 응답에 Cache-Control=no-store와 Pragma=no-cache
- 쿠키 변경: 성공·실패 모두 Set-Cookie 없음. refresh는 별도 F-1.3 API다.

## 데이터 설계

- 엔티티: 기존 users, health_profiles, refresh_sessions
- 관계와 카디널리티: 사용자 1:1 건강 프로필, 사용자 1:N refresh 세션을 읽는다.
- 제약 조건: 기존 PK, user_id FK와 상태·시간 CHECK를 재사용한다.
- 인덱스: users와 refresh_sessions PK, health_profiles PK를 사용한다.
- 마이그레이션: 없음. 테이블·컬럼·제약·인덱스를 변경하지 않는다.
- 백필과 기존 데이터 영향: 없음. 기존 ACTIVE 사용자와 F-1.3 세션을 즉시 조회한다.
- 이력과 삭제: 읽기 전용이며 revoked_at·expires_at을 인증 판정에만 사용한다.

## ERD 영향

- docs/architecture/erd.md 변경: 아니오
- 변경 전 구조: users는 health_profiles와 1:1, refresh_sessions와 1:N 관계다.
- 변경 후 구조: 동일하다.
- 변경하지 않는 경우의 이유: 기존 관계와 컬럼만 읽으며 영속 상태를 쓰지 않는다.
- ERD 검증 방법: validate_erd.py와 Alembic check로 스키마 변경이 없음을 확인한다.

## 애플리케이션 흐름

1. FastAPI `APIKeyCookie` 보안 의존성이 access 쿠키를 읽는다.
2. verifier가 HS256과 필수 issuer·audience·claim을 확인하고 UUID·시간을 파싱한다.
3. 검증 실패는 원인을 노출하지 않고 AUTH_REQUIRED를 발생시킨다.
4. 저장소가 sub 사용자, sid refresh 세션과 건강 프로필을 하나의 읽기 조회로 가져온다.
5. 서비스가 사용자 ACTIVE·이메일 인증과 세션 소유권·미폐기·고정 만료를 확인한다.
6. 인증 의존성이 검증된 principal을 라우터에 제공한다.
7. /me 라우터가 공개 필드만 스키마로 변환하고 no-store 헤더와 함께 반환한다.

## 보안과 개인정보

- 소유권 검사: JWT sub와 users.id, JWT sid와 refresh_sessions.id·user_id가 모두
  일치해야 한다.
- 즉시 폐기: 매 요청에서 refresh_sessions.revoked_at과 expires_at을 확인해 logout과
  세션 만료를 남은 JWT exp보다 우선한다.
- 열거 방지: 모든 access 인증 실패는 동일한 AUTH_REQUIRED 코드·메시지다.
- 민감 필드: password_hash, normalized_login_id, normalized_email, token_hash는 조회
  결과와 로그에 노출하지 않는다.
- 로그 제외 항목: access·refresh token, Cookie 헤더, token hash와 개인 신체 정보

## 로컬 어댑터

- 데이터베이스: PostgreSQL 16과 SQLAlchemy 동기 읽기 저장소
- 시간: SystemClock, 단위 테스트는 FakeClock
- 토큰: PyJWT HS256 verifier와 기존 AUTH_TOKEN_SECRET
- 이메일: 사용하지 않음
- 스케줄러: 사용하지 않음

## 호환성

- OpenAPI 영향: GET /auth/me와 `AccessCookieAuth` security scheme, 200·401·503 추가
- 기존 데이터 영향: 없음. 기존 access JWT의 claim과 F-1.3 세션 구조를 그대로 쓴다.
- 롤백: /me 라우터와 인증 의존성·조회 코드를 제거한다. 스키마 롤백은 없다.
