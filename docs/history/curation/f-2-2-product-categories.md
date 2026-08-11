---
feature_id: "F-2.2"
title: "제품 카테고리"
requirement_id: "FR-2"
domain: "curation"
status: "implemented"
completed_on: "2026-08-12"
feature_packet: "docs/features/curation/f-2-2-product-categories"
pull_request: null
commit: null
---

# F-2.2 제품 카테고리 구현 이력

## 구현 요약

프론트엔드는 인증 없이 제품 카테고리 목록을 조회하고, 안정된 slug를 이후 제품 목록
필터 값으로 사용할 수 있다. 응답은 DB와 무관한 `all`·`전체`를 항상 첫 번째에 두며,
활성 카테고리만 승인된 순서로 제공한다. 비타민·단백질·오메가3 기준 데이터는 로컬
PostgreSQL 시드로 반복 실행해도 같은 상태로 수렴한다.

## 구현 범위

### 포함

- `product_categories` 모델·마이그레이션과 데이터 무결성 제약
- 활성 카테고리 저장소, 가상 전체 항목을 조립하는 서비스와 공개 FastAPI 라우터
- 비타민·단백질·오메가3의 고정 UUID·slug 기반 멱등 시드
- GET /api/v1/curation/categories의 OpenAPI·오류 계약
- 단위·통합·계약·인수 테스트와 ERD·시드 문서

### 제외

- 제품 엔티티와 카테고리 연결, 제품 목록 필터링은 F-2.3으로 분리했다.
- 제품 상세·전문가 코멘트·외부 구매 링크는 F-2.4 계열로 분리했다.
- 카테고리 관리 API, 다국어, 추천 소식, AWS·AI 연동은 포함하지 않았다.

## 주요 구현 내용

- `SQLAlchemyProductCategoryRepository`가 활성 행만 조회하고 `sort_order`, `slug`
  오름차순으로 정렬한다. DB에 잘못 저장된 예약 slug `all`도 공개 목록에서 제외한다.
- `ProductCategoryService`가 저장소 결과 앞에 가상 `all` 항목을 정확히 한 번 붙이고,
  저장소 오류를 내부 상세 없는 503 `SERVICE_UNAVAILABLE`로 변환한다.
- 라우터는 `slug`, `name`만 응답해 내부 UUID·활성 상태·정렬 값을 노출하지 않는다.
- 시드 러너에 `ProductCategorySeedSet`을 등록해 slug 충돌 시 승인 이름·활성·정렬
  순서를 복원한다.

## API 변경

- `GET /api/v1/curation/categories`
  - 인증·요청 본문·쿼리·페이지네이션: 없음
  - 200: `{"items":[{"slug":"all","name":"전체"}, ...]}`
  - 503 `SERVICE_UNAVAILABLE`: PostgreSQL 조회 실패
- 활성 DB 행이 없어도 200과 `all` 한 항목을 반환한다.
- OpenAPI operation ID는 `curation_list_product_categories`이며 보안 정의가 붙지 않는다.

## 데이터·ERD·마이그레이션

- Alembic `20260812_0006_product_categories`가 UUID PK, 고유 slug, 이름·slug·정렬
  CHECK, 모든 필드 NOT NULL인 `product_categories`를 추가한다.
- 공개 목록 조회를 위해 `(is_active, sort_order, slug)` 비고유 인덱스를 추가했다.
- 비타민·단백질·오메가3를 고정 UUID와 자연 키 slug로 시드한다. `all`은 DB에 저장하지
  않는다.
- ERD에는 F-2.2 실제 테이블과 F-2.3 이전 제품 관계 미구현 경계를 명시했다.
- 테스트 PostgreSQL에서 0006 downgrade와 upgrade를 각각 실행했고 `alembic check`에서
  추가 스키마 차이가 없음을 확인했다.

## 보안과 개인정보

- 제품 분류 기준 데이터만 제공하는 공개 읽기 API이므로 인증·소유권 검사는 없다.
- 사용자 입력과 동적 SQL이 없고 사용자·건강·인증 정보를 조회하거나 반환하지 않는다.
- DB 오류 상세는 응답에 포함하지 않고 공통 503 오류로 변환한다.
- 시드에는 고정 카탈로그 정보만 있으며 실제 사용자·이메일·건강정보가 없다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-2.2-001~006을 단위·통합·계약·인수 테스트에 연결 | 6개 조건 모두 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-2.2` | 10개 통과 |
| 전체 로컬 검증 | `make verify` | 210개 통과, 커버리지 94.79% |
| 정적 검사 | `ruff format --check`, `ruff check`, `mypy` | 모두 통과 |
| 데이터·ERD | 0006 downgrade·upgrade, ERD validator, `alembic check`, 시드 2회 | 모두 통과, 스키마 차이 없음 |
| API 계약 | `make openapi` 뒤 전체 검증의 OpenAPI 검사 | `openapi.json` 일치 |

## 주요 결정과 근거

- `all`은 상품 분류가 아니라 필터 미적용 상태이므로 DB 행·제품 관계로 만들지 않고
  서비스가 응답마다 생성한다.
- 운영자가 새 분류를 DB로 추가할 수 있도록 실제 항목은 하드코딩하지 않고 활성 행을
  조회한다. 화면 순서를 예측할 수 있도록 동일 sort_order는 slug로 다시 정렬한다.
- 삭제 대신 `is_active`로 공개 여부를 제어해 이후 제품 관계를 보존할 수 있게 했다.
- 작은 기준 목록이라 페이지네이션을 두지 않고 F-2.3이 같은 slug를 필터 계약으로
  재사용하게 했다.

## 알려진 제약

- 카테고리와 제품의 연결이 아직 없어 이 API만으로 제품 목록을 조회할 수 없다.
- 관리자 API가 없어 기준 데이터 변경은 현재 마이그레이션·시드 또는 DB 관리 절차가
  필요하다.
- 이름은 한국어 단일 값이며 다국어·지역화 구조가 없다.

## 후속 작업

- F-2.3에서 제품·카테고리 관계와 `category` slug 기반 추천 제품 목록 필터를 구현한다.
- F-2.4 계열에서 제품 상세, 전문가 코멘트와 외부 구매 연결을 추가한다.
- AWS 배포와 AI 연결은 2차 개발에서 로컬 어댑터 경계를 유지해 교체한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/curation/f-2-2-product-categories
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
