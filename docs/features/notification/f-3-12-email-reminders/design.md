# F-3.12 설계

## API 계약

- 메서드와 경로: 공개 HTTP API 변경 없음. 로컬 worker 내부 작업이다.
- 인증: 사용자 요청 경로가 없다. 대상 User는 ACTIVE·email_verified_at 조건으로 제한한다.
- 요청: Notification과 현재 시각·APP_TIMEZONE, SMTP 설정
- 성공 응답: HTTP 없음. worker는 개인정보 없이 등록·성공·재시도·실패 건수만 기록한다.
- 오류 응답: HTTP 없음. DB 오류는 worker 상위 루프로 전파하고 SMTP 오류는 전달 상태로
  흡수한다.
- 멱등성: notification_id UNIQUE, 원자적 claim과 상태 조건부 갱신으로 정상 반복 실행의
  중복 등록·발송을 막는다.

## 데이터 설계

- 엔티티: EmailDelivery 신규, Notification·User·CareItem·Product 조회
- 관계와 카디널리티: Notification 1:0..1 EmailDelivery
- 제약 조건: notification_id UNIQUE·FK CASCADE, 상태 enum CHECK, attempt_count 0~3,
  상태별 sent_at·next_retry_at·last_error 일관성, updated_at >= created_at
- 인덱스: PENDING·SENDING·RETRY의 `(next_retry_at, id)` 부분 인덱스
- 마이그레이션: 20260814_0020_email_deliveries, downgrade는 전달 테이블만 제거
- 백필과 기존 데이터 영향: 전체 과거 알림 백필 없음. worker 실행 당일 09시 일정의
  기존 Notification만 등록한다.
- 이력과 삭제: recipient_email·시도·오류 코드를 보존한다. Notification 물리 삭제 시
  CASCADE하며 별도 삭제·정리 기능은 없다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: EMAIL_DELIVERIES는 계획 엔티티로만 표시됐다.
- 변경 후 구조: 실제 열, 상태·시도 제약, 1:0..1 관계와 due 부분 인덱스를 확정한다.
- 변경하지 않는 경우의 이유: 해당 없음
- ERD 검증 방법: 0020 upgrade/downgrade/upgrade, `alembic check`, `make erd-check`

## 애플리케이션 흐름

1. NotificationJob이 재구매·유통기한 논리 이벤트 생성을 먼저 마친다.
2. EmailReminderService는 오전 9시 이후 당일 scheduled_at의 누락 EmailDelivery를
   ACTIVE·인증 사용자에 한해 INSERT SELECT·충돌 무시로 등록한다.
3. 저장소는 due PENDING·RETRY 또는 lease 만료 SENDING 중 한 건을 행 잠금과
   SKIP LOCKED로 가져와 attempt_count를 올리고 5분 lease의 SENDING으로 커밋한다.
4. 서비스는 알림 종류와 제품명·기준일로 OutboundEmail을 만들고 SmtpEmailSender를
   호출한다.
5. 성공은 claim attempt token을 조건으로 SENT 처리한다. EmailDeliveryError는 1·2회면
   5분 뒤 RETRY, 3회면 FAILED로 기록하고 다음 due 건을 계속 처리한다.
6. due 건이 없거나 batch 100에 도달하면 종류별 건수 요약을 반환해 안전하게 로그한다.

## 보안과 개인정보

- 소유권 검사: 공개 API가 없고 Notification.user_id와 User를 DB에서 결합한다. ACTIVE·
  인증 사용자만 등록한다.
- 민감 필드: recipient_email은 전달 이력에 필요해 저장하되 API로 노출하지 않는다.
- 로그 제외 항목: 이메일 주소, 사용자·Notification·CareItem ID, 제품명, 기준일과 SMTP
  오류 원문을 기록하지 않는다.

## 로컬 어댑터

- 데이터베이스: Docker PostgreSQL, INSERT ON CONFLICT, FOR UPDATE SKIP LOCKED
- 시간: SystemClock, APP_TIMEZONE 기본 Asia/Seoul, 09:00, retry·lease 300초
- 이메일: 기존 SmtpEmailSender와 Mailpit, 테스트 FakeEmailSender
- 스케줄러: 기존 worker poll, poll당 최대 100건

## 호환성

- OpenAPI 영향: 없음. 기준 파일 일치만 확인한다.
- 기존 데이터 영향: 과거 전체 알림을 보내지 않고 실행 당일 일정만 전달 등록한다.
- 롤백: worker 이메일 단계를 제거하고 0020 downgrade로 email_deliveries만 삭제한다.
  Notification·화면 알림과 User·CareItem은 보존한다.
