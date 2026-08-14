# F-3.9 설계

## API 계약

- 메서드와 경로: `GET /api/v1/notifications`,
  `PUT /api/v1/notifications/{notification_id}/read`
- 인증: HttpOnly access JWT 쿠키와 기존 require_current_user 의존성
- 요청: 목록 query `page=1`, `page_size=20`; 읽음 path UUID; 요청 본문 없음
- 성공 응답: 목록은 items/page/page_size/total/has_next, 읽음은 알림 id와 read_at
- 오류 응답: 401 AUTH_REQUIRED, 404 NOTIFICATION_NOT_FOUND, 422 VALIDATION_FAILED,
  503 SERVICE_UNAVAILABLE
- 멱등성: 목록은 읽기 전용이다. 읽음 API는 최초 read_at을 유지하며 재호출해도 같은
  결과를 반환한다. worker 생성은 기존 논리 이벤트 UNIQUE를 재사용한다.

## 데이터 설계

- 엔티티: 기존 Notification, CareItem, Product
- 관계와 카디널리티: Notification N:1 CareItem, CareItem N:1 Product
- 제약 조건: 기존 종류·트리거·예약/읽음 시각 CHECK와 논리 이벤트 UNIQUE 재사용
- 인덱스: 기존 `(user_id, read_at, created_at DESC, id)` 조회 인덱스 재사용
- 마이그레이션: 없음. 현재 head 0019 유지
- 백필과 기존 데이터 영향: 없음. F-3.8 재구매 이벤트가 즉시 조회 대상이 된다.
- 이력과 삭제: 소프트 삭제된 CareItem의 Notification은 조회 이력으로 보존한다.
  물리 삭제 시 기존 CASCADE 정책을 따른다. MVP에는 알림 삭제·정리 작업이 없다.

## ERD 영향

- docs/architecture/erd.md 변경: 아니오
- 변경 전 구조: F-3.8이 Notification 관계·제약·인덱스를 이미 반영했다.
- 변경 후 구조: 동일하다. F-3.9는 기존 열의 생성·조회·갱신 동작만 공개한다.
- 변경하지 않는 경우의 이유: 새 엔티티·열·관계·인덱스가 없다.
- ERD 검증 방법: `make erd-check`, `alembic check`, 현재 head 0019 왕복 검증

## 애플리케이션 흐름

1. worker가 주입 시각을 APP_TIMEZONE으로 변환하고 오전 9시 게이트를 검사한다.
2. 공통 트리거 D-5·D-3·D-1을 계산한 뒤 재구매와 유통기한 저장소를 같은 세션에서
   실행한다.
3. 유통기한 저장소는 활성 CareItem의 expiration_date를 비교해 EXPIRATION 이벤트를
   `ON CONFLICT DO NOTHING`으로 생성한다.
4. 목록 API는 인증 사용자 ID로 Notification을 필터하고 CareItem·Product를 조인해
   현재 제품명과 페이지 메타데이터를 반환한다.
5. 읽음 API는 user_id와 notification_id를 함께 조건으로 원자적 갱신한다. read_at이
   이미 있으면 값을 덮어쓰지 않고 반환한다.
6. 서비스는 저장소 오류를 AppError 503으로, 소유 알림 부재를 404로 변환한다.

## 보안과 개인정보

- 소유권 검사: 모든 HTTP 조회·갱신 SQL에 현재 user_id 조건을 적용한다.
- 민감 필드: user_id와 이메일을 공개 응답에 포함하지 않고 no-store를 설정한다.
- 로그 제외 항목: 알림 ID, CareItem ID, 사용자 ID, 제품명, 기준일을 기록하지 않는다.

## 로컬 어댑터

- 데이터베이스: Docker PostgreSQL과 기존 SessionLocal
- 시간: SystemClock, APP_TIMEZONE 기본 Asia/Seoul, DB 시각은 UTC
- 이메일: 이 기능에서는 호출하지 않으며 F-3.12가 Notification을 소비한다.
- 스케줄러: 기존 로컬 worker poll 루프가 통합 NotificationJob을 실행한다.

## 호환성

- OpenAPI 영향: Notification 목록·읽음 경로와 스키마 추가
- 기존 데이터 영향: 없음. 기존 REPURCHASE 행은 그대로 조회된다.
- 롤백: API 라우터와 EXPIRATION 작업 코드를 제거한다. 스키마 변경이 없어 DB
  downgrade가 필요 없고 이미 생성된 EXPIRATION 행은 보존하거나 명시적으로 정리한다.
