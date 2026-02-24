from .assets import router as assets_router
from .attendance import router as attendance_router
from .auth import router as auth_router
from .food import router as food_router
from .makeup import router as makeup_router
from .people import router as people_router
from .resources import router as resources_router

__all__ = [
    "assets_router",
    "attendance_router",
    "auth_router",
    "food_router",
    "makeup_router",
    "people_router",
    "resources_router",
]
