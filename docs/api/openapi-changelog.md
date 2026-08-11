# OpenAPI 변경 기록

기능 PR에서 호환성에 영향을 주는 API 변경을 기록한다.

| 날짜 | 기능 ID | 변경 | 호환성 | 마이그레이션 참고 사항 |
| --- | --- | --- | --- | --- |
| 2026-08-12 | F-2.4 | GET /api/v1/curation/products/{product_id} 공개 상세와 패키지·성분·200/404/422/503 계약 추가 | 신규 공개 읽기 API로 F-2.3 목록과 기존 호출에 호환 | nutrients·product_nutrients 마이그레이션 20260812_0008과 성분 시드 필요 |
| 2026-08-12 | F-2.3 | GET /api/v1/curation/products 공개 필터·페이지 목록과 200/404/422/503 계약 추가 | 신규 공개 읽기 API와 정적 이미지 경로로 기존 호출과 호환 | products·product_category_mappings 마이그레이션 20260812_0007과 제품 시드 필요 |
| 2026-08-12 | F-2.2 | GET /api/v1/curation/categories 공개 목록과 200/503 계약 추가 | 신규 공개 읽기 API로 기존 호출과 호환 | product_categories 마이그레이션 20260812_0006과 기준 시드 필요 |
| 2026-08-11 | F-1.4 | GET /api/v1/auth/me, AccessCookieAuth와 200/401/503 계약 추가 | 신규 API와 재사용 인증 의존성으로 기존 호출과 호환 | users·health_profiles·refresh_sessions 읽기 전용, 마이그레이션 없음 |
| 2026-08-11 | F-1.3 | POST /api/v1/auth/refresh·logout, 회전·쿠키 삭제와 200/204/401/503 계약 추가 | 신규 API이며 F-1.2 로컬 refresh 원문 형식은 재로그인 필요 | 기존 refresh_sessions 상태 컬럼 재사용, 마이그레이션 없음 |
| 2026-08-11 | F-1.2 | POST /api/v1/auth/login, HttpOnly 세션 쿠키와 200/401/403/422/503 계약 추가 | 신규 API로 기존 호출과 호환 | refresh_sessions 마이그레이션 20260811_0005 필요 |
| 2026-08-11 | F-1.1.3 | POST 이메일 인증 발급·재전송·확인 API와 400/404/409/410/422/429/503 계약 추가 | 신규 API로 기존 호출과 호환 | email_verifications 마이그레이션 20260811_0003~0004 필요 |
| 2026-08-11 | F-1.1.2 | POST /api/v1/auth/signup/validation과 200/422/503 계약 추가 | 신규 API로 기존 호출과 호환 | 기존 users 고유 인덱스 재사용, 마이그레이션 없음 |
| 2026-08-10 | F-1.1.1 | GET /api/v1/auth/login-id/availability와 200/422/503 계약 추가 | 신규 API로 기존 호출과 호환 | 기존 users 고유 인덱스 재사용, 마이그레이션 없음 |
| 2026-08-10 | F-1.1 | POST /api/v1/auth/signup과 요청·응답·409/422/503 오류 계약 추가 | 신규 API로 기존 호출과 호환 | users·health_profiles 마이그레이션 20260810_0002 필요 |
| 2026-08-10 | 하네스 | 초기 API 규칙만 작성 | 실행 API 없음 | 백엔드 부트스트랩 대기 |
