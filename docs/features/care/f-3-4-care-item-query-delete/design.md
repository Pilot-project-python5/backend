# F-3.4 설계

## API 계약

- 메서드와 경로: `GET /api/v1/care/items`,
  `DELETE /api/v1/care/items/{care_item_id}`
- 인증: HttpOnly access JWT와 서버 refresh session을 함께 검증하는 `AccessCookieAuth`
- 요청: GET은 `page` 기본 1·1 이상, `page_size` 기본 20·1~100. DELETE는 UUID 경로 변수
- 성공 응답: GET 200은 items·page·page_size·total·has_next. 각 항목은 CareItem ID,
  Product ID·유형·브랜드·이름·image_url, 구매일·복용 시작일·총수량·단위·회당량·
  하루 횟수·등록 시각. DELETE는 본문 없는 204
- 오류 응답: 공통 401 `AUTH_REQUIRED`, 422 `VALIDATION_FAILED`, 503
  `SERVICE_UNAVAILABLE`; DELETE의 미존재·타 사용자·기삭제는 404
  `CARE_ITEM_NOT_FOUND`
- 멱등성: 목록은 읽기 전용이다. 삭제는 첫 요청 204, 이후에는 활성 리소스가 없어
  404이므로 응답 기준 멱등 API로 정의하지 않는다.

## 데이터 설계

- 엔티티: 기존 `care_items`에 `deleted_at TIMESTAMPTZ NULL` 추가
- 관계와 카디널리티: users 1:N·products 1:N·care_items 1:N snapshots 유지
- 제약 조건: `deleted_at IS NULL OR deleted_at >= created_at`; 기존 제약 유지
- 인덱스: 기존 전체 이력 `(user_id, created_at, id)`를 유지하고 활성 목록용
  `(user_id, created_at, id) WHERE deleted_at IS NULL` 부분 인덱스를 추가한다. B-tree
  역방향 스캔으로 `created_at DESC, id DESC` 정렬을 지원한다.
- 마이그레이션: `20260812_0014_care_item_soft_delete`, down_revision 0013
- 백필과 기존 데이터 영향: nullable 컬럼이므로 기존 CareItem은 모두 활성 상태로 유지,
  데이터 백필 없음
- 이력과 삭제: 삭제는 `deleted_at`·`updated_at`만 같은 서버 시각으로 갱신한다.
  CareItem과 성분 스냅샷은 보존하며 사용자 계정 물리 삭제 시 기존 CASCADE는 유지한다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: CareItem에 삭제 상태가 없어 목록 제외와 이력 보존을 함께 표현할 수 없음
- 변경 후 구조: nullable deleted_at으로 활성 여부를 표현하고 삭제 시 자식 스냅샷을
  보존하는 정책과 부분 인덱스를 명시
- 변경하지 않는 경우의 이유: 해당 없음
- ERD 검증 방법: ORM·0014·통합 스키마 테스트와 ERD validator 비교

## 애플리케이션 흐름

1. 공통 인증 계층이 현재 사용자와 유효 세션을 확인한다.
2. 목록 서비스가 페이지 범위를 저장소에 전달한다.
3. 저장소가 현재 사용자와 `deleted_at IS NULL`로 count하고 Product를 join해 최신순
   페이지를 조회한다. Product의 게시 여부는 필터하지 않는다.
4. 서비스가 has_next를 계산하고 라우터가 Decimal 문자열과 제품 표시 정보를 응답한다.
5. 삭제 서비스는 서버 시각을 받아 현재 사용자·항목 ID·활성 상태를 한 UPDATE 조건으로
   검사하고 `deleted_at`·`updated_at`을 기록한다.
6. 영향 행이 없으면 404, DB 예외면 rollback 후 503, 성공이면 commit 후 204를 반환한다.

## 보안과 개인정보

- 소유권 검사: 모든 쿼리와 삭제 UPDATE에 인증 `user_id`를 포함하며 타 사용자 존재를
  404로 숨긴다. 요청에서 user_id를 받지 않는다.
- 민감 필드: 복용 제품·구매일·복용 계획과 수량은 건강 관련 사용자 데이터다.
- 로그 제외 항목: 사용자 ID·CareItem ID·구매·복용 정보 전체를 기본 로그에 추가하지 않는다.

## 로컬 어댑터

- 데이터베이스: 로컬 PostgreSQL 개발·테스트 DB
- 시간: 삭제 시각은 기존 SystemClock을 사용하고 시간 테스트는 FakeClock을 사용
- 이메일: 사용하지 않음
- 스케줄러: 사용하지 않음

## 호환성

- OpenAPI 영향: 보호 목록·삭제 두 API와 응답·페이지·오류·no-store 계약 추가
- 기존 데이터 영향: 0014 적용 시 기존 CareItem은 deleted_at NULL인 활성 항목이다.
- 롤백: 앱을 이전 버전으로 되돌린 뒤 0014 downgrade로 부분 인덱스와 deleted_at을
  제거한다. 이미 소프트 삭제한 행은 다시 활성처럼 보이므로 운영 데이터에서는
  downgrade 전 삭제 시각 백업과 명시적 승인이 필요하다.
