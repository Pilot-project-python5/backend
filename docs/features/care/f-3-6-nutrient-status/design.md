# F-3.6 설계

## API 계약

- 메서드와 경로: `GET /api/v1/care/nutrient-status`
- 인증: HttpOnly access JWT와 서버 refresh session을 함께 검증
- 요청: 경로·쿼리·본문 없음
- 성공 응답: 200, no-store. `as_of_date`, `age`, `gender`, `reference_version`,
  `reference_source_name`, `reference_source_url`, `nutrients`를 제공한다. 각 성분은
  nutrient_id·code·name·daily_amount·unit·reference_available·reference_amount·
  reference_type·achievement_rate_percent를 가진다.
- 오류 응답: 401 AUTH_REQUIRED, 503 SERVICE_UNAVAILABLE
- 멱등성: 읽기 API이며 같은 사용자·DB·기준일에는 같은 정렬과 값을 반환한다.

## 데이터 설계

- 엔티티: NutrientReferenceVersion, NutrientReferenceValue
- 관계와 카디널리티: NutrientReferenceVersion 1:N NutrientReferenceValue,
  Nutrient 1:N NutrientReferenceValue
- 제약 조건: version·checksum 고유, reference_amount 양수, gender MALE/FEMALE,
  reference_type RNI/AI, age_min 0 이상·age_max >= age_min, unit MG/G/MCG/IU,
  정확한 구간 중복 UNIQUE. 겹치는 구간과 CSV 메타데이터 불일치는 적재기에서 거부한다.
- 인덱스: `(version_id, nutrient_id, gender, age_min, age_max)` 조회 인덱스와 정확한
  구간 UNIQUE
- 마이그레이션: 0015에서 두 테이블·FK·CHECK·UNIQUE·인덱스를 추가한다.
- 백필과 기존 데이터 영향: 기존 사용자·카탈로그·CareItem은 바꾸지 않는다. 기준값은
  마이그레이션이 아니라 멱등 CSV 시드로 적재한다.
- 이력과 삭제: 기준 버전·값은 이력 데이터이므로 새 버전 추가를 우선하고 참조 중
  Nutrient는 RESTRICT한다. 시드가 관리하는 같은 버전 값은 검증 후 원자적으로 교체한다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: 두 엔티티가 논리 ERD에만 있고 실제 모델·마이그레이션은 없음
- 변경 후 구조: 실제 필드에 published_on·reference_type을 포함하고 제약·인덱스·
  CSV 원자 적재 및 보존 정책을 설명한다.
- 변경하지 않는 경우의 이유: 해당 없음
- ERD 검증 방법: ERD 검증기, ORM·0015·PostgreSQL 스키마 통합 테스트 비교

## 애플리케이션 흐름

1. 인증 의존성이 현재 사용자 ID와 프로필을 검증한다.
2. 서비스가 주입한 Clock과 APP_TIMEZONE으로 계산 기준일·만 나이를 만든다.
3. 저장소가 F-3.5와 같은 활성 영양제 성분 원천과 설정된 기준 버전 메타데이터·해당
   성별·나이 구간을 조회한다.
4. 서비스가 일일 예정량을 canonical_unit으로 합산하고 기준 단위 일치를 확인한다.
5. 기준이 있으면 Decimal 비율을 계산하고, 없으면 명시적 기준 없음 상태를 만든다.
6. 라우터가 결정적으로 정렬된 no-store 응답으로 변환한다.

## 보안과 개인정보

- 소유권 검사: 저장소 조건에 현재 user_id와 CareItem.deleted_at IS NULL을 적용한다.
- 민감 필드: 생년월일 원문은 응답하지 않고 계산한 만 나이만 제공한다.
- 로그 제외 항목: 사용자 ID, 생년월일, 성별, 복용 성분량과 인증 쿠키

## 로컬 어댑터

- 데이터베이스: 로컬 PostgreSQL과 SQLAlchemy 저장소
- 시간: SystemClock/FakeClock과 APP_TIMEZONE
- 이메일: 해당 없음
- 스케줄러: 해당 없음

## 호환성

- OpenAPI 영향: 보호 GET 경로와 새 응답 스키마를 additive하게 추가한다.
- 기존 데이터 영향: 기존 행·API를 변경하지 않는다. 시드 이후 기준 테이블만 추가된다.
- 롤백: 앱을 되돌리고 0015를 downgrade하면 기준 테이블만 제거되며 기존 데이터는
  유지된다. CSV 원본은 앱 롤백과 함께 제거한다.
