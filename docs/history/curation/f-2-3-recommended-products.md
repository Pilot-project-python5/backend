---
feature_id: "F-2.3"
title: "추천 제품 목록"
requirement_id: "FR-2"
domain: "curation"
status: "implemented"
completed_on: "2026-08-12"
feature_packet: "docs/features/curation/f-2-3-recommended-products"
pull_request: "https://github.com/Pilot-project-python5/backend/pull/10"
commit: "4e09e10"
---

# F-2.3 추천 제품 목록 구현 이력

## 2026-08-15 민재코치 카탈로그 반영

- 활성 카테고리를 11개, 게시 추천 제품을 32개로 확장했다.
- 원본에 없는 가격과 이미지는 각각 0과 로컬 공통 플레이스홀더로 명시 처리했다.
- 기존 카탈로그에서 제외된 제품은 복용 이력 참조를 보존하기 위해 비공개 처리했다.
- 제품별 핵심 성분·카테고리 안내 코멘트·쿠팡 링크를 결정적 시드로 추가했다.
- 외부 Notion 없이 재현할 수 있도록 `docs/development/seed-data.md`에 원본과 정규화
  결정을 스냅샷했다.

## 구현 요약

방문자는 인증 없이 전체 또는 활성 카테고리별 게시 추천 제품을 페이지 단위로 조회할
수 있다. 목록은 편집 순서와 SKU로 안정적으로 정렬되고, 카드 미리보기·원화 참고
가격·로컬 제품 이미지와 정확한 total·has_next를 제공한다. 민재코치 승인 제품 32종과
카테고리 매핑은 로컬 PostgreSQL 시드로 반복 실행해도 승인 상태로 수렴한다.

## 구현 범위

### 포함

- products와 product_category_mappings ORM·마이그레이션·ERD
- 공개 GET /api/v1/curation/products와 category·page·page_size 계약
- 게시·활성 연결 필터, 다중 카테고리 중복 제거와 안정 정렬
- 제품 카드 미리보기·페이지 응답과 공통 404·422·503 오류
- 제품 32종·카테고리 매핑 멱등 시드와 공통 로컬 SVG 정적 이미지
- 단위·통합·계약·인수 테스트와 OpenAPI·개발 문서

### 제외

- 구성 성분·단위당 함량과 단일 제품 상세는 F-2.4로 분리했다.
- 전문가 코멘트와 외부 구매 이동은 F-2.4.1·F-2.4.2로 분리했다.
- 관리자 CRUD, 실시간 가격, 이미지 업로드, 결제·주문·배송은 제외했다.
- AWS 스토리지·CDN, 추천 소식과 AI 연결은 2차 범위로 유지했다.

## 주요 구현 내용

- `SQLAlchemyProductRepository`가 게시 제품과 활성 카테고리 매핑의 EXISTS 조건으로
  count와 페이지를 조회해 다대다 JOIN 중복을 원천 차단한다.
- 실제 category는 활성 여부를 먼저 확인하고 all은 별도 DB 카테고리 없이 필터를
  생략한다. 제품별 category_slugs는 활성 카테고리 순서로 다시 조립한다.
- `ProductService`가 미존재·비활성 카테고리를 404로, 쿼리 실행·결과 읽기 DB 오류를
  503으로 변환하고 has_next를 계산한다.
- 패키지 내부 SVG를 FastAPI `/static`에 mount해 외부 저장소 없이 image_url이 실제
  파일로 동작한다.
- 제품 시드는 SKU 충돌 시 공개 필드를 복원하고, 실제 반환된 제품 ID로 기존 매핑을
  승인 매핑으로 교체하므로 사전 데이터의 UUID가 달라도 FK를 보존한다.

## API 변경

- `GET /api/v1/curation/products`
  - 인증: 없음
  - category: 기본 all, 실제 활성 slug
  - page: 기본 1·최소 1, page_size: 기본 20·1~100
  - 200: items, page, page_size, total, has_next
  - 항목: id, sku, product_type, brand, name, image_url, display_price,
    currency=KRW, category_slugs
  - 404 CATEGORY_NOT_FOUND, 422 VALIDATION_FAILED, 503 SERVICE_UNAVAILABLE
- `/static/products/*.svg`가 로컬 제품 이미지를 200 image/svg+xml로 제공한다.

## 데이터·ERD·마이그레이션

- Alembic `20260812_0007_recommended_products`가 products와
  product_category_mappings를 추가한다.
- products는 UUID PK, 고유 SKU, 제품 유형·브랜드·이름·이미지·패키지·가격·게시·
  정렬·UTC 시간과 값 CHECK를 가진다.
- 제품·카테고리는 복합 PK 매핑으로 N:M이며 양쪽 삭제 시 매핑을 CASCADE한다.
- `(is_published, sort_order, sku)`와 `(category_id, product_id)` 조회 인덱스를
  추가했다.
- 제품 32종을 SKU 자연 키로 시드하고 11개 승인 카테고리 매핑을 복원한다.
- 테스트 DB에서 0007 downgrade·upgrade와 alembic check를 통과했다.

## 보안과 개인정보

- 공개 카탈로그 읽기라 인증·소유권 검사가 없으며 사용자·건강·token 데이터를 조회하지
  않는다.
- category 형식과 페이지 숫자 범위를 FastAPI에서 검증하고 SQLAlchemy 바인딩 쿼리를
  사용한다.
- DB 오류 상세와 내부 쿼리는 공통 503 응답에 노출하지 않는다.
- 시드와 SVG는 개발용 제품 샘플만 포함하며 개인정보·건강정보·비밀정보가 없다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-2.3-001~008을 단위·통합·계약·인수 테스트에 연결 | 8개 조건 모두 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-2.3` | 21개 통과 |
| 전체 로컬 검증 | `make verify` | 232개 통과, 커버리지 95.31% |
| 정적 검사 | `ruff format --check`, `ruff check`, `mypy` | 모두 통과 |
| 데이터·ERD | 0007 downgrade·upgrade, ERD validator, `alembic check`, 시드 2회 | 모두 통과, 스키마 차이 없음 |
| API·파일 | OpenAPI 일치, 로컬 curl 목록·SVG HEAD | 목록 JSON과 image/svg+xml 200 확인 |

## 주요 결정과 근거

- 낮은 변경 빈도의 기준 카탈로그와 프론트엔드 total 표시를 고려해 커서 대신 1 기반
  offset 페이지를 선택했다.
- 추천의 편집 의도를 보존하도록 가격·이름이 아니라 sort_order·sku를 기본 정렬로
  사용하고 사용자 정렬 옵션은 두지 않았다.
- category 오타를 빈 목록으로 숨기지 않도록 미존재·비활성 slug를 404로 구분했다.
- 로컬 오프라인 실행과 2차 CDN 전환을 함께 만족하도록 DB는 image_url만 알고,
  1차에는 같은 백엔드가 SVG를 제공한다.
- F-2.4.1과 F-2.4.2가 별도 기능 ID이므로 F-2.3에는 코멘트·구매 링크를 섞지 않았다.

## 알려진 제약

- offset 페이지는 조회 중 카탈로그 편집이 발생하면 페이지 경계가 달라질 수 있으나,
  현재 시드 중심 저빈도 변경 범위에서는 허용한다.
- 원본에 가격이 없어 현재 0을 가격 미제공 값으로 사용한다.
- 공통 로컬 SVG는 개발·연동용 이미지이며 운영용 상품 원본이나 CDN 최적화를 제공하지 않는다.
- 제품 패키지 값은 DB에 있으나 F-2.4 전까지 공개 목록 응답에는 노출하지 않는다.

## 후속 작업

- F-2.4에서 단일 제품 패키지·구성 성분·단위당 함량 상세를 구현한다.
- F-2.4.1에서 전문가 코멘트, F-2.4.2에서 활성 외부 구매 링크 이동을 구현한다.
- 2차 AWS 전환에서 image_url을 CDN HTTPS URL로 바꾸되 API 필드 계약은 유지한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/curation/f-2-3-recommended-products
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
