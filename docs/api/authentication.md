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

### F-1.1.3 인증번호 발급·재전송·확인

- POST /api/v1/auth/email-verifications는 가입 응답의 user_id로 인증번호를 발급한다.
- POST /api/v1/auth/email-verifications/resend는 60초 이후 새 인증번호를 발급한다.
- POST /api/v1/auth/email-verifications/confirm은 verification_id와 숫자 6자리
  code를 확인한다.
- 코드는 10분간 유효하고 expires_at과 같은 시각부터 만료다.
- 새 코드를 발급하면 이전 미사용 코드는 즉시 무효화되고 실패 횟수는 0으로 시작한다.
- 잘못된 코드는 최대 5회까지 누적하며 5번째 실패부터 해당 코드를 잠근다.
- 잠긴 뒤에도 최초 발급 60초가 지나면 새 코드를 요청할 수 있다.
- 확인 성공 시 users.status를 ACTIVE로 바꾸고 email_verified_at을 기록한다.
- 코드 원문은 응답·로그·DB에 남기지 않으며 발급 ID와 환경 비밀값을 사용한
  HMAC-SHA256 해시만 저장한다.
- 1차 로컬 MVP의 이메일은 Mailpit으로 확인한다. 운영 공개 전 계정·IP 속도 제한과
  운영 이메일 공급자·재시도 큐를 추가해야 한다.

## 세션

### F-1.2 로그인

- POST /api/v1/auth/login은 로그인 아이디와 비밀번호를 받는다.
- 아이디는 trim·casefold 정규화해 조회하며, 미등록 아이디와 틀린 비밀번호는 모두
  401 AUTH_INVALID_CREDENTIALS로 응답한다.
- 이메일 미인증 계정은 403 AUTH_EMAIL_UNVERIFIED, 정지 계정은
  403 AUTH_ACCOUNT_SUSPENDED로 차단한다.
- 액세스 토큰은 15분 HS256 JWT이며, 리프레시 토큰은 14일 불투명 난수 토큰이다.
- 응답 본문에는 토큰을 넣지 않는다. `allyakkkuk_access_token`과
  `allyakkkuk_refresh_token` HttpOnly 쿠키로만 전달한다.
- 두 쿠키는 SameSite=Lax다. 로컬·테스트는 `AUTH_COOKIE_SECURE=false`, HTTPS 배포
  환경은 `AUTH_COOKIE_SECURE=true`를 사용해야 한다.
- 액세스 쿠키 경로는 /api/v1, 리프레시 쿠키 경로는 /api/v1/auth다.
- 로그인 성공마다 별도 refresh_sessions 행을 만들어 다중 기기 로그인을 허용한다.
  DB에는 `AUTH_TOKEN_SECRET`과 세션 ID로 HMAC-SHA256한 리프레시 해시만 저장한다.
- 인증 응답은 Cache-Control: no-store와 Pragma: no-cache를 사용한다.
- 토큰 검증·갱신·회전과 로그아웃은 F-1.3 이후 범위다.
- 프론트엔드와 API가 교차 사이트로 분리되면 SameSite=None+Secure와 별도 CSRF
  방어를 함께 설계해야 한다.

### F-1.3 로그아웃 및 인증 유지

- POST /api/v1/auth/refresh는 요청 본문 없이 refresh 쿠키를 회전한다.
- refresh 원문은 `session UUID.secret` 형식이며 64자 이상 secret 원문은 저장하지
  않는다. session UUID와 secret을 AUTH_TOKEN_SECRET으로 HMAC-SHA256한 값만 저장한다.
- 성공 시 같은 refresh_sessions 행의 token_hash·last_used_at을 갱신하고 새 access·
  refresh 쿠키와 두 만료 시각을 200으로 반환한다.
- access는 갱신 시점부터 15분이다. refresh 만료는 최초 로그인부터 14일로 고정하며
  쿠키 Max-Age는 남은 초로 설정한다.
- 회전된 이전 refresh token을 다시 사용하면 해당 세션을 폐기한다. 클라이언트는 같은
  세션의 refresh 요청을 직렬화해야 한다.
- 누락·형식 오류·미등록·만료·폐기·불일치·비활성 계정은 같은
  401 AUTH_SESSION_INVALID이며 인증 쿠키를 삭제한다.
- POST /api/v1/auth/logout은 일치하는 현재 기기 세션만 폐기하고 두 쿠키를 삭제한다.
  세션이 없거나 이미 무효해도 204인 멱등 API다.
- DB 처리 실패는 503이며 기존 쿠키를 변경하지 않는다.
- F-1.2 형식으로 이미 발급된 로컬 refresh token은 selector가 없어 한 번 재로그인이
  필요하다.
- 현재 사용자 확인과 보호 API access JWT 검증은 F-1.4 범위다.

## Swagger

Swagger에서 로그인·refresh·logout API를 실행한 뒤 동일 출처 요청에서 인증 쿠키
흐름을 검증할 수 있어야 한다. 로컬 프론트엔드 출처와 자격증명 전달 정책은
환경설정으로 관리한다.
