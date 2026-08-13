# F-3.5 인수 조건

## AC-F-3.5-001 계획 기반 일일 예정 섭취량

전제: 현재 사용자가 활성 영양제 CareItem과 등록 시점 성분 스냅샷을 가지고 있다.

행동: `GET /api/v1/care/daily-intake`를 요청한다.

결과: 각 스냅샷의 단위당 함량 × 회당 복용량 × 하루 횟수를 계산해 성분별 일일
예정 섭취량을 200으로 반환한다.

## AC-F-3.5-002 동일 성분 단위 환산과 합산

G·MG·MCG인 같은 nutrient_id는 Nutrient canonical_unit으로 정확히 환산한 뒤 하나로
합산한다. IU 기준 성분은 IU 스냅샷끼리 합산하고 질량 단위와 IU를 서로 변환하지 않는다.
Decimal 계산은 중간 반올림 없이 수행하며 응답은 후행 0을 제거한 문자열이다.

## AC-F-3.5-003 스냅샷 불변성·복수 구매

같은 제품 또는 성분의 복수 CareItem은 각각 계산에 기여한다. 제품 카탈로그의 함량·
단위가 바뀌거나 연결이 비활성화되어도 기존 CareItem은 저장된 스냅샷 값을 사용한다.

## AC-F-3.5-004 소유권·활성·제품 유형 경계

- 다른 사용자의 CareItem과 `deleted_at IS NOT NULL` CareItem은 제외한다.
- MEDICATION과 성분 스냅샷이 없는 SUPPLEMENT는 결과에 기여하지 않는다.
- 미래 intake_start_date를 가진 활성 계획도 특정 날짜의 실제 섭취가 아닌 일일 계획
  총량이므로 포함한다.

## AC-F-3.5-005 빈 결과·정렬·응답 최소화

- 대상 스냅샷이 없으면 200과 `{"nutrients": []}`를 반환한다.
- 결과는 nutrient_code ASC, nutrient_id ASC로 안정 정렬한다.
- 각 항목은 nutrient_id·nutrient_code·nutrient_name·daily_amount·unit만 제공하고
  user_id·care_item_id·개별 복용 계획은 노출하지 않는다.

## AC-F-3.5-006 인증·캐시·장애

- 미인증 요청은 401 `AUTH_REQUIRED`다.
- 성공 응답은 `Cache-Control: no-store`를 포함한다.
- DB 실패와 변환 불가능한 저장 단위는 503 `SERVICE_UNAVAILABLE`이며 부분 결과를
  반환하지 않는다.

## 데이터·ERD 인수 조건

## AC-F-3.5-007 파생 계산과 ERD 무변경

일일 예정 섭취량을 DB에 저장하거나 신규 테이블·컬럼·인덱스를 만들지 않는다. 기존
CareItem·성분 스냅샷·Nutrient 모델과 `docs/architecture/erd.md`의 파생값 정의가
일치하고 ERD 검증이 통과한다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-3.5-001~002 | 예정 섭취량 서비스 단위·인수 테스트 | 공식·질량 환산·IU·Decimal |
| AC-F-3.5-003~004 | 저장소 통합·인수 테스트 | 스냅샷·복수 구매·소유권·활성 필터 |
| AC-F-3.5-005 | 계약·인수 테스트 | 빈 배열·정렬·응답 최소화 |
| AC-F-3.5-006 | 계약·서비스 테스트 | 401·503·no-store·부분 결과 금지 |
| AC-F-3.5-007 | ERD·스키마 회귀 검사 | 마이그레이션·영속 데이터 변경 없음 |
