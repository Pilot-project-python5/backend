# F-3.5 설계

## API 계약

- 메서드와 경로: `GET /api/v1/care/daily-intake`
- 인증: HttpOnly access JWT 쿠키 `AccessCookieAuth`; access JWT와 서버 refresh
  session을 함께 검증한다.
- 요청: 경로·쿼리·본문 값 없음
- 성공 응답: 200 `DailyIntakeResponse`와 `Cache-Control: no-store`
  - nutrients: nutrient_id, nutrient_code, nutrient_name, daily_amount, unit 배열
  - 빈 대상은 `{"nutrients": []}`
- 오류 응답: 401 `AUTH_REQUIRED`, DB 장애 또는 변환 불가능한 저장 단위는 503
  `SERVICE_UNAVAILABLE`
- 멱등성: 읽기 전용 GET이며 반복 요청은 영속 상태를 바꾸지 않는다.

## 데이터 설계

- 엔티티: 기존 care_items, care_nutrient_snapshots, nutrients를 읽기만 한다.
- 관계와 카디널리티: care_items 1:N care_nutrient_snapshots, nutrients 1:N
  care_nutrient_snapshots 유지
- 제약 조건: 기존 F-3.2·F-3.4 제약을 변경하지 않는다.
- 인덱스: 기존 활성 사용자 CareItem 부분 인덱스와 snapshot nutrient_id 인덱스를
  사용하며 신규 인덱스를 만들지 않는다.
- 마이그레이션: 없음. 일일 예정 섭취량은 파생값으로 저장하지 않는다.
- 백필과 기존 데이터 영향: 없음
- 이력과 삭제: `deleted_at IS NULL`만 계산하고 소프트 삭제 행·스냅샷은 보존한다.

## ERD 영향

- docs/architecture/erd.md 변경: 파생값 설명만 보강, Mermaid 구조 변경 없음
- 변경 전 구조: 이미 일일 예정 섭취량을 활성 영양제 스냅샷과 복용 계획의 파생값으로
  정의한다.
- 변경 후 구조: 동일. 설명에 사용자 소유·소프트 삭제 필터, G·MG·MCG 환산,
  IU 동일 단위 합산과 비저장 정책을 명시한다.
- 구조를 변경하지 않는 이유: 테이블·컬럼·관계·제약·인덱스·보존 정책을 바꾸지 않고
  기존 파생값 정의를 구현한다.
- ERD 검증 방법: Feature Packet·저장소 조회·ORM과 기존 ERD 설명을 비교하고
  `make erd-check`를 실행한다.

## 애플리케이션 흐름

1. 보호 API 공통 인증이 현재 user_id를 확정한다.
2. 저장소가 현재 사용자 소유이면서 deleted_at NULL인 CareItem과 성분 스냅샷,
   Nutrient 표시·기준 단위를 조회한다.
3. 서비스가 각 행의 amount_per_unit, dose_per_intake와 intakes_per_day를 Decimal로
   곱한다.
4. G·MG·MCG는 Nutrient canonical_unit으로 정확히 환산하고 IU는 IU인지 확인한다.
5. nutrient_id별로 합산하고 nutrient_code·nutrient_id 순으로 정렬한다.
6. 라우터가 Decimal을 정규화한 문자열로 직렬화하고 no-store 헤더와 함께 반환한다.

## 보안과 개인정보

- 소유권 검사: 요청 user_id를 받지 않고 인증된 현재 사용자 ID를 저장소 조건에 강제한다.
- 민감 필드: 복용 성분과 예정 섭취량은 건강 관련 데이터다.
- 로그 제외 항목: user_id, care_item_id, nutrient별 복용량 전체를 기본 로그에 남기지
  않는다. 응답에는 care_item_id와 사용자 ID를 노출하지 않는다.

## 로컬 어댑터

- 데이터베이스: 로컬 PostgreSQL 개발·테스트 DB
- 시간: 계산 기준 날짜를 사용하지 않으므로 Clock 의존성 없음
- 이메일: 사용하지 않음
- 스케줄러: 사용하지 않음

## 호환성

- OpenAPI 영향: 보호 GET 경로와 200·401·503 스키마를 추가한다.
- 기존 데이터 영향: 읽기 전용이며 기존 행을 갱신하지 않는다.
- 롤백: 신규 라우터·서비스·저장소 조회와 문서를 제거한다. DB downgrade는 없다.
