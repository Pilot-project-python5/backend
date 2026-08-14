# F-3.10 설계

## API 계약

- 메서드와 경로: `GET /api/v1/medications`,
  `GET /api/v1/medications/{product_id}`
- 인증: access JWT와 서버 refresh session이 모두 유효한 로그인 사용자
- 요청: 목록은 page 기본 1, page_size 기본 20·최대 100. 상세는 UUID product_id
- 성공 응답: 목록은 제품·포장·분류·성분 요약의 페이지, 상세는 효능·용법·주의·보관·
  출처까지 포함한다.
- 오류 응답: 401 AUTH_REQUIRED, 404 MEDICATION_NOT_FOUND, 422 입력 형식,
  503 SERVICE_UNAVAILABLE
- 멱등성: 읽기 API이며 같은 DB·페이지 입력에 같은 정렬 결과를 반환한다.

## 데이터 설계

- 엔티티: Product 기존 행, MedicationDetail 신규 1:1 상세
- 관계와 카디널리티: Product 1 — 0..1 MedicationDetail. 제품 삭제 시 상세 CASCADE
- 제약 조건: product_id PK/FK, permit_code UNIQUE·형식, classification 허용값,
  필수 텍스트 trim 길이, source_url HTTPS·공백/fragment/userinfo 금지,
  updated_at >= created_at
- 인덱스: `(classification, product_id)` 관리·확장 조회 인덱스. 목록은 기존
  Product `(is_published, sort_order, sku)` 인덱스를 사용한다.
- 마이그레이션: 0017에서 medication_details 생성. 의약품 Product·상세는 시드가 적재
- 백필과 기존 데이터 영향: 기존 Product·CareItem은 변경하지 않는다. 기존에 상세 없는
  임의 MEDICATION 테스트 행은 API 대상에서 제외된다.
- 이력과 삭제: Product가 원본이며 삭제 시 상세만 CASCADE한다. 사용자의 CareItem은
  Product RESTRICT로 카탈로그 삭제를 막고 이력을 보존한다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: 논리 ERD에 예정된 medication_details 설명만 있고 실제 필드·제약 없음
- 변경 후 구조: products와 1:0..1 medication_details 관계 및 실제 필드·제약·인덱스
- 변경하지 않는 경우의 이유: 해당 없음
- ERD 검증 방법: 0017 upgrade/downgrade, inspector 스키마 테스트와 validate_erd.py

## 애플리케이션 흐름

1. 인증 의존성이 현재 사용자의 유효한 access·refresh session을 확인한다.
2. 서비스가 저장소에 게시 MEDICATION과 MedicationDetail의 결합 페이지·상세를 요청한다.
3. 저장소는 Product의 안정 정렬과 페이지 경계를 적용하고 DTO만 반환한다.
4. 서비스는 없음과 저장소 오류를 각각 404·503 공통 오류로 변환한다.
5. 라우터는 Decimal 포장 수량을 문자열로 직렬화하고 개인 정보 없이 응답한다.

## 보안과 개인정보

- 소유권 검사: 카탈로그 읽기라 행 소유권은 없지만 로그인 세션을 요구한다. 복용 등록
  소유권은 기존 F-3.1이 처리한다.
- 민감 필드: 사용자·처방·복용 기록을 읽지 않으며 사용자 ID를 응답하지 않는다.
- 로그 제외 항목: 사용자 식별자와 향후 처방·진단 정보는 로그에 남기지 않는다.

## 로컬 어댑터

- 데이터베이스: Docker PostgreSQL dev/test와 결정적 코드 시드
- 시간: 상세 source_reviewed_on과 결정적 created_at·updated_at만 저장
- 이메일: 없음
- 스케줄러: 없음

## 호환성

- OpenAPI 영향: 의약품 태그의 보호 목록·상세 스키마와 오류 응답 추가
- 기존 데이터 영향: 새 테이블·새 시드만 추가하며 기존 행을 수정·삭제하지 않는다.
- 롤백: 0017 downgrade는 medication_details만 제거한다. 시드 Product는 마이그레이션
  소유가 아니므로 운영 롤백 시 별도 승인 없이는 자동 삭제하지 않는다.
