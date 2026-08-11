# F-2.3 설계

## API 계약

- 메서드와 경로: GET /api/v1/curation/products
- 인증: 없음. 공개 조회이며 AccessCookieAuth를 요구하지 않는다.
- 요청: category 선택(기본 all), page 정수(기본 1, 최소 1), page_size 정수(기본 20,
  1~100)
- 성공 응답: items와 page, page_size, total, has_next. 항목은 id, sku, product_type,
  brand, name, image_url, display_price, currency=KRW, category_slugs다.
- 오류 응답: 404 CATEGORY_NOT_FOUND, 422 VALIDATION_FAILED, 503 SERVICE_UNAVAILABLE
- 멱등성: 읽기 전용 GET이며 같은 DB 상태와 요청에서 순서·내용이 같다.
- 정렬: sort_order ASC, sku ASC. 사용자 정렬 옵션은 없다.

## 데이터 설계

- 엔티티: products, product_category_mappings 신규. product_categories는 F-2.2 재사용
- products 필드: id UUID PK, sku varchar(50), product_type varchar(20), brand
  varchar(100), name varchar(200), image_url text, unit_form varchar(20),
  units_per_package numeric(10,2), display_price integer, is_published boolean,
  sort_order integer, created_at·updated_at timestamptz
- 관계와 카디널리티: products N:M product_categories. 매핑은 product_id와 category_id
  복합 PK·FK이며 양쪽 삭제 시 CASCADE한다.
- 제약 조건: sku UNIQUE·대문자 영숫자/내부 하이픈 CHECK, product_type 허용값,
  brand·name·image_url 비공백, unit_form TABLET/CAPSULE/SCOOP/PACKET,
  units_per_package > 0, display_price·sort_order >= 0, updated_at >= created_at,
  전 필드 NOT NULL
- 인덱스: products(is_published, sort_order, sku),
  product_category_mappings(category_id, product_id)
- 마이그레이션: 20260812_0007_recommended_products, 이전 head 0006 뒤에 적용
- 백필과 기존 데이터 영향: 신규 빈 테이블이라 백필 없음. 별도 시드가 제품과 매핑을
  적재하며 기존 회원·세션·카테고리에 영향을 주지 않는다.
- 이력과 삭제: 공개 제외는 is_published=false를 사용한다. 물리 삭제 시 매핑만
  CASCADE되며 향후 CareItem이 연결된 뒤 삭제 정책은 F-3에서 강화한다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: products·product_category_mappings가 논리 초안이고 F-2.2 실제
  카테고리와 연결되지 않았다.
- 변경 후 구조: 두 테이블, 제품 편집 순서·시간 필드, 복합 PK·FK·CASCADE와 조회
  인덱스가 실제 ORM·마이그레이션과 일치한다.
- 마이그레이션 고려: 0007 downgrade는 category 매핑을 먼저 제거한 뒤 products를
  제거한다. F-2.4 이후에는 독립 downgrade하지 않는다.
- ERD 검증 방법: validate_erd.py, 0007 downgrade·upgrade, alembic check,
  PostgreSQL inspector로 PK·FK·CHECK·인덱스 비교

## 애플리케이션 흐름

1. 라우터가 category·page·page_size를 검증해 서비스로 전달한다.
2. category가 all이 아니면 저장소가 활성 카테고리 존재를 확인한다.
3. 저장소가 활성 카테고리와 매핑된 게시 제품 ID를 중복 없이 필터링한다.
4. 같은 필터에서 total을 세고 offset·limit와 정렬을 적용해 제품·활성 category slug를
   읽는다.
5. 서비스가 category 미존재를 404, DB 오류를 503으로 변환하고 has_next를 계산한다.
6. 라우터가 KRW 통화와 공개 필드만 직렬화한다.

## 보안과 개인정보

- 소유권 검사: 공개 기준 데이터라 인증·사용자 소유권이 없다.
- 입력 공격면: 선언된 slug 정규식과 숫자 범위만 허용하고 SQLAlchemy 바인딩 쿼리를
  사용한다.
- 민감 필드: 개인정보·건강정보·token을 조회하거나 반환하지 않는다.
- 로그 제외 항목: DB 예외 상세와 내부 쿼리는 공개 오류에 포함하지 않는다.

## 로컬 어댑터

- 데이터베이스: PostgreSQL 16, SQLAlchemy 동기 조회와 PostgreSQL upsert 시드
- 파일: 패키지 내부 SVG를 /static/products 경로로 FastAPI StaticFiles가 제공한다.
- 시간: 고정 UTC 시드 시각만 사용하고 현재 시각에 의존하지 않는다.
- 이메일: 사용하지 않음
- 스케줄러: 사용하지 않음

## 호환성

- OpenAPI 영향: 공개 GET /curation/products, 쿼리·페이지 응답과 404·422·503 추가
- 기존 데이터 영향: 신규 테이블과 라우트라 기존 API와 호환한다.
- 롤백: 라우터·정적 mount·시드·ORM 등록을 제거하고 0007 downgrade로 매핑과 제품
  테이블을 제거한다.
