# F-3.7 설계

## API 계약

- 메서드와 경로: 기존 `POST /api/v1/care/items`, `GET /api/v1/care/items`
- 인증: Access JWT와 서버 refresh session 검증
- 요청: 변경 없음
- 성공 응답: POST·GET 항목에 expected_depletion_date, GET 항목에
  days_until_depletion 정수 추가
- 오류 응답: 기존 401·404·422·503 유지
- 멱등성: 조회 D-day는 같은 DB·기준일에 결정적이며 등록은 기존처럼 매번 새 이력 생성

## 데이터 설계

- 엔티티: CareItem
- 관계와 카디널리티: 변경 없음
- 제약 조건: expected_depletion_date NOT NULL,
  expected_depletion_date >= intake_start_date
- 인덱스: `(expected_depletion_date, user_id)`
- 마이그레이션: 0016에서 nullable 열 추가 → 기존 행 SQL 백필 → CHECK → NOT NULL →
  인덱스 순서로 적용
- 백필과 기존 데이터 영향: `intake_start_date + ceil(total_quantity /
  (dose_per_intake * intakes_per_day)) - 1` 공식으로 모든 기존 행 계산
- 이력과 삭제: 소프트 삭제 행도 보존·백필하되 활성 목록·후속 알림에서 제외한다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: CareItem에 총수량·복용 계획만 있고 예상 소진일은 예정 상태
- 변경 후 구조: expected_depletion_date 저장값과 days_until_depletion 파생값을 명시
- 변경하지 않는 경우의 이유: 해당 없음
- ERD 검증 방법: validator, ORM·0016·실제 PostgreSQL 스키마·백필 왕복 테스트

## 애플리케이션 흐름

1. 등록 서비스가 승인된 공식으로 예상 소진일을 계산한다.
2. 저장소가 CareItem과 예상 소진일을 같은 트랜잭션으로 저장한다.
3. 등록 API가 저장된 예상 소진일을 반환한다.
4. 목록 서비스가 저장된 예상 소진일과 APP_TIMEZONE 오늘의 차이를 계산한다.
5. 목록 API가 음수·0·양수 days_until_depletion을 그대로 반환한다.

## 보안과 개인정보

- 소유권 검사: 기존 user_id·deleted_at IS NULL 저장소 필터 유지
- 민감 필드: 사용자 ID와 실제 복용 기록은 응답하지 않음
- 로그 제외 항목: user_id·care_item_id·복용 계획·예상 소진일

## 로컬 어댑터

- 데이터베이스: 로컬 PostgreSQL·SQLAlchemy·Alembic
- 시간: SystemClock/FakeClock, APP_TIMEZONE
- 이메일: 해당 없음
- 스케줄러: 해당 없음

## 호환성

- OpenAPI 영향: 기존 응답에 필수 필드를 추가하는 additive 확장
- 기존 데이터 영향: 전 행 결정적 백필, 요청 계약과 기존 행 식별자·수량은 유지
- 롤백: 0016 downgrade가 인덱스·CHECK·열만 제거하고 기존 CareItem은 보존
