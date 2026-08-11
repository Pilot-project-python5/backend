# F-1.2 인수 조건

## AC-F-1.2-001 ACTIVE 사용자 로그인

전제: 이메일 인증을 완료한 ACTIVE 사용자가 있다.

행동: 대소문자가 다른 아이디와 올바른 비밀번호로 로그인한다.

결과: 200과 사용자 요약·만료 시각을 반환하고 액세스·리프레시 HttpOnly 쿠키를
설정하며 refresh_sessions 한 행을 저장한다.

## AC-F-1.2-002 토큰 원문 비노출과 계약

전제: 로그인이 성공한다.

행동: 응답 본문, 저장된 세션과 생성된 액세스 JWT를 확인한다.

결과: 본문·DB에 액세스·리프레시 원문이 없고, 리프레시 해시가 원문과 다르며 액세스
JWT의 issuer·audience·subject·session·type·발급·만료·JWT ID가 정확하다.

## AC-F-1.2-003 존재하지 않거나 틀린 자격 증명

전제: 존재하지 않는 아이디 또는 틀린 비밀번호다.

행동: 로그인한다.

결과: 두 경우 모두 같은 401 AUTH_INVALID_CREDENTIALS와 메시지이며 쿠키·세션을
만들지 않는다. 미등록 아이디에도 dummy 비밀번호 검증을 수행한다.

## AC-F-1.2-004 이메일 미인증 차단

전제: 비밀번호는 맞지만 PENDING_EMAIL_VERIFICATION이거나 email_verified_at이 없다.

행동: 로그인한다.

결과: 403 AUTH_EMAIL_UNVERIFIED이며 쿠키와 세션을 만들지 않는다.

## AC-F-1.2-005 정지 사용자 차단

전제: 비밀번호가 맞는 SUSPENDED 사용자다.

행동: 로그인한다.

결과: 403 AUTH_ACCOUNT_SUSPENDED이며 쿠키와 세션을 만들지 않는다.

## AC-F-1.2-006 수명과 쿠키 속성

전제: 주입된 현재 시각에 로그인이 성공한다.

행동: 성공 응답의 두 Set-Cookie를 확인한다.

결과: 액세스 만료는 정확히 15분, 리프레시 만료는 정확히 14일이며 두 쿠키 모두
HttpOnly·SameSite=Lax다. 경로와 Max-Age가 다르고 Secure 설정을 따른다.

## AC-F-1.2-007 다중 세션과 DB 실패

전제: 같은 ACTIVE 사용자가 여러 기기에서 로그인하거나 DB 저장이 실패한다.

행동: 로그인을 반복한다.

결과: 성공 요청마다 서로 다른 활성 세션을 저장하며, DB 실패 요청은 503이고 어떤
쿠키도 설정하지 않는다.

## 데이터·ERD 인수 조건

빈 PostgreSQL에서 refresh_sessions PK, users CASCADE FK, token_hash UNIQUE,
시간 CHECK와 사용자·만료 인덱스가 재현된다. ORM·마이그레이션·논리 ERD가 일치한다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-1.2-001 | tests/acceptance/auth/test_login.py | 성공·정규화·세션 저장 |
| AC-F-1.2-002 | tests/acceptance/auth/test_login.py, tests/unit/auth/test_tokens.py | 비노출·JWT claims·해시 |
| AC-F-1.2-003 | tests/unit/auth/test_login_service.py, tests/contract/auth/test_login_contract.py | 동일 401·dummy 검증 |
| AC-F-1.2-004 | tests/acceptance/auth/test_login.py | 미인증 403 |
| AC-F-1.2-005 | tests/acceptance/auth/test_login.py | 정지 403 |
| AC-F-1.2-006 | tests/contract/auth/test_login_contract.py, tests/unit/auth/test_tokens.py | 쿠키·수명 경계 |
| AC-F-1.2-007 | tests/acceptance/auth/test_login.py, tests/unit/auth/test_login_service.py | 다중 세션·DB 실패 |
