# 인증 계약

## 회원가입

입력 필드:

- name
- login_id
- password
- password_confirmation
- email
- birth_date
- gender
- height_cm
- weight_kg

가입 검증과 이메일 인증의 정확한 API 순서는 F-1.1과 F-1.1.3 Feature Packet에서 확정한다.

## 이메일 인증

- 6자리 코드
- 10분 유효
- 60초 재전송 대기
- 최대 5회 실패
- 인증 전 로그인 불가
- 코드 원문을 영구 저장하지 않는다

## 세션

- 액세스와 리프레시 토큰은 HttpOnly Secure 쿠키를 사용한다.
- 인증 실패는 아이디와 비밀번호 중 어떤 값이 틀렸는지 노출하지 않는다.
- 로그아웃은 현재 리프레시 세션을 폐기한다.
- 토큰 수명, 회전, SameSite와 CSRF 정책은 F-1.2 Feature Packet에서 확정한다.

## Swagger

Swagger에서 로그인 API를 실행한 뒤 동일 출처 요청에서 인증 쿠키 흐름을 검증할 수 있어야 한다. 로컬 프론트엔드 출처와 자격증명 전달 정책은 환경설정으로 관리한다.
