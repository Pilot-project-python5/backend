---
feature_id: "F-1.2"
title: "로그인"
requirement_id: "FR-1"
domain: "auth"
status: "implemented"
completed_on: "2026-08-11"
feature_packet: "docs/features/auth/f-1-2-login"
pull_request: "https://github.com/Pilot-project-python5/backend/pull/6"
commit: null
---

# F-1.2 로그인 구현 이력

## 구현 요약

이메일 인증을 완료한 ACTIVE 사용자는 아이디와 비밀번호로 로그인해 15분 액세스
JWT와 14일 리프레시 토큰을 HttpOnly 쿠키로 받을 수 있다. 미등록 아이디와 틀린
비밀번호는 같은 오류로 처리하며, 리프레시 원문 대신 HMAC 해시만 저장해 기기별 다중
세션을 지원한다.

## 구현 범위

### 포함

- 아이디·비밀번호 확인과 이메일 인증·계정 상태별 로그인 차단
- HS256 액세스 JWT와 고엔트로피 불투명 리프레시 토큰 발급
- refresh_sessions 테이블과 리프레시 HMAC-SHA256 해시 저장
- 액세스·리프레시 HttpOnly·SameSite=Lax 쿠키와 환경별 Secure 설정
- Swagger/OpenAPI의 성공 헤더·오류 계약과 계층별 자동 테스트

### 제외

- 액세스 JWT 검증과 보호 API 인가 의존성
- 리프레시 회전·재사용 탐지·인증 갱신과 로그아웃
- 전체 기기 로그아웃, 세션 목록과 세션 수 제한
- 로그인 실패 속도 제한, 계정 잠금, CAPTCHA와 별도 CSRF 토큰
- AWS 비밀 관리·배포와 AI 연동

## 주요 구현 내용

로그인 서비스는 아이디를 trim·casefold 정규화한 뒤 사용자 행을 잠금 조회한다.
미등록 아이디에도 시작 시 미리 만든 dummy Argon2id 해시를 검증해 계정 존재 여부에
따른 처리 시간 차이를 줄이고, 미등록과 비밀번호 불일치를 같은 401로 변환한다.
올바른 비밀번호가 확인된 뒤에만 이메일 미인증과 정지 상태를 구분해 반환한다.

성공하면 새 세션 UUID를 만들고 issuer·audience·subject·session ID·type·jti·iat·exp를
가진 15분 HS256 JWT와 14일 불투명 리프레시 토큰을 발급한다. 리프레시 원문은 세션
UUID와 AUTH_TOKEN_SECRET으로 HMAC-SHA256한 뒤 해시만 트랜잭션으로 저장한다. 저장이
성공한 뒤 라우터가 두 토큰을 각각의 쿠키에 기록하므로 실패 응답에는 부분 쿠키가 없다.

## API 변경

- POST /api/v1/auth/login: login_id와 password를 받는 공개 API, 성공 200
- 성공 본문: user_id, login_id, name, ACTIVE, authenticated_at과 두 만료 시각
- 액세스 쿠키: allyakkkuk_access_token, Path=/api/v1, Max-Age=900
- 리프레시 쿠키: allyakkkuk_refresh_token, Path=/api/v1/auth, Max-Age=1209600
- 두 쿠키 모두 HttpOnly·SameSite=Lax이며 Secure는 AUTH_COOKIE_SECURE를 따른다.
- 오류: 401 AUTH_INVALID_CREDENTIALS, 403 AUTH_EMAIL_UNVERIFIED 또는
  AUTH_ACCOUNT_SUSPENDED, 422 VALIDATION_FAILED, 503 SERVICE_UNAVAILABLE
- 인증 응답 캐시를 막기 위해 Cache-Control: no-store와 Pragma: no-cache를 반환한다.
- 신규 API이므로 기존 호출과 호환되며 openapi.json과 변경 기록을 갱신했다.

## 데이터·ERD·마이그레이션

20260811_0005 마이그레이션으로 refresh_sessions를 추가했다. id UUID PK, users CASCADE
FK, 64자 token_hash UNIQUE, expires_at, revoked_at, last_used_at, created_at을 저장한다.
만료는 생성 이후여야 하고 폐기·마지막 사용 시각은 값이 있으면 생성 시각 이상이어야
한다. 사용자 세션 이력 조회용 (user_id, created_at) 인덱스와 만료 정리용 expires_at
인덱스를 제공하며 시드 변경은 없다.

논리 ERD·개념 데이터 모델·SQLAlchemy 모델·마이그레이션을 함께 갱신했다. 전용 빈
PostgreSQL에서 전체 upgrade를, 별도 DB에서 직전 20260811_0004부터 head까지 upgrade를
검증했고 두 임시 DB는 확인 후 삭제했다. Alembic 자동 비교에서도 차이가 없었다.

## 보안과 개인정보

비밀번호·액세스 토큰·리프레시 토큰 원문은 응답 본문·DB·애플리케이션 로그에 남기지
않는다. 액세스 JWT 서명과 리프레시 HMAC에는 이메일 인증 비밀값과 분리된
AUTH_TOKEN_SECRET을 사용하며 32자 미만 설정은 시작 단계에서 거부한다. 비밀번호가
확인되기 전에는 사용자 상태를 공개하지 않고, DB 실패는 내부 상세 없이 503으로
변환한다.

로컬 HTTP에서는 AUTH_COOKIE_SECURE=false를 사용하지만 HTTPS 배포 전 true로 바꿔야
한다. SameSite=Lax는 1차 동일 사이트 웹 구성을 전제로 하므로 프론트와 API를 교차
사이트로 배포할 때는 SameSite=None+Secure와 별도 CSRF 방어를 함께 설계해야 한다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-1.2-001~007 연결 테스트 | 성공·오류·토큰·쿠키·다중 세션·DB 실패 경계 통과 |
| 대상 기능 검사 | make feature-check FEATURE=F-1.2 | 기능 연결 테스트 24개 통과 |
| 전체 로컬 검증 | make verify | 120개 통과, 커버리지 94.65%, Ruff·mypy·ERD·Alembic·이중 시드·OpenAPI 통과 |
| 빈 DB 마이그레이션 | 전용 빈 DB upgrade head와 별도 0004→head | 두 경로 통과 후 임시 DB 삭제 |

## 주요 결정과 근거

- 브라우저 스크립트에 토큰을 노출하지 않도록 본문 반환 대신 HttpOnly 쿠키 두 개를
  사용했다.
- 짧게 유지되는 액세스 토큰은 자체 검증 가능한 JWT로, 서버에서 폐기·회전해야 하는
  리프레시 토큰은 불투명 난수와 서버 저장 세션으로 분리했다.
- 리프레시 원문 유출 영향을 줄이기 위해 DB에는 단순 해시가 아닌 서버 비밀값과 세션
  UUID를 포함한 HMAC만 저장했다.
- 사용자별 단일 세션을 덮어쓰지 않고 로그인마다 행을 추가해 기기별 동시 로그인을
  보존했다.
- 계정 열거 가능성을 줄이기 위해 자격 증명 실패를 하나의 코드·메시지로 합치고 상태
  오류는 올바른 비밀번호 확인 후에만 반환한다.

## 알려진 제약

F-1.2는 토큰 발급까지만 구현하므로 액세스 JWT를 실제 보호 API에서 검증하지 않으며,
리프레시 쿠키를 사용한 갱신·회전·재사용 탐지와 로그아웃도 아직 없다. 전역 로그인
속도 제한·계정 잠금·CAPTCHA가 없고, AUTH_TOKEN_SECRET 회전 시 기존 액세스와
리프레시 세션을 단계적으로 유지하는 키 버전 정책도 제공하지 않는다.

로컬 기본 비밀값과 Secure=false는 개발 전용이다. 운영 배포·HTTPS·비밀 저장소·
관측성은 2차 개발에서 연결해야 한다.

## 후속 작업

- F-1.3 로그아웃 및 인증 유지에서 refresh 회전과 현재 세션 폐기 구현
- F-1.4 세션 상태 확인에서 access JWT 검증과 보호 API 인증 의존성 구현
- 운영 공개 전 로그인 속도 제한·감사 이벤트·키 버전과 CSRF 정책 확정
- 2차 개발에서 AWS 비밀 저장소·HTTPS 배포 설정 연결

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/auth/f-1-2-login
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
