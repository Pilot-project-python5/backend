# 알약꾹 백엔드 에이전트 가이드

## 목적과 범위

- 1차 MVP는 인터넷, AWS 계정, 운영 이메일 공급자와 AI 서비스 없이 로컬에서 완전히 실행되어야 한다.
- 1차 범위는 회원·이메일 인증, 전문가 큐레이션 API, 마이케어, 의약품, 영양소 계산, 소진·유통기한 알림과 Swagger다.
- 추천 소식 알림과 AI 코칭은 1차 범위에서 제외한다.
- 2차에서 AWS 인프라, 운영 이메일, 모니터링과 다른 개발자의 AI 모듈을 연결한다.
- 프론트엔드는 백엔드 OpenAPI와 Swagger가 확정된 뒤 개발한다.

## 작업 모델

- Codex 단일 모델로 작업한다.
- 서브에이전트나 병렬 에이전트를 사용하지 않는다.
- 사용자 요청의 범위를 임의로 넓히지 않는다.
- 데이터 소유권, 보안, 계산, API 호환성 또는 개발 단계가 달라지는 모호함은 구현 전에 질문한다.

## 문서 읽기 순서

1. docs/README.md
2. docs/product/requirements.md
3. docs/product/scope.md와 docs/product/phase-plan.md
4. docs/features/manifest.yaml
5. 대상 Feature Packet의 feature.yaml, spec.md, design.md, acceptance.md, tasks.md
6. 관련 architecture, api, development 문서
7. 출처 이력이 필요할 때만 docs/source-map.md

저장소 문서만으로 기능을 명세·구현·검증할 수 있어야 한다. docs/product/requirements.md와 승인된 Feature Packet이 구현 권위이며 외부 문서 서비스 연결은 필수가 아니다. 사용자가 새 외부 요구사항을 제공해 로컬 기준과 충돌하면 구현을 멈추고 결정을 받은 뒤 같은 변경에서 로컬 기준 문서와 Feature Packet을 먼저 갱신한다.

## SDD 기능 개발

1. 기능 ID를 manifest에서 확인한다.
2. specify-sdd-feature 스킬로 Feature Packet을 생성하거나 갱신한다.
3. 사용자의 명시적 승인 전에는 feature.yaml 상태를 approved로 바꾸지 않는다.
4. 데이터 구조가 바뀌면 maintain-project-erd 스킬로 Feature Packet과 docs/architecture/erd.md의 변경을 함께 확정한다.
5. 인수 조건을 자동 테스트로 먼저 표현한다.
6. 마이그레이션, 도메인 로직, API, 테스트와 문서를 하나의 수직 기능으로 구현한다.
7. verify-sdd-feature 스킬로 증거를 수집한다.
8. record-feature-history 스킬로 docs/history에 실제 구현 내용과 검증 근거를 기록한다.
9. prepare-feature-pr 스킬로 기능 단위 PR을 준비한다.

## PR 규칙

- 원칙적으로 기능 ID 하나당 PR 하나다.
- 브랜치 이름은 feat/<feature-id>-<slug> 형식이다.
- 하나의 PR은 하나의 주 기능 ID만 구현한다.
- 결합이 불가피한 의존 기능은 Feature Packet과 PR 본문에 이유를 기록한다.
- 관련 없는 리팩터링, 대규모 포맷 변경, AWS 배포와 AI 구현을 섞지 않는다.
- 외부 push, commit 또는 PR 생성은 사용자가 명시적으로 요청할 때만 수행한다.

## 로컬 우선 기술 경계

- PostgreSQL 개발 DB와 테스트 DB를 분리한다. SQLite로 대체하지 않는다.
- 마이그레이션은 빈 DB에서 재현 가능해야 한다.
- 시드 데이터는 반복 적재 가능하고 결정적이어야 하며 실제 개인정보나 건강정보를 포함하지 않는다.
- 이메일, 시간, 스케줄러, 파일 저장소와 향후 AI는 교체 가능한 경계 뒤에 둔다.
- 시간 의존 테스트는 fake clock, 이메일 테스트는 fake sender를 사용한다.
- API 경로는 /api/v1을 사용한다.
- 인증은 HttpOnly Secure 쿠키 기반 액세스·리프레시 토큰을 사용한다.

## API와 Swagger

- 요청·응답 스키마, 예시, 필수값, 허용 범위, 상태 코드와 공통 오류 코드를 문서화한다.
- 인증 쿠키, 페이지네이션, 필터, 정렬과 상태값 의미를 명시한다.
- 구현과 생성된 OpenAPI가 다르면 기능을 완료로 판단하지 않는다.
- 호환성에 영향을 주는 OpenAPI 변경은 Feature Packet과 changelog를 함께 갱신한다.

## 검증 명령

docs/development/commands.md의 명령 인터페이스는 루트 Makefile을 통해 실행한다.
대상 명령이 없거나 실행되지 않으면 통과한 것으로 간주하지 않는다.

- make dev
- make migrate
- make seed
- make test
- make feature-check FEATURE=F-x.y
- make history-new FEATURE=F-x.y
- make history-check FEATURE=F-x.y
- make erd-check
- make openapi-check
- make verify

## 완료 정의

- Feature Packet이 승인된 뒤 구현 이력과 연결된 implemented 상태다.
- 모든 인수 조건에 검증 증거가 있다.
- 관련 테스트, 마이그레이션, 시드와 OpenAPI 검사가 통과한다.
- 데이터 변경이 있으면 ERD, 마이그레이션과 실제 모델이 일치한다.
- docs/history의 기능 이력 문서가 실제 구현과 일치하고 엄격 검증을 통과한다.
- 외부 AWS와 AI 없이 로컬에서 기능을 재현할 수 있다.
- Swagger와 실제 동작이 일치한다.
- 임시 파일, 비밀정보, 실제 개인정보와 범위 밖 변경이 없다.

## 코드 리뷰 규칙

- 승인되지 않은 기능 명세를 구현한 변경을 지적한다.
- 한 PR에 여러 주 기능 ID가 섞인 변경을 지적한다.
- 알림 날짜 경계, 중복 발송 방지, 소유권 검증과 인증 실패 처리가 빠진 변경을 지적한다.
- 의약품을 영양소 합계에 포함하거나 1차 범위에 AI·AWS 의존성을 추가한 변경을 지적한다.
- 테스트를 약화하거나 삭제해 통과시킨 변경을 지적한다.
- 데이터 모델을 바꾸면서 Feature Packet과 docs/architecture/erd.md를 갱신하지 않은 변경을 지적한다.
- 구현을 완료하면서 docs/history 문서나 검증 근거를 누락한 변경을 지적한다.
