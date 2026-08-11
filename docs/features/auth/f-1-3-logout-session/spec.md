# F-1.3 로그아웃 및 인증 유지

## 목표

로그인 사용자가 14일 세션 범위 안에서 비밀번호를 다시 입력하지 않고 액세스 토큰을
안전하게 갱신하고, 현재 기기의 서버 세션을 폐기해 로그아웃할 수 있게 한다.

## 사용자 이야기

로그인 사용자로서, 짧은 액세스 토큰이 만료돼도 현재 기기의 유효한 리프레시 세션으로
인증을 이어가고 원할 때 해당 기기만 로그아웃하고 싶다.

## 비즈니스 규칙

1. POST /api/v1/auth/refresh는 요청 본문 없이 refresh HttpOnly 쿠키를 사용한다.
2. 리프레시 원문은 `session UUID.secret` 형식이며 secret은 48바이트 안전 난수다.
3. 세션 UUID로 refresh_sessions를 잠금 조회하고 secret은 저장된 HMAC-SHA256 해시와
   상수 시간 비교한다.
4. 갱신 성공 시 15분 액세스 JWT와 새 리프레시 secret을 발급하고 같은 세션 행의
   token_hash·last_used_at을 원자적으로 바꾼다.
5. 회전해도 refresh_sessions.expires_at은 최초 로그인 시각부터 14일로 고정한다.
   새 refresh 쿠키의 Max-Age는 남은 세션 수명이다.
6. 회전된 이전 토큰이 다시 사용되면 해당 세션의 revoked_at을 기록하고
   401 AUTH_SESSION_INVALID를 반환한다.
7. 누락·형식 오류·미등록·만료·폐기·해시 불일치·비활성 사용자 세션은 모두 같은
   401 AUTH_SESSION_INVALID와 메시지로 응답하고 인증 쿠키를 삭제한다.
8. ACTIVE가 아니거나 email_verified_at이 없는 사용자의 refresh 세션은 폐기한다.
9. POST /api/v1/auth/logout은 refresh 쿠키가 가리키는 현재 세션만 폐기한다.
10. 로그아웃은 쿠키 누락·형식 오류·미등록·만료·이미 폐기·해시 불일치에도 204를
    반환하는 멱등 API이며 성공 응답에서 두 인증 쿠키를 삭제한다.
11. 로그아웃의 해시 불일치는 임의 세션 폐기 공격을 막기 위해 서버 세션을 변경하지
    않는다.
12. DB 조회·회전·폐기 실패는 503 SERVICE_UNAVAILABLE이며 쿠키를 설정하거나
    삭제하지 않는다.
13. refresh와 logout 성공 응답은 Cache-Control: no-store와 Pragma: no-cache를 쓴다.

## 포함 범위

- selector·secret refresh token 형식과 로그인 발급 형식 변경
- 고정 14일 세션 안의 access·refresh token 회전
- 이전 refresh token 재사용 탐지와 현재 세션 폐기
- 현재 기기 세션 로그아웃과 인증 쿠키 삭제
- refresh_sessions의 token_hash·last_used_at·revoked_at 상태 전이
- Swagger/OpenAPI의 쿠키·응답·오류 계약과 자동 테스트

## 제외 범위

- 현재 사용자·세션 상태 조회와 보호 API용 access JWT 검증(F-1.4)
- 전체 기기 로그아웃, 세션 목록과 사용자별 세션 수 제한
- 슬라이딩 14일 만료와 장기 로그인 유지
- 비밀번호 변경·재설정에 따른 전체 세션 폐기
- IP 속도 제한, 별도 CSRF 토큰, 운영 키 회전·AWS 연동

## 시나리오

### 기본 흐름

- 사용자는 로그인으로 selector·secret refresh 쿠키를 받는다.
- 액세스 만료 전후와 무관하게 유효한 refresh 쿠키로 갱신을 요청한다.
- 서버는 같은 세션 행을 회전하고 만료 시각은 보존한 채 새 쿠키와 만료 정보를 준다.
- 사용자가 로그아웃하면 해당 세션만 폐기하고 브라우저의 두 쿠키를 삭제한다.

### 실패와 경계

- expires_at과 같은 시각부터 세션은 만료이며 갱신할 수 없다.
- 이전 토큰 재사용은 새 토큰까지 포함한 해당 세션 전체를 폐기한다.
- 서로 다른 기기 세션은 회전·폐기 상태를 공유하지 않는다.
- 무효한 refresh 요청은 같은 401로 통합하고 로그아웃은 같은 입력에도 204다.
- DB 실패에서는 기존 브라우저 쿠키를 유지해 사용자가 재시도할 수 있게 한다.

## 미결 질문

- 없음. 2026-08-11 사용자가 selector·secret 형식, 매회 회전·재사용 폐기, 고정 14일
  만료, 현재 세션 로그아웃, 통합 401과 F-1.4 분리 권장 계약을 승인했다.

## 추적성

- 요구사항: FR-1
- 로컬 요구사항: docs/product/requirements.md
- 관련 로컬 문서: docs/api/authentication.md, docs/architecture/erd.md,
  docs/features/auth/f-1-2-login
- 외부 출처 URL(선택): 없음
- 마지막 검토일: 2026-08-11
