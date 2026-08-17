# 의약품 API 계약

## 공통 경계

- 모든 경로는 access JWT와 서버 refresh session이 유효한 로그인 사용자만 호출한다.
- 사용자는 의약품을 직접 생성·수정하지 않고 DB가 관리하는 시드 카탈로그만 읽는다.
- 게시된 `MEDICATION` Product와 MedicationDetail이 모두 있는 행만 노출한다.
- 응답에는 `Cache-Control: no-store`를 적용한다.
- 1차 로컬 시드는 API·UI 검증용 실사용 금지 예시다. 운영 전 품목별 공식 허가정보로
  교체·검토해야 하며 이 API는 개인화된 처방이나 복약 판단을 제공하지 않는다.

## F-3.10 의약품 목록

- `GET /api/v1/medications`
- page는 1부터, page_size는 기본 20·허용 범위 1~100이다.
- Product `sort_order`, `sku` 오름차순으로 안정 정렬한다.
- 목록 항목은 제품·포장, 품목 추적 코드, OTC/PRESCRIPTION 분류와 유효성분 요약을
  반환한다. 포장 수량은 Decimal 정밀도를 보존하는 문자열이다.
- 대상이 없거나 범위 밖 페이지면 200과 빈 items를 반환한다.
- 인증 없음은 401, 입력 오류는 422, DB 실패는 503이다.

~~~json
{
  "items": [
    {
      "id": "22000000-0000-4000-8000-000000000010",
      "sku": "LOCAL-MED-001",
      "brand": "영양꾹 로컬 테스트",
      "name": "복용 관리 예시 의약품 A",
      "image_url": "/static/products/local-medication-a.svg",
      "package": {"unit_form": "TABLET", "units_per_package": "20"},
      "permit_code": "LOCAL-MED-001",
      "classification": "OTC",
      "active_ingredients": "개발용 예시 성분 A — 실사용 금지"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 2,
  "has_next": false
}
~~~

## F-3.10 의약품 상세

- `GET /api/v1/medications/{product_id}`
- 목록 공통 필드에 효능, 용법·용량, 주의사항, 보관법과 출처명·URL·검토일을 추가한다.
- 없는 UUID, 영양제, 미게시 의약품과 상세 없는 의약품은 모두 404
  `MEDICATION_NOT_FOUND`로 통일해 내부 게시 상태를 노출하지 않는다.
- UUID 형식 오류는 422, DB 실패는 503이다.

~~~json
{
  "id": "22000000-0000-4000-8000-000000000010",
  "sku": "LOCAL-MED-001",
  "brand": "영양꾹 로컬 테스트",
  "name": "복용 관리 예시 의약품 A",
  "image_url": "/static/products/local-medication-a.svg",
  "package": {"unit_form": "TABLET", "units_per_package": "20"},
  "permit_code": "LOCAL-MED-001",
  "classification": "OTC",
  "active_ingredients": "개발용 예시 성분 A — 실사용 금지",
  "efficacy": "실제 의약품 정보가 아닌 로컬 MVP API·UI 검증용 예시 데이터입니다.",
  "dosage_instructions": "실제 복용에 사용하지 말고 화면 흐름 검증에만 사용하세요.",
  "precautions": "운영 전 품목별 공식 허가정보 검토와 승인 데이터 교체가 필요합니다.",
  "storage_instructions": "로컬 테스트 데이터이며 실제 보관 지침이 아닙니다.",
  "source": {
    "name": "영양꾹 로컬 테스트 시드(실사용 금지)",
    "url": "https://example.invalid/allyakkkuk/medications/local-med-001",
    "reviewed_on": "2026-08-14"
  }
}
~~~

## 마이케어 연결

- 목록·상세의 id를 기존 `POST /api/v1/care/items`의 product_id로 사용한다.
- 의약품도 구매일·복용 시작일·수량·복용 계획·예상 소진일을 관리한다.
- 의약품은 `GET /api/v1/care/daily-intake`와 nutrient-status 영양소 합계에서 제외한다.
- 유통기한·만료 상태와 알림은 F-3.11 이후 계약으로 추가한다.
