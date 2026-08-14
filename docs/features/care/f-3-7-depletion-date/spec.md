# F-3.7 예상 소진일

## 목표

사용자가 등록한 총수량·회당 복용량·하루 횟수·복용 시작일로 마지막 복용 예정일과
현재 기준 남은 일수를 제공해 소진 상태와 후속 재구매 알림의 안정적인 기준을 만든다.

## 사용자 이야기

사용자로서, 복용 제품이 언제 소진될지 미리 알기 위해 예상 소진일과 D-day를 보고 싶다.

## 비즈니스 규칙

1. 일일 사용량은 `dose_per_intake × intakes_per_day`이며 Decimal로 계산한다.
2. 필요 복용 일수는 `ceil(total_quantity / 일일 사용량)`이다. 나누어떨어지지 않는
   남은 수량도 마지막 부분 복용일 하루로 계산한다.
3. 예상 소진일은 복용 시작일을 첫 복용일로 포함해
   `intake_start_date + 필요 복용 일수 - 1일`이다.
4. 등록 시 예상 소진일을 계산해 CareItem에 저장한다. 1차에는 복용 계획 수정 API가
   없어 값이 바뀌지 않으며 후속 알림이 같은 날짜를 사용한다.
5. 기존 CareItem은 같은 공식으로 전부 백필하고 이후 NOT NULL로 강제한다.
6. 목록의 `days_until_depletion`은 `expected_depletion_date - APP_TIMEZONE 오늘`의
   정수 일수다. 소진일은 0, 지난 날은 음수, 미래 시작 계획도 양수로 반환한다.
7. D-day는 저장하지 않고 조회 시 계산해 날짜 경과에 따른 오래된 상태를 만들지 않는다.
8. 현재 사용자의 삭제되지 않은 항목만 목록에 반환하며 등록 응답에도 예상 소진일을
   포함한다.

## 포함 범위

- 예상 소진일 계산·등록 저장과 기존 행 백필
- POST 등록 응답의 expected_depletion_date
- GET 활성 목록의 expected_depletion_date·days_until_depletion
- PostgreSQL CHECK·인덱스, ERD·OpenAPI·테스트

## 제외 범위

- 실제 복용 기록에 따른 잔량 차감과 누락·추가 복용 보정
- 재구매 필요 상태·알림과 화면 표시 문자열 조합
- 복용 계획 수정·일시 중단·재개와 삭제 항목 복원
- 유통기한과 의약품 별도 복용 규칙

## 시나리오

### 기본 흐름

- 총 60정, 1회 1정, 하루 2회, 8월 1일 시작은 30일을 사용해 8월 30일 소진이다.
- 총 10정, 하루 3정은 4일째의 부분 복용을 마지막 날로 계산한다.
- 조회일이 소진일 3일 전이면 days_until_depletion=3, 소진일이면 0, 다음 날이면 -1이다.

### 실패와 경계

- 기존 양수·범위 검증으로 0 일일 사용량과 0 총수량은 입력될 수 없다.
- 인증 없음은 401, DB 실패는 503이며 다른 사용자·삭제 항목은 목록에 없다.
- 0016 upgrade는 기존 행을 같은 공식으로 백필하고 downgrade는 기존 CareItem을 보존한다.
- 날짜 계산은 주입한 시계와 APP_TIMEZONE으로 UTC 자정 경계를 검증한다.

## 미결 질문

- 없음. 사용자가 2026-08-14 마지막 부분 복용도 하루로 계산하는 권장 계약을 승인했다.

## 추적성

- 요구사항: FR-3
- 로컬 요구사항: docs/product/requirements.md
- 관련 로컬 문서: docs/architecture/erd.md, docs/architecture/data-model.md,
  docs/api/care.md, docs/features/care/f-3-3-inventory-quantity,
  docs/features/care/f-3-4-care-item-query-delete
- 외부 출처 URL(선택): 없음
- 마지막 검토일: 2026-08-14
