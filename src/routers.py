from fastapi import APIRouter

from src.controllers.user_login_controller import router as login_router
from src.controllers.user_logout_controller import router as logout_router
from src.controllers.user_permission_controller import (
	router as permission_router,
)
from src.controllers.user_registration_controller import (
	router as registration_router,
)

router = APIRouter()
router.include_router(registration_router)
router.include_router(login_router)
router.include_router(logout_router)
router.include_router(permission_router)