"""Public transport contracts owned by the catalog module."""

from modules.catalog.admin_routes import router as admin_catalog_router
from modules.catalog.exploration_routes import router as exploration_router
from modules.catalog.routes import router as catalog_router

__all__ = ["admin_catalog_router", "catalog_router", "exploration_router"]
