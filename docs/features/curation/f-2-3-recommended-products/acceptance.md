# F-2.3 인수 조건

## AC-F-2.3-001 공개 전체 목록

전제: 게시 제품 32종이 각각 활성 카테고리에 연결돼 있다.

행동: 인증 없이 기본 쿼리로 GET /api/v1/curation/products를 호출한다.

결과: 200이며 sort_order·sku 순서의 중복 없는 카드 미리보기와 page=1,
page_size=20, 정확한 total·has_next를 반환한다. 내부 is_published·sort_order·시간은
노출하지 않는다.

## AC-F-2.3-002 카테고리 필터와 중복 제거

전제: 한 게시 제품이 여러 활성 카테고리에 연결되고 다른 게시 제품은 별도 카테고리에
연결돼 있다.

행동: 실제 활성 category slug로 조회한다.

결과: 해당 카테고리의 게시 제품만 한 번씩 반환하며 category_slugs는 활성 매핑만
안정된 순서로 포함한다.

## AC-F-2.3-003 비활성·미존재 카테고리

전제: 비활성 카테고리와 존재하지 않는 유효 형식 slug가 있다.

행동: 각각 category로 조회한다.

결과: 두 요청 모두 404 CATEGORY_NOT_FOUND다. 형식이 잘못된 slug는 422다.

## AC-F-2.3-004 게시·활성 연결 경계

전제: 비게시 제품, 활성 카테고리 연결이 없는 제품과 비활성 카테고리에만 연결된 제품이
있다.

행동: all과 실제 category로 목록을 조회한다.

결과: 어느 목록에도 해당 제품이 나타나지 않고 total에도 포함되지 않는다.

## AC-F-2.3-005 페이지 경계

전제: page_size보다 많은 게시 추천 제품이 있다.

행동: 첫 페이지, 다음 페이지와 마지막 페이지 뒤를 조회하고 잘못된 숫자 범위를 보낸다.

결과: 페이지별 항목·total·has_next가 정확하고 범위 밖 빈 페이지는 200이다. page<1,
page_size<1 또는 >100은 422다.

## AC-F-2.3-006 결정적 제품·매핑 시드

전제: 빈 PostgreSQL 또는 승인 값과 제품 매핑이 변경된 로컬 DB가 있다.

행동: 등록된 전체 시드를 두 번 실행한다.

결과: 제품 32종이 SKU별 한 행이고 승인 필드·게시·정렬·카테고리 매핑으로 수렴하며
로컬 image_url은 실제 200 정적 파일을 가리킨다.

## AC-F-2.3-007 DB 실패

전제: 카테고리 확인, count 또는 제품 결과 읽기 중 SQLAlchemy 오류가 발생한다.

행동: 목록을 조회한다.

결과: 빈 정상 응답이 아니라 내부 상세 없는 503 SERVICE_UNAVAILABLE다.

## AC-F-2.3-008 API·Swagger 계약

전제: 실제 API와 생성 OpenAPI를 확인한다.

행동: 추천 제품 목록 operation과 응답을 검사한다.

결과: 공개 무인증, 쿼리 범위·기본값, 200·404·422·503와 응답 예시가 실제 동작과
일치한다.

## 데이터·ERD 인수 조건

빈 PostgreSQL에서 0007이 재현되고 0006과의 downgrade·upgrade가 가능해야 한다.
products와 product_category_mappings의 PK, UNIQUE, FK CASCADE, CHECK, NOT NULL과
조회 인덱스가 ORM·마이그레이션·ERD에 일치하고 alembic check에 차이가 없어야 한다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-2.3-001 | tests/acceptance/curation/test_recommended_products.py | 기본 공개 목록 |
| AC-F-2.3-002 | tests/integration/curation/test_product_repository.py | 필터·중복·정렬 |
| AC-F-2.3-003 | tests/unit/curation/test_product_service.py, tests/contract/curation/test_product_list_contract.py | 404·422 |
| AC-F-2.3-004 | tests/integration/curation/test_product_repository.py | 게시·활성 연결 |
| AC-F-2.3-005 | tests/unit/curation/test_product_service.py, tests/acceptance/curation/test_recommended_products.py | 페이지 메타데이터 |
| AC-F-2.3-006 | tests/integration/curation/test_product_seed.py | 시드·정적 이미지 |
| AC-F-2.3-007 | tests/unit/curation/test_product_repository_failures.py, tests/unit/curation/test_product_service.py | 통합 503 |
| AC-F-2.3-008 | tests/contract/curation/test_product_list_contract.py | 공개 OpenAPI 계약 |
