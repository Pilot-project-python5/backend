# F-3.3 구매 및 보유 수량

## 목표

구매한 제품의 최초 총수량과 그 수량이 의미하는 정·캡슐·스쿱·포 단위를 구매
항목에 함께 보존한다. 같은 제품을 소진 전에 다시 구매해도 과거 항목의 수량을
덮어쓰거나 합산하지 않고 독립 구매 이력으로 남긴다.

## 사용자 이야기

사용자로서, 같은 제품을 여러 번 구매하더라도 각 구매분의 수량과 단위를 구분해
재고·소진 이력을 정확히 관리하고 싶다.

## 비즈니스 규칙

1. F-3.1의 `total_quantity`는 해당 CareItem이 처음 등록될 때의 구매 총수량이며
   실제 복용으로 자동 차감되는 현재 잔량이 아니다.
2. 수량 단위는 클라이언트 요청으로 받지 않고 등록 대상 Product의 `unit_form`을
   `quantity_unit`으로 복사한다.
3. 허용 수량 단위는 TABLET·CAPSULE·SCOOP·PACKET이다.
4. 등록 후 Product의 `unit_form`이 변경돼도 기존 CareItem의 `quantity_unit`은
   갱신하지 않는다.
5. 동일 사용자가 같은 제품을 다시 등록하면 기존 CareItem의 수량을 수정·합산하지
   않고 새로운 CareItem과 새 UUID를 생성한다. 기존 항목이 아직 미소진이어도 같다.
6. 구매일·총수량·복용 계획 검증과 오류 계약은 F-3.1을 그대로 적용한다.
7. 영양제 재등록은 각 CareItem 아래 F-3.2 성분 스냅샷도 독립적으로 생성한다.
8. 기존 CareItem은 0013 적용 시점에 연결된 Product의 `unit_form`으로 한 번
   백필하고 이후 변경하지 않는다.

## 포함 범위

- 등록 시 제품 수량 단위 스냅샷 생성
- 구매 총수량의 불변 초기 수량 의미 확정
- 미소진 여부와 무관한 독립 재구매 항목 보존
- 기존 CareItem 수량 단위 백필
- ORM·0013 마이그레이션·ERD·OpenAPI 문서
- 단위·통합·계약·인수 테스트

## 제외 범위

- 실제 복용 기록에 따른 잔량 차감
- 여러 CareItem의 수량 합산·병합·이전
- 구매 항목 수정·삭제·목록 조회
- 예상 소진일·D-day·LOW_STOCK·DEPLETED 계산
- 유통기한·알림
- 수량 단위 변환과 제품 카탈로그 쓰기 API
- AWS·AI 연결

## 시나리오

### 기본 흐름

1. 로그인 사용자가 제품과 구매일·총수량·복용 계획을 등록한다.
2. 저장소가 Product의 `unit_form`을 읽고 새 CareItem의 `quantity_unit`으로 복사한다.
3. 영양제면 F-3.2 성분 스냅샷도 같은 트랜잭션에서 생성한다.
4. API가 기존 등록 값과 `quantity_unit`을 201로 반환한다.

### 실패와 경계

- 인증·제품 없음·날짜·수량·DB 장애는 F-3.1 계약을 유지한다.
- Product 단위가 나중에 바뀌어도 과거 CareItem 단위는 바뀌지 않는다.
- 동일 제품 재등록은 비멱등 생성이며 기존 항목을 수정하지 않는다.
- 새 영양제 구매 항목은 새 수량 단위와 성분 스냅샷을 각각 보존한다.

## 미결 질문

- 없음. 미소진 여부와 무관하게 재구매를 독립 CareItem으로 보존하고, 수량 단위는
  Product.unit_form의 등록 시점 스냅샷으로 관리하는 권장안을 승인했다.

## 추적성

- 요구사항: FR-3
- 로컬 요구사항: docs/product/requirements.md
- 관련 로컬 문서: docs/features/care/f-3-1-care-item-registration,
  docs/features/care/f-3-2-supplement-nutrients, docs/architecture/erd.md,
  docs/api/care.md
- 외부 출처 URL(선택): https://app.notion.com/p/3b82779e926281ef83c3ceef2fbe18cb
- 마지막 검토일: 2026-08-12
