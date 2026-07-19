from pathlib import Path

from scripts.check_module_boundaries import find_violations


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_boundary_checker_allows_public_and_same_context_imports(tmp_path: Path) -> None:
    _write(tmp_path, "router.py", "from modules.auth.public import auth_router\n")
    _write(tmp_path, "modules/auth/service.py", "from modules.auth.repository import Repo\n")
    _write(tmp_path, "modules/catalog/service.py", "from modules.auth.public import RoleName\n")
    _write(
        tmp_path,
        "modules/moderation/domain.py",
        "from modules.submissions.contracts import SubmissionStatus\n",
    )

    assert find_violations(tmp_path) == []


def test_boundary_checker_rejects_router_and_cross_context_deep_imports(tmp_path: Path) -> None:
    _write(tmp_path, "router.py", "from modules.auth.routes import router\n")
    _write(tmp_path, "modules/catalog/service.py", "from modules.auth.repository import Repo\n")

    violations = find_violations(tmp_path)

    assert [violation.imported for violation in violations] == [
        "modules.auth.repository",
        "modules.auth.routes",
    ]
