# F-1.2 로그인

## 목표

이메일 인증을 마친 사용자가 로그인 아이디와 비밀번호로 인증하고, 이후 API 인증과
세션 갱신에 사용할 액세스·리프레시 쿠키를 안전하게 발급받게 한다.

## 사용자 이야기

ACTIVE 사용자로서, 자격 증명을 제출해 토큰 원문이 응답 본문이나 DB에 노출되지 않는
쿠키 기반 세션으로 로그인하고 싶다.

## 비즈니스 규칙

1. POST /api/v1/auth/login은 로그인 아이디와 비밀번호를 받는 공개 API다.
2. 로그인 아이디는 회원가입과 같은 trim·casefold 정규화 규칙으로 조회한다.
3. 존재하지 않는 아이디와 틀린 비밀번호는 모두 401 AUTH_INVALID_CREDENTIALS와
   같은 메시지를 반환한다. 존재하지 않는 아이디에도 dummy Argon2id 검증을 수행한다.
4. 비밀번호가 맞더라도 email_verified_at이 없거나 상태가
   PENDING_EMAIL_VERIFICATION이면 403 AUTH_EMAIL_UNVERIFIED다.
5. SUSPENDED 사용자는 403 AUTH_ACCOUNT_SUSPENDED다.
6. ACTIVE이면서 email_verified_at이 있는 사용자만 로그인할 수 있다.
7. 액세스 토큰은 HS256 JWT이며 15분 동안 유효하다. issuer, audience, subject,
   session ID, token type, issued-at, expiration과 JWT ID를 포함한다.
8. 리프레시 토큰은 48바이트 이상의 안전한 난수 기반 불투명 토큰이며 14일 동안
   유효하다. 원문 대신 서버 비밀값 기반 HMAC-SHA256 해시만 DB에 저장한다.
9. 로그인 성공마다 새 refresh_sessions 행을 만들어 기기별 다중 로그인을 허용한다.
10. 액세스와 리프레시 토큰은 응답 본문에 포함하지 않고 HttpOnly 쿠키로만 전달한다.
11. 액세스 쿠키 경로는 /api/v1, 리프레시 쿠키 경로는 /api/v1/auth다. 두 쿠키 모두
    SameSite=Lax이며 로컬·테스트 Secure=false, 배포 환경은 설정으로 Secure=true다.
12. 성공 응답은 200과 사용자 ID·아이디·이름·ACTIVE 상태, 인증 시각과 두 토큰의
    만료 시각을 반환하고 Cache-Control: no-store를 사용한다.
13. PostgreSQL 저장 실패는 503 SERVICE_UNAVAILABLE이며 토큰·비밀번호·DB 상세를
    응답이나 로그에 노출하지 않는다.

## 포함 범위

- 로그인 자격 증명 확인과 사용자 상태 차단
- 액세스 JWT와 불투명 리프레시 토큰 발급
- refresh_sessions 이력 테이블과 리프레시 해시 저장
- HttpOnly·SameSite=Lax 쿠키 2개와 Secure 환경 설정
- Swagger/OpenAPI 요청·응답·오류·Set-Cookie 계약
- fake clock·고정 토큰 발급기를 사용하는 자동 테스트

## 제외 범위

- 액세스 토큰 검증 의존성과 보호 API 인가
- 리프레시 토큰 회전·인증 갱신·재사용 탐지
- 로그아웃과 세션 폐기 API
- 전체 기기 로그아웃, 세션 목록과 사용자별 세션 수 제한
- 비밀번호 변경·재설정과 로그인 실패 계정 잠금
- IP 속도 제한, CAPTCHA, 별도 CSRF 토큰과 운영 키 관리

## 미결 질문

- 없음. 2026-08-11에 사용자가 권장 계약의 아이디·비밀번호 로그인, 상태별 오류,
  액세스 15분·리프레시 14일, HttpOnly·SameSite=Lax 쿠키, 로컬 Secure=false,
  기기별 다중 세션과 리프레시 해시 저장을 승인했다.

## 추적성

- 요구사항: FR-1
- 로컬 요구사항: docs/product/requirements.md
- 관련 문서: docs/api/authentication.md, docs/api/errors.md,
  docs/architecture/erd.md, docs/development/testing.md
- 외부 출처 URL(선택): 없음
- 마지막 검토일: 2026-08-11
