import pytest

from modules.auth.domain import Permission, has_admin_role, has_permission


@pytest.mark.parametrize(
    ("role", "allowed", "denied"),
    [
        ("moderator", Permission.MODERATION_PUBLISH, Permission.CATALOG_WRITE),
        ("editor", Permission.CATALOG_WRITE, Permission.MODERATION_PUBLISH),
        ("admin", Permission.ROLES_MANAGE, "unknown:permission"),
        ("future-role", Permission.CATALOG_READ, Permission.MODERATION_READ),
    ],
)
def test_role_permission_matrix_denies_unassigned_authority(
    role: str, allowed: str, denied: str
) -> None:
    roles = {role}
    assert has_permission(roles, allowed) is (role != "future-role")
    assert not has_permission(roles, denied)


def test_only_known_administrative_roles_unlock_admin_area() -> None:
    assert has_admin_role({"moderator"})
    assert has_admin_role({"editor"})
    assert has_admin_role({"admin"})
    assert not has_admin_role(set())
    assert not has_admin_role({"future-role"})
