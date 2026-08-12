# 전문가 큐레이션 API 계약

## F-2.2 제품 카테고리

- GET /api/v1/curation/categories
- 인증 없이 호출하는 공개 읽기 API다.
- 요청 본문·쿼리·페이지네이션은 없다.
- 응답 항목은 이후 제품 필터에 사용할 slug와 화면 표시용 name만 포함한다.
- `all`·`전체`는 DB에 저장하지 않는 필터 미적용 가상 항목이며 항상 첫 번째다.
- 실제 카테고리는 is_active=true만 sort_order, slug 오름차순으로 제공한다.
- 활성 카테고리가 없어도 all 항목 하나를 200으로 반환한다.
- DB 실패는 503 SERVICE_UNAVAILABLE로 반환한다.

~~~json
{
  "items": [
    {"slug": "all", "name": "전체"},
    {"slug": "vitamin", "name": "비타민"},
    {"slug": "protein", "name": "단백질"},
    {"slug": "omega-3", "name": "오메가3"}
  ]
}
~~~

## F-2.3 추천 제품 목록

- GET /api/v1/curation/products
- 인증 없이 호출하는 공개 읽기 API다.
- category 기본값은 all이며 실제 값은 F-2.2의 활성 slug를 사용한다.
- 유효하지만 없거나 비활성인 category는 404 CATEGORY_NOT_FOUND, 형식 오류는
  422 VALIDATION_FAILED다.
- page는 1부터 시작하고 기본값 1이다. page_size는 기본 20, 허용 범위 1~100이다.
- 게시 제품이면서 활성 카테고리가 하나 이상 연결된 제품만 제공한다.
- sort_order, sku 오름차순이며 다중 카테고리 제품도 한 번만 반환한다.
- 목록 항목은 카드 미리보기 필드만 반환하고 패키지·성분 상세는 F-2.4에서 제공한다.
- display_price는 로컬 시드가 관리하는 원화 참고 가격이며 currency는 KRW 고정이다.
- 로컬 image_url은 백엔드의 /static/products SVG를 가리키며 2차에는 같은 필드에 CDN
  URL을 사용할 수 있다.
- DB 실패는 503 SERVICE_UNAVAILABLE로 반환한다.

~~~json
{
  "items": [
    {
      "id": "22000000-0000-4000-8000-000000000001",
      "sku": "LIFE-TWO-PER-DAY",
      "product_type": "SUPPLEMENT",
      "brand": "Life Extension",
      "name": "라이프익스텐션 투퍼데이",
      "image_url": "/static/products/life-extension-two-per-day.svg",
      "display_price": 28400,
      "currency": "KRW",
      "category_slugs": ["vitamin"]
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 3,
  "has_next": false
}
~~~

## F-2.4 추천 제품 상세

- GET /api/v1/curation/products/{product_id}
- 인증 없이 호출하는 공개 읽기 API다.
- product_id는 UUID이며 형식 오류는 422 VALIDATION_FAILED다.
- 게시 상태이고 활성 카테고리 연결이 하나 이상인 제품만 상세에 노출한다.
- 미존재·비게시·활성 카테고리 연결 없음은 모두 404 PRODUCT_NOT_FOUND다.
- F-2.3 목록 공통 필드에 package와 nutrients를 추가한다.
- category_slugs는 활성 카테고리만 sort_order·slug 순으로 제공한다.
- nutrients는 활성 성분만 제품별 sort_order·code 순으로 제공하며 없으면 빈 배열이다.
- units_per_package와 amount_per_unit은 Decimal 정밀도를 보존하는 JSON 문자열이다.
- 1차 성분 단위는 MG, G, MCG, IU다.
- DB 실패는 503 SERVICE_UNAVAILABLE로 반환한다.
- 전문가 코멘트와 구매 링크는 F-2.4.1·F-2.4.2에서 응답을 독립 확장한다.

~~~json
{
  "id": "22000000-0000-4000-8000-000000000001",
  "sku": "LIFE-TWO-PER-DAY",
  "product_type": "SUPPLEMENT",
  "brand": "Life Extension",
  "name": "라이프익스텐션 투퍼데이",
  "image_url": "/static/products/life-extension-two-per-day.svg",
  "display_price": 28400,
  "currency": "KRW",
  "category_slugs": ["vitamin"],
  "package": {
    "unit_form": "TABLET",
    "units_per_package": "120"
  },
  "nutrients": [
    {
      "code": "VITAMIN_C",
      "name": "비타민 C",
      "amount_per_unit": "235",
      "unit": "MG"
    }
  ],
  "expert_comments": []
}
~~~

## F-2.4.1 전문가 코멘트

- 기존 GET /api/v1/curation/products/{product_id}의 200 응답에
  expert_comments 배열을 추가한다.
- F-2.3 목록에는 코멘트를 추가하지 않고 UI 토글을 열 때 상세를 조회한다.
- 활성 코멘트만 sort_order, id 오름차순으로 제공하며 없으면 빈 배열이다.
- 각 항목은 id, author_label, content를 포함한다.
- content는 렌더링 형식을 부여하지 않은 일반 JSON 문자열이다.
- 공개 제품 조건과 404 PRODUCT_NOT_FOUND, 422 VALIDATION_FAILED,
  503 SERVICE_UNAVAILABLE은 F-2.4 계약을 유지한다.

~~~json
{
  "expert_comments": [
    {
      "id": "24000000-0000-4000-8000-000000000001",
      "author_label": "MJ's COMMENT",
      "content": "개발용 전문가 추천 코멘트"
    }
  ]
}
~~~
