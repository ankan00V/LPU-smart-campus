from .assets import router as assets_router
from .admin import router as admin_router
from .attendance import router as attendance_router
from .auth import router as auth_router
from .copilot import router as copilot_router
from .enterprise import router as enterprise_router
from .food import router as food_router
from .identity_shield import router as identity_shield_router
from .remedial import router as remedial_router
from .messages import router as messages_router
from .people import router as people_router
from .realtime import router as realtime_router
from .resources import router as resources_router
from .saarthi import router as saarthi_router

__all__ = [
    "admin_router",
    "assets_router",
    "attendance_router",
    "auth_router",
    "copilot_router",
    "enterprise_router",
    "food_router",
    "identity_shield_router",
    "remedial_router",
    "messages_router",
    "people_router",
    "realtime_router",
    "resources_router",
    "saarthi_router",
]
