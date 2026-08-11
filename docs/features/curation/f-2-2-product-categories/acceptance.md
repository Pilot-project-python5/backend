# F-2.2 인수 조건

## AC-F-2.2-001 공개 카테고리 목록

전제: 비타민·단백질·오메가3 활성 카테고리가 승인된 sort_order로 저장돼 있다.

행동: 인증 쿠키 없이 GET /api/v1/curation/categories를 호출한다.

결과: 200과 all·전체를 첫 번째로, 활성 DB 카테고리를 sort_order·slug 순서로 담은
slug·name items를 반환한다. 내부 UUID·is_active·sort_order는 노출하지 않는다.

## AC-F-2.2-002 비활성·동순위 경계

전제: 비활성 카테고리와 sort_order가 같은 활성 카테고리 둘 이상이 있다.

행동: 목록을 조회한다.

결과: 비활성 항목은 없고 동순위 활성 항목은 slug 오름차순이다. 가상 all은 정확히
한 번 맨 앞에 있다.

## AC-F-2.2-003 빈 카탈로그

전제: 활성 product_categories 행이 없다.

행동: 목록을 조회한다.

결과: 200과 `{"items":[{"slug":"all","name":"전체"}]}`를 반환한다.

## AC-F-2.2-004 DB 실패

전제: 카테고리 DB 조회가 실패한다.

행동: 목록을 조회한다.

결과: 빈 정상 응답이 아니라 503 SERVICE_UNAVAILABLE이며 내부 DB 상세를 숨긴다.

## AC-F-2.2-005 결정적·멱등 시드

전제: 빈 PostgreSQL 또는 이름·활성·순서가 변경된 기존 slug 행이 있다.

행동: 전체 시드를 두 번 실행한다.

결과: vitamin·protein·omega-3가 slug별 한 행만 존재하고 고정 ID 또는 기존 자연 키
행을 유지한 채 승인 이름·활성·10·20·30 순서로 수렴한다. 실제 개인정보는 없다.

## AC-F-2.2-006 API·Swagger 계약

전제: 실제 API와 생성 OpenAPI를 확인한다.

행동: 카테고리 operation을 검사한다.

결과: operation_id, 공개 무인증, 200 응답 스키마·예시와 503 오류가 실제 동작과
일치하며 페이지네이션·인증 보안 정의는 붙지 않는다.

## 데이터·ERD 인수 조건

빈 PostgreSQL에서 0006 마이그레이션이 재현되고 ORM·ERD·실제 스키마의 PK, UNIQUE,
CHECK, NOT NULL과 (is_active, sort_order, slug) 인덱스가 일치해야 한다. Alembic check에
새 차이가 없어야 하며 downgrade 범위는 F-2.3 이전 product_categories까지다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-2.2-001 | tests/acceptance/curation/test_product_categories.py | 공개 목록·정렬 |
| AC-F-2.2-002 | tests/integration/curation/test_product_category_repository.py | 비활성·동순위 |
| AC-F-2.2-003 | tests/unit/curation/test_product_category_service.py | all 단독 응답 |
| AC-F-2.2-004 | tests/unit/curation/test_product_category_service.py, tests/unit/curation/test_product_category_repository_failures.py, tests/contract/curation/test_product_category_contract.py | 실행·결과 읽기 실패의 통합 503 |
| AC-F-2.2-005 | tests/integration/curation/test_product_category_seed.py | 결정적 멱등 upsert |
| AC-F-2.2-006 | tests/contract/curation/test_product_category_contract.py | 공개 OpenAPI 계약 |
