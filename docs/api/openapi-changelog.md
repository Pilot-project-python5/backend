# OpenAPI 변경 기록

기능 PR에서 호환성에 영향을 주는 API 변경을 기록한다.

| 날짜 | 기능 ID | 변경 | 호환성 | 마이그레이션 참고 사항 |
| --- | --- | --- | --- | --- |
| 2026-08-14 | F-3.8 | GET /api/v1/care/items 항목에 inventory_status 추가 | 기존 요청을 유지하는 additive 응답 확장 | notifications 20260814_0019 필요, 기존 CareItem 변경·알림 백필 없음 |
| 2026-08-14 | F-3.11 | POST·GET care items에 nullable 유통기한·D-day·상태를 추가하고 PUT 구매분별 유통기한 갱신 API 추가 | 기존 요청은 선택 필드, 기존 응답은 additive 확장이고 신규 PUT은 멱등 보호 API | care_items.expiration_date nullable·조회 인덱스 20260814_0018 필요, 기존 행은 null 유지 |
| 2026-08-14 | F-3.10 | GET /api/v1/medications 보호 목록·상세와 의약품 복약정보·출처 계약 추가 | 신규 보호 읽기 API이며 기존 Product·CareItem 계약은 유지 | medication_details 20260814_0017과 로컬 실사용 금지 의약품 시드 필요 |
| 2026-08-14 | F-3.7 | POST·GET /api/v1/care/items 응답에 expected_depletion_date, GET 항목에 days_until_depletion 추가 | 기존 요청을 유지하는 additive 응답 확장 | care_items 예상 소진일 백필·CHECK·NOT NULL·인덱스 20260814_0016 필요 |
| 2026-08-14 | F-3.6 | GET /api/v1/care/nutrient-status 나이·성별 기준량 비교 계약 추가 | 신규 보호 읽기 API이며 기존 care API 계약은 유지 | nutrient_reference_versions·values 20260814_0015와 KDRI CSV 시드 필요 |
| 2026-08-13 | F-3.5 | GET /api/v1/care/daily-intake 성분별 일일 예정 섭취량 계약 추가 | 신규 보호 읽기 API이며 기존 care API 계약은 유지 | 기존 care_items·care_nutrient_snapshots·nutrients 읽기 전용, 마이그레이션 없음 |
| 2026-08-13 | F-3.4 | GET /api/v1/care/items 페이지 목록과 DELETE /api/v1/care/items/{care_item_id} 소프트 삭제 계약 추가 | 신규 보호 API이며 기존 POST 계약은 유지 | care_items.deleted_at·시간 CHECK·활성 부분 인덱스 20260813_0014 추가, 기존 행은 활성 유지 |
| 2026-08-12 | F-3.3 | POST /api/v1/care/items 201 응답에 서버 결정 quantity_unit 추가 | 기존 요청·응답 필드를 유지하는 additive 응답 확장 | care_items.quantity_unit 마이그레이션 20260812_0013과 기존 행 Product 단위 백필 필요 |
| 2026-08-12 | F-3.1 | POST /api/v1/care/items 보호 생성 API와 201/401/404/422/503 계약 추가 | 신규 API로 기존 호출과 호환, 응답에 사용자 ID를 노출하지 않음 | care_items 마이그레이션 20260812_0011 필요, 사용자 데이터 시드 없음 |
| 2026-08-12 | F-2.4.2 | GET /api/v1/curation/products/{product_id}/purchase 307·404·422·503 계약과 보안 헤더 추가 | 신규 공개 리다이렉트 API로 기존 응답과 호환 | purchase_links 마이그레이션 20260812_0010과 HTTPS 개발 시드 필요 |
| 2026-08-12 | F-2.4.1 | 제품 상세 200 응답에 expert_comments 배열 추가 | 기존 상세 필드를 유지하는 additive 응답 확장, 목록은 변경 없음 | expert_comments 마이그레이션 20260812_0009과 코멘트 시드 필요 |
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
