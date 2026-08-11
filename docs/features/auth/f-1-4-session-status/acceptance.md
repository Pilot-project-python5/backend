# F-1.4 인수 조건

## AC-F-1.4-001 현재 사용자와 세션 조회

전제: ACTIVE·이메일 인증 사용자가 유효한 access JWT와 미폐기 refresh 세션을 가진다.

행동: access HttpOnly 쿠키로 GET /api/v1/auth/me를 호출한다.

결과: 200과 authenticated=true, 공개 사용자·건강 프로필 필드, access·refresh 만료
시각을 반환한다. token과 내부 해시·정규화 식별자는 노출하지 않는다.

## AC-F-1.4-002 Access JWT 엄격 검증

전제: access 쿠키가 누락됐거나 JWT가 손상·위조·만료됐거나 issuer, audience, type,
sub, sid, jti, iat, exp 중 하나가 잘못됐다.

행동: /me 또는 동일 인증 의존성을 쓰는 보호 API를 호출한다.

결과: 모든 경우 401 AUTH_REQUIRED와 같은 메시지이며 실패 세부와 token 원문을
노출하지 않는다.

## AC-F-1.4-003 세션 소유권과 즉시 폐기

전제: JWT sub·sid와 DB 소유 관계가 다르거나 세션이 미등록·폐기·고정 만료 상태다.

행동: 아직 JWT exp가 남은 access 쿠키로 인증한다.

결과: 401 AUTH_REQUIRED다. 특히 logout 직후 기존 access token도 즉시 거부된다.

## AC-F-1.4-004 계정 상태 검증

전제: access JWT의 사용자가 미등록, 이메일 미인증 또는 SUSPENDED 상태다.

행동: 인증 의존성을 사용하는 API를 호출한다.

결과: 계정 상태를 구분해 노출하지 않고 401 AUTH_REQUIRED를 반환한다.

## AC-F-1.4-005 DB 실패

전제: 올바른 access JWT를 해석한 뒤 사용자·세션·프로필 DB 조회가 실패한다.

행동: /me를 호출한다.

결과: 503 SERVICE_UNAVAILABLE이며 401로 숨기거나 인증 쿠키를 변경하지 않는다.

## AC-F-1.4-006 인증 응답·OpenAPI 계약

전제: 실제 API와 생성된 OpenAPI를 확인한다.

행동: /me 성공·401·503과 보안 정의를 검사한다.

결과: `AccessCookieAuth`의 cookie name, 200·401·503 스키마와 실제 응답이 일치하고,
성공은 no-store 헤더이며 모든 응답에 Set-Cookie가 없다.

## AC-F-1.4-007 명시적 refresh 흐름

전제: access JWT가 만료됐지만 refresh 세션은 유효하다.

행동: 먼저 /me를 호출하고 이어서 POST /auth/refresh 후 새 access로 /me를 호출한다.

결과: 첫 호출은 401, refresh는 200, 마지막 /me는 200이다. /me 자체는 token을
자동 갱신하지 않는다.

## 데이터·ERD 인수 조건

테이블·컬럼·관계·제약·인덱스를 바꾸지 않고 기존 users, health_profiles,
refresh_sessions를 읽기만 하므로 마이그레이션과 Mermaid ERD 변경은 없다. Alembic
check와 ERD 검증에 새 차이가 없어야 한다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-1.4-001 | tests/acceptance/auth/test_current_user.py | 공개 사용자·세션 응답 |
| AC-F-1.4-002 | tests/unit/auth/test_access_tokens.py, tests/contract/auth/test_current_user_contract.py | claim·통합 401 |
| AC-F-1.4-003 | tests/unit/auth/test_current_user_service.py, tests/acceptance/auth/test_current_user.py | 소유권·즉시 폐기 |
| AC-F-1.4-004 | tests/unit/auth/test_current_user_service.py | 계정 상태 통합 |
| AC-F-1.4-005 | tests/unit/auth/test_current_user_service.py, tests/contract/auth/test_current_user_contract.py | 503 |
| AC-F-1.4-006 | tests/contract/auth/test_current_user_contract.py | 보안 스키마·캐시·쿠키 |
| AC-F-1.4-007 | tests/acceptance/auth/test_current_user.py | 명시적 refresh 흐름 |
