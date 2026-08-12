---
feature_id: "F-3.3"
title: "구매 및 보유 수량"
requirement_id: "FR-3"
domain: "care"
status: "implemented"
completed_on: "2026-08-12"
feature_packet: "docs/features/care/f-3-3-inventory-quantity"
pull_request: "https://github.com/Pilot-project-python5/backend/pull/16"
commit: "eaece5b"
---

# F-3.3 구매 및 보유 수량 구현 이력

## 구현 요약

복용 제품을 등록하면 구매 총수량과 함께 카탈로그 제품의 정·캡슐·스쿱·포 단위를
등록 시점 값으로 보존하고 201 응답에 제공한다. 같은 제품을 소진 전에 다시 구매해도
기존 항목을 수정·합산하지 않고 독립 CareItem으로 생성한다. 실제 복용 기록이 없는
1차 MVP에서는 부정확한 잔량을 별도 저장하지 않는다.

## 구현 범위

### 포함

- Product.unit_form을 CareItem.quantity_unit으로 복사하는 등록 흐름
- 201 응답의 TABLET·CAPSULE·SCOOP·PACKET quantity_unit 필드
- 미소진 여부와 무관한 동일 제품 재구매의 독립 구매 항목 보존
- care_items quantity_unit ORM·0013 백필 마이그레이션·ERD
- 기존 F-3.1·F-3.2 등록·스냅샷 회귀 호환성 보강
- 단위·계약·통합·인수·마이그레이션 테스트와 OpenAPI 갱신

### 제외

- 실제 복용 기록 기반 잔량 차감과 mutable remaining_quantity는 추가하지 않았다.
- 여러 구매 항목의 수량 합산·병합·이전은 제공하지 않는다.
- 구매 항목 조회·수정·삭제는 F-3.4로 분리했다.
- 예상 소진일·D-day·LOW_STOCK·DEPLETED는 F-3.7 이후로 분리했다.
- 유통기한·알림과 AWS·AI 연결은 이번 범위에 포함하지 않았다.

## 주요 구현 내용

- `SQLAlchemyCareItemRepository`가 제품 ID·유형과 unit_form을 함께 조회하고 새
  CareItem에 quantity_unit을 직접 주입한다.
- 클라이언트가 quantity_unit을 보내더라도 요청 모델의 계약 값으로 사용하지 않으며
  서버 카탈로그 단위만 저장·응답한다.
- 같은 제품 재등록 시 기존 행을 조회·갱신하지 않고 매번 새 UUID와 total_quantity를
  저장한다.
- 영양제 등록은 기존 F-3.2 흐름을 유지해 각 새 CareItem 아래 독립 성분 스냅샷도
  같은 트랜잭션으로 생성한다.
- 서비스와 라우터가 저장된 quantity_unit을 제한된 응답 타입으로 전달한다.

## API 변경

- 기존 `POST /api/v1/care/items`의 201 `CareItemResponse`에 `quantity_unit` 필수
  필드를 추가했다. 허용값은 TABLET·CAPSULE·SCOOP·PACKET이다.
- 요청에는 quantity_unit을 추가하지 않고 product_id·구매일·복용 계획·수량 계약을
  유지한다.
- HttpOnly `AccessCookieAuth`, 401 `AUTH_REQUIRED`, 404 `PRODUCT_NOT_FOUND`,
  422 `VALIDATION_FAILED`, 503 `SERVICE_UNAVAILABLE`와 no-store 응답은 같다.
- 사용자 ID와 성분 스냅샷은 응답에 노출하지 않는다.
- additive 응답 확장을 OpenAPI 기준 파일과 변경 기록에 반영했다.

## 데이터·ERD·마이그레이션

- Alembic `20260812_0013_care_item_quantity_unit`이 care_items에
  `quantity_unit VARCHAR(20) NOT NULL`을 추가한다.
- 0012의 기존 CareItem은 연결된 Product.unit_form으로 한 번 백필한 뒤 NOT NULL과
  TABLET·CAPSULE·SCOOP·PACKET CHECK를 적용한다.
- 수량 단독 검색 요구가 없어 신규 인덱스는 추가하지 않았다.
- 0013 downgrade는 quantity_unit 컬럼만 제거하고 CareItem과 F-3.2 성분 스냅샷을
  보존하며 재-upgrade할 수 있다.
- ERD에 quantity_unit과 구매 총량·독립 재구매·불변 단위 정책을 반영했다.
- 사용자 구매 데이터이므로 시드를 추가하지 않았다.

## 보안과 개인정보

- 기존 access JWT와 서버 refresh session 검증을 그대로 적용한다.
- user_id와 quantity_unit을 클라이언트 결정값으로 사용하지 않고 인증 사용자와 DB
  카탈로그 값으로만 새 CareItem을 만든다.
- 구매 수량과 복용 계획은 건강 관련 사용자 데이터로 취급하며 no-store를 유지하고
  사용자·항목 ID와 계획 전체를 새 로그에 남기지 않았다.
- 실제 개인정보·건강정보·비밀정보를 시드나 테스트 고정 데이터에 사용하지 않았다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-3.3-001~007을 단위·계약·통합·인수 테스트에 연결 | 7개 조건 모두 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-3.3` | 6개 통과 |
| 전체 로컬 검증 | `make verify` | 322개 통과, 커버리지 95.99% |
| 정적 검사 | `ruff format --check`, `ruff check`, `mypy` | 모두 통과, 소스 170개 타입 검사 |
| 데이터·ERD | 0012→0013 백필·downgrade·재-upgrade, ERD validator, `alembic check` | 모두 통과, 스키마 차이 없음 |
| 시드 | 전체 시드 연속 2회 실행 | 각 5세트·16건으로 멱등 통과 |
| API 확인 | `make openapi`, 전체 OpenAPI 일치 검사 | additive 응답 확장 반영 및 일치 |

## 주요 결정과 근거

- total_quantity를 현재 잔량이 아닌 최초 구매 총량으로 정의했다. 실제 복용 기록 없이
  잔량을 저장하면 정확하지 않은 상태를 사실처럼 남기기 때문이다.
- 미소진 재구매도 합산하지 않는다. 합치면 구매일·복용 시작일·성분 스냅샷·향후
  유통기한 중 어떤 값을 대표로 삼을지 불명확하고 과거 이력도 훼손된다.
- 수량 단위는 요청받지 않고 Product.unit_form을 스냅샷한다. 클라이언트 불일치와
  이후 카탈로그 변경이 과거 수량 의미를 바꾸는 일을 막기 위해서다.
- 수량 단위 인덱스는 만들지 않았다. F-3.3과 예정된 F-3.4 조회에 단위 필터 요구가
  없고 불필요한 쓰기 비용을 피하기 위해서다.
- 기존 행은 정확한 등록 당시 Product 단위를 알 수 없어 0013 적용 시점 값으로 최선
  백필하고 이후에는 변경하지 않는다.

## 알려진 제약

- total_quantity는 실제 잔량이 아니며 복용 누락·추가 복용을 반영하지 않는다.
- 기존 행의 quantity_unit은 실제 등록 당시 값이 아니라 0013 적용 시점 Product 값이다.
- 구매 항목을 API로 조회·수정·삭제할 수 없다.
- 여러 구매분을 화면에서 어떻게 묶어 보여줄지는 F-3.4 조회 계약에서 정한다.

## 후속 작업

- F-3.4에서 사용자 소유 구매 항목 목록·삭제와 표현 방식을 구현한다.
- F-3.5~F-3.6에서 성분 스냅샷 기반 일일 예정 섭취량과 영양성분 현황을 구현한다.
- F-3.7~F-3.9에서 계획 기준 소진일·재구매 상태·화면 알림을 구현한다.
- F-3.11~F-3.12에서 유통기한과 이메일 리마인더를 구현한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/care/f-3-3-inventory-quantity
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
