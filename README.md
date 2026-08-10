# 알약꾹 백엔드

알약꾹 1차 MVP를 위한 로컬 우선 FastAPI 백엔드입니다. AWS, 운영 이메일
공급자와 AI 서비스 없이 Docker Compose만으로 API, PostgreSQL 개발·테스트 DB,
Mailpit과 알림 작업자 기반을 실행합니다.

## 빠른 시작

~~~bash
cp .env.example .env.local
make dev
make migrate
make seed
~~~

- Swagger: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/openapi.json
- Mailpit: http://localhost:8025
- 생존 확인: http://localhost:8000/api/v1/health/live
- 준비 확인: http://localhost:8000/api/v1/health/ready

전체 로컬 검증은 `make verify`로 실행합니다. 프로젝트 개발 규칙과 기능 단위
SDD 흐름은 `AGENTS.md`와 `docs/README.md`를 기준으로 합니다.
