"""버전 1 API 라우터."""

from fastapi import APIRouter

from yeongyangkkuk.api.health import router as health_router
from yeongyangkkuk.auth.current_user_router import router as current_user_router
from yeongyangkkuk.auth.email_verification_router import (
    router as email_verification_router,
)
from yeongyangkkuk.auth.login_router import router as login_router
from yeongyangkkuk.auth.router import router as auth_router
from yeongyangkkuk.auth.session_router import router as session_router
from yeongyangkkuk.care.care_item_router import router as care_item_router
from yeongyangkkuk.coaching.router import router as coaching_router
from yeongyangkkuk.curation.product_category_router import (
    router as product_category_router,
)
from yeongyangkkuk.curation.product_detail_router import router as product_detail_router
from yeongyangkkuk.curation.product_router import router as product_router
from yeongyangkkuk.curation.purchase_link_router import router as purchase_link_router
from yeongyangkkuk.medication.router import router as medication_router
from yeongyangkkuk.notification.router import router as notification_router

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
api_router.include_router(coaching_router)
