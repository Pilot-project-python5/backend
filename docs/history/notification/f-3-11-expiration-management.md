---
feature_id: "F-3.11"
title: "유통기한 관리"
requirement_id: "FR-3"
domain: "notification"
status: "implemented"
completed_on: "2026-08-14"
feature_packet: "docs/features/notification/f-3-11-expiration-management"
pull_request: null
commit: null
---

# F-3.11 유통기한 관리 구현 이력

## 구현 요약

로그인 사용자는 영양제·의약품 구매분마다 유통기한을 선택 입력하거나 나중에 교정하고,
활성 목록에서 KST 기준 D-day와 NORMAL·EXPIRING_SOON·EXPIRED 상태를 확인할 수 있다.
날짜를 모르는 기존·신규 항목은 기존 등록 계약을 깨지 않고 null 상태로 유지되며 후속
만료 알림 대상에서 제외된다.

## 구현 범위

### 포함

- 복용 항목 등록의 선택 유통기한 저장·응답
- 활성 복용 항목 목록의 유통기한 날짜·부호 있는 D-day·파생 상태
- 보호된 구매분별 유통기한 추가·교정 PUT API
- care_items nullable 날짜·조회 인덱스·0018 마이그레이션·ERD
- 단위·계약·저장소·마이그레이션·인수 테스트와 OpenAPI·개발 문서

### 제외

- 유통기한 제거, 제조일·개봉일·개봉 후 사용기한 관리는 제외했다.
- 실제 복용 기록·잔량 보정과 복용 계획·수량 수정은 제외했다.
- 재구매 상태는 F-3.8, 화면 알림은 F-3.9, 이메일 발송은 F-3.12로 분리했다.
- AWS 배포·외부 스케줄러와 AI 연결은 2차 범위로 유지했다.

## 주요 구현 내용

- 등록 서비스가 선택 날짜를 예상 소진일·성분 스냅샷과 같은 트랜잭션에 저장한다.
- 목록 서비스는 주입된 시계와 APP_TIMEZONE의 오늘을 사용해 날짜 차이를 계산하고,
  순수 도메인 함수가 null·NORMAL·EXPIRING_SOON·EXPIRED를 결정한다.
- D-6 이상은 NORMAL, D-5부터 D0은 EXPIRING_SOON, 다음 날부터는 EXPIRED다.
- 갱신 저장소는 `id + user_id + deleted_at IS NULL` 조건으로 날짜와 updated_at을 원자
  갱신하며 같은 날짜 재요청도 같은 200 결과를 낸다.
- 조회 상태는 날짜 경과에 따라 달라지므로 저장하지 않고 예상 소진·재고와 독립적으로
  계산한다.

## API 변경

- `POST /api/v1/care/items` 요청에 선택 `expiration_date`를 추가하고 201 응답에는
  nullable 날짜를 항상 포함한다.
- `GET /api/v1/care/items` 항목에 nullable `expiration_date`,
  `days_until_expiration`, `expiration_status`를 추가한다.
- `PUT /api/v1/care/items/{care_item_id}/expiration`은 필수 ISO 날짜를 받아 200으로
  care_item_id와 저장 날짜를 반환한다.
- 세 API 모두 기존 AccessCookieAuth와 no-store를 사용한다. 인증 없음 401, 잘못된
  형식 422, 갱신 대상 없음 404, DB 장애 503의 공통 오류 계약을 적용한다.

## 데이터·ERD·마이그레이션

- Alembic 0018이 care_items에 nullable DATE `expiration_date`를 추가한다. 백필이나
  서버 기본값 없이 기존 행은 null을 유지한다.
- 후속 알림 후보 조회를 위해 `(expiration_date, user_id)` B-tree 인덱스를 추가했다.
- ORM·ERD·개념 데이터 모델에 저장 날짜와 비저장 D-day·상태 규칙을 동기화했다.
- 0018 downgrade는 인덱스와 날짜 열만 제거하며 기존 CareItem 행은 보존한다.
- 카탈로그 기준 데이터 변경이 아니므로 신규 시드는 없고 전체 기존 시드 7세트의
  연속 2회 멱등 실행을 회귀 검증했다.

## 보안과 개인정보

- 등록·목록·갱신은 기존 access JWT와 서버 refresh session 검증을 재사용한다.
- 갱신 조건에 현재 user_id와 활성 행 조건을 함께 적용하고, 다른 사용자·삭제·없는
  항목을 같은 404로 반환해 존재 여부를 구분해 노출하지 않는다.
- 요청·응답에 user_id·deleted_at을 넣지 않고 개인 건강 관련 응답은 no-store다.
- 사용자 식별자·구매분 ID·유통기한 값을 새 애플리케이션 로그에 남기지 않는다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-3.11-001~005 단위·계약·통합·인수 테스트 | 5개 조건 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-3.11` | 56개 통과 |
| 전체 로컬 검증 | `make verify` | 419개 통과, 커버리지 95.60% |
| 정적 검사 | ruff format/check, mypy | 모두 통과, 소스 214개 타입 검사 |
| 데이터·ERD | 0018 왕복, alembic check, ERD validator | 모두 통과 |
| 시드·API | 전체 시드 연속 2회, OpenAPI 일치 검사 | 7세트·84건 멱등, 계약 일치 |

## 주요 결정과 근거

- expiration_date는 필수 대신 선택으로 두었다. 기존 데이터·클라이언트 호환성과 실제로
  사용자가 날짜를 모를 수 있는 상황을 보존하기 위해서다.
- 날짜 없음에 별도 UNKNOWN 문자열을 만들지 않고 날짜·D-day·상태를 모두 null로
  통일해 미관리 상태를 명시하고 알림 대상에서 안전하게 제외한다.
- D0까지 EXPIRING_SOON으로 두고 다음 날 EXPIRED로 전환했다. 날짜만 제공되는 계약에서
  당일의 임의 시간대 만료를 가정하지 않기 위해서다.
- 과거·구매일 이전 날짜를 허용했다. 이미 만료된 구매분 기록과 포장에 인쇄된 날짜를
  보존하고, 임의의 제조·구매 순서 규칙을 사실처럼 강제하지 않기 위해서다.
- 제거 대신 교정 PUT만 제공했다. 1차에 필요한 오입력 수정은 지원하면서 알림 기준을
  의도치 않게 지우는 별도 상태 전이는 후속 정책으로 남기기 위해서다.

## 알려진 제약

- 유통기한은 날짜 단위이며 시간·제조일·개봉 후 사용기한을 표현하지 않는다.
- 날짜는 DB·API로 직접 관리하며 관리자 UI나 카탈로그 공통 유통기한은 없다.
- 사용자가 날짜를 입력하지 않으면 상태를 추론하지 않고 만료 알림도 만들지 않는다.
- 갱신 이력은 별도 감사 테이블에 남기지 않고 CareItem의 최신 값과 updated_at만 보존한다.

## 후속 작업

- F-3.8에서 expected_depletion_date 기준 재구매 상태를 독립적으로 구현한다.
- F-3.9에서 D-5·D-3·D-1 오전 9시 화면 알림 생성·조회·확인을 구현한다.
- F-3.12에서 같은 논리 알림의 이메일 전달·중복 방지·재시도를 구현한다.
- 2차에서 AWS 스케줄링·운영 데이터·관측성과 AI 연결을 별도 승인한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/notification/f-3-11-expiration-management
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
