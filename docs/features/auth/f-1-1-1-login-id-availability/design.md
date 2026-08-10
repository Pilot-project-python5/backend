# F-1.1.1 설계

## API 계약

- 메서드와 경로: GET /api/v1/auth/login-id/availability
- 인증: 불필요
- 요청: query login_id, 영문자·숫자 5~20자
- 성공 응답: 200, login_id와 available 불리언
- 오류 응답: 422 VALIDATION_FAILED, 503 SERVICE_UNAVAILABLE
- 멱등성: 읽기 전용 조회이며 같은 DB 상태에서는 반복 요청 결과가 같다. 조회 결과는
  아이디를 예약하지 않는다.

## 데이터 설계

- 엔티티: 기존 users
- 관계와 카디널리티: 변경 없음
- 제약 조건: 기존 users.normalized_login_id UNIQUE를 최종 고유성 기준으로 사용
- 인덱스: 기존 고유 인덱스를 조회에 재사용
- 마이그레이션: 없음
- 백필과 기존 데이터 영향: 읽기 전용이므로 없음
- 이력과 삭제: 데이터를 생성·수정·삭제하지 않음

## ERD 영향

- docs/architecture/erd.md 변경: 아니오
- 변경 전 구조: users.normalized_login_id에 UNIQUE 제약과 고유 인덱스가 존재
- 변경 후 구조: 변경 없음
- 변경하지 않는 경우의 이유: 기존 인덱스를 이용한 읽기 전용 조회만 추가
- ERD 검증 방법: make erd-check와 Alembic autogenerate check로 비의도 스키마 변경 확인

## 애플리케이션 흐름

1. FastAPI와 Pydantic이 query login_id의 길이와 문자 형식을 검증한다.
2. 서비스가 로그인 아이디를 회원가입과 동일한 규칙으로 정규화한다.
3. 저장소가 users.normalized_login_id 고유 인덱스로 존재 여부만 조회한다.
4. 서비스가 요청 아이디와 available 불리언을 반환한다.
5. DB 오류는 롤백이 필요 없는 읽기 실패로 분류하고 공개 503 오류로 변환한다.

## 보안과 개인정보

- 소유권 검사: 공개 회원가입 보조 API이므로 기존 사용자 인증과 소유권 검사는 없음
- 민감 필드: 로그인 아이디 존재 여부. 응답은 계정 상태와 다른 사용자 정보를 제외함
- 로그 제외 항목: DB 오류 상세, 사용자 행과 요청 전체
- 열거 위험: 기능 목적상 아이디 존재 여부를 공개하되 응답을 불리언으로 제한하고 운영
  전 공개 API 속도 제한을 별도 보안 과제로 둠

## 로컬 어댑터

- 데이터베이스: 로컬 PostgreSQL 16과 SQLAlchemy 2 동기 세션
- 시간: 사용하지 않음
- 이메일: 사용하지 않음
- 스케줄러: 사용하지 않음

## 호환성

- OpenAPI 영향: 공개 GET 엔드포인트와 LoginIdAvailabilityResponse 스키마 추가
- 기존 데이터 영향: 없음
- 롤백: 라우트와 조회 서비스·저장소 코드를 제거하면 되며 DB 롤백은 없음
