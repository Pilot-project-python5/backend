# F-2.4.2 외부 구매 연결

## 목표

사용자가 추천 제품의 구매 버튼을 선택하면 백엔드가 현재 활성화된 안전한 외부 구매
URL을 결정해 이동시킨다. 판매처 URL을 프론트엔드에 고정하지 않아 DB 시드 변경으로
구매 목적지를 교체할 수 있게 한다.

## 사용자 이야기

방문자로서, 관심 있는 추천 제품을 구매할 수 있도록 관리 중인 외부 판매처로 이동하고
싶다.

## 비즈니스 규칙

1. 인증 없이 `GET /api/v1/curation/products/{product_id}/purchase`를 호출할 수 있다.
2. 게시 제품이면서 활성 카테고리 연결이 있는 제품만 공개 제품으로 취급한다.
3. 공개 제품의 활성 구매 링크 중 `sort_order ASC, id ASC` 첫 항목을 선택한다.
4. 성공하면 307 Temporary Redirect와 Location 헤더를 반환한다.
5. 성공 응답에 `Cache-Control: no-store`와 `Referrer-Policy: no-referrer`를 넣는다.
6. 공개 조건을 만족하지 않는 제품은 404 `PRODUCT_NOT_FOUND`로 숨긴다.
7. 공개 제품에 활성 링크가 없으면 404 `PURCHASE_LINK_NOT_FOUND`를 반환한다.
8. URL은 절대 HTTPS이고 hostname이 있으며 userinfo·fragment·공백이 없고 2048자
   이하여야 한다.
9. 링크는 DB 시드 데이터로만 관리하고 클릭 기록을 저장하지 않는다.
10. DB 조회 실패는 내부 정보를 감춘 503 `SERVICE_UNAVAILABLE`로 변환한다.

## 포함 범위

- 공개 제품별 외부 구매 리다이렉트 API
- purchase_links ORM·마이그레이션·ERD
- 활성 링크 선택과 안정 정렬
- 안전한 URL 검증과 보안 응답 헤더
- 민재코치 승인 제품 32종의 쿠팡 상품 URL 결정적 시드
- 단위·통합·계약·인수 테스트와 Swagger·OpenAPI

## 제외 범위

- 서비스 내부 결제·주문·배송
- 판매처 실시간 가용성·제휴·가격 API 연동
- 관리자 링크 CRUD
- 클릭 분석, 사용자 추적과 클릭 이력 저장
- AWS·AI 연결

## 시나리오

### 기본 흐름

1. 방문자가 공개 추천 제품의 구매 경로를 호출한다.
2. 저장소가 공개 제품 조건과 첫 활성 링크를 조회한다.
3. 서비스가 목적지를 반환하고 API가 안전 헤더와 함께 307로 이동시킨다.

### 실패와 경계

- UUID 형식이 아니면 공통 422 `VALIDATION_FAILED`다.
- 미존재·비게시·활성 카테고리 없음은 같은 404 `PRODUCT_NOT_FOUND`다.
- 공개 제품이나 활성 링크가 없으면 404 `PURCHASE_LINK_NOT_FOUND`다.
- 비활성 링크는 선택하지 않고 같은 순서에서는 UUID가 작은 링크를 고른다.
- DB 장애는 안전한 503이며 URL이나 연결 정보가 오류 본문에 포함되지 않는다.
- 읽기와 리다이렉트만 수행하므로 같은 요청은 서버 상태를 변경하지 않는다.

## 미결 질문

- 없음. MVP는 클릭 기록을 수집하지 않고 분석·보존 정책은 2차로 미룬다.

## 추적성

- 요구사항: FR-2
- 로컬 요구사항: docs/product/requirements.md
- 관련 로컬 문서: docs/api/curation.md, docs/architecture/erd.md
- 외부 출처 URL(선택): https://app.notion.com/p/3b62779e926280e287baccedfce27f9c
- 마지막 검토일: 2026-08-15

모호했던 URL 보안·클릭 기록·오류 분리 결정은 Notion의
`F-2.4.1·F-2.4.2 구현 의사결정` 페이지에 기록했다.
