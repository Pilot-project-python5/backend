# 마이케어 API 계약

## F-3.1 복용 제품 등록

- `POST /api/v1/care/items`
- HttpOnly access JWT 쿠키가 필요한 보호 API다.
- 요청에서 `user_id`를 받지 않고 인증된 현재 사용자에게만 새 항목을 귀속한다.
- `product_id`는 DB 제품 카탈로그에 존재해야 한다. 영양제·의약품 모두 등록할 수
  있으며 게시 여부는 등록 조건이 아니다.
- 구매일은 서버 기준 오늘 이후일 수 없고 복용 시작일은 구매일보다 빠를 수 없다.
  미래 복용 시작일은 예약 등록으로 허용한다.
- 총수량과 1회 복용량은 0 초과, 최대 `999999999.999`, 소수점 셋째 자리까지다.
- 1회 복용량은 총수량 이하이며 일일 복용 횟수는 1~24다.
- 같은 제품과 같은 값을 반복 등록해도 매번 별도 이력과 UUID를 생성한다.
- 수량은 Decimal 정밀도를 보존하는 JSON 문자열로 응답한다.
- 성공 응답은 201이며 `Cache-Control: no-store`를 포함한다.
- 인증 실패는 401 `AUTH_REQUIRED`, 카탈로그 제품 없음은 404
  `PRODUCT_NOT_FOUND`, 값 검증 실패는 422 `VALIDATION_FAILED`, DB 실패는 503
  `SERVICE_UNAVAILABLE`다.

~~~json
{
  "product_id": "22000000-0000-4000-8000-000000000001",
  "purchase_date": "2026-08-10",
  "intake_start_date": "2026-08-12",
  "total_quantity": "60",
  "dose_per_intake": "1",
  "intakes_per_day": 2
}
~~~

~~~json
{
  "id": "31000000-0000-4000-8000-000000000001",
  "product_id": "22000000-0000-4000-8000-000000000001",
  "purchase_date": "2026-08-10",
  "intake_start_date": "2026-08-12",
  "total_quantity": "60",
  "quantity_unit": "CAPSULE",
  "dose_per_intake": "1",
  "intakes_per_day": 2,
  "created_at": "2026-08-12T09:00:00Z"
}
~~~

## F-3.2 영양제 성분 스냅샷

- API 경로·요청·응답·상태 코드는 F-3.1과 동일하다.
- 등록 대상이 `SUPPLEMENT`이면 등록 시점의 활성 영양성분 ID·이름·단위당
  함량·단위를 새 복용 항목 아래 스냅샷으로 저장한다.
- 복용 항목과 모든 스냅샷은 한 트랜잭션으로 저장하며, 일부라도 실패하면 전체를
  롤백하고 기존 503 `SERVICE_UNAVAILABLE` 계약을 적용한다.
- `MEDICATION`이거나 활성 성분이 없는 영양제는 복용 항목만 만들고 정상 201을
  반환한다.
- 스냅샷은 내부 계산용 데이터이므로 요청·응답에 스냅샷 ID나 사용자 ID를 노출하지
  않는다. 등록 후 카탈로그 변경도 기존 스냅샷에 반영하지 않는다.

## F-3.3 구매 총수량과 단위

- `total_quantity`는 해당 CareItem의 최초 구매 총량이며 실제 복용으로 자동 차감되는
  현재 잔량이 아니다.
- 요청에 수량 단위를 받지 않고 등록 시 Product의 `unit_form`을 `quantity_unit`으로
  복사한다. 허용값은 TABLET·CAPSULE·SCOOP·PACKET이다.
- 201 응답에 `quantity_unit`을 필수로 제공한다. 클라이언트가 같은 이름의 추가 값을
  보내도 서버 카탈로그 단위를 덮어쓸 수 없다.
- 제품 단위가 바뀌어도 이미 등록한 CareItem의 quantity_unit은 바뀌지 않는다.
- 같은 제품을 소진 전에 다시 등록해도 기존 수량을 합산·수정하지 않고 독립 CareItem을
  생성한다.

## F-3.4 복용 제품 조회·삭제

### 활성 목록 조회

- `GET /api/v1/care/items?page=1&page_size=20`
- HttpOnly access JWT 쿠키가 필요한 보호 API이며 현재 사용자 소유의 삭제되지 않은
  CareItem만 반환한다.
- page는 1 이상, page_size는 기본 20이고 1~100이다. 응답은 items·page·page_size·
  total·has_next를 제공하며 범위를 넘는 페이지도 200과 빈 items를 반환한다.
- `created_at DESC, id DESC` 최신 등록순으로 안정 정렬한다. 같은 제품 재구매분은
  합산하지 않고 독립 항목으로 반환한다.
- 각 항목은 CareItem의 ID·제품 ID·구매일·복용 시작일·총수량·단위·회당 복용량·하루
  횟수·등록 시각과 현재 Product의 유형·브랜드·이름·이미지를 제공한다.
- 제품이 비게시 상태로 바뀌어도 이미 등록한 활성 항목은 숨기지 않는다. 제품 표시
  정보는 현재 카탈로그 값이고 구매 시점 스냅샷은 아니다.
- total_quantity와 dose_per_intake는 불필요한 끝자리 0을 제거한 Decimal 문자열이다.
- 사용자 ID, deleted_at과 영양성분 스냅샷은 응답하지 않는다.
- 성공은 200과 `Cache-Control: no-store`, 인증 실패는 401 `AUTH_REQUIRED`, 잘못된
  페이지 값은 422 `VALIDATION_FAILED`, DB 실패는 503 `SERVICE_UNAVAILABLE`다.

~~~json
{
  "items": [
    {
      "id": "31000000-0000-4000-8000-000000000001",
      "product_id": "22000000-0000-4000-8000-000000000001",
      "product_type": "SUPPLEMENT",
      "brand": "Life Extension",
      "name": "라이프익스텐션 투퍼데이",
      "image_url": "/static/products/life-extension-two-per-day.svg",
      "purchase_date": "2026-08-10",
      "intake_start_date": "2026-08-12",
      "total_quantity": "60",
      "quantity_unit": "CAPSULE",
      "dose_per_intake": "1",
      "intakes_per_day": 2,
      "created_at": "2026-08-13T09:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1,
  "has_next": false
}
~~~

### 이력 보존형 삭제

- `DELETE /api/v1/care/items/{care_item_id}`
- 현재 사용자의 활성 CareItem만 삭제할 수 있고 성공은 본문 없는 204와
  `Cache-Control: no-store`다.
- 삭제는 서버 현재 시각을 deleted_at과 updated_at에 기록하는 소프트 삭제다.
  CareItem과 F-3.2 성분 스냅샷 행은 보존하고 이후 활성 목록에서 제외한다.
- 다른 사용자 소유, 미존재와 이미 삭제된 항목은 존재 여부를 구분하지 않고 404
  `CARE_ITEM_NOT_FOUND`로 통일한다.
- 인증 실패는 401 `AUTH_REQUIRED`, 잘못된 UUID는 422 `VALIDATION_FAILED`, DB 실패는
  503 `SERVICE_UNAVAILABLE`다.
- 삭제 복원·휴지통·보존 기간 만료 후 물리 정리는 F-3.4 범위에 포함하지 않는다.

### 후속 기능 경계

- 예상 소진일·상태·알림은 F-3.7 이후에 추가한다.
- 유통기한은 F-3.11에서 추가하며 F-3.1 요청에는 포함하지 않는다.

## F-3.5 일일 예정 섭취량

- `GET /api/v1/care/daily-intake`
- HttpOnly access JWT 쿠키가 필요한 보호 API이며 현재 사용자 소유의 삭제되지 않은
  영양제 CareItem과 등록 시점 성분 스냅샷만 계산한다.
- 각 스냅샷의 `amount_per_unit × dose_per_intake × intakes_per_day`를 계산하고 같은
  nutrient_id를 Nutrient의 canonical_unit으로 환산해 합산한다.
- G·MG·MCG는 정확한 10진 비율로 상호 변환한다. IU는 IU끼리만 합산하고 질량 단위와
  서로 변환하지 않는다.
- 미래 intake_start_date를 포함한 활성 복용 계획 전체의 하루 총량이다. 실제 복용
  여부·총수량·소진 상태·현재 잔량은 사용하지 않는다.
- 응답 항목은 nutrient_id·nutrient_code·nutrient_name·daily_amount·unit이며
  nutrient_code·nutrient_id 순으로 정렬한다. daily_amount는 Decimal 정밀도를 보존하고
  불필요한 후행 0을 제거한 문자열이다.
- 성분 대상이 없으면 200과 빈 nutrients 배열을 반환한다.
- 성공은 200과 `Cache-Control: no-store`, 인증 실패는 401 `AUTH_REQUIRED`, DB 장애나
  변환 불가능한 저장 단위는 503 `SERVICE_UNAVAILABLE`다.
- 계산 결과를 저장하지 않으며 신규 마이그레이션과 시드 변경이 없다.

~~~json
{
  "nutrients": [
    {
      "nutrient_id": "23000000-0000-4000-8000-000000000001",
      "nutrient_code": "VITAMIN_C",
      "nutrient_name": "비타민 C",
      "daily_amount": "470",
      "unit": "MG"
    }
  ]
}
~~~

### 후속 기능 경계

- 나이·성별 기준량과 달성 비율은 F-3.6에서 이 결과를 사용해 확장한다.
- 예상 소진일·D-day·잔량·재구매 상태는 F-3.7 이후에 계산한다.

## F-3.6 영양성분 현황

- `GET /api/v1/care/nutrient-status`
- 현재 사용자의 삭제되지 않은 영양제 계획을 F-3.5와 동일하게 계산하고, 서버 시각을
  `APP_TIMEZONE`으로 변환한 날짜의 만 나이·성별에 맞는 2025 한국인 영양소 섭취기준과
  비교한다. RNI를 우선하고 RNI가 없는 항목은 AI를 사용한다.
- 비율은 보충제 계획의 일일 예정량이 총 식이 기준량에서 차지하는 값이며 음식 섭취나
  임상적 결핍·과잉 판정이 아니다. `현재량 / 기준량 × 100`을 소수 첫째 자리로
  반올림하고 100%를 초과해도 자르지 않는다.
- 일반 OMEGA_3처럼 공식 기준 항목과 동일성을 보장할 수 없는 성분은 현재량과
  `reference_available=false`를 반환하고 기준량·유형·비율은 null이다.
- 응답은 계산 기준일·만 나이·성별·기준 버전·출처와 성분 배열을 제공한다. 성분은
  nutrient_code·nutrient_id 순으로 정렬되며 Decimal 값은 후행 0을 제거한 문자열이다.
- 성공은 200과 `Cache-Control: no-store`, 인증 실패는 401 `AUTH_REQUIRED`, 기준 버전
  없음·DB 장애·단위 불일치는 부분 결과 없는 503 `SERVICE_UNAVAILABLE`다.

~~~json
{
  "as_of_date": "2026-08-14",
  "age": 36,
  "gender": "FEMALE",
  "reference_version": "KDRI-2025-20260316",
  "reference_source_name": "보건복지부·한국영양학회 2025 한국인 영양소 섭취기준",
  "reference_source_url": "https://www.kns.or.kr/fileroom/FileRoom_view.asp?BoardID=Kdr&idx=167",
  "nutrients": [
    {
      "nutrient_id": "23000000-0000-4000-8000-000000000001",
      "nutrient_code": "VITAMIN_C",
      "nutrient_name": "비타민 C",
      "daily_amount": "150",
      "unit": "MG",
      "reference_available": true,
      "reference_amount": "100",
      "reference_type": "RNI",
      "achievement_rate_percent": "150"
    }
  ]
}
~~~
