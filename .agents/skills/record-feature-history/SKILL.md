---
name: record-feature-history
description: 구현과 검증이 끝난 영양꾹 백엔드 기능의 실제 결과를 docs/history에 생성·갱신·검증한다. 기능 완료 후 PR 준비 전, 구현 요약·API·데이터·ERD·마이그레이션·보안·테스트 근거·제약과 후속 작업을 기록할 때 사용한다. 요구사항이나 예상 설계가 아니라 확인된 구현 결과만 문서화한다.
---

# 기능 구현 이력 기록

완료된 기능의 실제 동작과 검증 근거를 구현 코드와 같은 PR에 남긴다.

## 작업 절차

1. AGENTS.md, docs/history/README.md, 승인된 Feature Packet과 verify-sdd-feature 결과를 읽는다.
2. 전체 기능 diff, 최종 API, 마이그레이션, ERD, 시드와 테스트 결과를 확인한다.
3. 이력 문서가 없으면 scripts/create_history.py로 생성하고 있으면 기존 문서를 갱신한다.
4. 템플릿의 모든 HISTORY_REQUIRED 표식을 실제 구현 근거로 교체한다.
5. API나 데이터 변경이 없더라도 변경 없음과 이유를 명시한다.
6. Feature Packet의 history_path를 생성된 저장소 상대 경로로 갱신한다.
7. 이력 문서 status를 implemented로 바꾼다.
8. scripts/validate_history.py --strict를 실행한다.
9. 리뷰 중 구현이 바뀌면 머지 전에 이력과 검증 근거를 다시 갱신한다.

## 경로 규칙

~~~text
docs/history/<domain>/<normalized-feature-id>-<slug>.md
~~~

F-1.1과 signup은 docs/history/auth/f-1-1-signup.md가 된다.

## 내용 규칙

- 검증 결과와 코드에서 확인한 사실만 기록한다.
- 요구사항이나 Feature Packet 전체를 반복하지 않는다.
- 사용자에게 보이는 결과와 중요한 내부 동작을 함께 요약한다.
- API 메서드·경로와 주요 상태·오류 변경을 기록한다.
- 데이터 변경 시 ERD, 마이그레이션, 제약, 인덱스와 시드 영향을 기록한다.
- 인수 조건 ID와 실행 명령·결과를 연결한다.
- 알려진 제약과 후속 기능을 숨기지 않는다.
- 비밀정보, 실제 개인정보·건강정보, 토큰과 긴 로그를 기록하지 않는다.
- PR과 커밋이 아직 없으면 null로 두고 생성 뒤 갱신한다.

## 생성 명령

~~~bash
python .agents/skills/record-feature-history/scripts/create_history.py \
  docs/features/auth/f-1-1-signup \
  --completed-on 2026-08-10
~~~

## 검증 명령

~~~bash
python .agents/skills/record-feature-history/scripts/validate_history.py \
  docs/history/auth/f-1-1-signup.md \
  --strict
~~~

## 완료 조건

이력 경로, 기록한 구현 결과, 검증 근거, 남은 제약과 엄격 검증 결과를 반환한다. 이력 문서가 최종 구현과 다르거나 필수 표식이 남아 있으면 PR 준비 완료로 판단하지 않는다.
