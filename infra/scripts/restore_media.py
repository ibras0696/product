from __future__ import annotations

import argparse
import hashlib
import sys
import tarfile
from pathlib import Path, PurePosixPath

MAX_MEMBERS = 500_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--max-bytes", type=int, required=True)
    return parser.parse_args()


def safe_members(archive: tarfile.TarFile, max_bytes: int) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    if len(members) > MAX_MEMBERS:
        raise RuntimeError("Media archive has too many entries")
    total = 0
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts:
            raise RuntimeError("Media archive contains an unsafe path")
        if not (member.isfile() or member.isdir()):
            raise RuntimeError("Media archive contains a link or special file")
        total += member.size
        if total > max_bytes:
            raise RuntimeError("Media archive exceeds the restore limit")
    return members


def extract(archive_path: Path, root: Path, max_bytes: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise RuntimeError("Isolated media target is not empty")
    with tarfile.open(archive_path, "r:gz") as archive:
        members = safe_members(archive, max_bytes)
        archive.extractall(root, members=members, filter="data")


def resolve_key(root: Path, key: str) -> Path:
    path = (root / key).resolve()
    if not path.is_relative_to(root.resolve()):
        raise RuntimeError("Database contains an unsafe media key")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_records(root: Path) -> None:
    count = 0
    for raw_line in sys.stdin:
        count += 1
        if count > MAX_MEMBERS:
            raise RuntimeError("Database contains too many media records")
        kind, checksum, original_key, preview_key = raw_line.rstrip("\n").split("\t")
        original = resolve_key(root, original_key)
        if not original.is_file():
            raise RuntimeError("A database media object is missing")
        if kind == "submission":
            if len(checksum) != 64 or sha256(original) != checksum:
                raise RuntimeError("A restored media checksum does not match")
            if not resolve_key(root, preview_key).is_file():
                raise RuntimeError("A database media preview is missing")
        elif kind != "published":
            raise RuntimeError("Unknown media record kind")


def main() -> None:
    args = parse_args()
    extract(args.archive, args.root, args.max_bytes)
    verify_records(args.root)


if __name__ == "__main__":
    main()
