# 백엔드 미사용 항목 정리 이력

## 2026-08-17 정리 범위

공개 API, 데이터 모델, 마이그레이션, 시드와 하네스 계약은 유지하고 코드·문서·테스트·
개발 DB·테스트 DB 참조를 함께 확인했을 때 사용되지 않는 항목만 제거했다.

### 제거한 항목

- 현재 통합 `NotificationJob`으로 대체된 `RepurchaseNotificationJob`과 전용 중복 테스트
- 실제 알림 작업자가 등록된 뒤 사용되지 않는 `BootstrapWorkerJob`과 전용 테스트
- 실행 명령에서 직접 고정하고 설정 소비자가 없는 `app_host`, `app_port` 설정 필드
- 모듈 설명과 중복되고 소비자가 없는 카탈로그 출처 상수 2개
- 코드·문서·개발 DB·테스트 DB 참조가 모두 0건인 예전 BSN 제품 SVG
- 로컬 macOS `.DS_Store`와 해당 파일의 Docker 빌드 컨텍스트 재유입

### 유지한 항목

- `sports-research-omega-3.svg`는 코드 참조가 없어도 기존 개발 DB 제품 1건이 사용하므로
  유지했다.
- `life-extension-two-per-day.svg`와 의약품 SVG는 DB, 문서 예시 또는 시드가 사용하므로
  유지했다.
- `FakeClock`, `FakeEmailSender`는 자동 테스트에서 사용하는 교체 가능 경계이므로
  유지했다.
- `argon2-cffi`, `email-validator`, `PyJWT`, `psycopg`, `uvicorn`은 import 이름 차이,
  프레임워크 간접 사용 또는 실행 진입점 때문에 의존성 분석에서 오탐된 항목이라
  유지했다.

## 호환성

- HTTP 경로, 요청·응답 스키마와 상태 코드를 변경하지 않았다.
- DB 테이블, 마이그레이션과 시드 결과를 변경하지 않았다.
- 정리 전후 `openapi.json` Git 객체 해시는
  `0cee0e38170740fdb5d8b101ca4ee4819f89091d`로 동일하다.

## 검증 결과

- Ruff 포맷 439개 파일 및 lint 통과
- mypy 243개 소스 파일 통과
- ERD 19개 엔티티·20개 관계 검증 통과
- Alembic 적용 및 ORM 차이 없음 확인
- 전체 시드 203건 2회 연속 적용 통과
- 전체 테스트 468개 통과, 커버리지 95.03%
- OpenAPI 저장 계약 일치 확인
