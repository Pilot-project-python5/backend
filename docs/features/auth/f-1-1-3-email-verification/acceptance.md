# F-1.1.3 인수 조건

## AC-F-1.1.3-001 인증번호 발급과 안전한 저장

전제: 이메일 미인증 사용자가 존재한다.

행동: 인증번호 발급을 요청한다.

결과: 201과 발급 ID·10분 만료·60초 재전송 시각을 반환하고 해당 이메일로 숫자
6자리 코드를 보내며 DB에는 코드 원문과 다른 HMAC 해시만 저장한다.

## AC-F-1.1.3-002 인증 성공

전제: 사용되지 않았고 만료되지 않은 인증번호다.

행동: 발급 ID와 올바른 코드를 확인한다.

결과: 200을 반환하고 발급 이력을 used 처리하며 사용자의 status를 ACTIVE,
email_verified_at을 현재 시각으로 같은 트랜잭션에서 갱신한다.

## AC-F-1.1.3-003 재전송 대기와 이전 코드 무효화

전제: 코드가 방금 발급됐다.

행동: 60초 전에 재전송하고, 정확히 60초에 다시 재전송한다.

결과: 첫 요청은 429이고 두 번째는 201이다. 새 발급은 실패 횟수 0이며 이전 발급은
superseded 처리되어 올바른 이전 코드를 입력해도 409다.

## AC-F-1.1.3-004 다섯 번 실패 잠금

전제: 유효한 인증번호가 있다.

행동: 잘못된 코드를 반복 입력한다.

결과: 1~4회는 400이고 5회부터 429이며 올바른 코드도 사용할 수 없다. 60초 뒤
재전송한 새 코드는 다시 확인할 수 있다.

## AC-F-1.1.3-005 만료 경계

전제: 인증번호 발급 후 정확히 10분이 지났다.

행동: 올바른 코드를 확인한다.

결과: 410 AUTH_VERIFICATION_EXPIRED이며 사용자와 발급 이력을 인증 완료로 바꾸지 않는다.

## AC-F-1.1.3-006 대상과 상태 오류

전제: 존재하지 않는 사용자·발급 ID, 이미 인증된 사용자, 사용 또는 대체된 발급이 있다.

행동: 각각 발급·재전송·확인을 요청한다.

결과: 존재하지 않음은 404, 이미 인증된 사용자의 발급은 409, 사용·대체된 발급 확인은
409이며 이메일·내부 상태를 추가로 노출하지 않는다.

## AC-F-1.1.3-007 인프라 실패 원자성

전제: DB 또는 SMTP 처리가 실패한다.

행동: 발급이나 확인을 요청한다.

결과: 503을 반환하며 SMTP 실패 발급이 활성 이력으로 커밋되거나 사용자가 부분적으로
ACTIVE가 되지 않는다.

## 데이터·ERD 인수 조건

빈 PostgreSQL에서 email_verifications 테이블, users CASCADE FK, 목적·횟수·시간 CHECK와
최신 발급 조회 인덱스가 재현된다. 모델·마이그레이션·docs/architecture/erd.md가 일치한다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-1.1.3-001 | tests/acceptance/auth/test_email_verification.py | 발급·메일·해시 |
| AC-F-1.1.3-002 | tests/acceptance/auth/test_email_verification.py | ACTIVE 원자적 전환 |
| AC-F-1.1.3-003 | tests/unit/auth/test_email_verification_service.py, tests/acceptance/auth/test_email_verification.py | fake clock 경계·대체 |
| AC-F-1.1.3-004 | tests/acceptance/auth/test_email_verification.py | 실패 누적·새 코드 초기화 |
| AC-F-1.1.3-005 | tests/unit/auth/test_email_verification_service.py | 10분 경계 |
| AC-F-1.1.3-006 | tests/contract/auth/test_email_verification_contract.py | 공개 오류 계약 |
| AC-F-1.1.3-007 | tests/unit/auth/test_email_verification_service.py | SMTP·DB 실패 |
