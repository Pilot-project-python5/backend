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
    {"slug": "multivitamin", "name": "종합비타민"},
    {"slug": "vitamin-b", "name": "비타민B군"},
    {"slug": "vitamin-c", "name": "비타민C"},
    {"slug": "vitamin-d", "name": "비타민D"},
    {"slug": "protein-supplement", "name": "단백질 보충제"},
    {"slug": "pre-workout", "name": "부스터"},
    {"slug": "creatine", "name": "크레아틴"},
    {"slug": "probiotics", "name": "유산균"},
    {"slug": "omega-3", "name": "오메가3"},
    {"slug": "magnesium", "name": "마그네슘"},
    {"slug": "melatonin", "name": "멜라토닌"}
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
- display_price는 원화 표시 필드이며 민재코치 원본에 가격이 없는 현재 시드는 0을
  가격 미제공 값으로 사용한다. currency는 KRW 고정이다.
- 로컬 image_url은 백엔드의 제품별 `/static/products/*.webp`를 가리키며 2차에는
  같은 필드에 CDN URL을 사용할 수 있다.
- DB 실패는 503 SERVICE_UNAVAILABLE로 반환한다.

~~~json
{
  "items": [
    {
      "id": "22000000-0000-4000-8000-000000000101",
      "sku": "KORYO-EUNDAN-MULTIVITAMIN-ALL-IN-ONE",
      "product_type": "SUPPLEMENT",
      "brand": "고려은단",
      "name": "고려은단 멀티비타민 올인원",
      "image_url": "/static/products/koryo-eundan-multivitamin-all-in-one.webp",
      "display_price": 0,
      "currency": "KRW",
      "category_slugs": ["multivitamin"]
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 32,
  "has_next": true
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
- 전문가 코멘트는 F-2.4.1에서 상세 응답을 확장하고 구매 링크는 F-2.4.2의 별도
  리다이렉트 경로로 제공한다.

~~~json
{
  "id": "22000000-0000-4000-8000-000000000101",
  "sku": "KORYO-EUNDAN-MULTIVITAMIN-ALL-IN-ONE",
  "product_type": "SUPPLEMENT",
  "brand": "고려은단",
  "name": "고려은단 멀티비타민 올인원",
  "image_url": "/static/products/koryo-eundan-multivitamin-all-in-one.webp",
  "display_price": 0,
  "currency": "KRW",
  "category_slugs": ["multivitamin"],
  "package": {
    "unit_form": "TABLET",
    "units_per_package": "60"
  },
  "nutrients": [
    {
      "code": "VITAMIN_C",
      "name": "비타민 C",
      "amount_per_unit": "100",
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
      "id": "24000000-0000-4000-8000-000000000101",
      "author_label": "MJ's COMMENT",
      "content": "개발용 전문가 추천 코멘트"
    }
  ]
}
~~~

## F-2.4.2 외부 구매 연결

- GET /api/v1/curation/products/{product_id}/purchase
- 인증 없이 호출하는 공개 리다이렉트 API다.
- 게시 제품이면서 활성 카테고리 연결이 있는 제품만 공개한다.
- 활성 링크 중 sort_order, id 오름차순 첫 항목으로 307 Temporary Redirect한다.
- 성공 응답은 Location과 `Cache-Control: no-store`,
  `Referrer-Policy: no-referrer` 헤더를 포함하고 본문은 없다.
- 미존재·비게시·활성 카테고리 없음은 404 PRODUCT_NOT_FOUND다.
- 공개 제품에 활성 링크가 없으면 404 PURCHASE_LINK_NOT_FOUND다.
- product_id 형식 오류는 422 VALIDATION_FAILED, DB 또는 저장 URL 안전성 실패는
  503 SERVICE_UNAVAILABLE다.
- URL은 hostname이 있는 HTTPS 절대 URL이며 userinfo·fragment·공백을 허용하지 않고
  최대 2048자다.
- 클릭·사용자·구매 이력을 쓰지 않는다.

~~~http
HTTP/1.1 307 Temporary Redirect
Location: https://www.coupang.com/vp/products/6743604050
Cache-Control: no-store
Referrer-Policy: no-referrer
~~~
