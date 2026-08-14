# 알림 API 계약

## F-3.9 화면 알림 조회·확인

### 사용자별 목록

- `GET /api/v1/notifications?page=1&page_size=20`
- HttpOnly access JWT 쿠키가 필요한 보호 API다.
- 현재 사용자에게 생성된 재구매(`REPURCHASE`)·유통기한(`EXPIRATION`) 논리 알림만
  `created_at DESC, id DESC` 최신순으로 반환한다.
- page는 1 이상, page_size는 기본 20이고 1~100이다. 범위를 넘은 페이지도 200과 빈
  items를 반환한다.
- 항목은 알림 ID, CareItem ID, 현재 제품명, 종류, 기준일, D-5·D-3·D-1 트리거,
  예약·생성·읽음 시각과 `is_read`를 제공한다. user_id와 이메일은 노출하지 않는다.
- 제품명은 현재 카탈로그 값이며 과거 표시명 스냅샷이 아니다. 화면 문구는 프론트엔드가
  종류·제품명·기준일로 구성한다.
- 생성된 알림은 CareItem이 나중에 소프트 삭제되거나 기준일이 교정돼도 감사 이력으로
  목록에 남는다.
- 성공은 200과 `Cache-Control: no-store`, 인증 실패는 401 `AUTH_REQUIRED`, 페이지
  검증 실패는 422 `VALIDATION_FAILED`, DB 실패는 503 `SERVICE_UNAVAILABLE`다.

~~~json
{
  "items": [
    {
      "id": "41000000-0000-4000-8000-000000000001",
      "care_item_id": "31000000-0000-4000-8000-000000000001",
      "product_name": "라이프익스텐션 투퍼데이",
      "notification_type": "REPURCHASE",
      "reference_date": "2026-08-19",
      "trigger_days_before": 5,
      "scheduled_at": "2026-08-14T00:00:00Z",
      "created_at": "2026-08-14T00:01:00Z",
      "read_at": null,
      "is_read": false
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1,
  "has_next": false
}
~~~

### 개별 읽음 처리

- `PUT /api/v1/notifications/{notification_id}/read`
- 요청 본문 없이 현재 사용자의 알림을 서버 UTC 시각으로 읽음 처리한다.
- 같은 알림을 다시 요청하면 최초 `read_at`을 덮어쓰지 않고 같은 결과를 반환한다.
- 다른 사용자 소유와 미존재 알림은 구분하지 않고 404 `NOTIFICATION_NOT_FOUND`로
  응답한다.
- 성공은 200과 `Cache-Control: no-store`, 인증 실패는 401, 잘못된 UUID는 422,
  DB 실패는 503이다.

~~~json
{
  "id": "41000000-0000-4000-8000-000000000001",
  "read_at": "2026-08-14T00:35:00Z"
}
~~~

## 유통기한 논리 알림

- 로컬 worker는 F-3.8 재구매 이벤트와 함께 `expiration_date`가 정확히 D-5·D-3·D-1인
  활성 CareItem의 `EXPIRATION` 이벤트를 APP_TIMEZONE 오전 9시 이후 생성한다.
- 오전 9시 전, 다른 D-day, 유통기한 없음, 소프트 삭제 항목은 대상이 아니다. 다음 날
  놓친 이벤트를 소급하지 않는다.
- 기존 논리 이벤트 고유 제약과 PostgreSQL 충돌 무시 처리를 사용해 반복·동시 실행에도
  종류·기준일·트리거별 한 건만 보존한다.

## 보관과 후속 기능

- 1차 로컬 MVP는 알림을 기간 제한 없이 보관하고 삭제·전체 읽음·읽지 않음 복원 API를
  제공하지 않는다.
- F-3.12는 당일 오전 9시 논리 이벤트를 ACTIVE·인증 사용자에 한해 Mailpit 이메일로
  전달한다. Notification별 전달 이력은 한 건이며 수신 주소 스냅샷, PENDING·SENDING·
  RETRY·SENT·FAILED 상태, 실제 시도 횟수와 안전 오류 코드를 내부 DB에 보존한다.
- 최초를 포함해 최대 3회 전송하며 1·2회 실패는 5분 뒤 재시도하고 3회는 FAILED로
  종료한다. 전달 상태 공개 API와 수동 재시도는 제공하지 않는다.
- 운영 전환 전에 개인정보 보유 기간, 정리 배치와 제품명 스냅샷 필요성을 다시 검토한다.
