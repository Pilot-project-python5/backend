"""Alembic 자동 비교가 읽는 기능 모델 레지스트리.

기능 PR에서 SQLAlchemy 모델을 추가할 때 이 모듈이 해당 모델 모듈을 가져오도록
갱신한다. 등록되지 않은 모델은 alembic check에서 발견할 수 없다.
"""

from allyakkkuk.auth.models import (
    EmailVerification,
    HealthProfile,
    RefreshSession,
    User,
)
from allyakkkuk.care.models import CareItem, CareNutrientSnapshot
from allyakkkuk.care.nutrient_reference_models import (
    NutrientReferenceValue,
    NutrientReferenceVersion,
)
from allyakkkuk.curation.models import (
    ExpertComment,
    Nutrient,
    Product,
    ProductCategory,
    ProductCategoryMapping,
    ProductNutrient,
    PurchaseLink,
)
from allyakkkuk.medication.models import MedicationDetail

__all__ = [
    "CareItem",
    "CareNutrientSnapshot",
    "EmailVerification",
    "ExpertComment",
    "HealthProfile",
    "MedicationDetail",
    "Nutrient",
    "NutrientReferenceValue",
    "NutrientReferenceVersion",
    "Product",
    "ProductCategory",
    "ProductCategoryMapping",
    "ProductNutrient",
    "PurchaseLink",
    "RefreshSession",
    "User",
]
