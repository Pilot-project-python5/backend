---
feature_id: "F-1.1.3"
title: "이메일 인증"
requirement_id: "FR-1"
domain: "auth"
status: "implemented"
completed_on: "2026-08-11"
feature_packet: "docs/features/auth/f-1-1-3-email-verification"
pull_request: null
commit: null
---

# F-1.1.3 이메일 인증 구현 이력

## 구현 요약

가입 직후 이메일 미인증 사용자는 로컬 Mailpit으로 받은 숫자 6자리 코드를 확인해
ACTIVE 상태가 될 수 있다. 10분 만료, 60초 재전송 대기, 5회 실패 잠금과 이전 코드
무효화가 적용되며 코드 원문은 DB·응답·로그에 남기지 않는다.

## 구현 범위

### 포함

- 인증번호 최초 발급·재전송·확인 공개 API 3개
- 발급 ID와 서버 비밀값을 사용하는 HMAC-SHA256 코드 해시
- 발급 이력, 실패 횟수, 만료·재전송·사용·대체 상태 저장
- 인증 성공과 users ACTIVE 전환의 단일 DB 트랜잭션
- Mailpit SMTP 어댑터, fake sender·clock·code generator 기반 자동 테스트
- Swagger/OpenAPI 오류·경계 예시와 로컬 비밀값 설정

### 제외

- 이메일 링크 인증, 이메일 주소 변경과 비밀번호 재설정
- 운영 이메일 공급자, 재시도 큐와 transactional outbox
- IP·계정 단위 속도 제한, CAPTCHA와 인증 요청 감사 로그
- AWS 비밀 관리와 HMAC 비밀값 회전 절차
- 로그인·세션 발급과 인증 전 사용자 정리 정책

## 주요 구현 내용

발급 서비스는 사용자 행을 먼저 잠가 같은 사용자의 동시 발급을 직렬화하고, 최신
발급의 60초 경계를 확인한다. 새 UUID와 안전한 난수 코드를 만든 뒤 발급 ID·코드를
HMAC-SHA256으로 해시하며, 이전 미사용 발급은 superseded 처리한다. DB 변경을 아직
커밋하지 않은 상태에서 SMTP 발송을 수행해 발송 실패 시 전체 발급을 롤백한다.

확인 서비스는 발급 소유 사용자 행과 발급 행을 같은 순서로 잠근다. 사용·대체·정지,
5회 잠금과 만료를 검사한 뒤 잘못된 입력 횟수를 저장하거나, 성공 시 used_at과
users.status=ACTIVE, email_verified_at·updated_at을 한 트랜잭션으로 커밋한다.

## API 변경

- POST /api/v1/auth/email-verifications: user_id로 발급, 201
- POST /api/v1/auth/email-verifications/resend: user_id로 재전송, 201
- POST /api/v1/auth/email-verifications/confirm: verification_id와 code 확인, 200
- 성공 응답에는 verification_id·expires_at·resend_available_at 또는
  user_id·ACTIVE·email_verified_at을 포함한다.
- 오류: 400 코드 불일치, 404 대상 없음, 409 이미 인증·비활성 발급·정지 상태,
  410 만료, 422 요청 형식, 429 재전송 대기·5회 잠금, 503 DB·SMTP 실패
- 신규 API이므로 기존 호출과 호환되며 openapi.json과 변경 기록을 갱신했다.

## 데이터·ERD·마이그레이션

20260811_0003 마이그레이션으로 email_verifications를 추가하고 20260811_0004로
완료·대체 시각 CHECK를 보강했다. users와 다대일
CASCADE FK이며 id, user_id, purpose, code_hash, expires_at,
resend_available_at, failed_attempts, used_at, superseded_at, created_at을 저장한다.
purpose=VERIFY_EMAIL, 실패 횟수 0~5, 생성 이후 만료·재전송 시각, used와 superseded의
생성 이전 기록과 동시 기록 금지를 CHECK로 보장한다. 사용자별 최신 발급 조회에
(user_id, created_at) 인덱스를 사용한다. 시드 변경은 없다.

논리 ERD, ORM과 마이그레이션을 함께 갱신했다. 별도 빈 PostgreSQL DB에서 전체
upgrade, F-1.1.3 downgrade, 재-upgrade를 실행했고 Alembic autogenerate 차이가 없음을
확인했다.

## 보안과 개인정보

인증번호 원문은 이메일 전송 순간에만 메모리에 존재하며 DB·응답·애플리케이션 로그에
남기지 않는다. 숫자 6자리의 작은 탐색 공간을 보완하기 위해 발급 ID와 환경 비밀값을
HMAC 입력에 포함하고 상수 시간 비교를 사용한다. 공개 API가 존재 여부와 재전송 상태를
일부 드러낼 수 있으므로 운영 공개 전 계정·IP 속도 제한과 봇 방지가 필요하다.

EMAIL_VERIFICATION_SECRET 기본값은 로컬 전용이며 공유·운영 환경에서는 저장소 밖의
32자 이상 비밀값으로 교체해야 한다. 이 값을 바꾸면 아직 유효한 인증번호도 모두
검증할 수 없게 된다.

## 테스트 및 검증

| 검증 항목 | 실행 명령 또는 근거 | 결과 |
| --- | --- | --- |
| 인수 조건 | AC-F-1.1.3-001~007 연결 테스트 | 19개 통과 |
| 대상 기능 검사 | make feature-check FEATURE=F-1.1.3 | 19개 통과 |
| 전체 로컬 검증 | make verify | 96개 통과, 커버리지 94.15%, Ruff·mypy·ERD·Alembic·시드·OpenAPI 통과 |
| 빈 DB 마이그레이션 | 전용 임시 DB upgrade→downgrade 20260810_0002→upgrade | 통과 후 임시 DB 삭제 |

## 주요 결정과 근거

- 가입 응답의 user_id와 발급 응답의 verification_id를 사용해 로그인 전 과정을
  명시적인 세 단계 API로 분리했다.
- 발급마다 새 행을 보존하고 이전 행을 superseded 처리해 재전송 이력과 무효화 이유를
  덮어쓰지 않는다.
- user 행을 먼저 잠그는 고정 순서로 동시 발급·확인의 상태 경쟁과 교착 가능성을 줄였다.
- 5번째 실패 요청부터 429를 반환하고, 60초 경계에서는 새 코드 발급을 허용한다.
- SMTP 발송 실패 시 DB 발급을 롤백해 메일을 받지 못한 활성 코드를 남기지 않는다.

## 알려진 제약

1차 로컬 MVP는 SMTP와 DB의 분산 트랜잭션을 제공하지 않는다. 메일 발송은 성공했지만
DB 커밋이 실패하면 사용 불가능한 코드가 전달될 수 있으며, 자동 재시도·전송 상태·
outbox가 없다. 발급 API는 회원가입 직후 프론트엔드가 별도로 호출해야 한다.

또한 공개 API에 전역 속도 제한과 CAPTCHA가 없고 HMAC 비밀값 회전을 지원하지 않는다.
Mailpit은 개발 수신함이며 운영 이메일 전달성·반송·수신 거부는 검증하지 않는다.

## 후속 작업

- F-1.2 로그인에서 PENDING_EMAIL_VERIFICATION 차단과 ACTIVE 사용자 세션 발급
- 2차 운영 이메일 공급자·outbox·재시도·전송 추적과 비밀 관리 연동
- 운영 공개 전 계정·IP 속도 제한, CAPTCHA, 감사 이벤트와 미인증 계정 정리 정책

## 관련 문서

- 요구사항: docs/product/requirements.md
- Feature Packet: docs/features/auth/f-1-1-3-email-verification
- ERD: docs/architecture/erd.md
- OpenAPI 변경 기록: docs/api/openapi-changelog.md
