# F-3.11 유통기한 관리

## 목표

사용자가 구매분별 유통기한을 등록·교정하고 재고 소진과 독립된 만료 상태와 D-day를
조회할 수 있게 해, 후속 화면·이메일 만료 알림의 기준 날짜를 만든다.

## 사용자 이야기

사용자로서, 수량이 남은 제품도 유통기한이 지나기 전에 확인하기 위해 구매 항목별
유통기한과 남은 날짜·상태를 관리하고 싶다.

## 비즈니스 규칙

1. 유통기한은 제품 공통값이 아니라 CareItem 구매분별 날짜다.
2. 기존 클라이언트·행과 사용자가 날짜를 모르는 경우를 위해 등록의 expiration_date는
   선택 값이다. 없으면 날짜·D-day·상태를 모두 null로 반환하고 알림 대상이 아니다.
3. 등록 요청의 날짜를 저장하고 보호된 PUT API는 현재 사용자 소유의 활성 항목 날짜를
   생성 또는 교체한다. 같은 날짜 재요청은 같은 결과인 멱등 갱신이다.
4. days_until_expiration은 `expiration_date - APP_TIMEZONE 오늘`이며 저장하지 않는다.
5. 날짜가 오늘보다 이전이면 EXPIRED, 오늘부터 D-5까지는 EXPIRING_SOON, D-6 이상은
   NORMAL이다. 당일은 만료 전 마지막 날로 EXPIRING_SOON이다.
6. 재고 상태와 유통기한 상태는 독립이다. 수량·예상 소진일과 무관하게 EXPIRED일 수 있다.
7. 과거 날짜도 이미 만료된 구매분 기록을 위해 허용하고 purchase_date와 순서를
   강제하지 않는다.
8. 다른 사용자·삭제·없는 항목은 모두 404 CARE_ITEM_NOT_FOUND이며 삭제 행을 갱신하지 않는다.

## 포함 범위

- 등록 선택 expiration_date 저장·응답
- 활성 목록 expiration_date·days_until_expiration·expiration_status
- 보호된 구매분별 유통기한 PUT 갱신 API
- nullable DATE 마이그레이션·알림 후보 조회 인덱스·ERD·OpenAPI
- KST 날짜 경계·상태·소유권·삭제·장애 테스트

## 제외 범위

- 유통기한 제거 API와 복용 계획·수량 수정
- F-3.8 재고 상태와 F-3.9·F-3.12 알림 생성·전송
- 제조일·개봉일·개봉 후 사용기한과 시간 단위 만료
- 실제 복용·잔량 보정과 제품 카탈로그 공통 유통기한

## 시나리오

### 기본 흐름

- 등록 시 유통기한을 알면 함께 저장하고, 모르면 기존 계약대로 생략한다.
- 사용자가 활성 항목의 날짜를 PUT으로 추가·교정한 뒤 목록에서 날짜·D-day·상태를 본다.
- KST 오늘이 D-6이면 NORMAL, D-5·D-1·D0이면 EXPIRING_SOON, 다음 날이면 EXPIRED다.

### 실패와 경계

- 인증 없음 401, 형식 오류 422, 다른 사용자·삭제·없음 404, DB 장애 503이다.
- 과거 날짜는 200/201로 저장해 즉시 EXPIRED가 되며 같은 날짜 PUT은 멱등이다.
- 0018 upgrade는 기존 행을 null로 유지하고 downgrade는 기존 CareItem을 보존한다.

## 미결 질문

- 없음. 사용자가 모호한 정책의 자율 추론과 근거 문서화를 승인했다. 선택 입력은 기존
  데이터·클라이언트 호환과 실제로 날짜를 모르는 상황을 보존하고, null 상태로 미관리
  항목을 명시하기 위해 채택했다.

## 추적성

- 요구사항: FR-3
- 로컬 요구사항: docs/product/requirements.md
- 관련 로컬 문서: docs/api/care.md, docs/architecture/erd.md,
  docs/features/care/f-3-4-care-item-query-delete,
  docs/features/care/f-3-7-depletion-date
- 외부 출처 URL(선택): 없음
- 마지막 검토일: 2026-08-14
