# 알약꾹 백엔드 문서

이 디렉터리는 알약꾹 백엔드의 SDD 실행 기준이다.

## 읽기 순서

1. product/requirements.md에서 저장소 요구사항 기준을 확인한다.
2. product/scope.md와 product/phase-plan.md에서 개발 범위를 확인한다.
3. product/phase-1-mvp-readiness.md에서 1차 완료 상태와 2차 경계를 확인한다.
4. features/manifest.yaml에서 기능 ID, 단계와 담당 경계를 확인한다.
5. 작업 대상의 Feature Packet을 읽는다.
6. 데이터 변경이 있으면 architecture/erd.md와 data-model.md를 읽는다.
7. architecture와 api 문서로 나머지 설계 제약을 확인한다.
8. development 문서의 로컬 실행과 검증 절차를 따른다.
9. 구현 완료 기능을 조사할 때 history의 기능 이력 문서를 읽는다.
10. 출처 이력이 필요할 때만 source-map.md를 확인한다.

## 문서 책임

- product/requirements.md: 외부 연결 없이 읽을 수 있는 제품 요구사항 기준
- product/phase-1-mvp-readiness.md: 1차 완료 범위, 검증 근거와 2차 인계 기준
- Feature Packet: 한 기능 PR의 구현 계약
- architecture: 여러 기능에 걸친 장기 설계 결정과 ERD
- api: 프론트엔드와 후속 AI 개발자를 위한 계약
- development: 로컬 실행과 반복 가능한 검증
- history: 완료된 기능의 실제 구현 내용과 검증 근거
- phase-2: 1차에서 지켜야 할 확장 경계
- source-map.md: 선택적으로 확인하는 외부 출처와 동기화 이력

Feature Packet은 사용자 승인 전까지 draft 상태다. 구현 완료 후에도 명세, ERD, 실제 동작이 다르면 구현을 완료로 판단하지 않는다. 외부 문서 서비스에 접속할 수 없어도 저장소 문서만으로 모든 개발 절차를 수행할 수 있어야 한다.
