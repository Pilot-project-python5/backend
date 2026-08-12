# F-3.2 설계

## API 계약

- 메서드와 경로: 기존 `POST /api/v1/care/items`
- 인증: HttpOnly access JWT 쿠키 `AccessCookieAuth` 유지
- 요청: F-3.1 필드와 검증을 변경하지 않음
- 성공 응답: 기존 201 `CareItemResponse` 유지. 스냅샷은 내부 저장 결과이며 이번
  응답에 추가하지 않음
- 오류 응답: 401 `AUTH_REQUIRED`, 404 `PRODUCT_NOT_FOUND`,
  422 `VALIDATION_FAILED`, 503 `SERVICE_UNAVAILABLE` 유지
- 멱등성: 없음. 반복 등록은 각 care_item 아래 새 스냅샷 집합을 생성한다.

## 데이터 설계

- 엔티티: care_nutrient_snapshots(id, care_item_id, nutrient_id,
  nutrient_name, amount_per_unit, unit)
- 관계와 카디널리티: care_items 1:N care_nutrient_snapshots,
  nutrients 1:N care_nutrient_snapshots
- 제약 조건: UUID PK·FK, `(care_item_id, nutrient_id)` UNIQUE, trim 기준
  1~100자 nutrient_name, 양수 NUMERIC(12,4) amount_per_unit,
  unit은 MG·G·MCG·IU
- 인덱스: 고유 `(care_item_id, nutrient_id)`, FK 보호용 `nutrient_id`
- 마이그레이션: `20260812_0012_care_nutrient_snapshots`, down_revision 0011
- 백필과 기존 데이터 영향: 기존 SUPPLEMENT care_items에 0012 적용 시점의 활성
  ProductNutrient·Nutrient 값을 한 번 삽입한다. MEDICATION과 활성 성분 없음은 0건이다.
  현재 공유 로컬 개발 DB care_items는 0건이며 사용자 행을 삭제하지 않는다.
- 이력과 삭제: care_item 삭제 시 CASCADE, nutrient 삭제는 RESTRICT. 제품·성분
  카탈로그 변경은 스냅샷을 갱신·삭제하지 않는다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: CARE_NUTRIENT_SNAPSHOTS가 개념 엔티티로만 존재하고 실제 구현
  제약·인덱스·백필·삭제 정책이 확정되지 않았다.
- 변경 후 구조: 실제 0012 필드, care_items·nutrients 관계, UNIQUE·CHECK·인덱스,
  CASCADE·RESTRICT와 불변 스냅샷 정책을 기록한다.
- 변경하지 않는 경우의 이유: 해당 없음
- ERD 검증 방법: ORM·0012·통합 스키마 검사와 ERD validator 비교

## 애플리케이션 흐름

1. F-3.1 서비스가 검증을 끝내고 저장소 create를 호출한다.
2. 저장소가 제품 ID와 product_type을 조회한다.
3. SUPPLEMENT면 활성 Nutrient와 ProductNutrient를 안정 순서로 조회해 값 객체로
   복사하고 MEDICATION이면 빈 집합을 사용한다.
4. 같은 세션에 CareItem과 CareNutrientSnapshot을 추가하고 한 번만 commit한다.
5. 조회·flush·commit 중 오류가 나면 rollback하고 기존 공통 503으로 변환한다.

## 보안과 개인정보

- 소유권 검사: 스냅샷은 요청 care_item_id를 받지 않고 인증 사용자 소유로 새로
  생성되는 CareItem ID에만 연결한다.
- 민감 필드: 스냅샷은 사용자의 복용 제품에서 파생된 건강 관련 데이터다.
- 로그 제외 항목: 사용자 ID, care_item_id와 성분 집합 전체를 기본 로그에 추가하지 않는다.

## 로컬 어댑터

- 데이터베이스: 로컬 PostgreSQL 개발·테스트 DB
- 시간: 새 시간 규칙 없음. F-3.1 SystemClock·APP_TIMEZONE 유지
- 이메일: 사용하지 않음
- 스케줄러: 사용하지 않음

## 호환성

- OpenAPI 영향: 요청·응답 스키마와 상태 코드는 바뀌지 않는다. Swagger 설명과
  저장소 기준 파일이 동일함을 확인한다.
- 기존 데이터 영향: 0012가 기존 영양제 care_items를 현재 활성 카탈로그로 최선
  백필한다. 이후 카탈로그 변경은 반영하지 않는다.
- 롤백: API 코드를 이전 버전으로 되돌리고 0012를 downgrade해 스냅샷 테이블만
  제거한다. care_items와 제품 카탈로그는 보존된다.
