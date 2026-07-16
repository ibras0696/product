import re
import subprocess
import sys
from pathlib import Path

VERSIONS_DIR = Path(__file__).resolve().parents[1] / "migrations" / "versions"
REVISION_PATTERN = re.compile(r"^(\d{4})_\d{2}_\d{4}_.+\.py$")


def next_revision() -> str:
    revisions = [
        int(match.group(1))
        for path in VERSIONS_DIR.glob("*.py")
        if (match := REVISION_PATTERN.match(path.name))
    ]
    return f"{max(revisions, default=0) + 1:04d}"


def normalize_name(raw_name: str) -> str:
    name = re.sub(r"[^a-z0-9]+", "_", raw_name.strip().lower()).strip("_")
    if not name:
        raise ValueError("Migration name must contain letters or digits")
    return name


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python scripts/create_migration.py "migration name"')
    revision = next_revision()
    name = normalize_name(sys.argv[1])
    subprocess.run(
        ["alembic", "revision", "--autogenerate", "--rev-id", revision, "-m", name],
        check=True,
    )


if __name__ == "__main__":
    main()
