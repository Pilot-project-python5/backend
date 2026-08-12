# F-3.3 인수 조건

## AC-F-3.3-001 구매 수량과 단위 보존

전제: DB에 TABLET·CAPSULE·SCOOP·PACKET 중 하나의 unit_form을 가진 제품이 있다.

행동: 로그인 사용자가 F-3.1 등록 API로 제품의 구매 총수량과 복용 계획을 등록한다.

결과: total_quantity와 Product.unit_form을 복사한 quantity_unit을 새 CareItem에
저장하고 201 응답에도 같은 값을 반환한다.

## AC-F-3.3-002 카탈로그 변경 격리

등록 후 Product.unit_form이 바뀌어도 기존 CareItem의 quantity_unit은 바뀌지 않는다.

## AC-F-3.3-003 재구매 이력 분리

- 같은 사용자가 같은 제품을 미소진 상태에서 다시 등록해도 기존 total_quantity와
  quantity_unit을 수정·합산하지 않는다.
- 두 요청은 서로 다른 ID의 CareItem 두 건을 생성한다.
- 영양제면 각 CareItem 아래 성분 스냅샷도 독립적으로 생성한다.

## AC-F-3.3-004 수량·인증·오류 계약

- total_quantity는 기존과 같이 0 초과 NUMERIC(12,3) 범위다.
- quantity_unit은 요청할 수 없고 서버가 카탈로그 값으로 결정한다.
- 401·404·422·503 계약과 사용자 소유권은 F-3.1과 같다.

## AC-F-3.3-005 기존 데이터 백필과 롤백

- 0012 상태의 기존 care_items는 0013 upgrade 때 연결된 Product.unit_form으로
  quantity_unit이 모두 백필된다.
- 0013 downgrade는 care_items 행과 F-3.2 스냅샷을 보존하고 quantity_unit 컬럼만
  제거하며 재-upgrade할 수 있다.

## AC-F-3.3-006 API 호환성

- 등록 요청과 기존 응답 필드는 유지하고 201 응답에 quantity_unit만 추가한다.
- Swagger는 TABLET·CAPSULE·SCOOP·PACKET 허용값과 예시를 제공한다.
- 요청·응답에 user_id를 노출하지 않는다.

## AC-F-3.3-007 데이터·ERD 일치

- care_items의 quantity_unit NOT NULL·CHECK와 기존 제약이 ORM·0013·ERD에서 일치한다.
- 사용자 데이터 시드와 외부 서비스 의존성을 추가하지 않는다.

## 비기능 경계

- 실제 개인정보·건강정보·비밀정보를 시드·문서·로그에 포함하지 않는다.
- AWS·AI·이메일·스케줄러 없이 로컬 PostgreSQL에서 검증할 수 있다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-3.3-001~002 | 등록 인수·저장소 통합 테스트 | 단위 복사·불변성 |
| AC-F-3.3-003 | 반복 등록 인수·통합 테스트 | 기존 행 미변경·독립 스냅샷 |
| AC-F-3.3-004 | 단위·계약 테스트 | 수량·인증·오류 회귀 |
| AC-F-3.3-005 | 0013 마이그레이션 왕복 테스트 | 백필·기존 행 보존 |
| AC-F-3.3-006 | OpenAPI 계약 테스트 | additive 응답 확장 |
| AC-F-3.3-007 | 통합 스키마·ERD 검사 | ORM·0013·ERD |
