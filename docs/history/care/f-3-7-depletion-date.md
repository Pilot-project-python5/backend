---
feature_id: "F-3.7"
title: "예상 소진일"
requirement_id: "FR-3"
domain: "care"
status: "implemented"
completed_on: "2026-08-14"
feature_packet: "docs/features/care/f-3-7-depletion-date"
pull_request: "https://github.com/Pilot-project-python5/backend/pull/20"
commit: "65db07b"
---

# F-3.7 예상 소진일 구현 이력

## 구현 요약

로그인 사용자는 복용 제품 등록 직후 예상 소진일을 확인하고, 활성 목록에서 현재
날짜 기준 D-day를 함께 조회할 수 있다. 총수량이 일일 사용량으로 나누어떨어지지
않으면 마지막 부분 복용도 하루로 계산하며 기존 복용 계획에도 같은 공식이 적용된다.

## 구현 범위

### 포함

- 총수량·회당 복용량·하루 횟수·복용 시작일 기반 예상 소진일 계산
- 등록 시 예상 소진일 영속화와 기존 CareItem 일괄 백필
- 등록 응답의 `expected_depletion_date`, 목록 응답의 예상일·`days_until_depletion`
- PostgreSQL 제약·인덱스, ERD·OpenAPI, 단위·계약·통합·인수 테스트

### 제외

- 실제 복용 기록에 따른 잔량 차감과 누락·추가 복용 보정은 포함하지 않았다.
- 재구매 상태, 화면·이메일 알림과 유통기한 알림은 후속 기능으로 분리했다.
- 복용 계획 수정·일시 중단·재개와 삭제 항목 복원은 포함하지 않았다.

## 주요 구현 내용

- 일일 사용량은 `dose_per_intake × intakes_per_day`, 필요 일수는 Decimal 나눗셈의
  올림으로 계산하고 시작일을 첫날로 포함해 `시작일 + 필요 일수 - 1일`을 저장한다.
- 등록 서비스는 계산 날짜가 Python·PostgreSQL 지원 범위를 넘으면 쓰기 전에 공통
  422 `DEPLETION_DATE_OUT_OF_RANGE`로 변환해 불완전한 계획을 만들지 않는다.
- 목록 서비스는 저장된 예상일과 `APP_TIMEZONE`의 오늘 차이를 계산한다. 소진 당일은
  0, 지난 계획은 음수로 반환하며 D-day 자체는 저장하지 않는다.
- 기존 사용자 소유권·소프트 삭제 필터와 DB 장애의 503 변환을 그대로 재사용했다.

## API 변경

- `POST /api/v1/care/items` 성공 응답에 ISO 날짜 `expected_depletion_date`를 추가했다.
- `GET /api/v1/care/items` 각 항목에 `expected_depletion_date`와 부호 있는 정수
  `days_until_depletion`을 추가했다.
- 요청 계약과 인증 방식은 바꾸지 않았다. 인증 없음은 401, DB 장애는 503이며 날짜
  범위 초과 등록은 422 `DEPLETION_DATE_OUT_OF_RANGE`다.

## 데이터·ERD·마이그레이션

- 0016 마이그레이션으로 `care_items.expected_depletion_date DATE NOT NULL`을 추가했다.
- 기존 행을 서비스와 같은 올림·시작일 포함 공식으로 백필한 뒤 시작일 이상 CHECK와
  `(expected_depletion_date, user_id)` 조회 인덱스를 적용했다.
- downgrade는 새 열·인덱스·제약만 제거하고 기존 CareItem을 보존한다.
- 논리 ERD와 개념 데이터 모델을 저장 날짜와 비저장 D-day 파생 규칙에 맞게 갱신했다.
- 새 시드 데이터는 필요하지 않으며 기존 6개 시드 세트의 멱등성을 재검증했다.

## 보안과 개인정보

- 기존 access JWT와 서버 refresh session 검증을 재사용하고 요청에서 user_id를 받지 않는다.
- 목록은 현재 사용자의 삭제되지 않은 항목만 읽고 다른 사용자·삭제 항목을 제외한다.
- 예상일과 D-day 외 개인정보를 새로 응답하거나 사용자 복용 정보를 로그에 남기지 않았다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-3.7-001~005 단위·계약·통합·인수 테스트 | 5개 조건 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-3.7` | 40개 통과 |
| 전체 로컬 검증 | `make verify` | 383개 통과, 커버리지 95.65% |
| 정적 검사 | ruff format/check, mypy | 모두 통과, 소스 198개 타입 검사 |
| 데이터·ERD | 0016 왕복·백필, alembic check, ERD validator | 모두 통과 |
| 시드·API | 전체 시드 연속 2회, OpenAPI 일치 검사 | 6세트·82건 멱등, 계약 일치 |

## 주요 결정과 근거

- 마지막 부분 복용도 실제 소진이 일어나는 마지막 날 하루로 계산한다. 내림 계산으로
  제품이 남았는데 소진 처리되는 오류를 막기 위해서다.
- 예상 소진일은 등록 시 저장하고 D-day는 조회 시 계산한다. 후속 알림이 동일한 기준
  날짜를 재사용하면서도 날짜 경과 때문에 D-day 저장값이 오래되는 문제를 피한다.
- 복용 시작일은 첫 복용일로 포함한다. 사용자가 입력한 시작일과 달력상의 마지막
  복용일을 직관적으로 일치시키기 위해서다.
- 극단적인 수량으로 지원 날짜 범위를 넘는 계획은 등록 단계에서 거부한다. DB 저장
  실패로 노출하기보다 수정 가능한 입력 오류로 명확하게 안내하기 위해서다.

## 알려진 제약

- 예상일은 예정 복용량 기준이며 실제 복용 누락·추가 복용을 반영하지 않는다.
- 1차에는 복용 계획 수정 API가 없어 등록 뒤 계산 입력이 바뀌지 않는 것을 전제로 한다.
- 앱 시간대가 변경되면 같은 UTC 시각의 D-day 경계도 바뀌므로 운영 설정을 명시적으로
  관리해야 한다.

## 후속 작업

- F-3.8에서 이 예상일을 기준으로 재구매 필요 상태와 알림 대상을 만든다.
- F-3.9·F-3.12에서 화면 알림 조회·확인과 이메일 전송을 구현한다.
- F-3.10·F-3.11에서 의약품 정보와 유통기한 관리 계약을 별도 구현한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/care/f-3-7-depletion-date
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
