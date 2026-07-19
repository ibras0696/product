#!/usr/bin/env python3
"""Enforce repository source-file size limits without counting generated code."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WARNING_LIMIT = 400
HARD_LIMIT = 600

SOURCE_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".jsx",
    ".mjs",
    ".mts",
    ".cjs",
    ".cts",
    ".py",
    ".sql",
    ".scss",
    ".sh",
    ".ts",
    ".tsx",
    ".vue",
    ".conf",
    ".yaml",
    ".yml",
}
EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "coverage",
    "dist",
    "htmlcov",
    "migrations",
    "node_modules",
    "playwright-report",
    "test-results",
}
EXCLUDED_PATH_SEQUENCES = {
    (".codex", "skills", "ui-ux-pro-max"),  # audited third-party design dataset/tooling
    ("shared", "api", "generated"),
    ("src", "generated"),
}
GENERATED_FILES = {Path("frontend/src/shared/api/schema.d.ts")}


def is_source_file(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if relative in GENERATED_FILES:
        return False
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    for sequence in EXCLUDED_PATH_SEQUENCES:
        width = len(sequence)
        if any(
            tuple(relative.parts[index : index + width]) == sequence
            for index in range(len(relative.parts) - width + 1)
        ):
            return False
    return path.suffix in SOURCE_SUFFIXES or path.name.startswith("Dockerfile")


def count_code_lines(path: Path) -> int:
    count = 0
    in_block_comment = False
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if in_block_comment:
            if "*/" in line:
                in_block_comment = False
            continue
        if line.startswith("/*"):
            in_block_comment = "*/" not in line[2:]
            continue
        if not line or line.startswith(("#", "//", "<!--", "*")):
            continue
        count += 1
    return count


def main() -> int:
    warnings: list[tuple[Path, int]] = []
    failures: list[tuple[Path, int]] = []

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or not is_source_file(path):
            continue
        lines = count_code_lines(path)
        if lines > HARD_LIMIT:
            failures.append((path, lines))
        elif lines > WARNING_LIMIT:
            warnings.append((path, lines))

    for path, lines in warnings:
        print(f"WARNING {path.relative_to(ROOT)}: {lines} code lines (review at {WARNING_LIMIT})")
    for path, lines in failures:
        print(f"ERROR {path.relative_to(ROOT)}: {lines} code lines (hard limit {HARD_LIMIT})")

    if failures:
        return 1
    print(f"File-size check passed: no source file exceeds {HARD_LIMIT} code lines.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
