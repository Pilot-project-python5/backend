---
feature_id: "F-1.3"
title: "로그아웃 및 인증 유지"
requirement_id: "FR-1"
domain: "auth"
status: "implemented"
completed_on: "2026-08-11"
feature_packet: "docs/features/auth/f-1-3-logout-session"
pull_request: null
commit: null
---

# F-1.3 로그아웃 및 인증 유지 구현 이력

## 구현 요약

로그인 사용자는 최초 로그인부터 14일인 세션 범위 안에서 refresh 쿠키를 회전해
15분 access JWT를 다시 받을 수 있다. 회전된 이전 토큰의 재사용은 해당 기기 세션을
폐기하고, 로그아웃은 다른 기기 세션에 영향을 주지 않은 채 현재 세션과 브라우저의
인증 쿠키만 제거한다.

## 구현 범위

### 포함

- `session UUID.secret` selector·secret refresh token 발급
- 고정 14일 만료 안의 access·refresh token 회전과 last_used_at 기록
- 이전 refresh token 재사용 탐지와 해당 세션 폐기
- 현재 기기 세션의 멱등 로그아웃과 두 인증 쿠키 삭제
- 통합 401 오류, DB 실패 503과 쿠키 변경 원자성
- Swagger/OpenAPI 쿠키·응답 계약과 단위·계약·PostgreSQL 인수 테스트

### 제외

- 현재 사용자·세션 상태 조회와 보호 API access JWT 검증
- 전체 기기 로그아웃, 세션 목록과 사용자별 세션 수 제한
- 슬라이딩 14일 만료와 장기 로그인 유지
- 비밀번호 변경·재설정에 따른 전체 세션 폐기
- 운영 속도 제한, 별도 CSRF token, 키 버전·회전과 AWS 연동

## 주요 구현 내용

토큰 발급기는 refresh 원문을 세션 UUID selector와 48바이트 안전 난수 secret으로
분리했다. selector로 잠금 세션을 찾고, secret은 세션 UUID와 AUTH_TOKEN_SECRET을
사용한 HMAC-SHA256으로 검증한다. 성공한 refresh는 기존 expires_at을 보존한 새
token pair를 만들고 같은 행의 token_hash와 last_used_at을 한 트랜잭션으로 바꾼다.

회전 뒤 이전 secret을 다시 제출하면 저장 해시 불일치로 판정해 revoked_at을 기록한다.
ACTIVE·이메일 인증 상태가 아닌 사용자 세션도 동일하게 폐기한다. logout은 HMAC까지
일치하는 활성 세션만 폐기하며, 누락·형식 오류·미등록·만료·이미 폐기·해시 불일치는
서버 상태를 바꾸지 않고 204로 끝낸다. 서비스 커밋이 성공한 뒤에만 라우터가 쿠키를
회전하거나 삭제한다.

## API 변경

- POST /api/v1/auth/refresh: refresh HttpOnly 쿠키를 회전하고 200 반환
- refresh 성공 본문: authenticated_at, access_token_expires_at,
  refresh_token_expires_at. 토큰 원문은 본문에 없다.
- refresh 오류: 무효 사유를 통합한 401 AUTH_SESSION_INVALID, DB 실패 503
- POST /api/v1/auth/logout: 현재 세션을 폐기하고 204 반환
- logout은 세션이 없거나 무효해도 204이며 유효 세션 DB 실패만 503이다.
- 성공·401 refresh는 두 쿠키를 설정 또는 삭제하고 DB 실패는 Set-Cookie가 없다.
- 두 API 모두 Cache-Control: no-store와 Pragma: no-cache를 반환한다.
- 신규 API이지만 F-1.2 로컬 refresh 원문 형식은 selector가 없어 재로그인이 필요하다.

## 데이터·ERD·마이그레이션

신규 테이블·컬럼·제약·인덱스와 Alembic 마이그레이션은 없다. F-1.2가 만든
refresh_sessions의 id를 selector로, token_hash를 현재 secret 검증값으로 사용한다.
회전은 token_hash·last_used_at을 갱신하고 로그아웃·재사용·비활성 계정은 revoked_at을
기록한다. expires_at은 갱신하지 않아 최초 로그인부터 14일인 절대 만료를 유지한다.

ERD Mermaid 구조는 유지하고 상태 전이 설명만 갱신했다. Alembic autogenerate check에서
새 작업이 없음을 확인했고 시드 변경도 없다. 전체 검증에서 기존 head 적용과 시드 2회
실행이 통과했다.

## 보안과 개인정보

refresh secret·access JWT·Cookie와 Set-Cookie 값은 응답 본문·DB·로그에 남기지 않는다.
서버는 selector만으로 회전하지 않고 HMAC 상수 시간 비교까지 성공해야 세션을 갱신한다.
무효 세션의 구체 사유와 사용자 상태는 같은 401로 숨긴다. 로그아웃의 해시 불일치는
selector를 아는 공격자가 임의 세션을 폐기하지 못하도록 서버 상태를 변경하지 않는다.

회전 토큰 재사용은 탈취 가능성으로 보고 해당 세션 전체를 폐기한다. 동일 세션의 동시
refresh도 이전 토큰 재사용으로 보일 수 있으므로 클라이언트 요청 직렬화가 필요하다.
SameSite=Lax는 1차 동일 사이트 구성을 전제로 하며 교차 사이트 배포에는 별도 CSRF
방어가 필요하다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-1.3-001~008 연결 테스트 | 발급·회전·재사용·만료·로그아웃·DB 실패·쿠키 계약 통과 |
| 대상 기능 검사 | make feature-check FEATURE=F-1.3 | 42개 통과 |
| 전체 로컬 검증 | make verify | 162개 통과, 커버리지 94.53%, Ruff·mypy·ERD·Alembic·이중 시드·OpenAPI 통과 |
| 스키마 무변경 | 테스트 PostgreSQL에서 alembic check | 새 upgrade 작업 없음 |

## 주요 결정과 근거

- 별도 selector 쿠키나 DB 컬럼을 추가하지 않고 기존 세션 UUID를 refresh 원문 selector로
  포함해 PK 조회와 secret 검증을 분리했다.
- refresh 수명을 갱신마다 14일 연장하지 않고 최초 로그인 기준으로 고정해 탈취 토큰이
  무기한 유지되지 않게 했다.
- 회전은 새 행을 만들지 않고 같은 기기 세션 행의 해시를 교체해 다중 기기 세션 경계를
  유지했다.
- 이전 토큰 재사용 시 최신 token까지 포함한 세션 전체를 폐기해 탈취 신호를 무시하지
  않는다.
- logout은 유효하지 않은 상태에도 204인 멱등 API로 만들어 클라이언트가 서버 세션
  존재 여부를 분기하지 않고 로컬 쿠키를 정리할 수 있게 했다.

## 알려진 제약

F-1.3은 access JWT를 보호 API에서 검증하지 않으므로 로그아웃 뒤 이미 발급된 access
token은 최대 15분 동안 암호학적으로 유효하다. F-1.2의 기존 로컬 refresh token은
selector가 없어 배포 뒤 한 번 재로그인해야 한다.

refresh 요청을 여러 탭에서 동시에 보내면 먼저 성공한 회전 뒤 두 번째 요청이 재사용
탐지로 세션을 폐기할 수 있다. 프론트엔드는 요청을 직렬화해야 하며 서버 측 유예 창은
제공하지 않는다. 전역 속도 제한, 키 버전과 단계적 회전, 감사 이벤트도 아직 없다.

## 후속 작업

- F-1.4 세션 상태 확인과 보호 API용 access JWT 검증 의존성
- 프론트엔드 refresh 요청 단일화와 401 시 로그인 화면 복귀 처리
- 비밀번호 변경 시 전체 세션 폐기와 전체 기기 로그아웃 정책
- 운영 공개 전 속도 제한·감사 이벤트·키 버전·CSRF 정책과 AWS 비밀 관리 연동

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/auth/f-1-3-logout-session
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
