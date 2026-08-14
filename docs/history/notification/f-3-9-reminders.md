---
feature_id: "F-3.9"
title: "리마인더 조회·확인"
requirement_id: "FR-3"
domain: "notification"
status: "implemented"
completed_on: "2026-08-14"
feature_packet: "docs/features/notification/f-3-9-reminders"
pull_request: "https://github.com/Pilot-project-python5/backend/pull/24"
commit: "56461f3"
---

# F-3.9 리마인더 조회·확인 구현 이력

## 구현 요약

로그인 사용자는 자신의 재구매·유통기한 화면 알림을 최신순 페이지로 조회하고 개별
알림을 멱등하게 읽음 처리할 수 있다. 로컬 worker는 유통기한 D-5·D-3·D-1 오전 9시
논리 이벤트도 생성하며, 재구매 알림과 같은 Notification을 화면·이메일 원본으로 쓴다.

## 구현 범위

### 포함

- `GET /api/v1/notifications` 현재 사용자 알림 최신순 페이지
- `PUT /api/v1/notifications/{notification_id}/read` 개별 멱등 읽음 처리
- 활성 CareItem 유통기한 D-5·D-3·D-1 EXPIRATION 논리 이벤트 생성
- 재구매·유통기한 통합 worker 작업, Swagger/OpenAPI와 API·운영 문서
- 단위·계약·PostgreSQL 통합·인수 테스트와 Feature Packet·결정 기록

### 제외

- 실제 이메일 전달·발송 상태·재시도는 F-3.12로 분리했다.
- 전체 읽음, 읽지 않음 복원, 알림 삭제와 자동 보관 정리는 제외했다.
- 제품명·번역 메시지 스냅샷, 푸시·SMS, AWS 스케줄러와 AI 연결은 제외했다.

## 주요 구현 내용

- ExpirationNotificationService는 F-3.8과 같은 APP_TIMEZONE 오전 9시 게이트와
  D-5·D-3·D-1 트리거를 사용한다. 저장소는 expiration_date가 정확히 일치하는 활성
  CareItem만 골라 `ON CONFLICT DO NOTHING`으로 EXPIRATION 이벤트를 생성한다.
- NotificationJob은 같은 세션 범위에서 REPURCHASE와 EXPIRATION 서비스를 순서대로
  실행하고 개인정보 없이 종류별 생성 건수만 기록한다.
- 목록 저장소는 Notification을 CareItem·Product와 조인하고 user_id로 격리해
  `created_at DESC, id DESC` 정렬과 전체 건수를 제공한다. 소프트 삭제된 CareItem도
  이미 생성된 알림 이력에는 남긴다.
- 읽음 저장소는 user_id와 알림 ID를 함께 조건으로 갱신하고 PostgreSQL coalesce로
  최초 read_at을 보존한다. 서비스는 목록의 is_read와 has_next를 파생한다.

## API 변경

- `GET /api/v1/notifications?page=1&page_size=20`은 access JWT가 필요한 보호 API다.
  page는 1 이상, page_size는 1~100이며 빈 초과 페이지도 200으로 반환한다.
- 항목은 id, care_item_id, 현재 product_name, notification_type, reference_date,
  trigger_days_before, scheduled_at, created_at, read_at, is_read를 제공한다.
- `PUT /api/v1/notifications/{notification_id}/read`는 본문 없이 최초 read_at을 200으로
  반환한다. 타인·없는 알림은 동일한 404 NOTIFICATION_NOT_FOUND로 숨긴다.
- 인증 실패는 401, 검증 실패는 422, DB 실패는 503이며 성공 응답은 no-store다.

## 데이터·ERD·마이그레이션

- 새 엔티티·열·관계·제약·인덱스·시드와 마이그레이션은 없다. F-3.8의 notifications,
  논리 이벤트 UNIQUE와 `(user_id, read_at, created_at DESC, id)` 인덱스를 재사용한다.
- ERD 구조와 현재 Alembic head 0019는 그대로이며 설명만 F-3.9 실제 생성·조회·읽음
  책임과 무기한 보관 정책으로 갱신했다.
- 기존 REPURCHASE 행은 배치·백필 없이 화면 목록에서 즉시 조회된다.

## 보안과 개인정보

- 기존 HttpOnly access JWT 인증을 재사용하고 조회·갱신 SQL 모두 현재 user_id를
  조건으로 사용한다. 타인·미존재 알림을 같은 404로 처리해 존재 여부를 숨긴다.
- 응답에 user_id와 이메일을 노출하지 않고 no-store를 설정한다. worker 로그에는 사용자,
  알림·CareItem ID, 제품명, 기준일을 기록하지 않는다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-3.9-001~006 단위·계약·PostgreSQL 통합·인수 테스트 | 6개 조건 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-3.9` | 22개 통과 |
| 전체 로컬 검증 | `make verify` | 454개 통과, 커버리지 95.56% |
| 정적 검사 | ruff format/check, mypy | 모두 통과, 소스 234개 타입 검사 |
| 데이터·ERD | 현재 0019 upgrade·alembic check, ERD validator | 모두 통과, 구조 변경 없음 |
| 시드·API | 전체 시드 연속 2회, OpenAPI 일치 검사 | 7세트·84건 멱등, 계약 일치 |

## 주요 결정과 근거

- 1차 로컬 MVP는 알림을 기간 제한 없이 보관하고 삭제 API를 두지 않는다. 초기 데이터
  규모에서 구현을 단순하게 유지하고 누락·중복·읽음 이력을 추적하기 위해서다.
- 목록은 과거 제품명 스냅샷 대신 현재 Product 이름을 조인한다. 기존 스키마를 재사용하고
  프론트엔드 표시 계약을 단순하게 유지하되, 운영에서 법적 이력 보존 요구가 생기면
  별도 스냅샷 마이그레이션을 승인한다.
- CareItem 소프트 삭제와 유통기한 교정 후에도 생성된 Notification을 보존한다. 논리
  이벤트가 당시 작업 결과와 사용자 확인 상태를 나타내는 감사 이력이기 때문이다.
- 개별 읽음은 PUT과 DB coalesce를 사용한다. 네트워크 재시도에도 최초 확인 시각을
  덮어쓰지 않는 명확한 멱등 계약을 제공하기 위해서다.
- 화면 메시지 문구는 저장하지 않고 알림 종류·제품명·기준일을 반환한다. 다국어와 문구
  변경을 DB 이력에서 분리하기 위해서다.

## 알려진 제약

- 제품명이 카탈로그에서 바뀌면 과거 알림에도 현재 이름이 표시된다.
- worker가 트리거 날짜 내내 중단되면 다음 날 누락 이벤트를 소급 생성하지 않는다.
- 무기한 보관은 로컬 MVP 정책이며 운영 전 개인정보 보유 기간과 정리 배치가 필요하다.
- 화면 전체 읽음·삭제·읽지 않음 복원과 실제 이메일 상태는 아직 제공하지 않는다.

## 후속 작업

- F-3.12에서 Notification별 EmailDelivery, 로컬 SMTP 전달, 중복 방지와 제한된 재시도를
  구현한다.
- 2차 AWS 전환 전에 알림 보관 기간, 운영 정리·재처리 절차와 관리형 스케줄러를 승인한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/notification/f-3-9-reminders
- ERD: docs/architecture/erd.md
- API 계약: docs/api/notifications.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
