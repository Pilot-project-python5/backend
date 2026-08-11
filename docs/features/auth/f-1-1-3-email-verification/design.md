# F-1.1.3 설계

## API 계약

- POST /api/v1/auth/email-verifications: user_id로 최초 또는 후속 인증번호를 발급하고
  201과 verification_id, expires_at, resend_available_at을 반환한다.
- POST /api/v1/auth/email-verifications/resend: 같은 응답 계약으로 새 인증번호를 만든다.
- POST /api/v1/auth/email-verifications/confirm: verification_id와 숫자 6자리 code를
  받아 200과 user_id, status=ACTIVE, email_verified_at을 반환한다.
- 세 API 모두 가입 과정의 공개 API다.
- 오류: 400 AUTH_VERIFICATION_CODE_INVALID, 404 RESOURCE_NOT_FOUND,
  409 AUTH_EMAIL_ALREADY_VERIFIED/AUTH_VERIFICATION_NOT_ACTIVE,
  410 AUTH_VERIFICATION_EXPIRED,
  429 AUTH_VERIFICATION_RESEND_TOO_SOON/AUTH_VERIFICATION_TOO_MANY_ATTEMPTS,
  422 VALIDATION_FAILED, 503 SERVICE_UNAVAILABLE.

## 데이터 설계

- email_verifications는 발급 이력마다 새 UUID 행을 만든다.
- 필드: id, user_id, purpose, code_hash, expires_at, resend_available_at,
  failed_attempts, used_at, superseded_at, created_at.
- purpose는 VERIFY_EMAIL, failed_attempts는 0~5다.
- expires_at과 resend_available_at은 created_at 이후이며 used_at과 superseded_at은
  각각 미사용·유효 여부를 표현하고 값이 있으면 created_at 이상이어야 한다.
- users와 다대일이며 사용자 삭제 시 발급 이력도 삭제한다.
- (user_id, created_at) 복합 인덱스로 최신 발급 이력을 조회한다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 논리 ERD에 있던 EMAIL_VERIFICATIONS를 실제 마이그레이션 수준으로 확정한다.
- superseded_at과 created_at, CHECK·FK·복합 인덱스를 명시한다.
- 마이그레이션: 20260811_0003이 테이블·기본 제약·인덱스를 만들고,
  20260811_0004가 완료·대체 시각 CHECK를 추가한다.
- 검증: 빈 PostgreSQL에서 Alembic upgrade/downgrade/upgrade, make erd-check,
  autogenerate 차이 검사를 실행한다.

## 애플리케이션 흐름

1. 발급 서비스가 사용자 행을 잠그고 존재·인증 상태와 최신 발급의 재전송 시각을 확인한다.
2. 안전한 난수 생성기로 코드를 만들고 HMAC-SHA256 해시만 새 이력에 저장한다.
3. 이전 미사용 이력을 superseded 처리한 뒤 같은 트랜잭션 안에서 로컬 SMTP로 보낸다.
4. 발송 성공 시 커밋하고 실패 시 롤백한다.
5. 확인 서비스가 발급 행을 잠그고 활성·만료·실패 횟수를 순서대로 검사한다.
6. 비교 실패는 횟수를 원자적으로 저장하고, 성공은 발급 사용 처리와 사용자 ACTIVE
   전환을 같은 트랜잭션에서 커밋한다.

## 보안과 개인정보

- 코드 원문과 이메일 본문은 로그·오류·DB에 남기지 않는다.
- 짧은 숫자 코드는 일반 비밀번호 해시만으로 오프라인 대입 공격에 약하므로 서버
  비밀값과 발급 ID를 HMAC 입력에 포함한다.
- HMAC 비밀값은 환경변수로 주입하며 2차 배포에서는 비밀 관리 서비스로 옮긴다.
- 공개 user_id·verification_id API는 1차 로컬 MVP 계약이다. 운영 공개 전 IP·계정
  속도 제한과 열거 방지 정책을 추가해야 한다.

## 로컬 어댑터

- 데이터베이스: PostgreSQL 16, SQLAlchemy 동기 세션
- 시간: SystemClock, 테스트에서는 FakeClock
- 이메일: Mailpit SMTP, 테스트에서는 FakeEmailSender
- 코드: secrets 기반 생성기, 테스트에서는 고정 생성기

## 호환성

- OpenAPI: 공개 POST 엔드포인트 3개와 스키마·오류 계약 추가
- 기존 데이터: users를 변경하지 않고 새 테이블만 추가
- 롤백: email_verifications를 삭제한다. 이미 ACTIVE로 바뀐 사용자는 downgrade로
  PENDING 상태에 되돌리지 않으므로 배포 롤백 전에 운영 데이터 정책이 필요하다.
