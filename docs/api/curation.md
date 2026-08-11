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
