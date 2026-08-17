---
feature_id: "F-2.4.1"
title: "전문가 코멘트"
requirement_id: "FR-2"
domain: "curation"
status: "implemented"
completed_on: "2026-08-12"
feature_packet: "docs/features/curation/f-2-4-1-expert-comment"
pull_request: "https://github.com/Pilot-project-python5/backend/pull/12"
commit: "9cdfd33"
---

# F-2.4.1 전문가 코멘트 구현 이력

## 2026-08-15 민재코치 카테고리 안내 반영

- 32개 제품에 카테고리 설명과 주의사항을 `MJ's COMMENT`로 연결했다.
- 이전 3종 개발 코멘트는 비활성화하고 고정 UUID 시드의 멱등성을 유지했다.

## 구현 요약

방문자는 인증 없이 추천 제품 상세에서 제품별 전문가 코멘트를 함께 조회할 수 있다.
활성 코멘트만 관리 순서와 UUID 순으로 안정적으로 제공하며 코멘트가 없는 제품은 빈
배열로 정상 응답한다. UI 제품 3종의 개발용 코멘트는 로컬 PostgreSQL 시드로 반복
실행해도 같은 승인 값으로 수렴한다.

## 구현 범위

### 포함

- 기존 `GET /api/v1/curation/products/{product_id}`의 `expert_comments` 응답 확장
- 활성 코멘트 조회, 안정 정렬과 빈 배열 계약
- expert_comments ORM·마이그레이션·ERD와 제품 삭제 CASCADE
- UI 제품 3종의 결정적 멱등 개발 시드
- 단위·통합·계약·인수 테스트와 OpenAPI·개발 문서

### 제외

- 코멘트 작성·수정·삭제 관리자 API와 전문가 계정 관리는 제외했다.
- 목록 API에는 코멘트를 넣지 않아 카드 목록 응답 크기를 유지했다.
- HTML 정제·Markdown 렌더링은 백엔드가 수행하지 않고 일반 문자열로 전달한다.
- 외부 구매 연결은 F-2.4.2, 실제 전문가 프로필은 프론트엔드 F-2.1로 분리했다.

## 주요 구현 내용

- `SQLAlchemyProductDetailRepository`가 기존 공개 제품 조건을 통과한 뒤 해당 제품의
  활성 코멘트를 `(sort_order, id)`로 조회한다.
- `ProductDetailService`가 저장 레코드를 불변 전문가 코멘트 값으로 변환하며 기존
  404·503 오류 경계를 그대로 유지한다.
- Pydantic 응답 스키마가 `id`, `author_label`, `content`를 필수 필드로 보장하고
  코멘트가 없을 때 `expert_comments: []`를 반환한다.
- 코멘트 시드는 고정 UUID와 제품 SKU 조회를 사용해 기존 제품의 실제 PK가 달라도
  올바른 제품에 연결하고 같은 ID의 승인 값을 갱신한다.

## API 변경

- `GET /api/v1/curation/products/{product_id}`
  - 인증: 없음
  - 200에 필수 배열 `expert_comments` 추가
  - 각 항목: UUID `id`, 문자열 `author_label`, 일반 문자열 `content`
  - 코멘트 없음: 빈 배열
  - 기존 404 PRODUCT_NOT_FOUND, 422 VALIDATION_FAILED, 503 SERVICE_UNAVAILABLE 유지
- F-2.3 제품 목록 응답은 변경하지 않았다.

## 데이터·ERD·마이그레이션

- Alembic `20260812_0009_expert_comments`가 expert_comments를 추가한다.
- UUID PK, products FK, 비공백 1~100자 작성자 라벨, 비공백 1~2000자 본문, 활성 여부와
  0 이상 표시 순서를 저장한다.
- 제품과 코멘트는 1:N이며 제품 삭제 시 코멘트를 CASCADE한다.
- `(product_id, is_active, sort_order, id)` 조회 인덱스를 추가했다.
- 제품 3종에 개발용 코멘트 각 1건을 고정 UUID와 제품 SKU 기준으로 시드한다.
- 테스트 DB에서 0009 downgrade·upgrade와 `alembic check`를 통과했다.

## 보안과 개인정보

- 공개 카탈로그 읽기라 인증·소유권 검사가 없고 사용자·건강·토큰 데이터를 조회하지 않는다.
- 공개 조건을 만족하지 않는 제품은 기존과 같은 404로 숨기고 DB 예외 세부정보는 503
  응답에 노출하지 않는다.
- 본문을 HTML로 해석하거나 실행하지 않고 JSON 일반 문자열로 전달한다. 프론트엔드는
  문자열을 HTML로 직접 삽입하지 않아야 한다.
- 시드는 개발용 문구만 포함하며 개인정보·건강정보·비밀정보가 없다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-2.4.1-001~006을 단위·통합·계약·인수 테스트에 연결 | 6개 조건 모두 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-2.4.1` | 9개 통과 |
| 전체 로컬 검증 | `make verify` | 258개 통과, 커버리지 95.48% |
| 정적 검사 | `ruff format --check`, `ruff check`, `mypy` | 모두 통과, 소스 138개 타입 검사 |
| 데이터·ERD | 0009 downgrade·upgrade, ERD validator, `alembic check`, 시드 2회 | 모두 통과, 스키마 차이 없음 |
| API 확인 | OpenAPI 일치, 개발 DB migrate·seed와 상세 curl | 실제 코멘트 포함 200 확인 |

## 주요 결정과 근거

- 코멘트는 새 엔드포인트 대신 기존 상세 응답에 넣어 상세 화면이 한 번의 조회로 완성되게
  하되 목록 응답은 유지했다.
- UI의 코멘트 펼치기는 상세 조회 시점에 처리할 수 있으므로 목록에 본문을 중복하지 않는다.
- MVP에 전문가 테이블을 추가하지 않고 표시 라벨을 코멘트가 소유하게 해 프론트엔드 정적
  전문가 소개와 백엔드 카탈로그의 결합을 피했다.
- 본문은 일반 문자열 계약으로 제한해 표시 기술을 서버가 강제하지 않고 저장형 XSS 처리
  책임을 명확히 했다.
- 물리 삭제 대신 `is_active`로 노출을 제어하고 복수 코멘트의 순서를 명시적으로 저장한다.

## 알려진 제약

- 코멘트는 DB 시드·직접 관리만 가능하며 관리자 쓰기 API가 없다.
- 작성자 라벨은 전문가 계정이나 프로필과 참조 무결성으로 연결되지 않는다.
- 시드 문구는 개발·Swagger·프론트엔드 연동용이며 의료 또는 구매 판단 자료가 아니다.

## 후속 작업

- F-2.4.2에서 활성 외부 구매 링크와 안전한 307 이동 계약을 별도 PR로 구현한다.
- 실제 전문가 관리가 필요해지면 관리자 권한·감사 이력과 함께 별도 기능으로 설계한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/curation/f-2-4-1-expert-comment
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
