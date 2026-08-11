# F-1.1.2 인수 조건

## AC-F-1.1.2-001 유효한 가입 정보

전제: 전체 필드가 F-1.1 규칙에 맞고 정규화 아이디와 이메일이 존재하지 않는다.

행동: POST /api/v1/auth/signup/validation으로 전체 가입 정보를 제출한다.

결과: 200과 valid=true, issues=[]를 반환하며 사용자·건강 프로필을 저장하거나
비밀번호를 해시하지 않는다.

## AC-F-1.1.2-002 아이디와 이메일 중복 일괄 확인

전제: 대소문자만 다른 정규화 아이디와 이메일이 기존 사용자에게 존재한다.

행동: 전체 가입 정보를 사전 검증한다.

결과: 200과 valid=false, login_id의 AUTH_LOGIN_ID_UNAVAILABLE issue와 email의
AUTH_EMAIL_UNAVAILABLE issue를 순서대로 반환하며 다른 사용자 정보는 노출하지 않는다.

## AC-F-1.1.2-003 요청 형식 검증

전제: 필수값 누락, 잘못된 형식·범위 또는 비밀번호 불일치가 포함된 요청이다.

행동: 전체 가입 정보를 사전 검증한다.

결과: 422 VALIDATION_FAILED와 body 필드 오류를 반환하고 DB 조회를 수행하지 않는다.

## AC-F-1.1.2-004 미래 생년월일

전제: 형식은 유효하지만 생년월일이 주입된 기준일보다 미래다.

행동: 전체 가입 정보를 사전 검증한다.

결과: 200과 valid=false, birth_date의 birth_date_future issue를 반환한다.

## AC-F-1.1.2-005 DB 조회 실패

전제: 요청 형식은 유효하지만 PostgreSQL 중복 조회가 실패한다.

행동: 전체 가입 정보를 사전 검증한다.

결과: 503 SERVICE_UNAVAILABLE을 반환하며 DB 오류 상세를 노출하지 않는다.

## AC-F-1.1.2-006 사전 검증과 실제 가입의 경계

전제: valid=true 응답을 받은 가입 정보다.

행동: 같은 정보로 실제 회원가입을 수행한다.

결과: 사전 검증은 식별자를 예약하거나 데이터를 남기지 않아 회원가입이 성공하며,
이후 경쟁 가입은 기존 UNIQUE 제약과 409 오류로 차단된다.

## 데이터·ERD 인수 조건

기존 users 정규화 고유 인덱스를 읽기에 사용한다. 테이블·관계·제약·인덱스를 바꾸지
않으므로 마이그레이션과 ERD 변경은 해당하지 않는다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-1.1.2-001 | tests/acceptance/auth/test_signup_validation.py | 정상 결과와 무저장 |
| AC-F-1.1.2-002 | tests/acceptance/auth/test_signup_validation.py | 두 중복 issue와 정규화 |
| AC-F-1.1.2-003 | tests/contract/auth/test_signup_validation_contract.py | SignupRequest 재사용과 422 |
| AC-F-1.1.2-004 | tests/unit/auth/test_signup_validation_service.py | fake clock 경계 |
| AC-F-1.1.2-005 | tests/unit/auth/test_signup_validation_service.py, tests/contract/auth/test_signup_validation_contract.py | DB 실패와 HTTP 503 |
| AC-F-1.1.2-006 | tests/acceptance/auth/test_signup_validation.py | 무예약과 최종 UNIQUE |
