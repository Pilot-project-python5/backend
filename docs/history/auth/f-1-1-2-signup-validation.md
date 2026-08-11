---
feature_id: "F-1.1.2"
title: "가입 정보 검증"
requirement_id: "FR-1"
domain: "auth"
status: "implemented"
completed_on: "2026-08-11"
feature_packet: "docs/features/auth/f-1-1-2-signup-validation"
pull_request: null
commit: null
---

# F-1.1.2 가입 정보 검증 구현 이력

## 구현 요약

사용자는 계정을 생성하기 전에 전체 가입 정보의 형식과 의미, 로그인 아이디·이메일
중복을 한 번에 확인할 수 있다. 검증은 사용자·건강 프로필을 만들거나 비밀번호를
해시하지 않으며, 미래 생년월일과 중복 항목을 결정적인 issue 목록으로 반환한다.

## 구현 범위

### 포함

- POST /api/v1/auth/signup/validation 공개 API
- F-1.1 SignupRequest를 재사용한 전체 가입 필드 형식·범위 검증
- fake clock 기반 미래 생년월일 판정
- 정규화 로그인 아이디·이메일 중복 일괄 조회
- valid와 field·code·message issue 응답
- 422 요청 검증과 503 DB 실패 계약, Swagger/OpenAPI와 자동 테스트

### 제외

- 사용자·건강 프로필 생성과 비밀번호 해시
- 아이디·이메일 예약 또는 선점
- 이메일 인증번호 생성·발송·확인
- 속도 제한, 봇 방지, 로그인과 세션
- DB 스키마·마이그레이션·ERD·시드 변경

## 주요 구현 내용

라우터가 F-1.1과 같은 SignupRequest로 필수값, 문자열·이메일 형식, 비밀번호 확인,
성별과 신체 범위를 먼저 검사한다. 서비스는 주입된 Clock으로 미래 생년월일을
판정하고 아이디·이메일을 기존 규칙으로 정규화한다. 저장소는 한 PostgreSQL 읽기
쿼리로 두 고유 값의 충돌을 모으며 서비스는 login_id, email, birth_date 순서로
issue를 만들어 valid를 결정한다.

## API 변경

- 신규 API: POST /api/v1/auth/signup/validation
- 인증: 불필요
- 요청: F-1.1 SignupRequest 전체 필드
- 성공: 200과 valid, issues. issue는 field, code, message를 포함한다.
- 오류: 422 VALIDATION_FAILED, 503 SERVICE_UNAVAILABLE
- operation_id: auth_validate_signup
- 생성된 openapi.json에 요청 재사용, 응답 스키마와 오류 예시를 반영했다.

## 데이터·ERD·마이그레이션

데이터 구조는 변경하지 않았다. F-1.1의 users.normalized_login_id와 normalized_email
고유 인덱스를 읽기 조회에 재사용한다. 테이블·관계·제약·인덱스·시드·마이그레이션과
docs/architecture/erd.md 변경은 없으며 Alembic autogenerate 검사에서 신규 작업이
없음을 확인했다.

## 보안과 개인정보

공개 회원가입 보조 API이므로 인증과 소유권 검사는 적용하지 않는다. 요청의 비밀번호,
비밀번호 확인, 이메일과 건강정보를 응답하거나 로그에 포함하지 않고 해시도 만들지
않는다. 기능 목적상 아이디·이메일 중복 여부를 field issue로 공개하므로 운영 공개 전
속도 제한과 봇 방지가 필요하다. DB 오류 상세와 사용자 행은 노출하지 않는다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-1.1.2-001~006 연결 테스트 | 17개 통과 |
| 대상 기능 검사 | make feature-check FEATURE=F-1.1.2 | 17개 통과 |
| 전체 로컬 검증 | make verify | 77개 통과, 커버리지 97.38%, Ruff·mypy·ERD·Alembic·시드·OpenAPI 통과 |

## 주요 결정과 근거

- 요청 스키마를 회원가입과 공유해 사전 검증과 실제 가입의 형식 규칙 차이를 막았다.
- 형식 오류는 공통 422로 처리하고, DB 조회가 필요한 중복과 기준일이 필요한 미래
  생년월일은 200의 issue로 일괄 반환해 가입 폼이 한 번에 수정할 수 있게 했다.
- 중복 조회를 한 쿼리로 수행하고 issue 순서를 고정해 응답과 테스트를 결정적으로
  유지했다.
- 사전 검증으로 식별자를 예약하지 않고 실제 가입의 UNIQUE와 409를 최종 기준으로
  유지해 경쟁 요청을 안전하게 처리한다.

## 알려진 제약

valid=true 직후 다른 요청이 먼저 가입할 수 있으므로 클라이언트는 실제 회원가입의
409 중복 오류도 처리해야 한다. 로컬 MVP에는 공개 검증 API의 속도 제한과 봇 방지가
포함되지 않는다.

## 후속 작업

- F-1.1.3 이메일 인증
- F-1.2 로그인
- 운영 공개 전 가입 보조 API 속도 제한과 봇 방지 정책

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/auth/f-1-1-2-signup-validation
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
