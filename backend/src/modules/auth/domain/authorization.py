from enum import StrEnum
from typing import Final


class RoleName(StrEnum):
    MODERATOR = "moderator"
    EDITOR = "editor"
    ADMIN = "admin"


class Permission(StrEnum):
    MODERATION_READ = "moderation:read"
    MODERATION_CLAIM = "moderation:claim"
    MODERATION_DECIDE = "moderation:decide"
    MODERATION_PUBLISH = "moderation:publish"
    CATALOG_READ = "catalog:read"
    CATALOG_WRITE = "catalog:write"
    CATALOG_EXPORT = "catalog:export"
    AUDIT_READ = "audit:read"
    ROLES_MANAGE = "roles:manage"


_MODERATOR_PERMISSIONS: Final = frozenset(
    {
        Permission.MODERATION_READ,
        Permission.MODERATION_CLAIM,
        Permission.MODERATION_DECIDE,
        Permission.MODERATION_PUBLISH,
        Permission.CATALOG_READ,
    }
)
_EDITOR_PERMISSIONS: Final = frozenset(
    {Permission.CATALOG_READ, Permission.CATALOG_WRITE, Permission.CATALOG_EXPORT}
)
_ROLE_PERMISSIONS: Final = {
    RoleName.MODERATOR: _MODERATOR_PERMISSIONS,
    RoleName.EDITOR: _EDITOR_PERMISSIONS,
    RoleName.ADMIN: frozenset(Permission),
}


def has_permission(roles: set[str] | frozenset[str], permission: str) -> bool:
    """Deny unknown roles and permissions instead of guessing their authority."""
    try:
        required = Permission(permission)
    except ValueError:
        return False
    return any(_permission_for_known_role(role, required) for role in roles)


def has_admin_role(roles: set[str] | frozenset[str]) -> bool:
    for role in roles:
        try:
            RoleName(role)
        except ValueError:
            continue
        return True
    return False


def _permission_for_known_role(role: str, permission: Permission) -> bool:
    try:
        known_role = RoleName(role)
    except ValueError:
        return False
    return permission in _ROLE_PERMISSIONS[known_role]
