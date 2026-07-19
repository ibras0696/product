"""Public application and transport contracts owned by the auth module."""

from modules.auth.admin_routes import router as admin_router
from modules.auth.dependencies import AuthRequestContext, get_auth_context, require_same_origin
from modules.auth.domain import Permission, RoleName
from modules.auth.routes import router as auth_router
from modules.auth.schemas import AdminAccount

__all__ = [
    "AdminAccount",
    "AuthRequestContext",
    "Permission",
    "RoleName",
    "admin_router",
    "auth_router",
    "get_auth_context",
    "require_same_origin",
]
