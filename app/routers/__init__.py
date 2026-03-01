from .assets import router as assets_router
from .admin import router as admin_router
from .attendance import router as attendance_router
from .auth import router as auth_router
from .food import router as food_router
from .makeup import router as makeup_router
from .messages import router as messages_router
from .people import router as people_router
from .resources import router as resources_router

__all__ = [
    "admin_router",
    "assets_router",
    "attendance_router",
    "auth_router",
    "food_router",
    "makeup_router",
    "messages_router",
    "people_router",
    "resources_router",
]
