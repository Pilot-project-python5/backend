# 기능 구현 이력

이 폴더는 구현과 검증이 끝난 기능의 실제 결과를 보관한다. 요구사항이나 구현 전 설계가 아니라 최종 코드, API, 데이터 변경과 검증 근거를 기록한다.

## 저장 경로

기능마다 문서 하나를 만든다.

~~~text
docs/history/<domain>/<normalized-feature-id>-<slug>.md
~~~

예시:

~~~text
docs/history/auth/f-1-1-signup.md
docs/history/notification/f-3-8-repurchase-notification.md
~~~

## 작성 시점

1. 승인된 Feature Packet으로 기능을 구현한다.
2. verify-sdd-feature 검증을 통과한다.
3. record-feature-history로 이력 문서를 생성하고 실제 결과를 채운다.
4. Feature Packet의 history_path를 생성된 경로로 갱신한다.
5. 이력 문서 엄격 검증을 통과한다.
6. 구현 코드와 같은 기능 PR에 포함한다.
7. 리뷰 중 동작이 바뀌면 머지 전에 이력 문서도 갱신한다.

## 작성 원칙

- 명령 출력과 실제 변경 사항으로 확인한 내용만 기록한다.
- 요구사항, Feature Packet이나 코드 전체를 복사하지 않는다.
- 사용자에게 보이는 동작, API, 데이터·ERD·마이그레이션과 보안 영향을 요약한다.
- 실행한 검증 명령과 결과를 남긴다.
- 변경 없음도 해당하지 않는 이유와 함께 명시한다.
- 알려진 제약과 후속 작업을 숨기지 않는다.
- 비밀정보, 실제 개인정보·건강정보와 긴 로그를 넣지 않는다.
- PR이나 커밋이 아직 없으면 null로 두고 생성 후 갱신할 수 있다.

## 문서 책임 구분

- docs/product/requirements.md: 제품 요구사항 기준
- Feature Packet: 구현 전 승인 계약
- docs/architecture/erd.md: 현재 논리 데이터 구조
- docs/history: 구현된 결과와 검증 근거
- docs/api/openapi-changelog.md: API 호환성 변경 기록

## 템플릿

새 문서는 docs/history/_template.md를 직접 복사하지 말고 create_history.py로 생성한다. 생성 직후 상태는 draft이며 실제 내용을 모두 채운 뒤 implemented로 바꾼다.
