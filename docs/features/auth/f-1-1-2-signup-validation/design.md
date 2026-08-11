# F-1.1.2 설계

## API 계약

- 메서드와 경로: POST /api/v1/auth/signup/validation
- 인증: 불필요
- 요청: F-1.1 SignupRequest와 동일한 name, login_id, password,
  password_confirmation, email, birth_date, gender, height_cm, weight_kg
- 성공 응답: 200, valid 불리언과 issues 배열. 각 issue는 field, code, message다.
- 오류 응답: 422 VALIDATION_FAILED, 503 SERVICE_UNAVAILABLE
- 멱등성: 읽기 전용이며 같은 DB 상태·기준일에서는 반복 결과가 같다. 식별자를
  예약하지 않는다.

## 데이터 설계

- 엔티티: 기존 users 읽기
- 관계와 카디널리티: 변경 없음
- 제약 조건: users.normalized_login_id와 normalized_email UNIQUE를 최종 기준으로 사용
- 인덱스: 기존 두 고유 인덱스를 중복 조회에 재사용
- 마이그레이션: 없음
- 백필과 기존 데이터 영향: 읽기 전용이므로 없음
- 이력과 삭제: 데이터를 생성·수정·삭제하지 않음

## ERD 영향

- docs/architecture/erd.md 변경: 아니오
- 변경 전 구조: users에 정규화 로그인 아이디와 이메일 고유 인덱스가 존재
- 변경 후 구조: 변경 없음
- 변경하지 않는 경우의 이유: 기존 데이터를 읽는 사전 검증만 추가
- ERD 검증 방법: make erd-check와 Alembic autogenerate check로 비의도 변경 확인

## 애플리케이션 흐름

1. SignupRequest가 필수값, 문자열·이메일 형식, 비밀번호, 성별과 신체 범위를 검증한다.
2. 서비스가 주입된 Clock으로 미래 생년월일을 확인한다.
3. 서비스가 아이디와 이메일을 F-1.1 규칙으로 정규화한다.
4. 저장소가 한 읽기 쿼리로 두 정규화 값의 중복 여부를 조회한다.
5. 서비스가 login_id, email, birth_date 순서로 issue를 만들고 valid를 결정한다.
6. 라우터가 비밀번호와 건강정보를 제외한 검증 결과만 반환한다.

## 보안과 개인정보

- 소유권 검사: 공개 회원가입 보조 API이므로 인증과 기존 사용자 소유권 검사는 없음
- 민감 필드: 비밀번호·비밀번호 확인·이메일·생년월일·성별·키·몸무게
- 로그 제외 항목: 요청 본문 전체, 비밀번호 필드, DB 오류 상세와 사용자 행
- 열거 위험: 아이디·이메일 중복 여부를 필드 issue로 공개하므로 운영 공개 전에
  속도 제한과 봇 방지 정책이 필요함

## 로컬 어댑터

- 데이터베이스: 로컬 PostgreSQL 16과 SQLAlchemy 2 동기 세션
- 시간: 주입 가능한 Clock으로 미래 생년월일 판정
- 이메일: 주소 형식과 중복만 확인하며 발송하지 않음
- 스케줄러: 사용하지 않음

## 호환성

- OpenAPI 영향: 공개 POST 엔드포인트, SignupValidationResponse와 issue 스키마 추가
- 기존 데이터 영향: 없음
- 롤백: 신규 라우트·서비스·저장소·응답 스키마를 제거하며 DB 롤백은 없음
