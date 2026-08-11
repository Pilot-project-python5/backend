# 인증 계약

## 회원가입

입력 필드:

- name
- login_id
- password
- password_confirmation
- email
- birth_date
- gender
- height_cm
- weight_kg

### F-1.1 계정 생성

- POST /api/v1/auth/signup
- 로그인 아이디는 영문자·숫자 5~20자이며 소문자 정규화 값을 고유하게 관리한다.
- 이메일은 전체 소문자 정규화 값을 계정 전체에서 고유하게 관리한다.
- 비밀번호는 영문자·숫자·특수문자를 포함한 8~20자이며 Argon2id 해시만 저장한다.
- 사용자와 건강 프로필을 하나의 트랜잭션으로 생성한다.
- 가입 직후 상태는 PENDING_EMAIL_VERIFICATION이다.
- 인증번호 생성·발송·확인은 F-1.1.3에서 구현한다.

### F-1.1.1 아이디 중복 확인

- GET /api/v1/auth/login-id/availability?login_id=User123
- 인증 없이 사용할 수 있다.
- 회원가입과 동일하게 영문자·숫자 5~20자만 허용한다.
- 대소문자를 구분하지 않고 users.normalized_login_id로 조회한다.
- 유효한 요청은 200과 login_id, available을 반환한다.
- 조회 결과는 아이디를 예약하지 않으며 회원가입 UNIQUE 제약이 최종 중복을 막는다.
- 잘못된 형식은 422, DB 조회 실패는 503을 반환한다.

### F-1.1.2 가입 정보 검증

- POST /api/v1/auth/signup/validation
- 인증 없이 F-1.1과 동일한 전체 가입 요청을 제출한다.
- 필수값·형식·범위·비밀번호 확인 오류는 422 VALIDATION_FAILED로 반환한다.
- 미래 생년월일과 정규화 아이디·이메일 중복은 200의 valid와 issues로 반환한다.
- issue는 login_id, email, birth_date 순서이며 field, code, message를 포함한다.
- 검증은 비밀번호를 해시하거나 데이터를 저장하고 식별자를 예약하지 않는다.
- 실제 가입의 UNIQUE 제약과 409가 최종 중복 판정 기준이다.
- DB 조회 실패는 503을 반환한다.

## 이메일 인증

- 6자리 코드
- 10분 유효
- 60초 재전송 대기
- 최대 5회 실패
- 인증 전 로그인 불가
- 코드 원문을 영구 저장하지 않는다

## 세션

- 액세스와 리프레시 토큰은 HttpOnly Secure 쿠키를 사용한다.
- 인증 실패는 아이디와 비밀번호 중 어떤 값이 틀렸는지 노출하지 않는다.
- 로그아웃은 현재 리프레시 세션을 폐기한다.
- 토큰 수명, 회전, SameSite와 CSRF 정책은 F-1.2 Feature Packet에서 확정한다.

## Swagger

Swagger에서 로그인 API를 실행한 뒤 동일 출처 요청에서 인증 쿠키 흐름을 검증할 수 있어야 한다. 로컬 프론트엔드 출처와 자격증명 전달 정책은 환경설정으로 관리한다.
