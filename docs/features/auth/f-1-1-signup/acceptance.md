# F-1.1 인수 조건

## AC-F-1.1-001 정상 회원가입

전제: 정규화 로그인 아이디와 이메일이 존재하지 않고 모든 필드가 유효하다.

행동: POST /api/v1/auth/signup 요청을 보낸다.

결과: 201과 사용자 식별자, 로그인 아이디, 이메일,
PENDING_EMAIL_VERIFICATION 상태와 email_verification_required=true를 반환하고
users와 health_profiles에 한 행씩 저장한다.

## AC-F-1.1-002 비밀번호 보호

전제: 유효한 가입 요청이 있다.

행동: 회원가입을 완료하고 저장값과 응답을 확인한다.

결과: Argon2id 비밀번호 해시만 저장되며 비밀번호 원문, 비밀번호 확인과 해시는
응답이나 로그에 나타나지 않는다.

## AC-F-1.1-003 로그인 아이디 중복

전제: 대소문자만 다른 동일 정규화 로그인 아이디의 사용자가 존재한다.

행동: 같은 정규화 로그인 아이디로 가입을 요청한다.

결과: 409 AUTH_LOGIN_ID_UNAVAILABLE을 반환하고 사용자와 건강 프로필을 추가하지
않는다.

## AC-F-1.1-004 이메일 중복

전제: 대소문자만 다른 동일 정규화 이메일의 사용자가 존재한다.

행동: 같은 정규화 이메일로 가입을 요청한다.

결과: 409 AUTH_EMAIL_UNAVAILABLE을 반환하고 추가 데이터를 저장하지 않는다.

## AC-F-1.1-005 입력 검증

전제: 필수값 누락, 잘못된 아이디·비밀번호 형식, 비밀번호 불일치, 미래 생년월일,
허용하지 않은 성별 또는 범위 밖 키·몸무게 중 하나가 포함된 요청이다.

행동: 회원가입을 요청한다.

결과: 422 VALIDATION_FAILED와 해당 필드 오류를 반환하고 데이터를 저장하지 않는다.

## AC-F-1.1-006 원자적 저장

전제: 사용자 저장 후 건강 프로필 저장이 실패하도록 구성한다.

행동: 회원가입을 요청한다.

결과: 트랜잭션이 롤백되어 users와 health_profiles 어느 쪽에도 가입 데이터가 남지
않는다.

## AC-F-1.1-007 미인증 상태와 기능 경계

전제: 유효한 가입 요청이다.

행동: 회원가입을 완료한다.

결과: email_verified_at은 null이고 상태는 PENDING_EMAIL_VERIFICATION이며 이메일
인증번호는 이 기능에서 생성하거나 발송하지 않는다.

## AC-F-1.1-008 DB·ERD·OpenAPI 일치

전제: 빈 테스트 PostgreSQL에 전체 마이그레이션을 적용한다.

행동: 스키마, 로컬 ERD와 생성된 OpenAPI를 검사한다.

결과: users와 health_profiles의 PK, 1:1 FK, UNIQUE/CHECK 제약과 회원가입 계약이
승인된 design.md와 일치한다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-1.1-001 | tests/acceptance/auth/test_signup.py | API와 두 테이블 저장 |
| AC-F-1.1-002 | tests/unit/auth/test_passwords.py, tests/acceptance/auth/test_signup.py | 해시·응답·로그 |
| AC-F-1.1-003 | tests/acceptance/auth/test_signup.py | 대소문자 정규화와 409 |
| AC-F-1.1-004 | tests/acceptance/auth/test_signup.py | 정규화 이메일 고유성 |
| AC-F-1.1-005 | tests/contract/auth/test_signup_contract.py | 필드별 422 계약 |
| AC-F-1.1-006 | tests/integration/auth/test_signup_repository.py | 트랜잭션 롤백 |
| AC-F-1.1-007 | tests/acceptance/auth/test_signup.py | 인증 발송은 후속 기능 |
| AC-F-1.1-008 | tests/integration/auth/test_signup_repository.py, tests/contract/auth/test_signup_contract.py | DB·ERD·OpenAPI |
