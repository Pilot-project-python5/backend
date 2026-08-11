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
