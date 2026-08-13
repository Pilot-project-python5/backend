---
feature_id: "F-3.4"
title: "복용 제품 조회·삭제"
requirement_id: "FR-3"
domain: "care"
status: "implemented"
completed_on: "2026-08-13"
feature_packet: "docs/features/care/f-3-4-care-item-query-delete"
pull_request: null
commit: null
---

# F-3.4 복용 제품 조회·삭제 구현 이력

## 구현 요약

로그인 사용자는 자신이 등록한 삭제되지 않은 영양제·의약품 구매 항목을 최신순 페이지로
조회할 수 있다. 같은 제품의 재구매분도 합치지 않고 독립 항목으로 보여주며, 항목 삭제는
구매·성분 이력을 보존하는 소프트 삭제로 처리해 이후 활성 목록에서 제외한다.

## 구현 범위

### 포함

- 현재 사용자 소유 활성 CareItem의 최신순 페이지 목록
- 비게시 제품을 포함한 현재 Product 유형·브랜드·이름·이미지 표시 정보
- 독립 재구매 항목과 등록 시점 구매·복용·수량 스냅샷 응답
- 사용자 소유 활성 항목의 deleted_at·updated_at 소프트 삭제
- 타 사용자·미존재·기삭제 항목의 동일 404 처리
- 0014 nullable 삭제 시각·시간 CHECK·활성 목록 부분 인덱스와 ERD
- 단위·계약·통합·인수·마이그레이션 테스트와 Swagger/OpenAPI 문서

### 제외

- 단일 CareItem 상세와 복용 계획·수량 수정 API는 추가하지 않았다.
- 삭제 복원·휴지통·삭제 이력 목록·보존 기간 만료 후 물리 정리는 제공하지 않는다.
- 영양성분 스냅샷 외부 조회와 실제 잔량·섭취량·소진일 계산은 포함하지 않았다.
- 재고·유통기한 상태와 화면·이메일 알림은 후속 기능으로 유지했다.
- AWS·AI와 외부 서비스 의존성을 추가하지 않았다.

## 주요 구현 내용

- 목록 저장소가 인증 user_id와 `deleted_at IS NULL`을 한 쿼리 경계로 사용해 total과
  Product join 페이지를 조회한다.
- 목록은 `created_at DESC, id DESC`로 정렬하고 total과 page·page_size로 has_next를
  계산한다. 범위를 넘는 페이지는 전체 total과 빈 items를 반환한다.
- Product 게시 여부는 등록된 사용자 항목의 가시성 조건으로 사용하지 않는다.
- 목록 수량은 DB scale과 무관하게 불필요한 끝자리 0을 제거한 Decimal 문자열로
  직렬화한다.
- 삭제 저장소는 item ID·인증 user_id·활성 조건을 한 UPDATE에 포함하고 서버 시각을
  deleted_at과 updated_at에 함께 기록한다.
- 영향 행이 없으면 소유권이나 과거 존재 여부를 추가 조회하지 않고 동일 404로 변환한다.
- DB 예외는 rollback 후 503으로 변환하며 CareItem과 성분 스냅샷은 물리 삭제하지 않는다.

## API 변경

- `GET /api/v1/care/items` 보호 목록 API를 추가했다. page 기본 1·1 이상,
  page_size 기본 20·1~100이며 items·page·page_size·total·has_next를 반환한다.
- 항목 응답은 CareItem과 현재 Product 표시 필드를 제공하고 user_id·deleted_at·성분
  스냅샷은 노출하지 않는다.
- `DELETE /api/v1/care/items/{care_item_id}` 보호 API를 추가했고 성공은 본문 없는 204다.
- 목록 200과 삭제 204는 `Cache-Control: no-store`를 포함한다.
- 두 API는 AccessCookieAuth를 사용하며 401 `AUTH_REQUIRED`, 422
  `VALIDATION_FAILED`, 503 `SERVICE_UNAVAILABLE`를 공통 적용한다.
- 삭제의 타 사용자·미존재·기삭제는 404 `CARE_ITEM_NOT_FOUND`로 통일했다.
- 기존 `POST /api/v1/care/items` 요청·응답·상태 코드는 변경하지 않았다.

## 데이터·ERD·마이그레이션

- Alembic `20260813_0014_care_item_soft_delete`가 care_items에 nullable
  `deleted_at TIMESTAMPTZ`를 추가한다.
- `deleted_at IS NULL OR deleted_at >= created_at` CHECK를 ORM·0014·ERD에 적용했다.
- `(user_id, created_at, id) WHERE deleted_at IS NULL` PostgreSQL 부분 인덱스를 추가해
  활성 최신순 목록의 필터·정렬을 지원한다.
- 기존 CareItem은 별도 백필 없이 deleted_at NULL인 활성 상태로 유지한다.
- 0014 downgrade는 부분 인덱스·CHECK·deleted_at만 제거하고 CareItem과 F-3.2 성분
  스냅샷을 보존하며 재-upgrade할 수 있다. 단, 삭제 상태 자체는 복원되지 않는다.
- 사용자 데이터이므로 운영 시드를 추가하지 않았고 기존 기준 시드도 변경하지 않았다.

## 보안과 개인정보

- 기존 access JWT와 서버 refresh session 동시 검증을 목록·삭제에 그대로 적용했다.
- 목록 count·조회와 삭제 UPDATE 모두 인증 user_id를 조건으로 사용하며 요청에서
  user_id를 받지 않는다.
- 타 사용자 항목은 미존재·기삭제와 같은 오류로 응답해 존재 여부를 숨긴다.
- 복용 제품·구매일·복용 계획·수량은 건강 관련 사용자 데이터로 취급해 no-store를
  적용하고 사용자·CareItem ID와 전체 계획을 새 로그에 남기지 않았다.
- 실제 개인정보·건강정보·비밀정보를 시드나 테스트 고정 데이터에 사용하지 않았다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-3.4-001~007을 단위·계약·통합·인수·마이그레이션 테스트에 연결 | 7개 조건 모두 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-3.4` | 21개 통과 |
| 전체 로컬 검증 | `make verify` | 343개 통과, 커버리지 95.97% |
| 정적 검사 | `ruff format --check`, `ruff check`, `mypy` | 모두 통과, 소스 176개 타입 검사 |
| 데이터·ERD | 0013→0014 upgrade·downgrade·재-upgrade, ERD validator, `alembic check` | 기존 행 활성 유지·이력 보존·스키마 일치 통과 |
| 시드 | 전체 시드 연속 2회 실행 | 각 5세트·16건으로 멱등 통과 |
| API 확인 | `make openapi`, 전체 OpenAPI 일치 검사 | 목록·삭제·인증·오류·예시 반영 및 일치 |

## 주요 결정과 근거

- 물리 삭제 대신 deleted_at 소프트 삭제를 선택했다. 향후 소진·알림 상태가 참조할
  구매·성분 이력과 F-3.3의 독립 재구매 정책을 보존하기 위해서다.
- 별도 상태 문자열 대신 nullable 시각을 사용했다. 현재 필요한 상태는 활성·삭제뿐이고
  삭제 시각도 보존해야 하므로 가장 작은 모델이다.
- 이미 삭제된 항목의 반복 DELETE는 204가 아니라 404로 확정했다. API가 다루는 자원이
  “현재 사용자의 활성 항목”이므로 첫 삭제 뒤에는 같은 활성 자원이 없기 때문이다.
- 제품 표시 정보는 현재 Product를 join하고 구매 시점 스냅샷을 추가하지 않았다.
  F-3.4 목적은 현재 목록 표시이며 계산 불변성은 CareItem 수량·성분 스냅샷이 담당한다.
- 삭제 여부를 API에 노출하지 않고 활성 항목만 제공해 1차 프론트엔드 계약을 단순하게
  유지했다.

## 알려진 제약

- 삭제 항목을 조회하거나 복원할 수 없으며 영구 정리 시점도 정하지 않았다.
- 제품 브랜드·이름·이미지는 현재 카탈로그 값이므로 운영자가 수정하면 목록 표시도
  바뀐다.
- offset 페이지네이션이므로 대량 데이터의 깊은 페이지 성능은 후속 규모 검증이 필요하다.
- 삭제 상태를 가진 DB를 0013으로 downgrade하면 행은 보존되지만 다시 활성처럼 보인다.

## 후속 작업

- F-3.5~F-3.6에서 삭제되지 않은 영양제 항목과 성분 스냅샷으로 일일 섭취량·현황을
  계산한다.
- F-3.7~F-3.9에서 활성 CareItem만 대상으로 소진일·재구매 상태·화면 알림을 구현한다.
- F-3.11~F-3.12에서 활성 항목의 유통기한·이메일 리마인더를 구현한다.
- 복원·물리 정리·보존 기간이 필요하면 별도 Feature Packet으로 정책을 확정한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/care/f-3-4-care-item-query-delete
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
