---
feature_id: "F-2.4"
title: "추천 제품 정보"
requirement_id: "FR-2"
domain: "curation"
status: "implemented"
completed_on: "2026-08-12"
feature_packet: "docs/features/curation/f-2-4-product-detail"
pull_request: "https://github.com/Pilot-project-python5/backend/pull/11"
commit: "b930113"
---

# F-2.4 추천 제품 정보 구현 이력

## 2026-08-15 민재코치 성분 반영

- 32개 제품의 명시된 핵심 성분을 패키지 한 단위 기준으로 정규화했다.
- CFU와 함량 미기재 혼합 성분은 추정하지 않고 로컬 시드 결정 문서에 제외 근거를 남겼다.

## 구현 요약

방문자는 인증 없이 추천 제품 한 건의 카드 정보, 패키지 형태·총 단위 수와 활성 구성
성분·단위당 함량을 조회할 수 있다. 공개 조건을 만족하지 않는 제품은 같은 404로
숨기고 성분이 없는 제품은 빈 배열로 정상 응답한다. UI 제품 3종의 개발용 성분 기준과
매핑은 로컬 PostgreSQL 시드로 반복 실행해도 승인 상태로 수렴한다.

## 구현 범위

### 포함

- 공개 `GET /api/v1/curation/products/{product_id}`
- F-2.3 목록 공통 필드와 package·nutrients 상세 응답
- 게시·활성 카테고리 공개 조건과 활성 성분 안정 정렬
- nutrients·product_nutrients ORM·마이그레이션·ERD
- 성분 4종·제품별 함량 4건의 결정적 멱등 시드
- 공통 404·422·503 오류와 Decimal 문자열 계약
- 단위·통합·계약·인수 테스트, OpenAPI·개발 문서

### 제외

- 전문가 코멘트는 F-2.4.1, 외부 구매 연결은 F-2.4.2로 분리했다.
- 의약품 효능·복용법·주의·보관 상세는 F-3.10으로 분리했다.
- 영양소 기준량·단위 변환·사용자 섭취 합산은 F-3 계열로 유지했다.
- 관리자 CRUD, 실제 가격 연동, 이미지 업로드, AWS·AI 연결은 제외했다.

## 주요 구현 내용

- `SQLAlchemyProductDetailRepository`가 게시 제품과 활성 카테고리 EXISTS를 함께
  검사해 상세 노출 조건을 한 쿼리 경계로 제한한다.
- 활성 category slug는 category 편집 순서와 slug, 활성 nutrient는 제품별
  `sort_order`와 code로 안정 정렬한다.
- `ProductDetailService`가 미존재·비게시·활성 카테고리 없음 결과를 같은
  `PRODUCT_NOT_FOUND`로, SQLAlchemy 오류를 안전한 503으로 변환한다.
- HTTP 경계에서 Decimal을 불필요한 후행 0 없이 문자열로 변환해 DB scale과 무관한
  정밀 계약을 제공한다.
- 성분 시드는 실제 SKU·code 조회 결과의 UUID로 매핑하므로 자연 키 충돌로 기존 UUID가
  달라도 FK를 보존하고, 시드 제품의 전체 성분 연결을 승인 값으로 복원한다.

## API 변경

- `GET /api/v1/curation/products/{product_id}`
  - 인증: 없음
  - path: UUID product_id
  - 200: 목록 공통 필드, `package`, `nutrients`
  - package: unit_form, Decimal 문자열 units_per_package
  - nutrients: code, name, Decimal 문자열 amount_per_unit, MG/G/MCG/IU unit
  - 404 PRODUCT_NOT_FOUND, 422 VALIDATION_FAILED, 503 SERVICE_UNAVAILABLE
- 기존 F-2.3 목록 응답은 변경하지 않았다.

## 데이터·ERD·마이그레이션

- Alembic `20260812_0008_product_nutrients`가 nutrients와 product_nutrients를 추가한다.
- nutrient는 UUID PK, 고유 code, 비공백 이름, 기준 단위, 활성 여부를 가진다.
- 제품·성분은 복합 PK 매핑으로 N:M이며 양수 단위당 함량, 허용 단위와 0 이상 제품별
  표시 순서를 가진다.
- 제품 삭제 시 매핑을 CASCADE하고 참조 중인 nutrient 삭제는 RESTRICT한다.
- `(is_active, code)`와 `(product_id, sort_order, nutrient_id)` 조회 인덱스를 추가했다.
- 성분 4종과 제품별 함량 4건을 code·SKU 자연 키로 시드한다.
- 테스트 DB에서 0008 downgrade·upgrade와 alembic check를 통과했다.

## 보안과 개인정보

- 공개 기준 카탈로그 읽기라 인증·소유권 검사가 없고 사용자·건강·token 데이터를
  조회하지 않는다.
- 미존재·비게시·활성 카테고리 없음은 같은 404로 처리해 내부 공개 상태를 구분해
  노출하지 않는다.
- SQLAlchemy 바인딩 쿼리를 사용하고 DB 예외·SQL·연결 정보를 공통 503 응답에 넣지 않는다.
- 시드는 개발용 제품 성분만 포함하며 개인정보·건강정보·비밀정보가 없다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-2.4-001~008을 단위·통합·계약·인수 테스트에 연결 | 8개 조건 모두 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-2.4` | 17개 통과 |
| 전체 로컬 검증 | `make verify` | 249개 통과, 커버리지 95.41% |
| 정적 검사 | `ruff format --check`, `ruff check`, `mypy` | 모두 통과, 소스 132개 타입 검사 |
| 데이터·ERD | 0008 downgrade·upgrade, ERD validator, `alembic check`, 시드 2회 | 모두 통과, 스키마 차이 없음 |
| API 확인 | OpenAPI 일치, 로컬 개발 DB migrate·seed와 상세 curl | 실제 package·nutrients 200 확인 |

## 주요 결정과 근거

- 목록과 상세의 필드 의미를 유지하면서 package·nutrients만 추가해 F-2.3 응답을
  가볍게 유지하고 이후 상세 확장을 분리했다.
- DB Numeric의 scale 후행 0이 클라이언트 계약이 되지 않도록 Decimal을 정규화한
  문자열로 제공한다.
- 전역 성분이 아니라 제품별 매핑이 표시 순서를 소유한다. 제품 라벨마다 성분 순서가
  다를 수 있기 때문이다.
- 성분은 향후 기준량·CareItem 스냅샷이 참조하므로 물리 삭제보다 비활성화를 선택하고
  참조 중 삭제를 RESTRICT한다.
- 의약품 상세는 독립 F-3.10 기능이므로 영양제 구성 성분 상세에 섞지 않았다.

## 알려진 제약

- 허용 단위는 MG·G·MCG·IU 네 가지이며 단위 변환은 아직 제공하지 않는다.
- 성분 기준 단위와 제품 함량 단위의 일치는 DB 간 CHECK가 아니라 시드·향후 쓰기
  서비스에서 검증한다.
- 영양제에만 성분 매핑을 허용하는 규칙도 현재 쓰기 API가 없어 시드 경계에서 검사한다.
- 시드 값은 개발·Swagger·프론트엔드 연동용 참고 데이터이며 의료·구매 판단 자료가 아니다.

## 후속 작업

- F-2.4.1에서 전문가 코멘트 모델·시드·상세 응답 확장을 구현한다.
- F-2.4.2에서 활성 외부 구매 링크와 안전한 이동 계약을 구현한다.
- F-3에서 기준량 CSV·단위 변환·성분 스냅샷과 섭취 합산을 구현한다.
- F-3.10에서 의약품 세부 정보와 의약품 시드를 확정한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/curation/f-2-4-product-detail
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
