# F-3.2 인수 조건

## AC-F-3.2-001 영양제 등록 시 성분 스냅샷

전제: 활성 성분이 연결된 SUPPLEMENT 제품이 카탈로그에 있다.

행동: 로그인 사용자가 F-3.1 등록 API로 제품을 등록한다.

결과: care_item과 각 활성 성분의 nutrient_id·당시 이름·단위당 함량·단위를 같은
트랜잭션에 저장하고 기존 201 응답을 반환한다.

## AC-F-3.2-002 카탈로그 변경 격리

전제: 영양제 등록으로 성분 스냅샷이 생성됐다.

행동: 이후 제품 성분 함량·단위·연결 또는 영양성분 이름·활성 상태를 변경한다.

결과: 기존 care_nutrient_snapshots의 이름·함량·단위·영양성분 연결은 바뀌지 않는다.

## AC-F-3.2-003 의약품과 성분 없음 경계

- MEDICATION 등록은 성공하고 스냅샷은 0건이다.
- 활성 성분이 없는 SUPPLEMENT 등록도 성공하고 스냅샷은 0건이다.
- 비활성 Nutrient 연결은 새 스냅샷에 포함하지 않는다.

## AC-F-3.2-004 원자성과 반복 등록

- 스냅샷 저장이 실패하면 새 care_item과 일부 스냅샷을 모두 롤백하고 503 계약을 유지한다.
- 같은 영양제를 반복 등록하면 서로 다른 care_item_id 아래 독립 스냅샷 집합을 만든다.
- 한 care_item_id와 nutrient_id 조합은 중복될 수 없다.

## AC-F-3.2-005 기존 행 백필

- 0011 상태에 존재하던 SUPPLEMENT care_items는 0012 upgrade 때 당시 활성 카탈로그
  성분으로 한 번 백필된다.
- MEDICATION·비활성 성분·활성 성분 없는 영양제에는 백필 행을 만들지 않는다.
- downgrade는 care_items를 보존하고 스냅샷 테이블만 제거하며 재-upgrade할 수 있다.

## AC-F-3.2-006 API 호환성과 보안

- 등록 API의 요청·201 응답·401·404·422·503·AccessCookieAuth 계약은 F-3.1과 같다.
- 요청과 응답에 스냅샷 ID·care_item 소유자 ID를 추가하지 않는다.
- 스냅샷은 인증 사용자가 새로 생성한 care_item에만 귀속된다.

## AC-F-3.2-007 데이터·ERD 일치

- care_nutrient_snapshots의 필드·FK·UNIQUE·CHECK·인덱스·삭제 정책이 ORM·0012·
  ERD와 일치한다.
- 사용자 데이터 시드와 외부 서비스 의존성을 추가하지 않는다.

## 비기능 경계

- 실제 개인정보·건강정보·비밀정보를 시드·문서·로그에 포함하지 않는다.
- AWS·AI·이메일·스케줄러 없이 로컬 PostgreSQL에서 검증할 수 있다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-3.2-001~002 | `tests/acceptance/care/test_supplement_nutrient_snapshots.py` | 생성·불변성 |
| AC-F-3.2-003~004 | 저장소 단위·통합 테스트 | 유형·활성·원자성·중복 |
| AC-F-3.2-005 | 0012 마이그레이션 왕복·백필 검사 | 기존 행 호환성 |
| AC-F-3.2-006 | 계약 회귀·OpenAPI 검사 | F-3.1 계약 유지 |
| AC-F-3.2-007 | `tests/integration/care/test_nutrient_snapshot_schema.py` | ORM·0012·ERD |
