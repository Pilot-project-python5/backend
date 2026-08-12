# F-2.4.2 인수 조건

## AC-F-2.4.2-001 활성 구매 링크 이동

전제: 공개 제품에 유효한 활성 구매 링크가 있다.

행동: 방문자가 제품 구매 경로를 호출한다.

결과: 첫 링크로 307 이동하고 Location·no-store·no-referrer 헤더를 반환한다.

## AC-F-2.4.2-002 활성·정렬 규칙

전제: 한 제품에 비활성 링크와 같은·다른 sort_order의 활성 링크가 있다.

행동: 구매 목적지를 조회한다.

결과: 비활성 링크를 제외하고 `sort_order ASC, id ASC` 첫 링크를 선택한다.

## AC-F-2.4.2-003 공개 제품 숨김

전제: 제품이 없거나 비게시이거나 활성 카테고리 연결이 없다.

행동: 구매 경로를 호출한다.

결과: 경우를 구분하지 않는 404 `PRODUCT_NOT_FOUND`를 반환한다.

## AC-F-2.4.2-004 링크 없음

전제: 공개 제품에 활성 구매 링크가 없다.

행동: 구매 경로를 호출한다.

결과: 404 `PURCHASE_LINK_NOT_FOUND`를 반환한다.

## AC-F-2.4.2-005 유효성·장애 계약

- 유효하지 않은 UUID는 422 `VALIDATION_FAILED`다.
- PostgreSQL 조회 실패는 세부정보 없는 503 `SERVICE_UNAVAILABLE`다.

## AC-F-2.4.2-006 안전한 URL과 데이터 구조

- 링크 URL은 HTTPS 절대 URL, hostname 존재, userinfo·fragment·공백 없음,
  최대 2048자 조건을 만족한다.
- purchase_links의 제약·FK·인덱스·CASCADE가 모델·0010 마이그레이션·ERD와 일치한다.

## AC-F-2.4.2-007 결정적 시드와 무추적

- 제품 3종의 고정 UUID example.com 링크 시드를 두 번 적용해도 승인 값과 건수가 같다.
- 구매 경로 호출은 클릭·사용자·구매 이력을 저장하지 않는다.

## 비기능 경계

- 성공 응답은 캐시되지 않고 referrer를 외부로 보내지 않는다.
- 실제 개인정보·건강정보·비밀정보가 시드나 로그에 포함되지 않는다.
- AWS·AI·실제 판매처 가용성 없이 로컬에서 검증할 수 있다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-2.4.2-001 | `tests/contract/curation/test_purchase_link_contract.py` | 307·보안 헤더 |
| AC-F-2.4.2-002 | `tests/integration/curation/test_purchase_link_repository.py` | 활성·안정 정렬 |
| AC-F-2.4.2-003~005 | 단위·계약 테스트 | 404·422·503 |
| AC-F-2.4.2-006 | URL 단위·스키마 통합·ERD·마이그레이션 검사 | 안전 조건·0010 왕복 |
| AC-F-2.4.2-007 | `tests/integration/curation/test_purchase_link_seed.py`, 인수 테스트 | 멱등·무추적 |
