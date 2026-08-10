# 명령 계약

아래 명령은 Makefile로 구현된 하네스의 안정적인 사용자 인터페이스다.

| 명령 | 목적 |
| --- | --- |
| make dev | 로컬 API, PostgreSQL, 메일과 작업자 시작 |
| make stop | 로컬 서비스 중지, 데이터 볼륨 유지 |
| make migrate | 개발 DB를 최신 마이그레이션으로 적용 |
| make seed | 개발 시드를 멱등하게 적재 |
| make test | 전체 자동 테스트 |
| make test-unit | 외부 입출력 없는 단위 테스트 |
| make test-integration | PostgreSQL 기반 통합 테스트 |
| make test-contract | OpenAPI와 오류 계약 테스트 |
| make feature-new FEATURE=F-x.y | Feature Packet 생성 |
| make feature-check FEATURE=F-x.y | 대상 기능의 명세와 테스트 검증 |
| make history-new FEATURE=F-x.y | 대상 Feature Packet에서 구현 이력 초안 생성 |
| make history-check FEATURE=F-x.y | 구현 이력의 추적성, 필수 내용과 완료 상태 검증 |
| make erd-check | 로컬 ERD 필수 구조와 실제 데이터 모델·마이그레이션의 일치 검증 |
| make openapi | OpenAPI 산출물 생성 |
| make openapi-check | 생성된 계약과 저장소 기준 비교 |
| make verify | 포맷, 린트, 타입, 테스트, 마이그레이션, 시드와 OpenAPI 전체 검증 |

명령이 없는 상태를 성공으로 처리하지 않는다. 새 도구가 추가되더라도 위 명령의 의미는 유지한다.

최초 실행 시 `.env.local`이 없으면 Makefile이 `.env.example`을 복사한다. 컨테이너
이미지와 Python 의존성은 `uv.lock`으로 고정한다. `feature-check`는 Feature Packet
엄격 검증과 해당 기능 ID가 표식된 테스트를 함께 실행하며, 연결된 테스트가 없으면
성공으로 처리하지 않는다.
