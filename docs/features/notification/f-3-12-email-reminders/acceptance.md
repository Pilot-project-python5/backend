# F-3.12 인수 조건

## AC-F-3.12-001 재구매·유통기한 이메일 성공

전제: ACTIVE·인증 사용자의 당일 09시 REPURCHASE·EXPIRATION Notification이 있다.

행동: 오전 9시 이후 worker를 실행한다.

결과: 각 Notification에 EmailDelivery가 한 건 등록되고 현재 이메일로 종류별 제목·본문이
전송되며 attempt_count 1, SENT와 sent_at이 저장된다.

## AC-F-3.12-002 등록 대상 경계

전제: 오전 9시 전 또는 전날 일정과 ACTIVE 미인증·PENDING·SUSPENDED 사용자의
Notification이 있다.

행동: worker를 실행한다.

결과: 오전 9시 전에는 신규 등록하지 않고, 이후에도 당일 일정의 ACTIVE·인증 사용자만
등록한다. 전날 누락분을 소급 등록하지 않는다.

## AC-F-3.12-003 반복·동시 실행 멱등성

전제: 같은 Notification을 여러 worker가 보거나 이미 SENT인 전달이 있다.

행동: worker를 반복·동시에 실행한다.

결과: notification_id UNIQUE로 전달 행은 하나이고 SKIP LOCKED·상태 조건으로 정상
상태의 SMTP 발송도 한 번이다. SENT는 다시 claim하지 않는다.

## AC-F-3.12-004 제한 재시도와 최종 실패

전제: SMTP가 연속 실패한다.

행동: 최초와 각 5분 retry 시각에 worker를 실행한다.

결과: 1·2회는 RETRY·next_retry_at·SMTP_DELIVERY_FAILED, 3회는 FAILED·next null로
남으며 이후 자동 시도하지 않는다. 다른 due 전달은 계속 처리한다.

## AC-F-3.12-005 lease 회수와 시도 토큰

전제: SENDING 전달의 5분 lease가 끝났거나 3번째 SENDING 결과가 불명이다.

행동: 다른 worker가 due claim과 결과 기록을 시도한다.

결과: 1·2차 lease는 다음 attempt로 회수하고 오래된 attempt 결과는 상태를 덮어쓰지
못한다. 3차 결과 불명은 DELIVERY_RESULT_UNKNOWN FAILED로 종료한다.

## AC-F-3.12-006 개인정보·데이터 계약

전제: 0020 마이그레이션과 이메일 작업을 검증한다.

행동: 제약 위반, downgrade/upgrade, 로컬 SMTP·가짜 발신기와 로그를 확인한다.

결과: DB가 1:1·상태·시도·시간 일관성을 강제하고 recipient_email 외 개인정보·ID·오류
원문이 이메일·로그에 노출되지 않는다. downgrade는 Notification을 보존한다.

## 유효성 및 실패 사례

- 위 AC-F-3.12-002~006으로 대상, 멱등, 재시도, 동시성, 개인정보 경계를 고정한다.

## 데이터·ERD 인수 조건

- 0020이 email_deliveries를 생성하고 Notification 1:0..1, 상태·attempt·시간 CHECK와 due
  부분 인덱스를 구현해야 한다.
- downgrade/upgrade, `alembic check`와 ERD validator가 Notification 보존과 문서 일치를
  확인해야 한다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-3.12-001 | tests/acceptance/notification/test_email_reminders.py | 두 종류 등록·SMTP 성공·내용 |
| AC-F-3.12-002 | tests/unit/notification/test_email_reminder_service.py, tests/integration/notification/test_email_delivery_repository.py | 09시·일정·사용자 상태 경계 |
| AC-F-3.12-003 | tests/acceptance/notification/test_email_reminders.py, tests/integration/notification/test_email_delivery_repository.py | 반복 등록·claim·SENT 멱등 |
| AC-F-3.12-004 | tests/unit/notification/test_email_reminder_service.py, tests/acceptance/notification/test_email_reminders.py | 5분·3회·다른 건 계속 |
| AC-F-3.12-005 | tests/integration/notification/test_email_delivery_repository.py | SKIP LOCKED·lease·attempt token |
| AC-F-3.12-006 | tests/integration/notification/test_email_delivery_migration.py, tests/unit/notification/test_email_templates.py | 제약·왕복·안전 내용 |
