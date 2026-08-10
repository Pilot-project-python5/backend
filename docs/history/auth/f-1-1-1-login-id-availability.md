---
feature_id: "F-1.1.1"
title: "아이디 중복 확인"
requirement_id: "FR-1"
domain: "auth"
status: "implemented"
completed_on: "2026-08-10"
feature_packet: "docs/features/auth/f-1-1-1-login-id-availability"
pull_request: null
commit: null
---

# F-1.1.1 아이디 중복 확인 구현 이력

## 구현 요약

사용자는 회원가입 전에 영문자·숫자 5~20자의 로그인 아이디가 사용 가능한지 공개
API로 확인할 수 있다. 기존 아이디는 대소문자를 구분하지 않고 판정하며 조회 결과는
아이디를 예약하지 않는다.

## 구현 범위

### 포함

- GET /api/v1/auth/login-id/availability 공개 조회 API
- 회원가입과 동일한 로그인 아이디 형식 검증과 소문자 정규화
- 기존 users.normalized_login_id 고유 인덱스를 이용한 존재 여부 조회
- 200 available 응답, 422 검증 오류와 503 DB 실패 계약
- Swagger/OpenAPI와 인수·계약·단위 테스트

### 제외

- 로그인 아이디 예약·선점과 회원가입 수행
- 이메일 중복 확인과 가입 정보 전체 검증
- 속도 제한과 봇 방지
- DB 스키마, 마이그레이션, ERD와 시드 변경

## 주요 구현 내용

Pydantic query 모델이 로그인 아이디 길이와 문자를 검사한다. 서비스는 F-1.1과 같은
함수로 아이디를 소문자 정규화하고, 저장소가 users.normalized_login_id에서 식별자
존재 여부만 조회한다. 조회 실패는 공개 503 오류로 변환하고 정상 조회는 입력 아이디와
available 불리언만 반환한다.

## API 변경

- 신규 API: GET /api/v1/auth/login-id/availability
- 인증: 불필요
- query: login_id, 영문자·숫자 5~20자
- 성공: 200과 login_id, available
- 오류: 422 VALIDATION_FAILED, 503 SERVICE_UNAVAILABLE
- operation_id: auth_check_login_id_availability
- 생성된 openapi.json에 query 제약, 응답 스키마와 오류 예시를 반영했다.

## 데이터·ERD·마이그레이션

데이터 구조는 변경하지 않았다. F-1.1이 생성한 users.normalized_login_id UNIQUE와
고유 인덱스를 읽기 조회에 재사용한다. 테이블·관계·제약·인덱스·시드·마이그레이션과
docs/architecture/erd.md 변경은 없으며 Alembic autogenerate 검사에서 신규 작업이
없음을 확인했다.

## 보안과 개인정보

공개 회원가입 보조 API이므로 인증과 소유권 검사는 적용하지 않는다. 기능 목적상
로그인 아이디의 사용 가능 여부를 공개하지만 계정 상태, 사용자 식별자와 다른
개인정보는 반환하지 않는다. DB 오류 상세도 응답에 노출하지 않는다. 운영 공개 전
속도 제한과 봇 방지는 별도 보안 정책으로 추가해야 한다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-1.1.1-001~005 연결 테스트 | 13개 통과 |
| 대상 기능 검사 | make feature-check FEATURE=F-1.1.1 | 13개 통과 |
| 전체 로컬 검증 | make verify | 60개 통과, 커버리지 97.06%, Ruff·mypy·ERD·Alembic·시드·OpenAPI 통과 |

## 주요 결정과 근거

- 사용할 수 있음과 사용할 수 없음을 모두 200의 available 불리언으로 반환해 가입 폼이
  정상 분기로 처리하게 했다.
- 회원가입과 동일한 정규화 함수를 재사용해 사전 조회와 최종 UNIQUE 판정의 규칙 차이를
  막았다.
- 조회 결과로 아이디를 예약하지 않고 회원가입 DB UNIQUE 제약을 최종 기준으로 유지해
  동시 요청 경쟁을 안전하게 처리한다.
- 데이터 모델 변경이 필요하지 않아 마이그레이션과 ERD 변경을 추가하지 않았다.

## 알려진 제약

사용 가능 응답 직후 다른 요청이 먼저 가입할 수 있으므로 클라이언트는 최종 회원가입의
409 AUTH_LOGIN_ID_UNAVAILABLE도 처리해야 한다. 로컬 MVP에는 공개 조회 속도 제한과
봇 방지가 포함되지 않는다.

## 후속 작업

- F-1.1.2 가입 정보 검증
- F-1.1.3 이메일 인증
- 운영 공개 전 로그인 아이디 조회 속도 제한과 봇 방지 정책

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/auth/f-1-1-1-login-id-availability
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
