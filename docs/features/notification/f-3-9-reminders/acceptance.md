# F-3.9 인수 조건

## AC-F-3.9-001 사용자별 최신순 목록

전제: 두 사용자에게 읽음·읽지 않음, 재구매·유통기한 알림이 여러 건 있다.

행동: 한 사용자가 기본값 또는 유효한 페이지 값으로 목록을 요청한다.

결과: 자신의 알림만 `created_at DESC, id DESC`로 반환하며 모든 공개 필드,
페이지 메타데이터와 no-store 헤더가 정확하다.

## AC-F-3.9-002 인증과 페이지 검증

전제: 인증 쿠키가 없거나 페이지 값이 허용 범위를 벗어난다.

행동: 알림 목록 또는 읽음 API를 요청한다.

결과: 인증 실패는 AUTH_REQUIRED 401, 페이지 검증 실패는 VALIDATION_FAILED 422의
공통 오류 계약을 따른다.

## AC-F-3.9-003 소유 알림 멱등 읽음

전제: 현재 사용자의 읽지 않은 알림과 다른 사용자의 알림이 있다.

행동: 소유 알림을 두 번 읽음 처리하고 타인·없는 알림도 요청한다.

결과: 소유 알림은 최초 read_at을 유지한 200을 두 번 반환하고, 타인·없는 알림은
구분 없이 NOTIFICATION_NOT_FOUND 404다.

## AC-F-3.9-004 유통기한 알림 시간·경계

전제: 유통기한이 D-5·D-3·D-1, D-4, 없음인 활성 항목과 삭제 항목이 있다.

행동: worker를 오전 9시 전과 이후에 실행한다.

결과: 오전 9시 이후 활성 D-5·D-3·D-1만 EXPIRATION 이벤트가 생기며 scheduled_at은
그날 현지 09:00의 UTC 시각이다. 다른 항목과 오전 9시 전에는 생기지 않는다.

## AC-F-3.9-005 생성과 읽음의 멱등성

전제: 같은 날짜의 대상 항목과 이미 읽은 알림이 있다.

행동: worker와 읽음 요청을 반복한다.

결과: 논리 이벤트는 종류·기준일·트리거별 하나이고 read_at도 최초 값에서 바뀌지 않는다.

## AC-F-3.9-006 이력 보존과 저장소 실패

전제: 알림 생성 뒤 CareItem이 소프트 삭제되거나 유통기한이 교정되며, 별도 사례에서
PostgreSQL 오류가 발생한다.

행동: 목록 조회·읽음 또는 worker를 실행한다.

결과: 기존 알림은 목록에 보존되고, HTTP 저장소 실패는 안전한 503이며 worker 실패는
상위 실행 루프가 재시도할 수 있는 도메인 오류로 전달되고 트랜잭션은 롤백된다.

## 유효성 및 실패 사례

- 위 AC-F-3.9-002, 003, 004, 005, 006으로 인증·권한·시간·멱등·실패 경계를 고정한다.

## 데이터·ERD 인수 조건

- 새 데이터 구조가 없어 마이그레이션과 ERD 구조 변경은 없다.
- 현재 head 0019, 기존 Notification 제약·인덱스와 docs/architecture/erd.md 일치를
  `alembic check`, 마이그레이션·ERD 검사로 확인한다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-3.9-001 | tests/acceptance/notification/test_in_app_notifications.py, tests/contract/notification/test_notification_contract.py | 소유권·정렬·페이지·응답 계약 |
| AC-F-3.9-002 | tests/acceptance/notification/test_in_app_notifications.py, tests/contract/notification/test_notification_contract.py | 401·422 공통 오류 |
| AC-F-3.9-003 | tests/acceptance/notification/test_in_app_notifications.py, tests/integration/notification/test_notification_repository.py | 멱등 읽음·404 은닉 |
| AC-F-3.9-004 | tests/acceptance/notification/test_expiration_notification.py, tests/unit/notification/test_expiration_service.py | 09시·D-day 경계 |
| AC-F-3.9-005 | tests/unit/notification/test_notification_job.py, tests/integration/notification/test_notification_repository.py | 생성·읽음 멱등성 |
| AC-F-3.9-006 | tests/acceptance/notification/test_in_app_notifications.py, tests/unit/notification/test_notification_service.py | 이력 보존·오류 변환 |
