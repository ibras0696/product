from fastapi import APIRouter

from modules.audit.public import audit_router
from modules.auth.public import admin_router, auth_router
from modules.catalog.public import admin_catalog_router, catalog_router, exploration_router
from modules.exports.public import export_router
from modules.health.public import health_router
from modules.media.public import public_media_router
from modules.moderation.public import moderation_router
from modules.publication.public import publication_router
from modules.submissions.public import submission_media_router, submissions_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)

# Keep the original browser contract during the Slice 0 transition.
api_router.include_router(auth_router, include_in_schema=False)

versioned_router = APIRouter(prefix="/v1")
versioned_router.include_router(auth_router)
versioned_router.include_router(admin_router)
versioned_router.include_router(catalog_router)
versioned_router.include_router(exploration_router)
versioned_router.include_router(submissions_router)
versioned_router.include_router(submission_media_router)
versioned_router.include_router(export_router)
versioned_router.include_router(moderation_router)
versioned_router.include_router(audit_router)
versioned_router.include_router(admin_catalog_router)
versioned_router.include_router(publication_router)
versioned_router.include_router(public_media_router)
api_router.include_router(versioned_router)
