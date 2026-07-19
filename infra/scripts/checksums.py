from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create(manifest: Path, files: list[Path]) -> None:
    if not files:
        raise SystemExit("No files supplied")
    manifest.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="utf-8"
    )


def verify(manifest: Path) -> None:
    root = manifest.parent
    lines = manifest.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise SystemExit("Checksum manifest is empty")
    for line in lines:
        checksum, separator, name = line.partition("  ")
        path = Path(name)
        if separator != "  " or len(checksum) != 64 or path.name != name:
            raise SystemExit("Checksum manifest is invalid")
        if sha256(root / path) != checksum:
            raise SystemExit(f"Checksum mismatch: {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("manifest", type=Path)
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args()
    if args.action == "create":
        create(args.manifest, args.files)
    elif args.files:
        raise SystemExit("verify does not accept file arguments")
    else:
        verify(args.manifest)


if __name__ == "__main__":
    main()
