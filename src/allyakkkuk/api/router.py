"""버전 1 API 라우터."""

from fastapi import APIRouter

from allyakkkuk.api.health import router as health_router
from allyakkkuk.auth.current_user_router import router as current_user_router
from allyakkkuk.auth.email_verification_router import (
    router as email_verification_router,
)
from allyakkkuk.auth.login_router import router as login_router
from allyakkkuk.auth.router import router as auth_router
from allyakkkuk.auth.session_router import router as session_router
from allyakkkuk.care.care_item_router import router as care_item_router
from allyakkkuk.curation.product_category_router import (
    router as product_category_router,
)
from allyakkkuk.curation.product_detail_router import router as product_detail_router
from allyakkkuk.curation.product_router import router as product_router
from allyakkkuk.curation.purchase_link_router import router as purchase_link_router
from allyakkkuk.medication.router import router as medication_router
from allyakkkuk.notification.router import router as notification_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(email_verification_router)
api_router.include_router(login_router)
api_router.include_router(session_router)
api_router.include_router(current_user_router)
api_router.include_router(product_category_router)
api_router.include_router(product_router)
api_router.include_router(product_detail_router)
api_router.include_router(purchase_link_router)
api_router.include_router(medication_router)
api_router.include_router(care_item_router)
api_router.include_router(notification_router)
