# F-1.3 인수 조건

## AC-F-1.3-001 selector·secret 로그인 발급

전제: ACTIVE 사용자가 로그인한다.

행동: 발급된 refresh 쿠키와 저장 세션을 확인한다.

결과: 원문은 `session UUID.64자 이상 secret` 형식이고 selector는 저장된 세션 ID와
같다. 원문은 응답 본문·DB에 없으며 저장 HMAC으로만 검증된다.

## AC-F-1.3-002 고정 만료 회전

전제: 최초 로그인에서 14일 뒤 만료되는 유효 세션이 있다.

행동: 만료 전 refresh API를 호출한다.

결과: 200과 새 access·refresh 쿠키를 반환하고 같은 세션 행의 token_hash와
last_used_at을 갱신한다. access는 현재부터 15분이고 refresh expires_at은 최초 값이며
쿠키 Max-Age는 남은 초다.

## AC-F-1.3-003 이전 토큰 재사용 탐지

전제: refresh 성공으로 이미 회전된 이전 토큰이 있다.

행동: 이전 토큰으로 다시 refresh한다.

결과: 401 AUTH_SESSION_INVALID, 인증 쿠키 삭제이며 해당 세션 revoked_at이 기록된다.
직전에 발급한 새 refresh token도 더 이상 사용할 수 없다.

## AC-F-1.3-004 무효 세션 통합 오류와 만료 경계

전제: 쿠키 누락·형식 오류·미등록·만료·폐기 중 하나거나 세션 사용자가 비활성이다.

행동: refresh한다.

결과: 모두 같은 401 AUTH_SESSION_INVALID와 메시지이며 쿠키를 삭제한다. expires_at과
같은 시각부터 만료이고 비활성 사용자의 기존 세션은 폐기한다.

## AC-F-1.3-005 현재 기기 로그아웃

전제: 한 사용자가 서로 다른 유효 세션 두 개를 가진다.

행동: 첫 번째 세션으로 logout한다.

결과: 204와 두 쿠키 삭제이며 첫 번째 revoked_at만 기록되고 두 번째 세션은 refresh할
수 있다.

## AC-F-1.3-006 멱등 로그아웃과 불일치 보호

전제: refresh 쿠키가 누락·형식 오류·미등록·만료·이미 폐기 또는 해시 불일치다.

행동: logout을 한 번 이상 호출한다.

결과: 매번 204와 두 쿠키 삭제다. 해시가 불일치하는 기존 세션은 변경하지 않는다.

## AC-F-1.3-007 DB 실패 원자성

전제: refresh 회전 또는 유효 세션 logout의 DB 처리가 실패한다.

행동: 해당 API를 호출한다.

결과: 503 SERVICE_UNAVAILABLE이며 새 토큰·쿠키 삭제를 포함한 Set-Cookie가 없고 기존
세션 상태는 커밋되지 않는다.

## AC-F-1.3-008 쿠키·OpenAPI 계약

전제: 로컬 또는 Secure 배포 설정에서 Swagger 계약을 확인한다.

행동: refresh 성공·401과 logout 204 응답을 검사한다.

결과: 쿠키 경로·HttpOnly·SameSite=Lax·Secure 설정, no-store 헤더와 200/204/401/503
상태가 실제 응답과 OpenAPI에 일치한다.

## 데이터·ERD 인수 조건

테이블·컬럼·관계·제약·인덱스가 바뀌지 않아 마이그레이션은 없다. 기존
refresh_sessions의 token_hash·last_used_at·revoked_at 상태 전이가 ORM·서비스·ERD
설명과 일치하고 Alembic check에 새 작업이 없어야 한다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-1.3-001 | tests/unit/auth/test_tokens.py, tests/acceptance/auth/test_session.py | selector·secret·HMAC |
| AC-F-1.3-002 | tests/unit/auth/test_session_service.py, tests/acceptance/auth/test_session.py | 회전·고정 만료·last_used |
| AC-F-1.3-003 | tests/unit/auth/test_session_service.py, tests/acceptance/auth/test_session.py | 재사용 폐기 |
| AC-F-1.3-004 | tests/unit/auth/test_session_service.py, tests/contract/auth/test_session_contract.py | 통합 401·시간 경계 |
| AC-F-1.3-005 | tests/acceptance/auth/test_session.py | 현재 기기만 로그아웃 |
| AC-F-1.3-006 | tests/unit/auth/test_session_service.py, tests/contract/auth/test_session_contract.py | 멱등·불일치 무변경 |
| AC-F-1.3-007 | tests/unit/auth/test_session_service.py, tests/contract/auth/test_session_contract.py | 503·쿠키 원자성 |
| AC-F-1.3-008 | tests/contract/auth/test_session_contract.py | 쿠키·OpenAPI |
