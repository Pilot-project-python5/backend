# 시드 데이터

## 실행 원칙

- 로컬 개발·Swagger·프론트엔드 연동을 위한 결정적 데이터다.
- 실행 시 Notion이나 판매처에 접속하지 않는다. 승인된 외부 자료는 코드와 이 문서에
  스냅샷으로 보관한다.
- 자연 키 또는 고정 UUID로 멱등 적용하며 반복 실행해도 중복되지 않는다.
- 실사용자·실제 이메일·실제 건강정보를 포함하지 않는다.

## 민재코치 카탈로그 스냅샷

- 원본: [민재코치 데이터](https://app.notion.com/p/3b62779e926280e287baccedfce27f9c)
- 원본 확인일: 2026-08-15
- 로컬 단일 원본: `src/allyakkkuk/curation/catalog_seed_data.py`
- 적용 범위: 활성 카테고리 11개, 게시 추천 제품 32개, 제품별 코치 코멘트와 쿠팡 링크

### 카테고리

| 순서 | slug | 표시 이름 |
| ---: | --- | --- |
| 10 | `multivitamin` | 종합비타민 |
| 20 | `vitamin-b` | 비타민B군 |
| 30 | `vitamin-c` | 비타민C |
| 40 | `vitamin-d` | 비타민D |
| 50 | `protein-supplement` | 단백질 보충제 |
| 60 | `pre-workout` | 부스터 |
| 70 | `creatine` | 크레아틴 |
| 80 | `probiotics` | 유산균 |
| 90 | `omega-3` | 오메가3 |
| 100 | `magnesium` | 마그네슘 |
| 110 | `melatonin` | 멜라토닌 |

`all`·`전체`는 필터 미적용을 나타내는 API 가상 항목이므로 DB에 저장하지 않는다.
이전 개발 시드의 `vitamin`, `protein`은 삭제하지 않고 비활성화한다.

### 추천 제품

| 순서 | SKU | 제품명 | 카테고리 | 패키지 단위 수 |
| ---: | --- | --- | --- | ---: |
| 10 | `KORYO-EUNDAN-MULTIVITAMIN-ALL-IN-ONE` | 고려은단 멀티비타민 올인원 | multivitamin | 60정 |
| 20 | `ALIVE-ONCE-DAILY-MENS` | 얼라이브 원스데일리 포맨 | multivitamin | 30정 |
| 30 | `ALIVE-ONCE-DAILY-WOMENS` | 얼라이브 원스데일리 포우먼 | multivitamin | 30정 |
| 40 | `KORYO-EUNDAN-MEGADOSE-B` | 고려은단 메가도스B | vitamin-b | 60정 |
| 50 | `THORNE-BASIC-B-COMPLEX` | 쏜리서치 베이직 B 컴플렉스 | vitamin-b | 60캡슐 |
| 60 | `SOLGAR-B-COMPLEX-100` | 솔가 B 컴플렉스 100 | vitamin-b | 100캡슐 |
| 70 | `KORYO-EUNDAN-VITAMIN-C-1000` | 고려은단 비타민C 1000 | vitamin-c | 600정 |
| 80 | `CHONGKUNDANG-PREMIUM-VITA-C-1000-PLUS` | 종근당건강 프리미엄 비타C 1000플러스 | vitamin-c | 100정 |
| 90 | `SOLGAR-VITAMIN-C-1000` | 솔가 비타민 C 1000 | vitamin-c | 100캡슐 |
| 100 | `CHONGKUNDANG-VITAMIN-D-2000-IU` | 종근당건강 비타민D 2000IU | vitamin-d | 90정 |
| 110 | `CHONGKUNDANG-VITAMIN-D-1000-IU` | 종근당 비타민D 1000IU | vitamin-d | 90정 |
| 120 | `SOLGAR-VITAMIN-D3-1000-IU` | 솔가 비타민 D3 1000IU | vitamin-d | 180캡슐 |
| 130 | `OPTIMUM-NUTRITION-GOLD-STANDARD-WHEY` | 옵티멈뉴트리션 골드 스탠다드 100% 웨이 | protein-supplement | 29스쿱 |
| 140 | `BSN-SYNTHA-6-ISOLATE-CHOCOLATE` | BSN 신타6 | protein-supplement | 48스쿱 |
| 150 | `SELEX-PROFIT-WPI` | 셀렉스 프로핏 WPI | protein-supplement | 1회분 |
| 160 | `EVL-ENGN-PRE-WORKOUT` | EVL ENGN 프리워크아웃 | pre-workout | 30스쿱 |
| 170 | `CELLUCOR-C4-ORIGINAL` | 셀루코어 C4 오리지널 | pre-workout | 30스쿱 |
| 180 | `SAMDAEOBAEK-PRE-WORKOUT-WORLD-CLASS` | 삼대오백 프리워크아웃 월드클래스 | pre-workout | 30스쿱 |
| 190 | `NOW-CREATINE-MONOHYDRATE` | 나우푸드 크레아틴 모노하이드레이트 | creatine | 120스쿱 |
| 200 | `SAMDAEOBAEK-CREATINE-MONOHYDRATE` | 삼대오백 크레아틴 모노하이드레이트 | creatine | 100스쿱 |
| 210 | `JAMBBAEK-JUST-CREATINE` | 잠백이 저스트 크레아틴 | creatine | 100스쿱 |
| 220 | `CHONGKUNDANG-LACTO-FIT-GOLD` | 종근당건강 락토핏 골드 | probiotics | 50포 |
| 230 | `GQ-LAB-PROBIOTICS-GOLD` | 지큐랩 100억 생유산균 골드 | probiotics | 60캡슐 |
| 240 | `NOW-PROBIOTIC-10-25-BILLION` | 나우푸드 프로바이오틱-10 250억 | probiotics | 30캡슐 |
| 250 | `CHONGKUNDANG-PROMEGA-OMEGA-3-TRIPLE` | 종근당건강 프로메가 오메가3 트리플 | omega-3 | 60캡슐 |
| 260 | `DR-LIN-RTG-OMEGA-3-ALPHA` | 닥터린 하이퍼셀 rTG 오메가3 알파 | omega-3 | 30캡슐 |
| 270 | `NUTRI-D-DAY-RTG-OMEGA-3-GOLD` | 뉴트리디데이 rTG 오메가3 골드 | omega-3 | 30캡슐 |
| 280 | `SOLGAR-MAGNESIUM-WITH-B6` | 솔가 마그네슘 위드 비타민 B6 | magnesium | 100정 |
| 290 | `DOCTORS-BEST-HIGH-ABSORPTION-MAGNESIUM` | 닥터스베스트 고흡수 킬레이트 마그네슘 | magnesium | 120정 |
| 300 | `NOW-MAGNESIUM-GLYCINATE` | 나우푸드 마그네슘 글리시네이트 | magnesium | 180정 |
| 310 | `NUTRIJEONG-PLANT-MELATONIN-2MG` | 뉴트리정 식물성 멜라토닌 2mg | melatonin | 60정 |
| 320 | `NUTRIJEONG-PLANT-MELATONIN-5MG` | 뉴트리정 식물성 멜라토닌 5mg | melatonin | 120정 |

각 제품의 쿠팡 URL은 원본 표의 상품 URL을 그대로 스냅샷했다. URL은 시드 적용 전에
애플리케이션 안전 검증을 거치고 DB CHECK도 적용한다.

## 누락 정보와 정규화 결정

- 원본에 가격이 없으므로 `display_price=0`을 “가격 미제공” 값으로 사용한다. 실시간
  판매가를 추정하거나 수집하지 않는다.
- 원본에 이미지가 없으므로 모든 신규 제품은 로컬
  `/static/products/catalog-placeholder.svg`를 사용한다.
- 현재 패키지 단위 계약에 병(BOTTLE)이 없어 셀렉스 330mL 한 병은 1회분 `PACKET`
  한 단위로 저장한다.
- 제품 상세의 함량은 반드시 한 정·한 캡슐·한 스쿱·한 포 기준으로 저장한다. “2정당”
  또는 “1일 2캡슐” 값은 단위 수로 나누었다.
- CFU는 현재 허용 단위가 아니므로 유산균 수는 `product_nutrients`에 넣지 않았다.
  함량이 명시되지 않은 혼합 성분도 추정하지 않는다.
- `µgRE`, `mgNE`, `µgDFE`는 현재 API 단위 계약에 별도 코드가 없어 각각 MCG 또는
  MG 수치로 저장하고 성분 이름으로 의미를 보완한다.
- 멜라토닌 2mg·5mg은 원본이 제품명 표기 기준임을 명시한다. 1회 2정 기준이므로
  단위당 각각 1mg·2.5mg으로 저장한다.
- 카테고리 설명과 주의사항은 현재 카테고리 응답 필드가 없어 각 제품의
  `MJ's COMMENT`로 제공한다.

## 기존 데이터 보존

- 이전 카탈로그의 `LIFE-TWO-PER-DAY`, `SPORTS-RESEARCH-OMEGA-3`는 CareItem 등의
  외래키와 과거 스냅샷을 보호하기 위해 삭제하지 않고 `is_published=false`로 바꾼다.
- 기존 BSN SKU와 UUID는 참조 안정성을 위해 유지하되 표시 이름·패키지·카테고리와
  성분을 민재코치 목록으로 갱신한다.
- 이전 코멘트와 example.com 구매 링크는 비활성화한다.

## 영양소 기준 CSV

- 나이·성별별 기준량은 `data/reference/nutrient_reference_kdri_2025.csv`가 별도로
  관리한다.
- 카탈로그 성분 중 기준 CSV에 없는 항목도 제품 상세와 복용량 합산에는 나타나며,
  영양성분 현황에서는 `reference_available=false`로 반환한다.

## 검증

- 필수 필드와 고정 키 중복
- 카테고리 11개·게시 추천 제품 32개
- 제품별 정확히 하나의 활성 카테고리 매핑·코치 코멘트·구매 링크
- 음수 또는 0 이하 패키지 수량과 성분 함량
- 지원하지 않는 단위와 외부 구매 URL 형식
- 반복 실행 후 같은 행 수와 값으로 수렴하는지
- 기존 CareItem 스냅샷과 외래키 보존
