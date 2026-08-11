# F-1.2 작업 목록

## 명세

- [x] 로그인·상태·토큰 수명·쿠키·다중 세션 정책을 확정한다
- [x] feature.yaml, spec.md, design.md와 acceptance.md를 승인한다
- [x] refresh_sessions 구조와 ERD 변경을 확정한다

## 테스트 우선

- [x] 인수 테스트를 추가한다
- [x] 단위·통합 테스트를 추가한다
- [x] API·쿠키 계약 테스트를 추가한다

## 구현

- [x] refresh_sessions 마이그레이션과 ORM 모델을 구현한다
- [x] JWT·리프레시 생성과 해시 경계를 구현한다
- [x] 로그인 서비스와 상태 차단을 구현한다
- [x] 로그인 API·쿠키·오류 계약을 구현한다
- [x] ERD·인증·환경설정·OpenAPI 문서를 갱신한다

## 검증

- [x] 대상 기능 검사를 실행한다
- [x] 빈 DB 마이그레이션과 시드 검사를 실행한다
- [x] ERD와 OpenAPI 검사를 실행한다
- [x] 로컬 전체 검증을 실행한다
- [x] docs/history에 구현 이력을 작성하고 엄격 검증을 실행한다
- [x] feature.yaml과 manifest 상태를 implemented로 갱신한다
- [x] PR 본문에 검증 근거를 기록한다
