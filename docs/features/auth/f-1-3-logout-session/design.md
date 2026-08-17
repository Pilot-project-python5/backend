# F-1.3 설계

## API 계약

- POST /api/v1/auth/refresh
  - 인증: yeongyangkkuk_refresh_token 쿠키
  - 요청 본문: 없음
  - 성공: 200과 authenticated_at, access_token_expires_at,
    refresh_token_expires_at, access·refresh Set-Cookie
  - 오류: 401 AUTH_SESSION_INVALID, 503 SERVICE_UNAVAILABLE
- POST /api/v1/auth/logout
  - 인증 재료: yeongyangkkuk_refresh_token 쿠키. 세션이 없어도 호출 가능하다.
  - 요청 본문: 없음
  - 성공: 204와 access·refresh 삭제 Set-Cookie
  - 오류: 유효 세션 DB 처리 실패의 503 SERVICE_UNAVAILABLE
- 두 API 모두 Cache-Control=no-store, Pragma=no-cache를 사용한다.
- refresh는 회전 요청 단위로 비멱등이며 이전 토큰 재사용 시 세션을 폐기한다.
- logout은 반복 호출해도 204인 멱등 API다.

## 데이터 설계

- 엔티티: 기존 users와 refresh_sessions
- 관계와 카디널리티: 변경 없음. 사용자 한 명은 여러 기기 세션을 가진다.
- 제약 조건: 기존 PK·CASCADE FK·token_hash UNIQUE·시간 CHECK를 재사용한다.
- 인덱스: 기존 PK 조회와 (user_id, created_at)·expires_at 인덱스를 유지한다.
- 마이그레이션: 없음. 테이블·컬럼·제약·인덱스를 바꾸지 않는다.
- 백필과 기존 데이터 영향: F-1.2 형식의 기존 로컬 refresh token은 selector가 없어
  401이므로 한 번 재로그인이 필요하다. 저장 행은 만료 정리 전까지 남을 수 있다.
- 이력과 삭제: 회전은 token_hash를 교체하고 last_used_at을 기록한다. 로그아웃,
  재사용 탐지와 비활성 계정은 revoked_at을 기록하며 행을 물리 삭제하지 않는다.

## ERD 영향

- docs/architecture/erd.md 변경: 설명만 예, Mermaid 구조는 아니오
- 변경 전 구조: refresh_sessions에 token_hash, expires_at, revoked_at, last_used_at이
  존재하지만 F-1.3 상태 전이가 확정되지 않았다.
- 변경 후 구조: 동일 구조에서 회전·마지막 사용·폐기의 기록 시점을 설명한다.
- 구조를 변경하지 않는 이유: 승인 동작을 기존 컬럼과 제약으로 모두 표현할 수 있다.
- ERD 검증 방법: validate_erd.py와 Alembic check로 구조 차이가 없음을 확인한다.

## 애플리케이션 흐름

1. 쿠키 원문을 점 하나 기준으로 나누고 canonical UUID selector와 64자 이상 secret을
   검증한다.
2. refresh는 세션과 사용자를 잠금 조회한다.
3. 만료·폐기·계정 상태와 HMAC 해시를 검사한다.
4. 해시 불일치는 같은 트랜잭션에서 세션을 폐기한 뒤 401을 반환한다.
5. 성공 시 기존 expires_at을 보존한 token pair를 만들고 해시·last_used_at을 커밋한다.
6. 커밋 뒤 라우터가 남은 수명을 Max-Age로 설정해 두 쿠키를 교체한다.
7. logout은 토큰이 유효할 때만 잠금 세션을 폐기하고, 그 밖의 입력은 변경 없이 204다.
8. 서비스 성공 뒤 라우터가 두 쿠키를 같은 경로·속성으로 삭제한다.

## 보안과 개인정보

- 소유권 검사: 쿠키 selector의 세션과 secret HMAC이 함께 일치할 때만 회전·로그아웃한다.
- 민감 필드: refresh secret 원문은 메모리와 쿠키에만 있고 DB에는 HMAC만 저장한다.
- 재사용 방어: 회전 뒤 같은 selector의 이전 secret이 오면 세션 전체를 폐기한다.
- 열거 방지: 무효 사유와 계정 상태를 같은 401 코드·메시지로 통합한다.
- 로그 제외 항목: access·refresh token, token_hash, Cookie 헤더와 Set-Cookie 값

## 로컬 어댑터

- 데이터베이스: PostgreSQL 16, SQLAlchemy 동기 세션과 행 잠금
- 시간: SystemClock, 테스트는 FakeClock
- 토큰: 기존 PyJWT·HMAC 발급기를 selector·secret과 고정 만료 회전으로 확장
- 이메일: 사용하지 않음
- 스케줄러: 사용하지 않음

## 호환성

- OpenAPI 영향: 공개 POST API 두 개, 쿠키 파라미터·Set-Cookie·401·503 계약 추가
- 기존 데이터 영향: 신규 스키마는 없지만 기존 형식의 로컬 refresh token은 재로그인
  전까지 사용할 수 없다. access token은 원래 만료 시각까지 유지된다.
- 롤백: session 라우터·서비스·저장소를 제거하고 로그인 refresh 원문 생성을 F-1.2
  방식으로 되돌린다. 이미 selector 형식으로 발급한 refresh token은 롤백 뒤 무효다.
