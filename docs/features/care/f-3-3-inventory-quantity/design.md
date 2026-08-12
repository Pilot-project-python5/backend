# F-3.3 설계

## API 계약

- 메서드와 경로: 기존 `POST /api/v1/care/items`
- 인증: HttpOnly access JWT 쿠키 `AccessCookieAuth`
- 요청: F-3.1 필드 유지. `quantity_unit`은 요청받지 않음
- 성공 응답: 기존 201 `CareItemResponse`에 `quantity_unit`을 필수 필드로 추가
- 오류 응답: 401 `AUTH_REQUIRED`, 404 `PRODUCT_NOT_FOUND`,
  422 `VALIDATION_FAILED`, 503 `SERVICE_UNAVAILABLE` 유지
- 멱등성: 없음. 재구매·반복 요청은 독립 CareItem을 만든다.

## 데이터 설계

- 엔티티: 기존 care_items에 `quantity_unit VARCHAR(20) NOT NULL` 추가
- 관계와 카디널리티: 기존 users 1:N·products 1:N 관계 유지
- 제약 조건: `quantity_unit IN ('TABLET', 'CAPSULE', 'SCOOP', 'PACKET')`;
  total_quantity의 기존 NUMERIC(12,3) 양수 제약 유지
- 인덱스: 수량 단위 단독 검색 요구가 없어 신규 인덱스 없음
- 마이그레이션: `20260812_0013_care_item_quantity_unit`, down_revision 0012
- 백필과 기존 데이터 영향: nullable 임시 컬럼 추가 → `products.unit_form`으로 기존
  care_items 백필 → CHECK·NOT NULL 적용. 모든 CareItem은 유효 Product FK를 가지므로
  백필 누락은 허용하지 않는다.
- 이력과 삭제: 기존 삭제 정책 유지. quantity_unit과 total_quantity를 등록 뒤
  카탈로그 변경으로 갱신하지 않는다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: care_items에 총수량만 있어 TABLET·CAPSULE·SCOOP·PACKET 중 어떤
  단위인지 Product의 현재 값에 의존한다.
- 변경 후 구조: care_items에 등록 시점 quantity_unit을 보존하고 초기 총수량·독립
  구매 이력·불변 정책을 기록한다.
- 변경하지 않는 경우의 이유: 해당 없음
- ERD 검증 방법: ORM·0013·통합 스키마 검사와 ERD validator 비교

## 애플리케이션 흐름

1. F-3.1 서비스가 요청 날짜·수량·복용 계획을 검증한다.
2. 저장소가 제품 ID·유형·unit_form을 함께 조회한다.
3. 새 CareItem에 Product.unit_form을 quantity_unit으로 복사한다.
4. SUPPLEMENT면 F-3.2 활성 성분 스냅샷을 추가한다.
5. CareItem과 성분 스냅샷을 한 번 commit하고 오류 시 전체 rollback한다.
6. 서비스·라우터가 quantity_unit을 201 응답까지 전달한다.

## 보안과 개인정보

- 소유권 검사: 요청에서 user_id·quantity_unit을 받지 않고 인증 사용자와 DB 제품
  값만 사용한다.
- 민감 필드: 구매 수량과 복용 계획은 건강 관련 사용자 데이터다.
- 로그 제외 항목: 사용자 ID, CareItem ID, 구매 수량과 복용 계획 전체를 기본 로그에
  추가하지 않는다.

## 로컬 어댑터

- 데이터베이스: 로컬 PostgreSQL 개발·테스트 DB
- 시간: F-3.1 SystemClock·APP_TIMEZONE 유지
- 이메일: 사용하지 않음
- 스케줄러: 사용하지 않음

## 호환성

- OpenAPI 영향: 201 응답의 additive 필수 필드 `quantity_unit` 추가. 요청과 오류는 유지
- 기존 데이터 영향: 0013이 현재 Product.unit_form으로 기존 CareItem을 최선 백필한다.
- 롤백: API 코드를 이전 버전으로 되돌리고 0013 downgrade로 quantity_unit 컬럼을
  제거한다. 기존 CareItem과 성분 스냅샷은 보존된다.
