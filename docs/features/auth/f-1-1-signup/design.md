# F-1.1 설계

## API 계약

- 메서드와 경로: POST /api/v1/auth/signup
- 인증: 불필요
- 요청: name, login_id, password, password_confirmation, email, birth_date,
  gender, height_cm, weight_kg
- 성공 응답: 201, id, login_id, email, status,
  email_verification_required, created_at
- 오류 응답: 409 AUTH_LOGIN_ID_UNAVAILABLE, 409 AUTH_EMAIL_UNAVAILABLE,
  422 VALIDATION_FAILED, 503 SERVICE_UNAVAILABLE
- 멱등성: 멱등 키를 제공하지 않는다. 동일 정규화 식별자의 재요청은 409다.

## 데이터 설계

- 엔티티: users, health_profiles
- 관계와 카디널리티: USERS 1 : 1 HEALTH_PROFILES. health_profiles.user_id가
  PK이자 users.id FK다.
- users 필드: UUID id, name varchar(50), login_id varchar(20),
  normalized_login_id varchar(20), email varchar(320), normalized_email varchar(320),
  password_hash varchar(255), email_verified_at timestamptz nullable, status varchar(32),
  created_at timestamptz, updated_at timestamptz
- health_profiles 필드: UUID user_id, birth_date date, gender varchar(16),
  height_cm numeric(5,2), weight_kg numeric(6,2), created_at timestamptz,
  updated_at timestamptz
- 제약 조건: users.normalized_login_id UNIQUE, status 허용값 CHECK,
  gender 허용값 CHECK, 이름 공백 불가, 미래 생년월일은 애플리케이션에서 검사,
  키·몸무게 DB CHECK, normalized_email UNIQUE
- 인덱스: normalized_login_id와 normalized_email 고유 인덱스
- 마이그레이션: 20260810_0001 기준점 다음 리비전에서 users를 먼저 만들고
  health_profiles를 FK ON DELETE CASCADE로 만든다. downgrade는 health_profiles,
  users 순으로 제거한다.
- 백필과 기존 데이터 영향: 빈 기능 스키마에 신규 테이블을 추가하므로 백필 없음
- 이력과 삭제: F-1.1은 삭제 API를 제공하지 않는다. 계정 상태와 생성·수정 일시는
  보존한다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: 논리 users와 health_profiles가 있으나 필드 길이, 상태값, 시간 필드와
  실제 제약이 확정되지 않음
- 변경 후 구조: 승인된 실제 필드, 1:1 FK, UNIQUE/CHECK, 삭제 정책과 인덱스를 명시
- 변경하지 않는 경우의 이유: 해당 없음
- ERD 검증 방법: validate_erd.py, Alembic autogenerate check, PostgreSQL 통합 테스트

## 애플리케이션 흐름

1. Pydantic 요청 모델이 필수값, 문자열 형식, 날짜와 숫자 범위를 검증한다.
2. 서비스가 이름·로그인 아이디·이메일을 정규화하고 비밀번호 일치를 검사한다.
3. Argon2id 포트가 비밀번호를 해시한다.
4. 저장소가 사용자와 건강 프로필을 같은 SQLAlchemy 세션에 추가하고 커밋한다.
5. 고유 제약 충돌을 안정적인 409 오류로 변환하고 다른 DB 장애는 공통 503으로
   변환한다.
6. API가 비밀번호 관련 필드를 제외한 201 응답을 반환한다.

## 보안과 개인정보

- 소유권 검사: 신규 계정 생성 API이므로 기존 사용자 소유권 검사는 해당하지 않는다.
- 민감 필드: 비밀번호·비밀번호 확인·비밀번호 해시, 이메일, 생년월일, 성별, 키,
  몸무게
- 로그 제외 항목: 요청 본문 전체와 모든 비밀번호 필드, 이메일과 건강 프로필
- 비밀번호 정책: Argon2id 해시만 저장하며 해시 구현은 교체 가능한 포트 뒤에 둔다.
- 응답 최소화: 건강 프로필과 비밀번호 해시는 회원가입 응답에서 반환하지 않는다.

## 로컬 어댑터

- 데이터베이스: PostgreSQL 16, SQLAlchemy 2 동기 세션
- 시간: 주입 가능한 Clock으로 created_at과 생년월일 기준일을 결정
- 이메일: F-1.1에서는 호출하지 않고 F-1.1.3에서 연결
- 스케줄러: 해당 없음

## 호환성

- OpenAPI 영향: 신규 공개 API와 SignupRequest, SignupResponse,
  Gender, UserStatus 스키마 추가
- 기존 데이터 영향: 신규 테이블이므로 없음
- 롤백: F-1.1 기능 데이터가 아직 외부에서 사용되지 않는 전제에서 신규 테이블을
  역순 삭제한다. 운영 데이터가 생긴 뒤에는 downgrade 전에 별도 백업·승인이 필요하다.
