---
feature_id: "F-1.1"
title: "회원가입"
requirement_id: "FR-1"
domain: "auth"
status: "implemented"
completed_on: "2026-08-10"
feature_packet: "docs/features/auth/f-1-1-signup"
pull_request: null
commit: null
---

# F-1.1 회원가입 구현 이력

## 구현 요약

웹 사용자가 이름, 로그인 아이디, 비밀번호, 이메일, 생년월일, 성별, 키와 몸무게를
제출해 이메일 미인증 계정과 건강 프로필을 원자적으로 생성할 수 있다. 로그인
아이디와 이메일은 대소문자와 무관하게 중복을 막고 비밀번호는 Argon2id 해시만
저장한다.

## 구현 범위

### 포함

- POST /api/v1/auth/signup 요청·응답과 Swagger/OpenAPI 계약
- 회원가입 필수값, 로그인 아이디·비밀번호 형식, 성별, 생년월일과 신체정보 검증
- 사용자와 건강 프로필의 PostgreSQL 트랜잭션 저장
- 정규화 로그인 아이디와 이메일 고유 제약 및 경쟁 요청 충돌 처리
- PENDING_EMAIL_VERIFICATION 초기 상태와 Argon2id 비밀번호 해시
- users·health_profiles ORM, Alembic 마이그레이션과 논리 ERD

### 제외

- 아이디 중복 확인 전용 API(F-1.1.1)
- 별도 가입 정보 검증 API(F-1.1.2)
- 인증번호 생성·발송·재전송·확인(F-1.1.3)
- 로그인, 세션 쿠키, 프로필 수정과 계정 삭제
- 운영 이메일, AWS와 AI 연결

## 주요 구현 내용

Pydantic 요청 모델이 필수값과 형식·범위를 검사하고 서비스가 주입된 시계로 미래
생년월일을 거부한다. 서비스는 로그인 아이디와 이메일을 소문자로 정규화하고
Argon2id 해시를 만든 뒤 SQLAlchemy 저장소에 전달한다. 저장소는 사용자를 먼저
flush하고 건강 프로필을 같은 트랜잭션에서 저장하며, 고유 제약 충돌을 안정적인
공개 오류로 변환하고 다른 DB 실패에서는 전체 트랜잭션을 롤백한다.

## API 변경

- 신규 API: POST /api/v1/auth/signup
- 인증: 불필요
- 요청: name, login_id, password, password_confirmation, email, birth_date, gender,
  height_cm, weight_kg
- 성공: 201과 id, login_id, email, PENDING_EMAIL_VERIFICATION 상태,
  email_verification_required=true, created_at
- 오류: 409 AUTH_LOGIN_ID_UNAVAILABLE, 409 AUTH_EMAIL_UNAVAILABLE,
  422 VALIDATION_FAILED, 503 SERVICE_UNAVAILABLE
- 요청·성공·주요 오류 예시를 생성된 openapi.json에 포함했다.

## 데이터·ERD·마이그레이션

- 마이그레이션 20260810_0002가 users와 health_profiles를 생성한다.
- health_profiles.user_id는 PK이자 users.id FK이며 ON DELETE CASCADE다.
- users.normalized_login_id와 users.normalized_email은 각각 UNIQUE다.
- 사용자 상태, 성별, 이름 길이, 키와 몸무게에 CHECK 제약을 적용했다.
- 두 테이블은 created_at과 updated_at을 UTC timestamptz로 저장한다.
- 신규 테이블이므로 백필과 시드 변경은 없다.
- 논리 ERD의 회원·인증 영역과 미확정 이메일 고유성 항목을 실제 계약에 맞게
  갱신했다.

## 보안과 개인정보

비밀번호와 비밀번호 확인은 요청 처리 중에만 사용하고 원문·확인값·해시를 응답과
로그에서 제외한다. 비밀번호는 Argon2id로 해시한다. 이메일과 건강 프로필은
회원가입 응답에 필요한 이메일을 제외하고 반환하지 않으며, DB 제약이나 SQL 오류는
공개 응답에 노출하지 않는다. 회원가입은 공개 API이므로 기존 사용자 소유권 검사는
해당하지 않는다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | F-1.1 표식 인수·계약·통합·단위 테스트 | AC-F-1.1-001~008 충족, 20개 통과 |
| 대상 기능 검사 | make feature-check FEATURE=F-1.1 | 20개 통과 |
| 전체 로컬 검증 | make verify | 47개 통과, 커버리지 97.21%, Ruff·mypy·ERD·Alembic·OpenAPI 통과 |
| 빈 DB 마이그레이션 | 임시 PostgreSQL DB에서 alembic upgrade head | 20260810_0002와 세 테이블 생성 확인 |
| 이전 기준점 업그레이드 | 20260810_0001에서 alembic upgrade head | 20260810_0002 적용 확인 |

## 주요 결정과 근거

- 이메일 인증과 계정 복구에서 계정 식별이 모호해지지 않도록 정규화 이메일을
  고유하게 관리한다.
- 사용자와 건강 프로필의 부분 저장을 막기 위해 하나의 트랜잭션으로 생성한다.
- 동시 요청에도 중복을 막기 위해 애플리케이션 사전 조회 대신 PostgreSQL UNIQUE
  제약을 최종 기준으로 사용한다.
- 비밀번호 보호 기본값으로 Argon2id를 사용하고 교체 가능한 해시 포트 뒤에 둔다.
- 이메일 인증번호 흐름은 별도 정책과 시간 경계를 갖기 때문에 F-1.1.3으로 분리한다.

## 알려진 제약

F-1.1만 적용된 상태에서는 계정이 PENDING_EMAIL_VERIFICATION에 머물며 로그인할 수
없다. 공개 회원가입 요청의 속도 제한과 봇 방지는 1차 로컬 기능 범위에 포함하지
않았고 운영 환경 도입 전에 별도 보안 정책이 필요하다.

## 후속 작업

- F-1.1.1 아이디 중복 확인
- F-1.1.2 가입 정보 검증
- F-1.1.3 이메일 인증
- F-1.2 로그인과 인증 쿠키

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/auth/f-1-1-signup
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
