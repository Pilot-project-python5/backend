# F-2.4.2 설계

## API 계약

- 메서드와 경로: `GET /api/v1/curation/products/{product_id}/purchase`
- 인증: 없음
- 요청: UUID `product_id` 경로 변수
- 성공 응답: 307, `Location`, `Cache-Control: no-store`,
  `Referrer-Policy: no-referrer`, 본문 없음
- 오류 응답: 404 `PRODUCT_NOT_FOUND`, 404 `PURCHASE_LINK_NOT_FOUND`,
  422 `VALIDATION_FAILED`, 503 `SERVICE_UNAVAILABLE`
- 멱등성: 조회와 리다이렉트만 수행하고 클릭 이력을 쓰지 않는다.

## 데이터 설계

- 엔티티: purchase_links(id, product_id, provider_name, url, is_active,
  sort_order)
- 관계와 카디널리티: products 1:N purchase_links
- 제약 조건: UUID PK·FK, trim 기준 1~100자 provider_name, 9~2048자 URL,
  `https://`·공백 없음·fragment 없음·authority userinfo 없음, sort_order 0 이상
- 인덱스: `(product_id, is_active, sort_order, id)`
- 마이그레이션: `20260812_0010_purchase_links`, down_revision 0009
- 백필과 기존 데이터 영향: 기존 행 백필 없음. 제품 3종의 고정 UUID 개발 시드 추가
- 이력과 삭제: 제품 삭제 시 CASCADE. 링크는 물리 삭제보다 비활성화를 우선한다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: products에 외부 구매 목적지 관계가 없다.
- 변경 후 구조: products 1:N purchase_links와 실제 제약·인덱스·삭제 정책 추가
- 변경하지 않는 경우의 이유: 해당 없음
- ERD 검증 방법: 모델·0010 마이그레이션·통합 검사와 ERD validator 비교

## 애플리케이션 흐름

1. 라우터가 UUID 제품 ID를 서비스에 전달한다.
2. 저장소가 게시 제품과 활성 카테고리 연결 여부를 확인한다.
3. 공개 제품이면 활성 링크를 sort_order와 id 순으로 한 건 조회한다.
4. 서비스가 제품 미공개와 링크 없음 오류를 구분하고 DB 장애를 503으로 변환한다.
5. 라우터가 목적지를 Location에 넣어 307과 no-store·no-referrer를 반환한다.

## 보안과 개인정보

- 소유권 검사: 공개 기준 카탈로그라 사용자 소유권 없음
- 민감 필드: 없음. 로그인·건강·구매·클릭 데이터를 읽거나 저장하지 않는다.
- 로그 제외 항목: 전체 목적지 URL과 query parameter를 애플리케이션 로그에 남기지 않는다.
- URL 방어: Python URL 검증과 DB CHECK를 함께 사용하고 시드 이외의 쓰기 경로는 없다.

## 로컬 어댑터

- 데이터베이스: 로컬 PostgreSQL 개발·테스트 DB
- 시간: 사용하지 않음
- 이메일: 사용하지 않음
- 스케줄러: 사용하지 않음

## 호환성

- OpenAPI 영향: 공개 GET 307 경로와 404·422·503 응답 추가
- 기존 데이터 영향: 새 테이블과 개발 시드만 추가하고 기존 응답은 변경하지 않는다.
- 롤백: API 코드를 이전 버전으로 되돌리고 Alembic을 0009로 downgrade한다.
