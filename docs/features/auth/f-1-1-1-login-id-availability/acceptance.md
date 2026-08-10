# F-1.1.1 인수 조건

## AC-F-1.1.1-001 사용 가능한 아이디

전제: 영문자·숫자 5~20자로 구성되고 정규화 값이 users에 없는 로그인 아이디다.

행동: GET /api/v1/auth/login-id/availability로 아이디를 조회한다.

결과: 200과 요청한 login_id, available=true를 반환하며 DB 데이터를 변경하지 않는다.

## AC-F-1.1.1-002 사용 중인 아이디

전제: 기존 사용자의 로그인 아이디와 대소문자만 다른 유효한 아이디다.

행동: 같은 API로 아이디를 조회한다.

결과: 200과 available=false를 반환하며 사용자 상태나 다른 개인정보를 노출하지 않는다.

## AC-F-1.1.1-003 입력 검증

전제: 5자 미만, 20자 초과, 한글·특수문자·공백 중 하나를 포함한 아이디다.

행동: 사용 가능 여부를 조회한다.

결과: 422 VALIDATION_FAILED와 query.login_id 필드 오류를 반환하고 DB 조회를 수행하지
않는다.

## AC-F-1.1.1-004 DB 조회 실패

전제: 유효한 아이디지만 PostgreSQL 조회가 실패한다.

행동: 사용 가능 여부를 조회한다.

결과: 503 SERVICE_UNAVAILABLE을 반환하며 DB 오류 상세를 노출하지 않는다.

## AC-F-1.1.1-005 조회와 가입의 경계

전제: available=true 응답을 받은 아이디다.

행동: 다른 요청이 같은 아이디로 먼저 가입한 뒤 기존 사용자가 가입을 시도한다.

결과: 조회는 아이디를 예약하지 않으며 최종 회원가입은 기존 UNIQUE 제약과
AUTH_LOGIN_ID_UNAVAILABLE 오류로 중복을 차단한다.

## 데이터·ERD 인수 조건

기존 users.normalized_login_id UNIQUE와 인덱스만 읽기에 사용한다. 테이블, 관계,
제약과 인덱스를 바꾸지 않으므로 마이그레이션과 ERD 변경은 해당하지 않는다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-1.1.1-001 | tests/acceptance/auth/test_login_id_availability.py | 사용 가능과 읽기 전용 |
| AC-F-1.1.1-002 | tests/acceptance/auth/test_login_id_availability.py | 대소문자 정규화 |
| AC-F-1.1.1-003 | tests/contract/auth/test_login_id_availability_contract.py | query 검증·오류 계약 |
| AC-F-1.1.1-004 | tests/unit/auth/test_login_id_availability_service.py, tests/contract/auth/test_login_id_availability_contract.py | DB 실패 변환과 HTTP 계약 |
| AC-F-1.1.1-005 | tests/acceptance/auth/test_login_id_availability.py | 조회 비예약과 가입 UNIQUE |
