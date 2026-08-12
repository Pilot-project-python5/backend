---
feature_id: "F-3.2"
title: "영양제 성분 연결"
requirement_id: "FR-3"
domain: "care"
status: "implemented"
completed_on: "2026-08-12"
feature_packet: "docs/features/care/f-3-2-supplement-nutrients"
pull_request: null
commit: null
---

# F-3.2 영양제 성분 연결 구현 이력

## 구현 요약

영양제를 마이케어에 등록하면 해당 시점의 활성 영양성분 ID·이름·단위당 함량·단위를
새 복용 항목 아래에 함께 보존한다. 이후 카탈로그가 바뀌어도 기존 스냅샷은 변하지
않아 후속 일일 섭취량 계산이 등록 당시 값을 사용할 수 있다. 의약품이나 활성 성분이
없는 영양제는 기존처럼 정상 등록되며 외부 API 계약은 바뀌지 않았다.

## 구현 범위

### 포함

- `POST /api/v1/care/items`의 영양제 등록 트랜잭션에 활성 성분 스냅샷 저장 추가
- 복용 항목과 스냅샷 전체의 원자적 커밋·롤백
- 의약품·비활성 성분·활성 성분 없음·반복 등록 경계 처리
- care_nutrient_snapshots ORM·0012 마이그레이션·기존 영양제 행 백필
- ERD·개념 데이터 모델·마이케어 API 문서 갱신
- 단위·계약·통합·인수·마이그레이션 왕복 테스트

### 제외

- 성분별 일일 예정 섭취량·단위 변환·영양소 기준량 계산은 F-3.5 이후로 분리했다.
- 스냅샷 조회·수정·삭제 API는 추가하지 않았다.
- 재구매·재고 병합, 소진일·상태·알림과 유통기한 정책은 후속 기능으로 남겼다.
- 의약품 성분을 영양소 합계에 포함하지 않았다.
- AWS·AI·이메일·스케줄러 연동은 로컬 1차 MVP 범위에서 제외했다.

## 주요 구현 내용

- `SQLAlchemyCareItemRepository`가 제품 유형을 확인하고 SUPPLEMENT인 경우에만 활성
  Nutrient와 ProductNutrient를 정렬 조회한다.
- 조회 결과를 `NutrientSnapshotSource` 값으로 분리한 뒤 새 CareItem ID 아래
  `CareNutrientSnapshot`으로 복사한다.
- CareItem과 모든 스냅샷을 같은 SQLAlchemy 세션에 추가하고 한 번만 commit한다.
  조회·flush·commit 실패는 전체 rollback 후 기존 저장 오류로 변환한다.
- 한 복용 항목 안의 동일 영양성분은 DB 고유 제약으로 차단하고, 동일 제품의 반복
  등록은 서로 다른 복용 항목과 독립 스냅샷 집합을 만든다.
- 등록 이후 카탈로그 행을 수정·비활성화하거나 제품-성분 연결을 삭제해도 과거
  스냅샷을 갱신하는 경로를 두지 않았다.

## API 변경

- 기존 `POST /api/v1/care/items` 내부 저장 동작만 확장했다.
- 요청 필드, 201 `CareItemResponse`, HttpOnly `AccessCookieAuth`, 401
  `AUTH_REQUIRED`, 404 `PRODUCT_NOT_FOUND`, 422 `VALIDATION_FAILED`, 503
  `SERVICE_UNAVAILABLE` 계약은 F-3.1과 같다.
- 요청·응답에 스냅샷 ID, nutrient_id 또는 user_id를 추가하지 않았다.
- 생성된 OpenAPI가 저장소 `openapi.json`과 동일해 Swagger 스키마 변경은 없다.

## 데이터·ERD·마이그레이션

- Alembic `20260812_0012_care_nutrient_snapshots`가 등록 시점 성분 테이블을 추가한다.
- care_items 1:N 관계는 부모 삭제 시 CASCADE하고 nutrients 1:N 관계는 영양성분
  삭제를 RESTRICT한다.
- `(care_item_id, nutrient_id)` UNIQUE, 비공백 1~100자 이름, 양수
  NUMERIC(12,4) 함량, MG·G·MCG·IU 단위 CHECK를 적용했다.
- nutrient_id 조회 인덱스를 추가했고 ORM·마이그레이션·ERD의 필드와 삭제 정책을
  일치시켰다.
- 0011에 이미 존재한 SUPPLEMENT 복용 항목은 0012 적용 시점의 활성 카탈로그로
  한 번 백필한다. 의약품·비활성 성분은 제외하며 downgrade는 기존 care_items를
  보존하고 스냅샷 테이블만 제거한다.
- 사용자 데이터 테이블이므로 운영·개발 시드를 추가하지 않았다.

## 보안과 개인정보

- 기존 access JWT와 서버 refresh session 검증을 그대로 적용한다.
- 클라이언트가 care_item_id나 user_id를 지정하지 못하며, 인증 사용자를 위해 서버가
  새로 만든 CareItem ID에만 스냅샷을 연결한다.
- 스냅샷은 복용 제품에서 파생된 건강 관련 데이터로 취급하고 응답에 노출하지 않으며
  사용자·항목 ID와 성분 집합을 로그에 추가하지 않았다.
- 테스트 데이터는 결정적 가상 값만 사용했고 실제 개인정보·건강정보·비밀정보를
  추가하지 않았다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-3.2-001~007을 단위·계약·통합·인수 테스트에 연결 | 7개 조건 모두 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-3.2` | 11개 통과 |
| 전체 로컬 검증 | `make verify` | 316개 통과, 커버리지 95.98% |
| 정적 검사 | `ruff format --check`, `ruff check`, `mypy` | 모두 통과, 소스 164개 타입 검사 |
| 데이터·ERD | 0011→0012 백필·downgrade·재-upgrade, ERD validator, `alembic check` | 모두 통과, 스키마 차이 없음 |
| API 확인 | `make openapi-check` | 저장소 OpenAPI와 일치, 변경 없음 |

## 주요 결정과 근거

- 계산 시점에 현재 카탈로그를 다시 읽지 않고 등록 시점 값을 복사한다. 카탈로그
  정정이 과거 사용자의 섭취량 계산을 소급 변경하지 않게 하기 위해서다.
- 활성 영양성분만 복사하되 활성 성분이 0개여도 등록을 허용한다. 카탈로그 게시·정비
  상태와 사용자의 복용 등록 가능 여부를 분리하기 위해서다.
- 의약품은 같은 CareItem 등록 흐름을 재사용하지만 영양소 스냅샷을 만들지 않는다.
  의약품 유효성분과 영양소 합계는 서로 다른 도메인으로 유지한다.
- 기존 행의 정확한 등록 당시 성분은 복원할 수 없어 0012 적용 시점 값을 최선 백필로
  사용한다. 이후에는 일반 등록 행과 똑같이 불변으로 둔다.
- API 응답에 스냅샷을 추가하지 않았다. 이번 기능은 후속 계산 입력의 보존 책임이며
  조회 표현은 별도 기능에서 설계하는 것이 기존 클라이언트 호환성에 안전하다.

## 알려진 제약

- 기존 F-3.1 행의 백필 값은 실제 등록 당시 값이 아니라 0012 적용 시점의 카탈로그다.
- 스냅샷을 API로 조회하거나 수정·삭제할 수 없다.
- 서로 다른 단위의 변환·합산과 일일 섭취량은 아직 계산하지 않는다.
- Nutrient는 과거 스냅샷이 참조하면 물리 삭제할 수 없고 비활성화를 사용해야 한다.

## 후속 작업

- F-3.3에서 구매·보유 수량과 재구매 의미를 확정한다.
- F-3.4에서 사용자 소유 복용 항목 조회·삭제와 이력 보존 정책을 구현한다.
- F-3.5~F-3.6에서 스냅샷 기반 일일 섭취량과 영양성분 현황을 계산한다.
- F-3.7 이후에서 소진일·재구매 상태·알림을 구현한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/care/f-3-2-supplement-nutrients
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
