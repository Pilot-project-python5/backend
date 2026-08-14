---
feature_id: "F-3.10"
title: "의약품 관리"
requirement_id: "FR-3"
domain: "medication"
status: "implemented"
completed_on: "2026-08-14"
feature_packet: "docs/features/medication/f-3-10-medication-management"
pull_request: "https://github.com/Pilot-project-python5/backend/pull/21"
commit: "3566f9d"
---

# F-3.10 의약품 관리 구현 이력

## 구현 요약

로그인 사용자는 DB 시드로 관리되는 게시 의약품을 목록에서 선택하고 출처를 포함한
복약 상세를 조회할 수 있다. 의약품은 기존 마이케어 등록·소진 흐름을 사용하면서도
영양소 합계에서는 제외되며, 로컬 데이터는 실제 복약에 쓰지 않는 예시임을 명시한다.

## 구현 범위

### 포함

- 보호된 의약품 목록·상세 API와 Swagger/OpenAPI 계약
- Product 1:0..1 MedicationDetail 모델·0017 마이그레이션·ERD
- OTC/PRESCRIPTION, 품목 코드, 성분·효능·용법·주의·보관·출처·검토일
- 결정적·멱등 로컬 예시 의약품 2건과 실제 존재하는 정적 이미지
- 단위·계약·저장소·마이그레이션·시드·인수 테스트

### 제외

- 사용자·운영자 의약품 CRUD와 카탈로그 밖 직접 입력은 포함하지 않았다.
- 실제 품목 허가정보 자동 수집·운영 승인 워크플로는 포함하지 않았다.
- 상호작용·금기·개인화 복약 지시, 처방전·약국·결제·실제 복용 기록은 제외했다.
- 유통기한 상태와 알림은 F-3.11 이후로 분리했다.

## 주요 구현 내용

- 저장소는 게시 MEDICATION Product와 MedicationDetail을 내부 조인해 상세 없는 행,
  미게시 행과 영양제를 동시에 제외하고 Product sort_order·sku로 안정 정렬한다.
- 목록은 제품·포장·품목 코드·분류·성분 요약을, 상세는 효능·용법·주의·보관과
  출처명·URL·검토일을 추가 제공한다.
- 서비스는 없는 상세를 404 MEDICATION_NOT_FOUND, 저장소 실패를 공통 503으로 변환한다.
- 시드가 Product와 MedicationDetail을 각각 고유 키로 upsert해 두 번 실행해도 동일한
  두 행으로 수렴하며 다른 카탈로그·CareItem을 삭제하지 않는다.
- 기존 CareItem 등록과 DailyIntake 경계를 회귀 검증해 의약품은 등록되지만 영양소
  계산에는 들어가지 않음을 보장한다.

## API 변경

- `GET /api/v1/medications` 보호 페이지 목록 API를 추가했다. page 1 이상,
  page_size 1~100이며 빈 페이지는 200이다.
- `GET /api/v1/medications/{product_id}` 보호 상세 API를 추가했다.
- 응답은 no-store이고 AccessCookieAuth를 요구한다. 인증 없음 401, 상세 없음 404,
  형식 오류 422, DB 장애 503을 공통 오류 계약으로 반환한다.
- 기존 Product·CareItem 요청과 응답 계약은 변경하지 않았다.

## 데이터·ERD·마이그레이션

- 0017로 medication_details를 만들고 product_id를 Product PK/FK로 사용한다. Product
  삭제 시 상세는 CASCADE되지만 참조 CareItem이 있는 Product는 기존 RESTRICT가 지킨다.
- permit_code UNIQUE·형식, OTC/PRESCRIPTION, 필수 텍스트 길이, HTTPS 출처 안전성과
  updated_at 순서를 CHECK로 강제한다.
- `(classification, product_id)` 인덱스를 추가하고 실제 필드·관계·제약을 ERD와 개념
  데이터 모델에 동기화했다.
- 로컬 예시 Product·MedicationDetail 2건과 SVG 2개를 일곱 번째 시드 세트로 추가했다.

## 보안과 개인정보

- 목록·상세 모두 기존 access JWT와 서버 refresh session 검증을 재사용한다.
- 카탈로그 API는 사용자 ID, 처방·진단·개인 복용 정보와 행 소유권을 읽지 않는다.
- 비게시·영양제·상세 없음·미존재를 같은 404로 반환해 내부 게시 상태를 노출하지 않는다.
- 사용자 식별자와 향후 처방·진단 정보는 새 로그에 남기지 않는다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-3.10-001~005 계약·통합·인수 테스트 | 5개 조건 자동화 |
| 대상 기능 검사 | `make feature-check FEATURE=F-3.10` | 20개 통과 |
| 전체 로컬 검증 | `make verify` | 403개 통과, 커버리지 95.60% |
| 정적 검사 | ruff format/check, mypy | 모두 통과, 소스 211개 타입 검사 |
| 데이터·ERD | 0017 왕복, alembic check, ERD validator | 모두 통과 |
| 시드·API | 전체 시드 연속 2회, OpenAPI 일치 검사 | 7세트·84건 멱등, 계약 일치 |

## 주요 결정과 근거

- 1차 분류는 OTC와 PRESCRIPTION 두 값으로 제한했다. 사용자 선택·표시에는 충분하면서
  임의의 세부 약효 분류를 새 표준처럼 만들지 않기 위해서다.
- 품목 코드와 출처·검토일을 필수로 두었다. 효능·용법·주의 정보가 바뀔 때 어느 품목의
  어떤 근거를 검토했는지 추적하기 위해서다.
- 로컬 시드는 실제 브랜드·복약 문구를 흉내 내지 않고 실사용 금지 예시로 만들었다.
  검증되지 않은 의료 내용을 서비스가 사실처럼 제공하는 위험을 피하기 위해서다.
- 게시 Product와 상세가 모두 있어야 API에 노출한다. 불완전한 시드나 영양제가 의약품
  선택 화면에 섞이지 않게 하는 단일 공개 조건이다.

## 알려진 제약

- 현재 두 의약품은 로컬 API·UI 검증용이므로 실제 복약 판단에 사용할 수 없다.
- 운영 전 품목별 공식 허가정보, 출처 URL, 검토 책임자·주기를 포함한 승인 데이터로
  반드시 교체해야 한다.
- Product와 MedicationDetail의 유형 일치는 교차 테이블 CHECK로 강제할 수 없어
  시드 검증·조인 조건·통합 테스트로 보장한다.

## 후속 작업

- F-3.11에서 CareItem 유통기한 입력·상태를 영양제와 의약품 모두에 추가한다.
- F-3.8·F-3.9·F-3.12에서 재구매 상태와 화면·이메일 알림을 구현한다.
- 2차 운영 전 공식 의약품 데이터 수집·검수·교체 절차를 별도 기능으로 승인한다.

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/medication/f-3-10-medication-management
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
