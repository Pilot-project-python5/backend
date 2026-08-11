# F-2.4 설계

## API 계약

- 메서드와 경로: `GET /api/v1/curation/products/{product_id}`
- 인증: 없음
- 요청: UUID path parameter 한 개
- 성공 응답: F-2.3 공통 필드, `package`, `nutrients`
- 오류 응답: 잘못된 UUID 422, 공개 대상 없음 404, DB 장애 503
- 멱등성: 읽기 API이므로 같은 DB 상태에서 같은 결과를 반환한다.

### 성공 응답 구조

- 공통: id, sku, product_type, brand, name, image_url, display_price,
  currency=`KRW`, category_slugs
- package: unit_form, units_per_package Decimal 문자열
- nutrients: code, name, amount_per_unit Decimal 문자열, unit

## 데이터 설계

- 엔티티: nutrients, product_nutrients
- 관계와 카디널리티: products N:M nutrients, product_nutrients가 연결과 제품별
  함량·단위·표시 순서를 소유한다.
- 제약 조건: nutrient code 고유·대문자 영숫자와 내부 밑줄, 이름 비공백,
  canonical_unit과 mapping unit은 MG/G/MCG/IU, amount_per_unit > 0,
  sort_order >= 0
- 인덱스: nutrients `(is_active, code)`, product_nutrients
  `(product_id, sort_order, nutrient_id)`
- 마이그레이션: `20260812_0008_product_nutrients`, 선행 0007
- 백필과 기존 데이터 영향: 신규 nullable 없는 테이블만 만들므로 기존 제품 행을
  잠그는 백필은 없다. 마이그레이션 후 로컬 시드가 기준 행과 매핑을 채운다.
- 이력과 삭제: 제품 삭제는 제품 성분 매핑 CASCADE, 참조 중인 nutrient 삭제는
  RESTRICT하며 비활성화를 우선한다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: products·product_category_mappings까지 실제 구현, 성분 관계는 논리 예정
- 변경 후 구조: nutrients·product_nutrients를 F-2.4 실제 구조로 확정하고 제약·인덱스·
  삭제 정책을 기록한다.
- 변경하지 않는 경우의 이유: 해당 없음
- ERD 검증 방법: `make erd-check`와 마이그레이션 downgrade/upgrade,
  `alembic check`

## 애플리케이션 흐름

1. FastAPI가 product_id UUID를 검증한다.
2. 상세 서비스가 저장소에 공개 제품 조회를 요청한다.
3. 저장소는 게시 여부와 활성 카테고리 EXISTS 조건으로 제품을 한 건 조회한다.
4. 저장소는 활성 카테고리와 활성 성분을 각각 안정된 순서로 조회한다.
5. 대상이 없으면 서비스가 404, SQLAlchemy 오류면 503 AppError로 변환한다.
6. router가 패키지·성분 Decimal을 응답 모델에 전달하고 Pydantic JSON 모드가
   문자열로 직렬화한다.

## 보안과 개인정보

- 소유권 검사: 공개 기준 카탈로그이므로 해당 없음
- 민감 필드: 사용자·건강·토큰 필드를 조회하지 않는다.
- 로그 제외 항목: SQL 문·연결 정보·내부 예외 상세를 오류 응답에 노출하지 않는다.

## 로컬 어댑터

- 데이터베이스: 로컬 PostgreSQL 개발·테스트 DB
- 시간: 이 기능에서 새 시간 계산 없음
- 이메일: 해당 없음
- 스케줄러: 해당 없음

## 호환성

- OpenAPI 영향: 신규 공개 GET operation과 상세 응답 schema 추가
- 기존 데이터 영향: 기존 F-2.3 API·테이블 변경 없음, 신규 성분 테이블만 참조
- 롤백: 앱 커밋을 되돌린 뒤 0008에서 0007로 downgrade하면 성분 매핑과 성분
  기준 행만 제거된다. F-2.3 제품 목록은 유지된다.
