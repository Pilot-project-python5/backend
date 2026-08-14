---
feature_id: "F-3.8"
title: "재구매 상태·알림"
requirement_id: "FR-3"
domain: "notification"
status: "implemented"
completed_on: "2026-08-14"
feature_packet: "docs/features/notification/f-3-8-repurchase-notification"
pull_request: "https://github.com/Pilot-project-python5/backend/pull/23"
commit: "25c9e93"
---

# F-3.8 재구매 상태·알림 구현 이력

## 구현 요약

로그인 사용자는 활성 복용 제품 목록에서 예상 소진일 기준 NORMAL·LOW_STOCK·DEPLETED
재고 상태를 확인할 수 있다. 로컬 worker는 APP_TIMEZONE 오전 9시 이후 정확한
D-5·D-3·D-1 구매분에 화면·이메일이 공유할 REPURCHASE 논리 알림을 한 번만 생성한다.

## 구현 범위

### 포함

- 활성 복용 항목 목록의 필수 inventory_status 파생 응답
- D-5·D-3·D-1 오전 9시 이후 재구매 논리 알림 멱등 생성
- notifications ORM·0019 마이그레이션·FK·CHECK·UNIQUE·조회 인덱스
- 기존 로컬 worker와 세션 단위 재구매 알림 작업 연결
- 단위·계약·마이그레이션·인수 테스트와 ERD·OpenAPI·로컬 운영 문서

### 제외

- 화면 알림 목록·읽음 처리와 EXPIRATION 이벤트는 F-3.9로 분리했다.
- 실제 로컬 SMTP 이메일 전달·중복 방지·재시도는 F-3.12로 분리했다.
- 실제 복용·잔량 보정, 누락 날짜 소급 생성, 수동 상태 변경은 제외했다.
- 푸시·SMS, AWS 스케줄러·운영 모니터링과 AI 연결은 1차 범위에 넣지 않았다.

## 주요 구현 내용

- 목록 서비스는 이미 계산한 days_until_depletion을 재사용해 D-6 이상 NORMAL,
  D-5부터 D0 LOW_STOCK, 다음 날부터 DEPLETED를 반환한다.
- 작업 서비스는 주입 시계를 APP_TIMEZONE으로 변환하고 오전 9시 전이면 DB를 조회하지
  않는다. 이후에는 오늘에서 5·3·1일 뒤 기준일만 저장소에 전달한다.
- 저장소는 삭제되지 않은 정확한 예상 소진일 후보만 조회하고 PostgreSQL
  `ON CONFLICT DO NOTHING`으로 논리 이벤트 고유 충돌을 무시한다.
- scheduled_at은 로컬 트리거 날짜 09:00을 UTC로 저장하고 created_at은 실제 실행
  시각으로 보존한다. 늦게 시작해도 당일만 생성하고 지난 트리거는 소급하지 않는다.
- worker는 실행마다 새 세션을 열고 성공 건수만 기록한다. DB 실패는 기존 실행 루프가
  기록한 뒤 다음 poll에서 다시 시도한다.

## API 변경

- 기존 `GET /api/v1/care/items` 각 항목에 필수 `inventory_status`를 추가했다.
- 요청·경로·인증·페이지·오류 상태는 변경하지 않은 additive 응답 확장이다.
- 작업자 전용 HTTP API와 Notification 공개 응답은 추가하지 않았다. F-3.9 전까지
  논리 이벤트는 내부 데이터다.

## 데이터·ERD·마이그레이션

- Alembic 0019가 notifications를 생성하고 User·CareItem 물리 삭제에 CASCADE FK를 둔다.
- 종류는 REPURCHASE·EXPIRATION, 트리거는 5·3·1로 제한하고 예약 시각·읽음 시각 순서를
  CHECK로 보장한다.
- `(care_item_id, notification_type, reference_date, trigger_days_before)` UNIQUE가
  채널 공통 논리 이벤트 중복을 막는다.
- `(user_id, read_at, created_at DESC, id)` 인덱스를 F-3.9 화면 조회에 준비했다.
- 기존 CareItem 변경·알림 백필·신규 시드는 없다. downgrade는 notifications만 제거해
  User·CareItem을 보존한다.

## 보안과 개인정보

- 사용자 목록은 기존 access JWT·서버 refresh session과 user_id·deleted_at 필터를
  재사용한다.
- worker는 CareItem의 소유 user_id를 Notification FK로 복사하고 삭제 항목을 제외한다.
- 새 공개 API나 사용자 ID 노출이 없고 개인 건강 응답은 기존 no-store를 유지한다.
- worker 로그에는 사용자·구매분·제품명·기준일을 남기지 않고 생성 건수와 실패만 기록한다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-3.8-001~006 단위·계약·마이그레이션·인수 테스트 | 6개 조건 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-3.8` | 39개 통과 |
| 전체 로컬 검증 | `make verify` | 432개 통과, 커버리지 95.61% |
| 정적 검사 | ruff format/check, mypy | 모두 통과, 소스 225개 타입 검사 |
| 데이터·ERD | 0019 왕복, alembic check, ERD validator | 모두 통과 |
| 시드·API | 전체 시드 연속 2회, OpenAPI 일치 검사 | 7세트·84건 멱등, 계약 일치 |

## 주요 결정과 근거

- “화면 알림과 이메일 생성”은 F-3.8에서 채널별 발송이 아니라 공유 Notification 논리
  이벤트 생성으로 해석했다. F-3.9·F-3.12의 조회·전송 상태가 같은 기준을 재사용하면서
  책임이 겹치지 않게 하기 위해서다.
- 오전 9시는 기존 APP_TIMEZONE, 기본 Asia/Seoul로 확정했다. DB·호스트 시간대에 따라
  일정이 달라지는 것을 막고 날짜 D-day 계산과 같은 경계를 쓰기 위해서다.
- worker가 09:00 정각에만 실행될 것을 기대하지 않고 당일 09:00 이후를 허용했다.
  60초 poll 지연·재시작에도 오늘 알림을 만들되 다음 날 소급은 하지 않기 위해서다.
- 재고 상태와 알림 생성 여부는 저장 컬럼으로 복제하지 않고 예상 소진일을 단일 기준으로
  사용한다. 날짜 경과로 상태가 오래되거나 두 값이 어긋나는 문제를 피하기 위해서다.
- 애플리케이션 사전 조회만으로 중복을 막지 않고 DB UNIQUE와 충돌 무시 쓰기를 사용했다.
  worker 복수 실행과 향후 여러 인스턴스에서도 같은 보장을 유지하기 위해서다.

## 알려진 제약

- 예상 소진일은 계획값이라 실제 복용 누락·추가 사용과 실잔량을 반영하지 않는다.
- worker가 트리거 날짜 내내 중단되면 해당 알림은 소급 생성하지 않는다.
- 이번 기능의 Notification은 내부 이벤트로, F-3.9 전에는 사용자가 조회·읽음 처리할
  공개 API가 없다.
- worker 생존 감시·분산 잠금·운영 재처리 도구는 제공하지 않지만 DB UNIQUE가 중복은 막는다.

## 후속 작업

- F-3.9에서 EXPIRATION 논리 알림 생성과 사용자별 목록·읽음 처리를 구현한다.
- F-3.12에서 두 알림 종류의 EmailDelivery·로컬 SMTP 발송·재시도 정책을 구현한다.
- 2차 AWS 전환에서 관리형 스케줄러·worker 생존 감시·누락 운영 절차를 별도 승인한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/notification/f-3-8-repurchase-notification
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
