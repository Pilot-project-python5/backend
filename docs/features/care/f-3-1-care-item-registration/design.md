# F-3.1 설계

## API 계약

- 메서드와 경로: `POST /api/v1/care/items`
- 인증: HttpOnly access JWT 쿠키 `AccessCookieAuth`
- 요청: `product_id`, `purchase_date`, `intake_start_date`,
  `total_quantity`, `dose_per_intake`, `intakes_per_day`
- 성공 응답: 201과 `id`, 요청 등록 값, `created_at`
- 오류 응답: 401 `AUTH_REQUIRED`, 404 `PRODUCT_NOT_FOUND`,
  422 `VALIDATION_FAILED`, 503 `SERVICE_UNAVAILABLE`
- 멱등성: 없음. 반복 등록은 각기 다른 UUID의 새 항목을 생성한다.

## 데이터 설계

- 엔티티: care_items(id, user_id, product_id, purchase_date,
  intake_start_date, total_quantity, dose_per_intake, intakes_per_day,
  created_at, updated_at)
- 관계와 카디널리티: users 1:N care_items, products 1:N care_items
- 제약 조건: UUID PK·FK, 수량 NUMERIC(12,3) 양수, dose_per_intake는
  total_quantity 이하, 일일 횟수 1~24, 복용 시작일은 구매일 이상,
  updated_at은 created_at 이상
- 인덱스: `(user_id, created_at, id)`, `product_id`
- 마이그레이션: `20260812_0011_care_items`, down_revision 0010
- 백필과 기존 데이터 영향: 신규 테이블이며 기존 행 백필과 사용자 데이터 시드는 없음
- 이력과 삭제: 사용자 삭제 시 CASCADE, 카탈로그 제품 삭제는 RESTRICT. 복용 이력의
  수정·삭제 정책은 F-3.4에서 별도 확정한다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: users·products와 실제 복용 이력을 연결하는 테이블이 없다.
- 변경 후 구조: users 1:N care_items와 products 1:N care_items, 실제 F-3.1 필드·제약·
  인덱스·삭제 정책을 기록한다.
- 변경하지 않는 경우의 이유: 해당 없음
- ERD 검증 방법: 모델·0011 마이그레이션·통합 스키마 검사와 ERD validator 비교

## 애플리케이션 흐름

1. 라우터가 공통 인증 의존성으로 현재 사용자 ID를 확정한다.
2. Pydantic이 형식·자리수·기본 범위를 검증한다.
3. 서비스가 서버 날짜 기준과 필드 간 날짜·수량 관계를 검증한다.
4. 저장소가 제품 존재를 확인하고 사용자 ID를 직접 주입해 새 항목을 저장한다.
5. 서비스가 저장 오류를 안전한 503으로 변환하고 라우터가 결과를 201로 직렬화한다.

## 보안과 개인정보

- 소유권 검사: 요청에서 user_id를 받지 않고 access JWT의 user_id만 저장한다.
- 민감 필드: 복용 제품과 복용 계획은 건강 관련 사용자 데이터로 취급한다.
- 로그 제외 항목: product_id를 제외한 복용 계획 전체와 인증 쿠키·JWT를 기본 로그에
  남기지 않는다.

## 로컬 어댑터

- 데이터베이스: 로컬 PostgreSQL 개발·테스트 DB
- 시간: `SystemClock`, 단위 테스트는 `FakeClock`
- 이메일: 사용하지 않음
- 스케줄러: 사용하지 않음

## 호환성

- OpenAPI 영향: 보호된 POST 201 경로와 401·404·422·503 응답 추가
- 기존 데이터 영향: 신규 테이블만 추가하고 기존 API 응답은 변경하지 않는다.
- 롤백: API 코드를 이전 버전으로 되돌리고 Alembic을 0010으로 downgrade한다.
