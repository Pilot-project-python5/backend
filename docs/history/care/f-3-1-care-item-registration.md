---
feature_id: "F-3.1"
title: "복용 제품 등록"
requirement_id: "FR-3"
domain: "care"
status: "implemented"
completed_on: "2026-08-12"
feature_packet: "docs/features/care/f-3-1-care-item-registration"
pull_request: null
commit: null
---

# F-3.1 복용 제품 등록 구현 이력

## 구현 요약

로그인 사용자는 DB 카탈로그에 존재하는 영양제 또는 의약품을 구매일·복용 시작일·
총수량·회당 복용량·일일 횟수와 함께 마이케어에 등록할 수 있다. 사용자 ID는 access
JWT에서만 가져오며 같은 제품을 반복 등록하면 기존 이력을 덮어쓰지 않고 별도 복용
항목을 생성한다. 날짜는 설정된 Asia/Seoul 기준으로 검증하고 건강 관련 응답은 캐시하지
않는다.

## 구현 범위

### 포함

- 보호된 `POST /api/v1/care/items` 등록 API
- 현재 인증 사용자 소유권 강제와 DB 카탈로그 제품 존재 확인
- 구매일·복용 시작일·총수량·회당 복용량·일일 횟수 검증
- care_items ORM·0011 마이그레이션·ERD와 API 문서
- 단위·계약·통합·인수 테스트와 Swagger·OpenAPI

### 제외

- 사용자의 직접 제품 입력과 카탈로그 쓰기 API는 제외했다.
- 등록 정보 수정·목록 조회·삭제와 이력 보존 정책은 F-3.4로 분리했다.
- 영양성분 스냅샷은 F-3.2, 재구매·재고 병합은 F-3.3으로 분리했다.
- 소진 예정일·상태·알림은 F-3.7 이후, 유통기한은 F-3.11로 분리했다.
- AWS·AI·이메일·스케줄러 연동은 이번 로컬 기능 범위에 포함하지 않았다.

## 주요 구현 내용

- `CareItemService`가 설정 시간대의 현재 날짜, 날짜 순서와 수량 관계를 DB 접근 전에
  검증한다.
- `SQLAlchemyCareItemRepository`가 게시 여부와 무관하게 제품 카탈로그 존재를 확인한
  뒤 인증 사용자 ID를 넣은 새 행을 커밋한다.
- 같은 제품·날짜 조합에 고유 제약을 두지 않고 새 UUID를 만들기 때문에 재등록 이력을
  독립적으로 보존한다.
- 라우터는 공통 `require_current_user` access 인증을 재사용하고 성공 응답에 no-store를
  적용한다.
- 유효성 오류는 필드 단위 공통 422, 제품 없음은 404, DB 장애는 내부 정보를 숨긴
  공통 503으로 변환한다.

## API 변경

- `POST /api/v1/care/items`
  - 인증: HttpOnly access JWT 쿠키 `AccessCookieAuth`
  - 요청: product_id, purchase_date, intake_start_date, total_quantity,
    dose_per_intake, intakes_per_day
  - 201: 새 항목 ID, 제품 ID, 등록 값, 생성 시각과 Cache-Control no-store
  - 401 AUTH_REQUIRED, 404 PRODUCT_NOT_FOUND, 422 VALIDATION_FAILED,
    503 SERVICE_UNAVAILABLE
- 요청·응답에 user_id를 노출하지 않고 Decimal 수량 응답은 문자열로 보존한다.
- 기존 인증·큐레이션 API 계약은 변경하지 않았다.

## 데이터·ERD·마이그레이션

- Alembic `20260812_0011_care_items`가 care_items를 추가한다.
- users 1:N care_items 관계는 사용자 삭제 시 CASCADE하고 products 1:N care_items
  관계는 제품 삭제를 RESTRICT한다.
- 수량은 NUMERIC(12,3) 양수, 회당 복용량은 총수량 이하, 일일 횟수는 1~24,
  복용 시작일은 구매일 이상, updated_at은 created_at 이상으로 DB CHECK한다.
- `(user_id, created_at, id)`와 `product_id` 인덱스를 추가했다.
- 테스트 DB에서 0011 downgrade·upgrade와 `alembic check`를 통과했다.
- care_items는 사용자 데이터이므로 개발 시드를 추가하지 않았다.

## 보안과 개인정보

- access JWT와 서버 refresh session 검증을 모두 통과한 활성 사용자만 등록할 수 있다.
- user_id는 요청에서 받지 않고 인증 컨텍스트에서만 가져와 수평 권한 상승을 막는다.
- 제품과 복용 계획은 건강 관련 사용자 데이터로 취급하며 성공 응답을 no-store로
  표시한다.
- 인증 쿠키·JWT와 복용 계획을 애플리케이션 로그에 추가로 남기지 않는다.
- 실제 개인정보·건강정보·비밀정보를 시드나 테스트 고정 데이터에 사용하지 않았다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-3.1-001~007을 단위·계약·통합·인수 테스트에 연결 | 7개 조건 모두 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-3.1` | 20개 통과 |
| 전체 로컬 검증 | `make verify` | 305개 통과, 커버리지 95.68% |
| 정적 검사 | `ruff format --check`, `ruff check`, `mypy` | 모두 통과, 소스 158개 타입 검사 |
| 데이터·ERD | 0011 downgrade·upgrade, ERD validator, `alembic check` | 모두 통과, 스키마 차이 없음 |
| API 확인 | `make openapi`, 저장소 OpenAPI 일치 검사 | Swagger 기준 갱신 및 일치 |

## 주요 결정과 근거

- F-3.1은 생성 책임만 가진다. 수정·삭제·상태 정책을 분리해 후속 요구사항 변경이 기존
  등록 계약과 이력을 훼손하지 않도록 했다.
- 동일 제품 재등록은 병합하지 않는다. 재구매와 기존 잔량의 의미가 F-3.3 경계이므로
  이번 기능은 사실 그대로 독립 행을 보존한다.
- 게시 여부는 큐레이션 노출 정책일 뿐 카탈로그 존재 여부가 아니므로 비게시 의약품도
  등록할 수 있게 했다.
- 미래 복용 시작일은 계획 등록을 위해 허용하되 미래 구매일은 거부한다.
- 구매일의 오늘은 UTC가 아닌 APP_TIMEZONE 기본값 Asia/Seoul 날짜로 계산해 자정 경계
  오류를 막는다.
- 유통기한은 F-3.11에서 정책과 함께 추가하며 이번 테이블에 의미가 정해지지 않은 nullable
  컬럼을 미리 만들지 않았다.

## 알려진 제약

- 등록한 항목을 이번 API로 조회·수정·삭제할 수 없다.
- 등록 시점 영양성분, 소진 예정일, 재고·만료 상태와 알림을 아직 생성하지 않는다.
- API 멱등성 키를 지원하지 않으며 반복 요청은 의도대로 별도 항목을 만든다.
- 카탈로그는 시드·DB 직접 관리만 가능하고 사용자 정의 제품은 지원하지 않는다.

## 후속 작업

- F-3.2에서 영양제의 등록 시점 성분 스냅샷을 추가한다.
- F-3.3에서 구매·보유 수량과 재구매 정책을 확정한다.
- F-3.4에서 사용자 소유 목록 조회·삭제와 보존 정책을 구현한다.
- F-3.7~F-3.9에서 소진 예정일·재구매 상태·화면 알림을 구현한다.
- F-3.11~F-3.12에서 유통기한과 이메일 리마인더를 구현한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/care/f-3-1-care-item-registration
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
