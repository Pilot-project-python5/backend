# F-3.12 이메일 리마인더

## 목표

F-3.8·F-3.9의 재구매·유통기한 논리 알림을 로컬 SMTP 이메일로 전달한다. Notification별
전달·시도·재시도·성공·최종 실패 상태를 보존해 반복 worker 실행에도 정상 상태에서는
한 번만 보내고 일시 실패를 최대 두 번 추가 재시도한다.

## 사용자 이야기

사용자로서, 앱을 열지 않아도 제품 재구매와 유통기한 확인 시점을 놓치지 않기 위해
D-5·D-3·D-1 오전 9시 알림을 인증된 이메일로 받고 싶다.

## 비즈니스 규칙

1. F-3.12는 기존 Notification을 이메일 전달의 단일 원본으로 사용하며 별도 알림 날짜를
   다시 계산하지 않는다.
2. APP_TIMEZONE 당일 오전 09시 일정의 Notification만 새 EmailDelivery로 등록하고
   전날 누락된 논리 이벤트는 새로 등록하지 않는다.
3. User가 ACTIVE이고 email_verified_at이 있는 경우에만 전달을 등록한다.
4. Notification 한 건당 EmailDelivery 한 건이며 수신 주소는 등록 시점 이메일을
   스냅샷으로 저장한다.
5. 상태는 PENDING·SENDING·RETRY·SENT·FAILED다. attempt_count는 실제 SMTP 시도 횟수로
   0~3이고 최대 3회는 최초 발송을 포함한다.
6. PENDING 또는 due RETRY를 원자적으로 SENDING claim하고 5분 lease를 둔다. 동시
   worker는 `FOR UPDATE SKIP LOCKED`로 같은 행을 동시에 가져가지 않는다.
7. SMTP 성공은 SENT와 sent_at을 저장하고 next_retry_at·last_error를 비운다. 이후에는
   다시 claim하지 않는다.
8. 1·2회 SMTP 실패는 RETRY와 5분 뒤 next_retry_at을 저장한다. 3회 실패는 FAILED로
   저장하고 자동 재시도하지 않는다.
9. SMTP 오류 원문 대신 `SMTP_DELIVERY_FAILED` 안전 코드만 last_error에 보존한다.
10. lease가 만료된 SENDING은 다음 시도로 회수하되, 3번째 SENDING 결과가 불명인 채
    lease가 끝나면 중복 위험을 줄이기 위해 FAILED·`DELIVERY_RESULT_UNKNOWN`으로
    종료한다.
11. 제목과 평문 본문은 알림 종류, 현재 제품명, 기준일과 trigger_days_before로 만든다.
    사용자·CareItem·Notification ID와 인증정보는 이메일·로그에 포함하지 않는다.
12. 한 poll에서 최대 100건을 처리하며 실패한 한 건이 다른 due 전달을 막지 않는다.

## 포함 범위

- email_deliveries ORM·0020 마이그레이션·제약·인덱스와 ERD
- 당일 논리 이벤트 전달 등록과 수신 이메일 스냅샷
- 동시 claim, 로컬 SMTP 전송, 성공·5분 재시도·3회 최종 실패 상태
- 재구매·유통기한 한국어 제목·평문 본문과 worker 연결
- 단위·마이그레이션·PostgreSQL 통합·인수 테스트, 로컬 Mailpit·운영 문서와 이력

## 제외 범위

- 공개 이메일 전달 상태 API와 사용자 수동 재시도·취소는 제외한다.
- HTML 디자인, 첨부파일, 템플릿 관리와 마케팅 수신 설정은 제외한다.
- 운영 이메일 공급자, 제공자 멱등 키, 반송·스팸 신고, AWS 큐·스케줄러는 2차다.
- 푸시·SMS와 AI 연동은 제외한다.

## 시나리오

### 기본 흐름

- 오전 9시 이후 생성된 재구매·유통기한 Notification이 EmailDelivery로 한 번 등록되고
  Mailpit으로 전송된 뒤 SENT가 된다.
- SMTP 일시 실패는 RETRY가 되고 5분 뒤 다시 claim해 성공할 수 있다.
- 반복 worker는 이미 등록·전송된 Notification을 중복 등록하거나 정상 재전송하지 않는다.

### 실패와 경계

- 오전 9시 전, 전날 일정, 비활성·미인증 사용자에는 새 전달을 등록하지 않는다.
- 동시에 실행한 worker 중 하나만 같은 due 행을 claim한다.
- 3회 실패와 결과 불명 3차 lease는 FAILED로 종료된다.
- SMTP 실패는 다음 전달 처리를 계속하고 DB 실패는 worker 실행 경계로 전파된다.
- SMTP 성공 후 DB 기록 전 프로세스 종료는 로컬 SMTP의 제공자 멱등 키 부재로 중복
  가능성이 남으며 알려진 제약으로 기록한다.

## 미결 질문

- 없음. Mailpit, APP_TIMEZONE, 3회(최초 포함), 고정 5분, batch 100, 실패 안전 코드와
  최종 FAILED 정책을 확정하고 Notion F-3.12 페이지에 근거를 기록했다.

## 추적성

- 요구사항: FR-3
- 로컬 요구사항: docs/product/requirements.md
- 관련 로컬 문서: docs/architecture/erd.md, docs/architecture/data-model.md,
  docs/api/notifications.md, docs/features/notification/f-3-8-repurchase-notification,
  docs/features/notification/f-3-9-reminders
- 외부 출처 URL(선택): https://app.notion.com/p/3b82779e9262814d80f1ce084430245d
- 마지막 검토일: 2026-08-14
