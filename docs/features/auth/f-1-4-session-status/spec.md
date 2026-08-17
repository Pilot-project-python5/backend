# F-1.4 세션 상태 확인

## 목표

프론트엔드가 access JWT로 현재 로그인 사용자의 기본·신체 정보와 세션 만료 상태를
조회하고, 이후 보호 API가 공통 인증 의존성을 재사용할 수 있게 한다.

## 사용자 이야기

로그인 사용자로서, 페이지를 열었을 때 현재 인증 상태와 내 정보를 확인하고 access가
만료되면 refresh 또는 재로그인 흐름으로 안전하게 전환하고 싶다.

## 비즈니스 규칙

1. GET /api/v1/auth/me는 요청 본문 없이 `yeongyangkkuk_access_token` HttpOnly 쿠키를
   사용한다.
2. access JWT는 HS256 알고리즘, issuer `yeongyangkkuk`, audience `yeongyangkkuk-api`, type
   `access`와 필수 sub·sid·jti·iat·exp claim을 모두 검증한다.
3. sub·sid·jti는 UUID여야 하며 iat은 현재보다 미래일 수 없고 exp와 같은 시각부터
   만료다.
4. sub 사용자와 sid refresh 세션의 소유 관계를 DB에서 확인한다.
5. 사용자는 ACTIVE이며 email_verified_at이 존재해야 하고, 세션은 미폐기 상태이며
   고정 expires_at 이전이어야 한다.
6. 로그아웃·세션 만료·계정 정지 뒤에는 아직 JWT exp가 남아 있어도 인증을 거부한다.
7. 인증 성공은 authenticated=true, 사용자 기본·신체 정보와 access·refresh 만료
   시각을 반환한다. 비밀번호 해시, 정규화 식별자와 token 값은 반환하지 않는다.
8. 쿠키 누락, JWT 오류, access 만료, 사용자·세션 불일치와 비활성 상태는 사유를
   구분하지 않고 401 AUTH_REQUIRED로 응답한다.
9. DB 조회 실패는 503 SERVICE_UNAVAILABLE로 응답한다.
10. /me는 자동 refresh를 수행하거나 인증 쿠키를 변경하지 않는다. 프론트엔드는
    401이면 POST /auth/refresh를 시도하고, refresh도 401이면 로그인으로 이동한다.
11. 성공 응답은 Cache-Control: no-store와 Pragma: no-cache를 사용한다.

## 포함 범위

- access JWT의 엄격한 claim·서명·시간 검증
- 사용자·건강 프로필·현재 refresh 세션 읽기와 즉시 폐기 반영
- GET /api/v1/auth/me 현재 사용자·세션 상태 응답
- 이후 보호 API가 재사용할 FastAPI 인증 의존성
- Swagger/OpenAPI cookie security scheme, 응답과 오류 계약
- 단위·계약·인수 테스트

## 제외 범위

- access token 자동 갱신과 refresh cookie 검증(F-1.3 API를 명시적으로 호출)
- 프로필 수정, 비밀번호 변경·재설정과 전체 기기 로그아웃
- 세션 목록·기기 정보·사용자별 세션 수 제한
- 역할·관리자 권한과 세분화된 인가 정책
- JWT 비대칭 키, 운영 키 회전, CSRF 확장과 AWS 연동

## 시나리오

### 기본 흐름

- ACTIVE 사용자가 로그인해 access·refresh 쿠키를 받는다.
- 브라우저가 /me를 호출하면 서버가 access JWT와 DB 세션 상태를 확인한다.
- 서버는 현재 사용자 정보와 access·refresh 만료 시각을 반환한다.
- 이후 보호 API는 같은 인증 의존성으로 현재 사용자와 세션을 주입받는다.

### 실패와 경계

- access 쿠키가 없거나 손상·위조·만료되면 401 AUTH_REQUIRED다.
- 다른 사용자의 sid를 담거나 존재하지 않는 사용자·세션을 가리켜도 같은 401이다.
- logout으로 revoked_at이 기록되거나 세션 expires_at에 도달하면 남은 JWT 수명과
  관계없이 같은 401이다.
- 계정이 정지되거나 이메일 인증 상태가 깨진 경우에도 같은 401이다.
- DB 장애는 인증 실패로 숨기지 않고 재시도 가능한 503으로 구분한다.

## 미결 질문

- 없음. 2026-08-11 사용자가 /me, DB 세션 확인에 의한 즉시 무효화, 통합 401,
  명시적 refresh와 재사용 가능한 Access JWT 인증 의존성 권장 계약을 승인했다.

## 추적성

- 요구사항: FR-1
- 로컬 요구사항: docs/product/requirements.md
- 관련 로컬 문서: docs/api/authentication.md, docs/api/errors.md,
  docs/features/auth/f-1-3-logout-session
- 외부 출처 URL(선택): 없음
- 마지막 검토일: 2026-08-11
