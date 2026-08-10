# F-1.1 작업 목록

## 명세

- [x] 이메일 고유성과 입력 범위 정책을 확정한다
- [x] F-1.1과 F-1.1.1~F-1.1.3의 기능 경계를 확정한다
- [x] feature.yaml, spec.md, design.md와 acceptance.md를 승인한다
- [x] users·health_profiles ERD 영향과 마이그레이션 계획을 승인한다

## 테스트 우선

- [x] F-1.1 인수 테스트를 추가한다
- [x] 비밀번호·정규화 단위 테스트와 PostgreSQL 통합 테스트를 추가한다
- [x] 회원가입 요청·응답·오류 계약 테스트를 추가한다

## 구현

- [x] users와 health_profiles 마이그레이션을 추가한다
- [x] docs/architecture/erd.md를 승인된 데이터 설계로 갱신한다
- [x] 회원가입 도메인·저장소·비밀번호 해시를 구현한다
- [x] POST /api/v1/auth/signup과 오류 계약을 구현한다
- [x] OpenAPI 산출물과 인증 문서를 갱신한다

## 검증

- [x] make feature-check FEATURE=F-1.1을 실행한다
- [x] 마이그레이션을 빈 개발·테스트 DB에서 검증한다
- [x] make erd-check를 실행한다
- [x] make openapi-check를 실행한다
- [x] make verify를 실행한다
- [x] docs/history/auth/f-1-1-signup.md를 작성하고 엄격 검증한다
- [x] feature.yaml의 history_path를 연결하고 status를 implemented로 갱신한다
- [x] PR 본문에 실제 검증 근거를 기록한다
