# F-3.11 설계

## API 계약

- 메서드와 경로: 기존 POST·GET `/api/v1/care/items` 확장,
  `PUT /api/v1/care/items/{care_item_id}/expiration`
- 인증: 기존 AccessCookieAuth와 서버 refresh session
- 요청: 등록 expiration_date 선택, PUT 본문 expiration_date 필수 ISO date
- 성공 응답: 등록·PUT은 저장 날짜, 목록은 nullable 날짜·부호 있는 D-day·nullable 상태
- 오류 응답: 401 AUTH_REQUIRED, 404 CARE_ITEM_NOT_FOUND, 422 VALIDATION_FAILED,
  503 SERVICE_UNAVAILABLE
- 멱등성: 등록은 비멱등 생성, PUT은 같은 항목·날짜에 멱등

## 데이터 설계

- 엔티티: 기존 CareItem
- 관계와 카디널리티: 변경 없음
- 제약 조건: expiration_date nullable DATE. 과거와 구매일 이전도 기록 목적상 허용
- 인덱스: `(expiration_date, user_id)`로 비삭제·기준일 후보 조회를 지원
- 마이그레이션: 0018 nullable 열과 인덱스 추가
- 백필과 기존 데이터 영향: 모든 기존 행은 null이며 API 상태도 null
- 이력과 삭제: 소프트 삭제 행의 날짜는 보존하되 조회·갱신·알림 대상에서 제외

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: CareItem에 유통기한 없음
- 변경 후 구조: nullable expiration_date와 조회 인덱스, 비저장 D-day·상태 규칙
- 변경하지 않는 경우의 이유: 해당 없음
- ERD 검증 방법: 0018 왕복·inspector 스키마 테스트·validate_erd.py

## 애플리케이션 흐름

1. 등록 서비스는 선택 날짜를 다른 스냅샷·예상일과 같은 트랜잭션에 저장한다.
2. PUT 서비스는 현재 사용자·활성 항목 조건으로 날짜를 원자 갱신한다.
3. 목록 서비스는 저장 날짜가 있으면 주입 시계·APP_TIMEZONE의 오늘과 차이를 계산한다.
4. 순수 도메인 함수가 null/NORMAL/EXPIRING_SOON/EXPIRED 상태를 반환한다.
5. 라우터는 개인 건강 응답에 no-store를 적용한다.

## 보안과 개인정보

- 소유권 검사: user_id와 deleted_at IS NULL을 PUT 조건에 포함
- 민감 필드: 요청·응답에 user_id 없음, 현재 사용자 항목만 반환
- 로그 제외 항목: care_item_id와 유통기한 값을 새 로그에 남기지 않음

## 로컬 어댑터

- 데이터베이스: Docker PostgreSQL dev/test
- 시간: 주입 Clock과 APP_TIMEZONE, 기본 Asia/Seoul
- 이메일: 없음
- 스케줄러: 없음. 알림은 후속 기능

## 호환성

- OpenAPI 영향: 기존 요청은 선택 필드 추가로 호환, 기존 응답은 additive 확장
- 기존 데이터 영향: null 백필 없이 열 추가만 적용
- 롤백: 0018 인덱스·열 제거, 기존 CareItem 보존. 날짜 데이터만 소실됨을 배포 전 고지
