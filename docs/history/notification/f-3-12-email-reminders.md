---
feature_id: "F-3.12"
title: "이메일 리마인더"
requirement_id: "FR-3"
domain: "notification"
status: "implemented"
completed_on: "2026-08-14"
feature_packet: "docs/features/notification/f-3-12-email-reminders"
pull_request: "https://github.com/Pilot-project-python5/backend/pull/25"
commit: "320c7c0"
---

# F-3.12 이메일 리마인더 구현 이력

## 구현 요약

재구매·유통기한 화면 알림을 같은 논리 이벤트에서 로컬 SMTP 이메일로 전달한다.
인증된 활성 사용자의 당일 오전 9시 알림만 등록하며, Notification별 중복 방지와
5분 간격 최대 3회 재시도·최종 실패 이력을 PostgreSQL에 보존한다.

## 구현 범위

### 포함

- REPURCHASE·EXPIRATION Notification 기반 로컬 SMTP 이메일 전달
- ACTIVE·이메일 인증 사용자 및 당일 오전 9시 일정 대상 필터
- Notification별 EmailDelivery 한 건, 수신 이메일 스냅샷과 전달 상태 이력
- 동시 claim, 5분 lease, 최초 포함 최대 3회 재시도와 최종 실패 처리
- Mailpit 로컬 확인 절차, ERD·요구사항·API 경계 문서와 자동화 테스트

### 제외

- 공개 전달 상태·수동 재시도·취소 API, HTML 이메일은 제외했다.
- 과거 알림 백필, 푸시·SMS, 추천 소식 알림은 제외했다.
- 운영 이메일 공급자, 제공자 멱등 키, 반송·스팸 처리와 AWS 큐·스케줄러는 2차다.

## 주요 구현 내용

- EmailReminderService는 APP_TIMEZONE 기준 오전 9시 이후 오늘 09시 일정만 등록한다.
  이어 오래된 마지막 SENDING을 종료하고 due 전달을 최대 100건 claim해 순차 처리한다.
- 저장소는 PostgreSQL `FOR UPDATE SKIP LOCKED`와 5분 SENDING lease를 사용한다. claim 때
  attempt_count를 증가시키고, 결과 갱신은 전달 ID와 시도 번호를 함께 확인해 오래된 결과가
  현재 상태를 덮어쓰지 못하게 한다.
- SMTP 성공은 SENT와 sent_at을, 1·2회 실패는 RETRY와 5분 뒤 시각을, 3회 실패는
  FAILED를 기록한다. 마지막 시도 중 프로세스가 종료되면 lease 만료 후
  DELIVERY_RESULT_UNKNOWN으로 종료한다.
- NotificationJob과 로컬 worker가 재구매·유통기한 논리 이벤트 생성 뒤 이메일 단계를
  실행하며, Mailpit 또는 테스트 가짜 발신기로 외부 서비스 없이 확인할 수 있다.

## API 변경

공개 HTTP API와 OpenAPI 계약 변경은 없다. 기존 화면 알림 API를 그대로 유지하며 이메일
전달 상태는 worker 내부와 DB에만 보존한다.

## 데이터·ERD·마이그레이션

- 0020 마이그레이션으로 notifications와 1:0..1인 email_deliveries를 추가했다.
  notification_id UNIQUE·CASCADE FK로 중복을 막고 recipient_email을 등록 시점 값으로
  보존한다.
- 상태 PENDING·SENDING·RETRY·SENT·FAILED, 시도 횟수 0~3, 상태별 시간·오류 일관성을
  CHECK로 강제한다. PENDING·SENDING·RETRY의 `(next_retry_at, id)` 부분 인덱스로 due
  claim을 지원한다.
- 새 시드는 없고 0020 downgrade는 email_deliveries만 삭제해 Notification을 보존한다.
  ERD와 데이터 모델 문서를 실제 제약에 맞게 갱신했다.

## 보안과 개인정보

ACTIVE이며 email_verified_at이 있는 사용자만 등록하고 수신 주소는 DB 내부 스냅샷으로
관리한다. 로그에는 이메일 주소, 사용자·Notification·CareItem ID, 제품명, 기준일과 SMTP
오류 원문을 남기지 않는다. DB에는 허용한 안전 오류 코드만 저장하고 이메일 본문에도 내부
식별자와 인증정보를 포함하지 않는다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-3.12-001~006 단위·PostgreSQL 통합·인수 테스트 | 6개 조건 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-3.12` | 12개 통과 |
| 전체 로컬 검증 | `make verify` | 466개 통과, 커버리지 95.07% |
| 정적 검사 | ruff format/check, mypy | 모두 통과, 소스 242개 타입 검사 |
| 데이터·ERD | 0020 upgrade·alembic check, ERD validator | 모두 통과, 엔티티 19개·관계 20개 |
| 시드·API | 전체 시드 연속 2회, OpenAPI 일치 검사 | 7세트·84건 멱등, 계약 일치 |

## 주요 결정과 근거

- 논리 이벤트는 Notification, 전달 시도는 EmailDelivery로 분리했다. 화면과 이메일의
  D-day 판단을 하나로 유지하면서 전달 실패가 화면 알림 생성을 되돌리지 않게 하기 위해서다.
- 사용자 이메일은 전달 등록 시 스냅샷으로 보존한다. 이후 계정 이메일이 바뀌어도 이미
  생성된 전달의 대상과 감사 이력을 명확하게 하기 위해서다.
- 놓친 과거 이벤트는 백필하지 않고 당일 09시 일정만 등록한다. 현재 논리 알림 정책과
  일치시키고 오래된 D-day 이메일이 뒤늦게 몰리는 혼란을 피하기 위해서다.
- 최대 3회·고정 5분과 batch 100을 코드 상수로 고정했다. 로컬 MVP에서 운영 설정 복잡도를
  줄이면서 일시 오류 복구와 무한 재시도를 함께 방지하기 위해서다.
- 마지막 SENDING lease 만료는 결과 불명 최종 실패로 종료한다. 제공자 멱등 키가 없는
  로컬 SMTP에서 결과를 모르는 전송을 자동 반복해 중복 메일을 늘리지 않기 위해서다.

## 알려진 제약

- SMTP가 메일을 수락한 직후 SENT 저장 전에 프로세스가 종료되면 1·2번째 시도는 lease
  만료 후 재전송되어 중복될 수 있다. 로컬 SMTP에는 제공자 멱등 키가 없기 때문이다.
- worker가 트리거 날짜 내내 중단되면 다음 날 과거 알림을 소급 발송하지 않는다.
- 전송이 순차 처리되고 공개 상태 조회·운영자 재처리 수단이 없다.

## 후속 작업

- 2차 AWS 전환에서 관리형 큐·스케줄러, 운영 이메일 공급자와 제공자 멱등 키 또는 outbox,
  지수 백오프·관측성·반송·스팸 처리와 운영자 재처리 절차를 승인한다.
- 운영 전 개인정보 보유 기간과 EmailDelivery 정리 정책을 확정한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/notification/f-3-12-email-reminders
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
