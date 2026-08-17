# F-2.4.1 인수 조건

## AC-F-2.4.1-001 활성 전문가 코멘트

전제: 공개 제품에 활성·비활성 전문가 코멘트가 연결돼 있다.

행동: 방문자가 제품 상세를 조회한다.

결과: 기존 상세 정보와 활성 expert_comments만 안정된 순서로 받는다.

## AC-F-2.4.1-002 빈 코멘트

활성 코멘트가 없는 공개 제품은 `expert_comments: []`를 포함해 200으로 응답한다.

## AC-F-2.4.1-003 기존 공개 조건과 오류

비공개 제품·잘못된 UUID·DB 장애는 F-2.4의 404·422·503 공통 계약을 유지한다.

## AC-F-2.4.1-004 응답 문자열 계약

각 코멘트는 id, author_label, content만 포함하고 content를 일반 JSON 문자열로 제공한다.

## AC-F-2.4.1-005 데이터 제약과 ERD

0009는 저자·내용 길이, 0 이상 정렬, product FK CASCADE와 활성 조회 인덱스를 추가하고
ORM·ERD와 일치한다. downgrade 뒤 F-2.4 테이블은 유지된다.

## AC-F-2.4.1-006 결정적 시드

코멘트 시드를 반복 실행하면 제품 32종의 고정 코멘트가 승인 문구·활성·순서로 수렴한다.

## 유효성 및 실패 사례

- 위 성공·빈 배열·오류·문자열 사례를 자동 테스트로 검증한다.

## 데이터·ERD 인수 조건

- AC-F-2.4.1-005~006으로 마이그레이션·ERD·시드 수렴을 검증한다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-2.4.1-001 | `tests/integration/curation/test_expert_comment_repository.py` | 활성·정렬 |
| AC-F-2.4.1-002 | `tests/contract/curation/test_expert_comment_contract.py` | 빈 배열 |
| AC-F-2.4.1-003 | 기존 상세 계약·단위 장애 테스트 | 404·422·503 |
| AC-F-2.4.1-004 | `tests/contract/curation/test_expert_comment_contract.py` | 응답 필드 |
| AC-F-2.4.1-005 | 스키마 통합·ERD·마이그레이션 검사 | 0009 왕복 |
| AC-F-2.4.1-006 | `tests/integration/curation/test_expert_comment_seed.py` | 멱등 시드 |
