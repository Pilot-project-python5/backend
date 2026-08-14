# 로컬 개발 환경

저장소는 FastAPI 애플리케이션과 로컬 실행 하네스를 제공한다. Docker Compose가
Python 3.12, PostgreSQL 개발·테스트 DB, Mailpit과 작업자를 같은 방식으로 실행한다.

## 사전 준비

- Compose를 지원하는 Docker
- Make
- Git

Python과 PostgreSQL은 가능한 한 컨테이너로 고정해 호스트 차이를 줄인다.

## 실행 흐름

1. 저장소를 복제한다.
2. .env.example을 .env.local로 복사한다.
3. make dev를 실행한다.
4. 마이그레이션과 개발 시드를 적용한다.
5. Swagger에서 API를 확인한다.
6. 로컬 SMTP 수신함에서 인증·알림 이메일을 확인한다.

~~~bash
cp .env.example .env.local
make dev
make migrate
make seed
make verify
~~~

## 로컬 주소

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/openapi.json
- Mailpit: http://localhost:8025
- PostgreSQL 개발 DB: localhost:5432
- PostgreSQL 테스트 DB: localhost:5433

`make dev`는 데이터 볼륨을 유지한 채 서비스를 시작한다. `make stop`도 개발 DB와
메일 데이터를 삭제하지 않는다. 테스트 DB는 tmpfs를 사용해 개발 DB와 공유하지 않는다.

## 필수 로컬 서비스

- api
- postgres-dev
- postgres-test 또는 테스트용 격리 DB
- mail
- worker

worker는 `WORKER_POLL_SECONDS` 간격으로 재구매·유통기한 논리 알림 작업을 실행한다.
APP_TIMEZONE 기준 오전 9시 전에는 쓰지 않고, 오전 9시 이후 예상 소진일 또는
유통기한이 당일 D-5·D-3·D-1인 활성 항목만 PostgreSQL 고유 제약으로 멱등 생성한다.
작업 실패는 기록한 뒤 다음 poll에서 다시 시도하며 과거 날짜 알림을 소급 생성하지
않는다. 생성 결과는 Swagger의 `/api/v1/notifications`에서 로그인 사용자 기준으로
조회·읽음 처리할 수 있다.

## 제약

- AWS 자격증명을 요구하지 않는다.
- 인터넷이 끊겨도 이미 빌드된 환경에서 테스트가 실행돼야 한다.
- 실제 이메일을 발송하지 않는다.
- 실제 개인정보와 건강정보를 입력하지 않는다.
- EMAIL_VERIFICATION_SECRET 기본값은 로컬 전용이다. 공유·운영 환경에서는 32자
  이상의 별도 비밀값으로 교체하고 저장소에 커밋하지 않는다.
- AUTH_TOKEN_SECRET 기본값도 로컬 전용이다. 운영에서는 이메일 인증 비밀값과 분리한
  32자 이상의 값을 비밀 저장소에서 주입하고, 기존 토큰 무효화 영향을 고려해 회전한다.
- AUTH_COOKIE_SECURE는 로컬 HTTP에서 false지만 HTTPS 배포 전 반드시 true로 바꾼다.

Docker가 설치되지 않은 환경에서는 컨테이너 명령을 통과한 것으로 간주하지 않는다.
Python 단위·계약 검사는 격리 환경에서 별도로 실행할 수 있지만 최종 완료 기준은
PostgreSQL을 포함한 `make verify`다.
