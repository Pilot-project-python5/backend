---
feature_id: "F-3.6"
title: "영양성분 현황"
requirement_id: "FR-3"
domain: "care"
status: "implemented"
completed_on: "2026-08-14"
feature_packet: "docs/features/care/f-3-6-nutrient-status"
pull_request: "https://github.com/Pilot-project-python5/backend/pull/19"
commit: "54cf3a4"
---

# F-3.6 영양성분 현황 구현 이력

## 구현 요약

로그인 사용자는 등록한 영양제 복용 계획의 일일 예정량을 자신의 만 나이·성별에 맞는
공인 영양소 기준량과 비교해 조회할 수 있다. 기준이 없는 성분도 누락하지 않으며,
기준 버전·출처와 이 비교가 음식 섭취 또는 임상 판정이 아니라는 의미를 함께 제공한다.

## 구현 범위

### 포함

- 현재 사용자 프로필의 KST 기준 만 나이 계산과 성별 구간 조회
- F-3.5 일일 예정량과 RNI 우선·AI 대체 기준량의 Decimal 비율 계산
- 기준이 없는 일반 OMEGA_3의 명시적 null 응답
- 2025 KDRI CSV 검증·checksum·결정적 UUID·원자적 멱등 적재
- 보호 GET API, PostgreSQL 기준 테이블, ERD·OpenAPI·인수·계약·통합·단위 테스트

### 제외

- 음식 섭취량, 실제 복용 기록과 임상적 결핍·과잉 판정은 포함하지 않았다.
- 임신·수유 추가량과 성분별 IU↔질량 환산은 지원하지 않는다.
- 일반 OMEGA_3를 EPA+DHA 공식 기준으로 임의 매핑하지 않았다.
- 기준 자동 다운로드, 사용자 기준 버전 선택, AWS·AI 연동은 포함하지 않았다.

## 주요 구현 내용

- 서비스가 주입한 시각을 Asia/Seoul 날짜로 바꾸고 지난 생일 기준 만 나이를 계산한다.
- 기존 DailyIntakeService를 재사용해 삭제되지 않은 영양제 계획만 합산하고, 설정한
  `KDRI-2025-20260316` 기준 버전의 사용자 성별·나이 구간을 결합한다.
- 기준이 있으면 현재량/기준량×100을 Decimal로 계산해 소수 첫째 자리
  ROUND_HALF_UP하고 100%를 초과해도 자르지 않는다.
- CSV 적재기는 정확한 열·허용값·양수·나이 구간·중복·겹침·메타데이터·성분 단위를
  전체 검증한 뒤 같은 버전 값을 한 트랜잭션에서 결정적으로 교체한다.
- 기준 버전 없음, 저장소 장애와 단위 불일치는 부분 결과 없이 공통 503으로 변환한다.

## API 변경

- `GET /api/v1/care/nutrient-status` 보호 읽기 API를 추가했다.
- 요청 값 없이 계산일·만 나이·성별·기준 버전·출처와 성분별 현재량·기준량·유형·
  달성 비율을 반환한다. Decimal은 후행 0을 제거한 문자열이다.
- 기준 없는 성분은 `reference_available=false`와 null 기준 필드를 반환하고, 성분이
  없으면 메타데이터와 빈 배열을 반환한다.
- 성공은 200과 `Cache-Control: no-store`, 인증 실패는 401 `AUTH_REQUIRED`, 기준·DB·
  단위 실패는 503 `SERVICE_UNAVAILABLE`다.

## 데이터·ERD·마이그레이션

- 0015 마이그레이션으로 `nutrient_reference_versions`와
  `nutrient_reference_values`를 추가했다.
- 버전·checksum 고유, HTTPS 출처, RNI/AI·성별·0~120세·양수량·단위 CHECK, 정확한
  구간 UNIQUE와 버전·성별·나이 조회 인덱스를 적용했다.
- 기준 버전 삭제는 값 CASCADE, Nutrient 삭제는 RESTRICT하며 기존 사용자·제품·
  CareItem 데이터는 변경하지 않는다.
- 공식 CSV 66행과 SHA-256을 적재하고 시드 2회 실행이 동일 상태로 수렴함을 검증했다.
- 논리 ERD와 개념 데이터 모델을 실제 필드·관계·제약·비저장 파생 계산에 맞게 갱신했다.

## 보안과 개인정보

- 기존 access JWT와 서버 refresh session 검증을 재사용하고 요청에서 user_id를 받지 않는다.
- 현재 사용자 프로필과 user_id로 제한한 CareItem만 읽으며 의약품·삭제 항목·다른
  사용자 항목은 계산 입력에서 제외한다.
- 생년월일 원문·user_id·care_item_id를 응답하지 않고 계산한 만 나이만 제공한다.
- 개인 건강 관련 응답에 no-store를 적용하고 사용자·복용 정보의 새 로그를 만들지 않았다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-3.6-001~007 단위·계약·통합·인수 테스트 | 7개 조건 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-3.6` | 13개 통과 |
| 전체 로컬 검증 | `make verify` | 374개 통과, 커버리지 95.67% |
| 정적 검사 | ruff format/check, mypy | 모두 통과, 소스 195개 타입 검사 |
| 데이터·ERD | 0015 왕복, alembic check, ERD validator | 모두 통과 |
| 시드·API | 전체 시드 연속 2회, OpenAPI 일치 검사 | 6세트·82건 멱등, 계약 일치 |

## 주요 결정과 근거

- 2025 한국인 영양소 섭취기준을 코드 상수가 아닌 CSV·버전·checksum으로 관리한다.
  건강 기준의 출처와 변경 이력을 추적하고 2차 교체를 안전하게 하기 위해서다.
- 개인 비교는 RNI를 우선하고 없으면 AI를 사용한다. 두 기준의 공식 의미를 보존하면서
  사용자에게 사용할 수 있는 대표 비교값 하나를 안정적으로 제공하기 위해서다.
- 일반 OMEGA_3는 EPA+DHA와 동일하다고 보장할 수 없어 기준 없음으로 반환한다.
  수치가 비슷해 보여도 다른 개념을 연결해 건강 정보를 왜곡하지 않기 위해서다.
- 계산 결과는 저장하지 않고 기존 예정량과 기준값으로 요청마다 만든다. 입력 변경 때
  동기화 오류를 만들지 않고 출처 버전과 계산일을 응답에서 명시하기 위해서다.

## 알려진 제약

- 1차 CSV는 현재 카탈로그의 단백질·비타민 C·비타민 D 성인·소아 1~120세 구간만
  포함하며 임신·수유 상태는 프로필에 없어 반영하지 않는다.
- 설정 버전이 적재되지 않은 로컬 DB는 API가 503이므로 마이그레이션 뒤 시드를 반드시
  실행해야 한다.
- 식사와 실제 복용 기록이 없으므로 비율을 개인의 실제 영양 상태로 해석할 수 없다.

## 후속 작업

- F-3.7에서 총수량·복용량으로 예상 소진일과 D-day를 계산한다.
- F-3.8 이후에서 재구매 상태와 화면·이메일 알림을 구현한다.
- 임신·수유나 새 기준 버전은 프로필·공식 원본·마이그레이션 정책을 별도 Feature
  Packet으로 승인한 뒤 추가한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/care/f-3-6-nutrient-status
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
