---
feature_id: "F-3.5"
title: "일일 섭취량 계산"
requirement_id: "FR-3"
domain: "care"
status: "implemented"
completed_on: "2026-08-13"
feature_packet: "docs/features/care/f-3-5-daily-intake"
pull_request: "https://github.com/Pilot-project-python5/backend/pull/18"
commit: "32163f9"
---

# F-3.5 일일 섭취량 계산 구현 이력

## 구현 요약

로그인 사용자는 자신이 등록한 삭제되지 않은 영양제 복용 계획을 기준으로 성분별
일일 예정 섭취량을 조회할 수 있다. 서로 다른 구매 항목의 같은 성분을 기준 단위로
정확히 환산해 합산하며, 의약품·삭제 항목·다른 사용자 데이터는 계산에서 제외한다.

## 구현 범위

### 포함

- 현재 사용자 소유 활성 영양제의 성분별 일일 예정 섭취량 조회
- 등록 시점 성분 스냅샷 × 회당 복용량 × 하루 횟수 계산
- G·MG·MCG 양방향 환산, IU 동일 단위 합산과 같은 성분 집계
- 복수 구매·미래 복용 시작 계획·비활성 Nutrient 표시값 경계 처리
- 보호 GET API, Swagger·OpenAPI와 단위·계약·통합·인수 테스트

### 제외

- 실제 복용 기록과 날짜별 복용 완료 여부는 구현하지 않았다.
- 총 보유 수량에 따른 현재 잔량·예상 소진일·D-day·재구매 상태는 계산하지 않는다.
- 나이·성별 영양소 기준 CSV와 달성 비율은 F-3.6으로 유지했다.
- IU와 질량 단위 사이의 성분별 환산은 지원하지 않는다.
- 계산 결과 저장·이력 테이블, 의약품 영양소 합계, AWS·AI를 추가하지 않았다.

## 주요 구현 내용

- 읽기 저장소가 인증 user_id, `deleted_at IS NULL`과 SUPPLEMENT 제품 유형을 한 쿼리
  경계에 적용하고 CareItem·CareNutrientSnapshot·Nutrient를 조회한다.
- ProductNutrient의 현재 함량은 읽지 않고 F-3.2에서 보존한 amount_per_unit·unit
  스냅샷만 계산 입력으로 사용한다.
- 서비스는 각 스냅샷의 함량과 CareItem의 dose_per_intake·intakes_per_day를 Decimal로
  곱하고 Nutrient canonical_unit으로 환산한다.
- 질량 단위는 MCG 기준의 정수 배율로 변환해 중간 반올림을 만들지 않으며, IU는 대상
  단위도 IU일 때만 허용한다.
- nutrient_id별 합계를 nutrient_code·nutrient_id 순으로 정렬하고 후행 0을 제거한
  문자열로 직렬화한다.
- 변환 불가능한 단위나 DB 예외는 일부 결과를 반환하지 않고 공통 503으로 변환한다.

## API 변경

- `GET /api/v1/care/daily-intake` 보호 읽기 API를 추가했다.
- 요청 경로·쿼리·본문 값은 없고, 응답은 nutrients 배열을 제공한다.
- 각 항목은 nutrient_id·nutrient_code·nutrient_name·daily_amount·unit만 포함한다.
- 대상 성분이 없으면 200과 빈 배열을 반환한다.
- 성공 응답은 `Cache-Control: no-store`를 포함한다.
- 인증 실패는 401 `AUTH_REQUIRED`, DB 또는 단위 데이터 실패는 503
  `SERVICE_UNAVAILABLE`다.
- 기존 CareItem 등록·목록·삭제 API 계약은 변경하지 않았다.

## 데이터·ERD·마이그레이션

- 신규 엔티티·테이블·컬럼·관계·제약·인덱스를 추가하지 않았다.
- 일일 예정 섭취량은 기존 care_items·care_nutrient_snapshots·nutrients의 읽기 전용
  파생값이며 DB에 저장하지 않는다.
- Alembic 마이그레이션·백필·시드 변경이 없다.
- ERD Mermaid 구조는 유지하고 저장값과 계산값 설명에 소유권·활성 필터, 단위 환산과
  비저장 정책을 보강했다.
- `alembic check`, ERD validator와 시드 연속 2회 실행으로 구조·멱등성을 확인했다.

## 보안과 개인정보

- 기존 access JWT와 서버 refresh session 동시 검증을 적용했다.
- 요청에서 user_id를 받지 않고 공통 인증이 확정한 현재 사용자 ID를 저장소 조건에
  강제한다.
- 다른 사용자·소프트 삭제 항목과 의약품을 저장소 조회 단계에서 제외한다.
- 응답에 user_id·care_item_id·개별 복용 계획을 노출하지 않고 건강 관련 응답에
  no-store를 적용한다.
- 사용자·CareItem ID와 성분별 전체 계획을 새 로그에 남기지 않으며 테스트 데이터는
  결정적인 가상 값만 사용한다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-3.5-001~007을 단위·계약·통합·인수 테스트에 연결 | 7개 조건 모두 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-3.5` | 18개 통과 |
| 전체 로컬 검증 | `make verify` | 361개 통과, 커버리지 96.04% |
| 정적 검사 | `ruff format --check`, `ruff check`, `mypy` | 모두 통과, 소스 183개 타입 검사 |
| 데이터·ERD | ERD validator, `alembic upgrade head`, `alembic check` | 구조 변경 없음·파생값 설명·스키마 일치 통과 |
| 시드 | 전체 시드 연속 2회 실행 | 각 5세트·16건으로 멱등 통과 |
| API 확인 | `make openapi`, 전체 OpenAPI 일치 검사 | 보호 API·응답·인증·오류·예시 반영 및 일치 |

## 주요 결정과 근거

- F-3.5 전용 경로를 `/api/v1/care/daily-intake`로 분리했다. 아직 구현되지 않은 F-3.6
  기준량과 F-3.7 소진 상태까지 `/care/summary`에 미리 고정하지 않기 위해서다.
- 미래 intake_start_date도 활성 계획 합계에 포함한다. 이번 값은 특정 날짜의 실제
  복용량이 아니라 등록된 복용 계획의 하루 총량이고 실제 복용 기록은 범위 밖이다.
- 모든 성분을 MG로 강제하지 않고 Nutrient별 canonical_unit을 사용한다. 단백질 G,
  비타민 D MCG·IU처럼 자연스러운 표시 단위를 보존하기 위해서다.
- IU와 질량 단위의 범용 환산을 금지했다. IU 환산 계수는 성분별로 달라 별도 기준
  데이터 없이 계산하면 잘못된 건강 정보를 제공할 수 있기 때문이다.
- 파생 계산을 저장하지 않았다. 입력이 이미 불변 스냅샷과 활성 CareItem에 있고
  계산 이력·캐시 요구사항이 없어 데이터 동기화 위험을 만들지 않기 위해서다.

## 알려진 제약

- Nutrient의 이름·코드·canonical_unit은 현재 기준 카탈로그 표시값이다. 제품의 단위당
  함량과 원본 단위만 CareItem 등록 시점 스냅샷이다.
- 잘못된 운영 데이터로 IU와 질량 단위가 섞이면 전체 요청이 503이며 자동 보정하거나
  일부 성분만 반환하지 않는다.
- 미래 시작 계획을 포함하므로 오늘 실제로 복용할 양을 나타내는 API가 아니다.
- 삭제되지 않았지만 예상 소진일을 지난 항목의 제외는 F-3.7 상태 계약 이후 확정한다.

## 후속 작업

- F-3.6에서 나이·성별 CSV 기준량을 연결하고 달성 비율·영양성분 현황을 계산한다.
- F-3.7에서 총수량과 복용 시작일을 사용해 예상 소진일·D-day·활성 상태를 계산한다.
- F-3.8 이후에서 재구매 상태와 화면·이메일 알림을 구현한다.
- IU와 질량 단위 사이의 성분별 변환이 필요해지면 검증된 출처·버전 기준 데이터와
  별도 Feature Packet으로 추가한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/care/f-3-5-daily-intake
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
