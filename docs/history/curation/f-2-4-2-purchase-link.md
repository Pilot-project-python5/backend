---
feature_id: "F-2.4.2"
title: "외부 구매 연결"
requirement_id: "FR-2"
domain: "curation"
status: "implemented"
completed_on: "2026-08-12"
feature_packet: "docs/features/curation/f-2-4-2-purchase-link"
pull_request: "https://github.com/Pilot-project-python5/backend/pull/13"
commit: "2d690c8"
---

# F-2.4.2 외부 구매 연결 구현 이력

## 2026-08-15 민재코치 구매 링크 반영

- 32개 제품에 원본 표의 쿠팡 상품 URL을 연결했다.
- 이전 example.com 개발 링크는 비활성화하고 URL 안전 검증과 무추적 계약을 유지했다.

## 구현 요약

방문자는 인증 없이 공개 추천 제품의 구매 경로를 호출해 현재 활성화된 외부 판매처로
307 이동할 수 있다. 목적지는 안전한 HTTPS 조건을 통과한 첫 활성 링크이며 응답은
캐시와 referrer 전달을 막는다. 제품 3종의 개발용 example.com 링크는 로컬 PostgreSQL
시드로 반복 실행해도 같은 승인 값으로 수렴하고 클릭 이력은 저장하지 않는다.

## 구현 범위

### 포함

- 공개 `GET /api/v1/curation/products/{product_id}/purchase`
- 공개 제품 조건과 첫 활성 링크 안정 선택
- 307 Location·no-store·no-referrer 응답 계약
- HTTPS 절대 URL 안전 검증
- purchase_links ORM·0010 마이그레이션·ERD
- UI 제품 3종의 결정적 멱등 개발 시드
- 단위·통합·계약·인수 테스트와 OpenAPI·개발 문서

### 제외

- 서비스 내부 결제·주문·배송과 실제 판매처 API 연동은 제외했다.
- 관리자 구매 링크 CRUD와 제휴·정산 관리는 제외했다.
- 클릭 분석, 사용자 추적과 클릭 이력 저장은 개인정보·보존 정책과 함께 2차로 미뤘다.
- AWS·AI 연결은 1차 로컬 MVP 범위 밖이다.

## 주요 구현 내용

- `SQLAlchemyPurchaseLinkRepository`가 게시 제품과 활성 카테고리 연결을 먼저 확인하고
  활성 링크를 `(sort_order, id)` 순으로 한 건만 조회한다.
- `PurchaseLinkService`가 공개 제품 없음과 활성 링크 없음을 서로 다른 404로 변환하고
  DB 장애·안전하지 않은 저장 URL은 내부정보가 없는 공통 503으로 막는다.
- URL 검증기가 HTTPS scheme, hostname, 길이, 공백·제어 문자, userinfo, fragment와
  port 구문을 확인한다.
- 라우터는 RedirectResponse로 본문 없는 307과 Location·no-store·no-referrer를
  반환하며 어떠한 클릭 쓰기도 수행하지 않는다.
- 시드는 고정 UUID와 제품 SKU 조회를 사용해 기존 제품 PK가 달라도 올바르게 연결한다.

## API 변경

- `GET /api/v1/curation/products/{product_id}/purchase`
  - 인증: 없음
  - path: UUID product_id
  - 307: 빈 본문, Location, Cache-Control no-store, Referrer-Policy no-referrer
  - 404 PRODUCT_NOT_FOUND: 미존재·비게시·활성 카테고리 없음
  - 404 PURCHASE_LINK_NOT_FOUND: 공개 제품에 활성 링크 없음
  - 422 VALIDATION_FAILED, 503 SERVICE_UNAVAILABLE
- 기존 목록·상세 성공 응답은 변경하지 않았다.

## 데이터·ERD·마이그레이션

- Alembic `20260812_0010_purchase_links`가 purchase_links를 추가한다.
- UUID PK, products FK, 비공백 1~100자 판매처 표시, 9~2048자 HTTPS URL, 활성 여부와
  0 이상 표시 순서를 저장한다.
- DB CHECK가 HTTPS 접두·공백·fragment·authority userinfo를 거르고 애플리케이션이
  hostname·port까지 다시 검증한다.
- 제품과 구매 링크는 1:N이며 제품 삭제 시 링크를 CASCADE한다.
- `(product_id, is_active, sort_order, id)` 조회 인덱스를 추가했다.
- 제품 3종의 example.com 링크 각 1건을 고정 UUID와 제품 SKU 기준으로 시드한다.
- 테스트 DB에서 0010 downgrade·upgrade와 `alembic check`를 통과했다.

## 보안과 개인정보

- 공개 카탈로그 이동이라 인증·소유권 검사가 없고 사용자·건강·구매 데이터를 읽지 않는다.
- HTTP, userinfo, fragment, 공백, hostname 부재와 비정상 port URL로 리다이렉트하지 않는다.
- no-store로 리다이렉트 응답 캐시를 막고 no-referrer로 외부 판매처에 현재 경로 전달을
  막는다.
- 클릭·사용자·구매 이력을 저장하지 않으며 애플리케이션이 목적지 URL을 별도 로그로
  남기지 않는다.
- 시드는 example.com 개발 URL만 포함하며 개인정보·비밀정보가 없다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-2.4.2-001~007을 단위·통합·계약·인수 테스트에 연결 | 7개 조건 모두 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-2.4.2` | 27개 통과 |
| 전체 로컬 검증 | `make verify` | 285개 통과, 커버리지 95.51% |
| 정적 검사 | `ruff format --check`, `ruff check`, `mypy` | 모두 통과, 소스 148개 타입 검사 |
| 데이터·ERD | 0010 downgrade·upgrade, ERD validator, `alembic check`, 시드 2회 | 모두 통과, 스키마 차이 없음 |
| API 확인 | OpenAPI 일치, 개발 DB migrate·seed와 curl | 실제 307·Location·보안 헤더 확인 |

## 주요 결정과 근거

- 구매 목적지를 상세 JSON에 노출하지 않고 별도 307 경로로 제공해 프론트엔드가 판매처
  URL을 직접 보관하지 않도록 했다.
- 302 대신 307을 사용해 임시 이동의 의미와 요청 메서드 보존 규칙을 명확히 했다.
- 판매처 우선순위를 `sort_order`로 관리하고 UUID를 최종 정렬 키로 사용해 결과를
  재현 가능하게 했다.
- URL은 시드 쓰기 전과 리다이렉트 직전에 검증한다. DB 밖에서 데이터가 변경되더라도
  안전하지 않은 목적지로 이동하지 않기 위해서다.
- 클릭 분석은 목적·동의·보존 기간이 정해지지 않았으므로 1차에 암묵적으로 수집하지 않는다.

## 알려진 제약

- 링크는 DB 시드·직접 관리만 가능하며 관리자 쓰기 API가 없다.
- example.com 목적지는 개발·Swagger·프론트엔드 연동용이며 실제 구매가 불가능하다.
- 판매처 가용성·가격·재고를 확인하지 않고 현재 활성 URL로만 이동한다.
- 클릭 분석과 제휴 파라미터 정책은 구현하지 않았다.

## 후속 작업

- 실제 판매처가 정해지면 HTTPS allowlist·제휴 파라미터·링크 점검 정책을 별도 승인한다.
- 클릭 분석이 필요하면 사용자 고지, 수집 목적, 보존 기간과 집계·삭제 방식을 먼저
  확정한 뒤 별도 기능으로 구현한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/curation/f-2-4-2-purchase-link
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
