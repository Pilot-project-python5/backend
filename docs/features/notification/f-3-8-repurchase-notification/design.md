# F-3.8 설계

## API 계약

- 메서드와 경로: 기존 GET `/api/v1/care/items` 응답 확장. 작업자 전용 HTTP API 없음
- 인증: 기존 AccessCookieAuth와 서버 refresh session
- 요청: 변경 없음
- 성공 응답: 각 목록 항목에 필수 NORMAL·LOW_STOCK·DEPLETED inventory_status
- 오류 응답: 기존 401·422·503 유지
- 멱등성: 목록은 읽기, 작업은 DB 고유 제약과 ON CONFLICT DO NOTHING으로 멱등

## 데이터 설계

- 엔티티: Notification
- 관계와 카디널리티: User 1:N Notification, CareItem 1:N Notification
- 제약 조건: notification_type REPURCHASE·EXPIRATION, trigger_days_before 5·3·1,
  scheduled_at <= created_at, read_at null 또는 created_at 이상, 논리 이벤트 조합 UNIQUE
- 인덱스: `(user_id, read_at, created_at DESC, id)` 후속 화면 조회 인덱스. 후보
  CareItem은 기존 `(expected_depletion_date, user_id)` 사용
- 마이그레이션: 0019 notifications 생성
- 백필과 기존 데이터 영향: 과거 알림 백필 없음. 적용 이후 당일 오전 9시 이후의 정확한
  트리거만 생성
- 이력과 삭제: User·CareItem 물리 삭제 시 CASCADE. CareItem 소프트 삭제는 기존 알림을
  보존하고 새 생성만 제외

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: 계획된 notifications 개념 구조
- 변경 후 구조: 실제 필드·FK·CHECK·UNIQUE·인덱스와 F-3.8 구현 경계
- 변경하지 않는 경우의 이유: 해당 없음
- ERD 검증 방법: 0019 왕복·inspector 스키마 테스트·validate_erd.py·alembic check

## 애플리케이션 흐름

1. 목록 서비스가 기존 days_until_depletion으로 inventory_status를 계산한다.
2. worker가 주입 시계의 현재 시각을 APP_TIMEZONE으로 변환하고 오전 9시 전이면 끝낸다.
3. 저장소가 당일 기준 D-5·D-3·D-1인 활성 CareItem과 user_id를 조회한다.
4. 서비스가 기준일·트리거·로컬 오전 9시 UTC scheduled_at을 가진 REPURCHASE 이벤트를
   만들고 저장소가 충돌을 무시해 한 건만 보존한다.
5. DB 오류는 작업에서 전파되고 기존 run_forever 경계가 기록 후 다음 poll에서 재시도한다.

## 보안과 개인정보

- 소유권 검사: 목록은 기존 현재 사용자 필터. 작업은 CareItem에 저장된 user_id를 그대로
  Notification FK로 사용하며 삭제 행을 제외
- 민감 필드: 새 공개 API에 user_id·Notification 내부 ID를 노출하지 않음
- 로그 제외 항목: user_id, care_item_id, 제품명, 기준일을 개별 로그에 남기지 않고 생성
  건수와 실패 유형만 기록

## 로컬 어댑터

- 데이터베이스: Docker PostgreSQL dev/test
- 시간: 주입 Clock과 APP_TIMEZONE, 기본 Asia/Seoul
- 이메일: 없음. F-3.12에서 Notification을 전달
- 스케줄러: 기존 로컬 worker poll 루프. 매 실행마다 서비스가 날짜·오전 9시 게이트와
  DB 멱등성을 적용

## 호환성

- OpenAPI 영향: 기존 GET 목록의 additive 필수 응답 필드
- 기존 데이터 영향: CareItem 변경·백필 없음, notifications는 빈 테이블로 시작
- 롤백: 애플리케이션 이전 버전 후 0019 테이블 제거. CareItem은 보존되지만 생성된
  논리 알림 이력은 소실되므로 운영에서는 사전 백업
