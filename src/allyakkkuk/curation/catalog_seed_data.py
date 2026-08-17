"""민재코치 승인 카탈로그의 로컬 단일 원본.

외부 Notion 페이지를 실행 시점에 조회하지 않는다. 2026-08-15에 확인한
`민재코치 데이터` 페이지를 결정적 개발 시드로 옮긴 스냅샷이다.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

CATALOG_SOURCE_URL = "https://app.notion.com/p/3b62779e926280e287baccedfce27f9c"
CATALOG_REVIEWED_ON = "2026-08-15"
PLACEHOLDER_IMAGE_URL = "/static/products/catalog-placeholder.svg"


def _uuid(prefix: str, value: int) -> UUID:
    return UUID(f"{prefix}-0000-4000-8000-{value:012d}")


@dataclass(frozen=True, slots=True)
class ProductCategorySeedRow:
    id: UUID
    slug: str
    name: str
    description: str
    caution: str
    sort_order: int


PRODUCT_CATEGORY_SEED_ROWS = (
    ProductCategorySeedRow(
        _uuid("21000000", 101),
        "multivitamin",
        "종합비타민",
        "전반적인 일상 컨디션 유지와 식사로 부족한 여러 비타민·미네랄 보충을 돕습니다.",
        "다른 비타민 제품과 함께 섭취할 때 같은 영양소의 중복과 "
        "과다 섭취를 확인하세요.",
        10,
    ),
    ProductCategorySeedRow(
        _uuid("21000000", 102),
        "vitamin-b",
        "비타민B군",
        "에너지 생성과 신경 건강을 돕고 피로 관리와 활기찬 일상 유지에 활용됩니다.",
        "종합비타민과 함께 섭취할 때 비타민 B군 함량이 중복되지 않는지 확인하세요.",
        20,
    ),
    ProductCategorySeedRow(
        _uuid("21000000", 103),
        "vitamin-c",
        "비타민C",
        "항산화 관리와 면역 건강, 철분 흡수를 돕습니다.",
        "고함량은 속 불편함이나 설사를 유발할 수 있으며 "
        "종합비타민과의 중복도 확인해야 합니다.",
        30,
    ),
    ProductCategorySeedRow(
        _uuid("21000000", 104),
        "vitamin-d",
        "비타민D",
        "뼈와 근육 건강 및 칼슘 흡수를 돕습니다.",
        "지용성 비타민이므로 과다 섭취와 종합비타민 중복에 주의하고 "
        "식사 후 복용하세요.",
        40,
    ),
    ProductCategorySeedRow(
        _uuid("21000000", 105),
        "protein-supplement",
        "단백질 보충제",
        "운동 후 근육 회복과 하루 단백질 섭취 보완을 돕습니다.",
        "식사 속 단백질까지 포함해 하루 총섭취량을 고려하세요.",
        50,
    ),
    ProductCategorySeedRow(
        _uuid("21000000", 106),
        "pre-workout",
        "부스터",
        "운동 전 집중력과 활력 및 고강도 운동 수행을 보조합니다.",
        "카페인 함량을 확인하고 늦은 시간이나 다른 카페인 음료와의 "
        "중복 섭취를 피하세요.",
        60,
    ),
    ProductCategorySeedRow(
        _uuid("21000000", 107),
        "creatine",
        "크레아틴",
        "고강도 운동의 근력과 반복 수행 능력을 보조합니다.",
        "충분한 수분을 섭취하고 신장 질환이 있다면 섭취 전 전문가와 상담하세요.",
        70,
    ),
    ProductCategorySeedRow(
        _uuid("21000000", 108),
        "probiotics",
        "유산균",
        "장내 환경과 배변 활동 및 장 건강 관리를 돕습니다.",
        "균주에 따라 기대 효과가 다를 수 있으므로 제품 정보를 확인하세요.",
        80,
    ),
    ProductCategorySeedRow(
        _uuid("21000000", 3),
        "omega-3",
        "오메가3",
        "심혈관 건강과 중성지방 관리 및 EPA·DHA 보충을 돕습니다.",
        "항응고제 복용 중이라면 혈액응고 영향 가능성을 전문가와 상담하세요.",
        90,
    ),
    ProductCategorySeedRow(
        _uuid("21000000", 110),
        "magnesium",
        "마그네슘",
        "근육과 신경 기능, 휴식과 컨디션 관리를 돕습니다.",
        "과다 섭취 시 설사나 복부 불편감이 생길 수 있으니 섭취량을 확인하세요.",
        100,
    ),
    ProductCategorySeedRow(
        _uuid("21000000", 111),
        "melatonin",
        "멜라토닌",
        "수면 리듬과 잠드는 시간 조절을 돕습니다.",
        "복용 후 졸림이 이어질 수 있으므로 운전이나 기계 조작 전 섭취에 주의하세요.",
        110,
    ),
)

CATEGORY_BY_SLUG = {row.slug: row for row in PRODUCT_CATEGORY_SEED_ROWS}


@dataclass(frozen=True, slots=True)
class ProductSeedRow:
    id: UUID
    sku: str
    product_type: str
    brand: str
    name: str
    image_url: str
    unit_form: str
    units_per_package: Decimal
    display_price: int
    sort_order: int
    category_slug: str
    purchase_url: str


def _product(
    position: int,
    sku: str,
    brand: str,
    name: str,
    unit_form: str,
    units_per_package: str,
    category_slug: str,
    purchase_id: int,
    *,
    stable_id: int | None = None,
) -> ProductSeedRow:
    return ProductSeedRow(
        id=_uuid("22000000", stable_id or 100 + position),
        sku=sku,
        product_type="SUPPLEMENT",
        brand=brand,
        name=name,
        image_url=PLACEHOLDER_IMAGE_URL,
        unit_form=unit_form,
        units_per_package=Decimal(units_per_package),
        display_price=0,
        sort_order=position * 10,
        category_slug=category_slug,
        purchase_url=f"https://www.coupang.com/vp/products/{purchase_id}",
    )


PRODUCT_SEED_ROWS = (
    _product(
        1,
        "KORYO-EUNDAN-MULTIVITAMIN-ALL-IN-ONE",
        "고려은단",
        "고려은단 멀티비타민 올인원",
        "TABLET",
        "60",
        "multivitamin",
        6743604050,
    ),
    _product(
        2,
        "ALIVE-ONCE-DAILY-MENS",
        "Alive",
        "얼라이브 원스데일리 포맨",
        "TABLET",
        "30",
        "multivitamin",
        9405085004,
    ),
    _product(
        3,
        "ALIVE-ONCE-DAILY-WOMENS",
        "Alive",
        "얼라이브 원스데일리 포우먼",
        "TABLET",
        "30",
        "multivitamin",
        3961975,
    ),
    _product(
        4,
        "KORYO-EUNDAN-MEGADOSE-B",
        "고려은단",
        "고려은단 메가도스B",
        "TABLET",
        "60",
        "vitamin-b",
        8289158533,
    ),
    _product(
        5,
        "THORNE-BASIC-B-COMPLEX",
        "Thorne",
        "쏜리서치 베이직 B 컴플렉스",
        "CAPSULE",
        "60",
        "vitamin-b",
        433050,
    ),
    _product(
        6,
        "SOLGAR-B-COMPLEX-100",
        "Solgar",
        "솔가 B 컴플렉스 100",
        "CAPSULE",
        "100",
        "vitamin-b",
        8136129840,
    ),
    _product(
        7,
        "KORYO-EUNDAN-VITAMIN-C-1000",
        "고려은단",
        "고려은단 비타민C 1000",
        "TABLET",
        "600",
        "vitamin-c",
        9334963084,
    ),
    _product(
        8,
        "CHONGKUNDANG-PREMIUM-VITA-C-1000-PLUS",
        "종근당건강",
        "종근당건강 프리미엄 비타C 1000플러스",
        "TABLET",
        "100",
        "vitamin-c",
        7576034776,
    ),
    _product(
        9,
        "SOLGAR-VITAMIN-C-1000",
        "Solgar",
        "솔가 비타민 C 1000",
        "CAPSULE",
        "100",
        "vitamin-c",
        8289152563,
    ),
    _product(
        10,
        "CHONGKUNDANG-VITAMIN-D-2000-IU",
        "종근당건강",
        "종근당건강 비타민D 2000IU",
        "TABLET",
        "90",
        "vitamin-d",
        5191718214,
    ),
    _product(
        11,
        "CHONGKUNDANG-VITAMIN-D-1000-IU",
        "종근당",
        "종근당 비타민D 1000IU",
        "TABLET",
        "90",
        "vitamin-d",
        7772010261,
    ),
    _product(
        12,
        "SOLGAR-VITAMIN-D3-1000-IU",
        "Solgar",
        "솔가 비타민 D3 1000IU",
        "CAPSULE",
        "180",
        "vitamin-d",
        6422546784,
    ),
    _product(
        13,
        "OPTIMUM-NUTRITION-GOLD-STANDARD-WHEY",
        "Optimum Nutrition",
        "옵티멈뉴트리션 골드 스탠다드 100% 웨이",
        "SCOOP",
        "29",
        "protein-supplement",
        9656690327,
    ),
    _product(
        14,
        "BSN-SYNTHA-6-ISOLATE-CHOCOLATE",
        "BSN",
        "BSN 신타6",
        "SCOOP",
        "48",
        "protein-supplement",
        6501142932,
        stable_id=2,
    ),
    _product(
        15,
        "SELEX-PROFIT-WPI",
        "셀렉스",
        "셀렉스 프로핏 WPI",
        "PACKET",
        "1",
        "protein-supplement",
        8288998337,
    ),
    _product(
        16,
        "EVL-ENGN-PRE-WORKOUT",
        "EVLution Nutrition",
        "EVL ENGN 프리워크아웃",
        "SCOOP",
        "30",
        "pre-workout",
        6422282118,
    ),
    _product(
        17,
        "CELLUCOR-C4-ORIGINAL",
        "Cellucor",
        "셀루코어 C4 오리지널",
        "SCOOP",
        "30",
        "pre-workout",
        8518179438,
    ),
    _product(
        18,
        "SAMDAEOBAEK-PRE-WORKOUT-WORLD-CLASS",
        "삼대오백",
        "삼대오백 프리워크아웃 월드클래스",
        "SCOOP",
        "30",
        "pre-workout",
        8211145897,
    ),
    _product(
        19,
        "NOW-CREATINE-MONOHYDRATE",
        "NOW Foods",
        "나우푸드 크레아틴 모노하이드레이트",
        "SCOOP",
        "120",
        "creatine",
        8203753238,
    ),
    _product(
        20,
        "SAMDAEOBAEK-CREATINE-MONOHYDRATE",
        "삼대오백",
        "삼대오백 크레아틴 모노하이드레이트",
        "SCOOP",
        "100",
        "creatine",
        7093646595,
    ),
    _product(
        21,
        "JAMBBAEK-JUST-CREATINE",
        "잠백이",
        "잠백이 저스트 크레아틴",
        "SCOOP",
        "100",
        "creatine",
        8474008747,
    ),
    _product(
        22,
        "CHONGKUNDANG-LACTO-FIT-GOLD",
        "종근당건강",
        "종근당건강 락토핏 골드",
        "PACKET",
        "50",
        "probiotics",
        8184298624,
    ),
    _product(
        23,
        "GQ-LAB-PROBIOTICS-GOLD",
        "지큐랩",
        "지큐랩 100억 생유산균 골드",
        "CAPSULE",
        "60",
        "probiotics",
        8232473970,
    ),
    _product(
        24,
        "NOW-PROBIOTIC-10-25-BILLION",
        "NOW Foods",
        "나우푸드 프로바이오틱-10 250억",
        "CAPSULE",
        "30",
        "probiotics",
        8402766000,
    ),
    _product(
        25,
        "CHONGKUNDANG-PROMEGA-OMEGA-3-TRIPLE",
        "종근당건강",
        "종근당건강 프로메가 오메가3 트리플",
        "CAPSULE",
        "60",
        "omega-3",
        7510928725,
    ),
    _product(
        26,
        "DR-LIN-RTG-OMEGA-3-ALPHA",
        "닥터린",
        "닥터린 하이퍼셀 rTG 오메가3 알파",
        "CAPSULE",
        "30",
        "omega-3",
        8349288599,
    ),
    _product(
        27,
        "NUTRI-D-DAY-RTG-OMEGA-3-GOLD",
        "뉴트리디데이",
        "뉴트리디데이 rTG 오메가3 골드",
        "CAPSULE",
        "30",
        "omega-3",
        9069646904,
    ),
    _product(
        28,
        "SOLGAR-MAGNESIUM-WITH-B6",
        "Solgar",
        "솔가 마그네슘 위드 비타민 B6",
        "TABLET",
        "100",
        "magnesium",
        1181656,
    ),
    _product(
        29,
        "DOCTORS-BEST-HIGH-ABSORPTION-MAGNESIUM",
        "Doctor's Best",
        "닥터스베스트 고흡수 킬레이트 마그네슘",
        "TABLET",
        "120",
        "magnesium",
        8201302227,
    ),
    _product(
        30,
        "NOW-MAGNESIUM-GLYCINATE",
        "NOW Foods",
        "나우푸드 마그네슘 글리시네이트",
        "TABLET",
        "180",
        "magnesium",
        1366689007,
    ),
    _product(
        31,
        "NUTRIJEONG-PLANT-MELATONIN-2MG",
        "뉴트리정",
        "뉴트리정 식물성 멜라토닌 2mg",
        "TABLET",
        "60",
        "melatonin",
        8773958461,
    ),
    _product(
        32,
        "NUTRIJEONG-PLANT-MELATONIN-5MG",
        "뉴트리정",
        "뉴트리정 식물성 멜라토닌 5mg",
        "TABLET",
        "120",
        "melatonin",
        9161001505,
    ),
)


def coach_comment_for(category_slug: str) -> str:
    category = CATEGORY_BY_SLUG[category_slug]
    return f"{category.description} {category.caution}"
