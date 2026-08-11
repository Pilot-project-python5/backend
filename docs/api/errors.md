# 오류 계약

## 응답 형식

~~~json
{
  "error": {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "아이디 또는 비밀번호가 올바르지 않습니다.",
    "fields": [],
    "request_id": "opaque-id"
  }
}
~~~

## 규칙

- code는 클라이언트 분기에 사용하는 안정적인 값이다.
- message는 사용자 표시용이며 민감한 내부 상태를 노출하지 않는다.
- fields는 입력 필드별 오류가 있을 때만 제공한다.
- request_id는 로컬 디버깅과 2차 관측성 연결을 위한 상관관계 값이다.
- DB 오류, 스택 트레이스, 토큰과 인증번호를 응답하거나 로그에 남기지 않는다.

## 초기 오류 코드

- AUTH_LOGIN_ID_UNAVAILABLE
- AUTH_EMAIL_UNAVAILABLE
- AUTH_EMAIL_UNVERIFIED
- AUTH_ACCOUNT_SUSPENDED
- AUTH_EMAIL_ALREADY_VERIFIED
- AUTH_VERIFICATION_CODE_INVALID
- AUTH_VERIFICATION_EXPIRED
- AUTH_VERIFICATION_NOT_ACTIVE
- AUTH_VERIFICATION_RESEND_TOO_SOON
- AUTH_VERIFICATION_TOO_MANY_ATTEMPTS
- AUTH_INVALID_CREDENTIALS
- AUTH_SESSION_INVALID
- AUTH_REQUIRED
- RESOURCE_NOT_FOUND
- VALIDATION_FAILED
- CARE_PRODUCT_NOT_ALLOWED
- NOTIFICATION_ALREADY_SCHEDULED
- SERVICE_UNAVAILABLE
- HTTP_ERROR
- INTERNAL_SERVER_ERROR

기능별 오류 코드는 Feature Packet에서 추가하고 OpenAPI에 반영한다.
