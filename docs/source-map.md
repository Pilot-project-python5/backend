# 출처와 동기화 이력

마지막 로컬 기준 갱신일: 2026-08-12

## 구현 권위

구현과 검증은 다음 저장소 파일만으로 수행한다.

1. docs/product/requirements.md
2. docs/product/scope.md
3. docs/product/phase-plan.md
4. docs/features/manifest.yaml
5. 승인된 Feature Packet
6. docs/architecture, docs/api, docs/development 문서

외부 문서 서비스 연결은 기능 명세, 구현, 테스트와 PR 준비의 전제 조건이 아니다.

## 외부 출처 기록

아래 링크는 요구사항이 처음 정리된 출처와 동기화 이력을 보존하기 위한 선택적 참조다.

- 요구사항 정의서: https://app.notion.com/p/5fe2779e9262829a86a98117cac67fb0
- 기능 명세서: https://app.notion.com/p/55a2779e9262830a91f6813664c0ddf5
- 시퀀스 다이어그램: https://app.notion.com/p/3b62779e92628041a925cedeccd0198d
- 백엔드 개발 1차·기능 고도화: https://app.notion.com/p/3b82779e926280c2b4eef9cb0eeb202e
- ERD: https://app.notion.com/p/3b82779e926281378a0cc5af78e34b84

## 동기화 규칙

1. 외부 문서를 읽지 못해도 현재 저장소 기준으로 작업을 계속한다.
2. 사용자가 새 요구사항이나 외부 문서 동기화를 명시적으로 요청할 때만 외부 출처를 확인한다.
3. 새 결정은 먼저 docs/product/requirements.md, 관련 설계 문서와 Feature Packet에 반영한다.
4. 외부 출처와 저장소 기준이 충돌하면 사용자 결정을 받은 뒤 저장소 기준을 갱신하고 구현한다.
5. Feature Packet의 external_url은 출처 이력이 필요할 때만 선택적으로 기록한다.
6. Swagger와 OpenAPI는 구현된 API 계약이며 제품 정책을 대신하지 않는다.

## 미보관 자료

초기 UI/UX 화면은 대화에서 제공됐지만 저장소의 영구 자산으로 아직 등록되지 않았다. API 필드나 사용자 흐름을 UI만으로 추론하지 말고 로컬 요구사항 또는 Feature Packet에 명시한다.
