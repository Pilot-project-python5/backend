---
name: specify-sdd-feature
description: 영양꾹 백엔드 기능 하나의 실행 가능한 SDD Feature Packet을 로컬 요구사항 기준에서 생성하거나 갱신한다. 기능 정의·구체화·분리·승인, 인수 조건 추가, 데이터·ERD 영향 정리 또는 구현 전 범위 확정을 요청받았을 때 사용한다. 외부 문서 서비스 연결을 요구하지 않으며 사용자가 구현을 별도로 요청하지 않으면 운영 코드를 구현하지 않는다.
---

# SDD 기능 명세

코드 변경을 시작하기 전에 요구사항 ID 하나를 검토 가능한 기능 계약으로 만든다.

## 작업 절차

1. 루트 AGENTS.md, docs/README.md, docs/product/requirements.md, docs/product/scope.md와 docs/features/manifest.yaml을 읽는다.
2. manifest에서 기능 ID를 찾는다.
3. 기존 Feature Packet이 있으면 재사용한다. 없으면 scripts/create_feature.py로 생성한다.
4. 저장소 요구사항 기준, 기존 설계 문서와 최신 사용자 결정을 비교한다. 외부 출처는 사용자가 동기화를 요청했을 때만 확인한다.
5. 모호함이 데이터 소유권, 보안, 계산 규칙, API 호환성, 개발 단계 범위 또는 인수 동작을 바꾸면 멈추고 사용자에게 질문한다.
6. feature.yaml, spec.md, design.md, acceptance.md와 tasks.md를 완성한다.
7. 데이터 구조가 바뀌면 design.md에 ERD 영향을 기록하고 maintain-project-erd를 사용한다.
8. Feature Packet을 기능 ID 하나로 제한한다. 피할 수 없는 의존성은 범위를 조용히 넓히지 말고 기록한다.
9. scripts/validate_feature.py를 실행한다.
10. 사용자가 기능 계약을 명시적으로 승인한 뒤에만 상태를 approved로 바꾼다.

## Feature Packet 규칙

- 인수 조건 ID는 AC-<기능-번호>-<순번> 형식으로 안정적으로 유지한다.
- 관찰 가능한 동작을 전제, 행동, 결과로 작성한다.
- 관련되는 경우 정상 흐름, 유효성 실패, 권한 실패, 멱등성과 시간 경계 사례를 포함한다.
- 범위 밖 동작을 명시한다.
- API와 영속성 설계는 구현할 수 있을 만큼 구체적으로 작성하되 코드 수준의 중복은 피한다.
- source.requirement_path는 docs/product/requirements.md를 가리킨다.
- 외부 URL은 출처 이력이 필요할 때만 source.external_url에 선택적으로 기록한다.
- 테이블, 관계, 제약 또는 인덱스가 바뀌면 ERD 변경 여부와 마이그레이션 계획을 명시한다.
- 해결되지 않은 항목은 미결 질문에 유지한다.

## 명령

Feature Packet 생성:

~~~bash
python .agents/skills/specify-sdd-feature/scripts/create_feature.py \
  --id F-1.1 \
  --slug signup \
  --title "회원가입" \
  --domain auth \
  --requirement FR-1 \
  --phase 1 \
  --priority P0
~~~

Feature Packet 검증:

~~~bash
python .agents/skills/specify-sdd-feature/scripts/validate_feature.py \
  docs/features/auth/f-1-1-signup
~~~

승인 또는 구현 상태가 예상될 때만 --strict 옵션을 사용한다.

## 완료 조건

기능 경로, 기록된 결정, 미결 질문, 검증 결과와 정확한 구현 범위를 반환한다. 검증이 실패했거나 승인이 없으면 구현 준비가 끝났다고 주장하지 않는다.
