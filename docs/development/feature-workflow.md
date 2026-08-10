# 기능 개발 흐름

## 1. 선택

- manifest에서 기능 ID와 단계, 우선순위, 담당을 확인한다.
- 브랜치를 feat/<feature-id>-<slug> 형식으로 만든다.

## 2. 명세

- specify-sdd-feature를 사용한다.
- 구현을 막는 질문을 해결한다.
- 데이터 변경이 있으면 maintain-project-erd를 사용해 ERD 영향과 마이그레이션 계획을 작성한다.
- 사용자 승인 후 상태를 approved로 바꾼다.

## 3. 구현

- 인수 테스트를 먼저 작성한다.
- 마이그레이션, 도메인, API, 테스트와 문서를 수직으로 구현한다.
- 범위 밖 리팩터링을 분리한다.

## 4. 검증

- verify-sdd-feature를 사용한다.
- 대상 기능 검사 후 make verify를 실행한다.
- 데이터 변경이 있으면 make erd-check를 실행한다.
- OpenAPI와 Swagger를 확인한다.

## 5. 이력 기록

- verify-sdd-feature의 검증 근거를 사용한다.
- record-feature-history로 docs/history/<domain>에 구현 이력을 작성한다.
- Feature Packet의 history_path를 연결하고 status를 implemented로 갱신한다.
- 엄격 이력 검증을 통과한다.

## 6. 리뷰

- prepare-feature-pr를 사용한다.
- 한 기능 ID, 구현 이력과 검증 근거를 PR에 기록한다.
- 사용자가 요청하지 않으면 외부 푸시나 PR 생성은 하지 않는다.
