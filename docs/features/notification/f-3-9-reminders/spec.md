# F-3.9 리마인더 조회·확인

## 목표

로그인 사용자가 자신의 재구매·유통기한 알림을 최신순으로 확인하고 개별 알림을
읽음 처리할 수 있게 한다. 유통기한이 있는 활성 복용 항목에도 재구매 알림과 동일한
D-5·D-3·D-1 오전 9시 논리 이벤트를 생성해 화면과 후속 이메일이 공유하게 한다.

## 사용자 이야기

사용자로서, 제품을 재구매하거나 유통기한을 확인할 시점을 놓치지 않기 위해 내 알림
목록을 보고 확인한 알림을 읽음 처리하고 싶다.

## 비즈니스 규칙

1. `GET /api/v1/notifications`는 access JWT로 식별한 현재 사용자의 Notification만
   `created_at DESC, id DESC` 순서로 반환한다.
2. 페이지는 1부터, page_size는 1~100이며 기본값은 각각 1과 20이다. 응답은 items,
   page, page_size, total, has_next를 포함한다.
3. 각 항목은 id, care_item_id, 현재 product_name, notification_type, reference_date,
   trigger_days_before, scheduled_at, created_at, read_at과 파생 is_read를 반환한다.
4. `PUT /api/v1/notifications/{notification_id}/read`는 현재 사용자의 알림만 현재
   UTC 시각으로 읽음 처리한다. 이미 읽은 경우 최초 read_at을 유지해 멱등 응답한다.
5. 존재하지 않거나 다른 사용자의 알림은 모두 NOTIFICATION_NOT_FOUND 404로 처리해
   소유권 정보를 노출하지 않는다.
6. 모든 성공 응답은 `Cache-Control: no-store`를 설정한다.
7. 유통기한 논리 이벤트는 APP_TIMEZONE 오늘 기준 오전 09시 이후, expiration_date가
   정확히 D-5·D-3·D-1인 삭제되지 않은 CareItem에만 생성한다.
8. 같은 CareItem·종류·기준일·트리거는 반복·동시 작업에서도 하나만 생성한다.
9. 오전 09시 전 실행이나 유통기한이 없는 항목, 소프트 삭제된 항목에는 새 이벤트를
   만들지 않고 다음 날 누락분을 소급하지 않는다.
10. 생성된 알림은 소프트 삭제나 기준일 교정 후에도 이력으로 목록에 남긴다. 1차
    MVP는 기간 제한, 삭제 API와 자동 정리를 두지 않는다.

## 포함 범위

- 유통기한 EXPIRATION 논리 알림 생성과 worker 연결
- 현재 사용자 알림 페이지 조회와 Swagger/OpenAPI 계약
- 개별 알림 멱등 읽음 처리와 소유권 보호
- 단위·계약·통합·인수 테스트, API·아키텍처·운영 문서와 구현 이력

## 제외 범위

- 실제 이메일 전달·전송 상태·재시도는 F-3.12로 분리한다.
- 전체 읽음, 읽지 않음 복원, 알림 삭제·보관 정리 API는 제외한다.
- 푸시·SMS, AWS 스케줄러·운영 배포, AI 연동은 제외한다.
- 제품명·메시지 문구 스냅샷을 저장하지 않는다.

## 시나리오

### 기본 흐름

- worker가 오전 9시 이후 실행되면 재구매와 유통기한 대상의 논리 이벤트를 멱등
  생성한다.
- 로그인 사용자는 자신의 재구매·유통기한 알림을 최신순 페이지로 조회한다.
- 사용자는 선택한 알림을 읽음 처리하고 같은 요청을 재시도해도 최초 read_at을 받는다.

### 실패와 경계

- 인증 누락·만료는 401, 잘못된 페이지 값은 422다.
- 없는 알림과 타인 알림의 읽음 처리는 동일한 404다.
- 오전 9시 전, D-4·D-2·D0, 유통기한 없음, 삭제 항목은 EXPIRATION 생성 대상이 아니다.
- 같은 날 worker를 반복·동시 실행해도 고유 제약으로 중복 이벤트를 만들지 않는다.
- PostgreSQL 조회·갱신 실패는 안전한 503으로 변환하고 트랜잭션을 롤백한다.

## 미결 질문

- 없음. 1차 MVP 알림 무기한 보관·삭제 API 제외, 현재 제품명 표시, 소프트 삭제 이후
  기존 알림 보존을 확정하고 Notion F-3.9 페이지에도 근거를 기록했다.

## 추적성

- 요구사항: FR-3
- 로컬 요구사항: docs/product/requirements.md
- 관련 로컬 문서: docs/architecture/data-model.md, docs/architecture/erd.md,
  docs/features/notification/f-3-8-repurchase-notification,
  docs/features/notification/f-3-11-expiration-management
- 외부 출처 URL(선택): https://app.notion.com/p/3b82779e92628117a42aca311a0d9754
- 마지막 검토일: 2026-08-14
