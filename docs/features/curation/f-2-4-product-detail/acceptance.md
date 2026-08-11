# F-2.4 인수 조건

## AC-F-2.4-001 공개 제품 상세

전제: 게시 상태이고 활성 카테고리가 연결된 시드 제품이 있다.

행동: 방문자가 제품 UUID로 상세를 조회한다.

결과: 목록 공통 필드와 패키지·활성 구성 성분을 200으로 받는다.

## AC-F-2.4-002 공개 조건과 미존재

미존재·비게시·활성 카테고리 연결 없음 제품 UUID를 조회하면 대상 상태를 구분해
노출하지 않고 모두 `404 PRODUCT_NOT_FOUND`를 반환한다.

## AC-F-2.4-003 UUID 검증

UUID 형식이 아닌 product_id는 공통 `422 VALIDATION_FAILED`를 반환한다.

## AC-F-2.4-004 활성 카테고리

상세의 category_slugs는 활성 카테고리만 sort_order와 slug 순으로 제공한다.

## AC-F-2.4-005 활성 성분과 빈 배열

활성 성분은 제품별 sort_order와 code 순으로 제공하고, 비활성 성분은 제외한다.
성분 매핑이 없는 공개 제품은 `nutrients: []`를 반환한다.

## AC-F-2.4-006 정밀 수량 계약

package.units_per_package와 nutrients.amount_per_unit은 Decimal 정밀도를 보존하는
JSON 문자열이며, 성분 단위는 MG·G·MCG·IU 중 하나다.

## AC-F-2.4-007 데이터 제약과 ERD

0008 마이그레이션은 code·단위·양수 함량·표시 순서 제약과 FK 삭제 정책·조회 인덱스를
추가하고 ORM·로컬 ERD와 일치한다. downgrade 후 0007 제품 목록 구조가 유지된다.

## AC-F-2.4-008 시드와 DB 장애

성분 시드를 두 번 실행해도 성분과 제품별 매핑이 승인 값으로 수렴한다. 조회 중 DB
장애가 발생하면 내부 상세 없이 `503 SERVICE_UNAVAILABLE`를 반환한다.

## 유효성 및 실패 사례

- 위 404·422·503과 빈 배열을 독립 자동 테스트로 검증한다.

## 데이터·ERD 인수 조건

- AC-F-2.4-007과 AC-F-2.4-008로 마이그레이션·ERD·시드 수렴을 검증한다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-2.4-001 | `tests/acceptance/curation/test_product_detail.py` | 공개 상세 |
| AC-F-2.4-002 | `tests/contract/curation/test_product_detail_contract.py` | 통합 404 포함 |
| AC-F-2.4-003 | `tests/contract/curation/test_product_detail_contract.py` | 공통 422 |
| AC-F-2.4-004 | `tests/integration/curation/test_product_detail_repository.py` | 카테고리 정렬 |
| AC-F-2.4-005 | `tests/integration/curation/test_product_detail_repository.py` | 활성 성분·빈 배열 |
| AC-F-2.4-006 | `tests/contract/curation/test_product_detail_contract.py` | Decimal JSON |
| AC-F-2.4-007 | 마이그레이션·ERD 검사 | 0008 왕복 |
| AC-F-2.4-008 | `tests/integration/curation/test_product_nutrient_seed.py`, 단위 장애 테스트 | 멱등 시드·503 |
