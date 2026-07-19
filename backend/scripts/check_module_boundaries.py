#!/usr/bin/env python3
"""Reject deep imports across backend bounded contexts."""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"


@dataclass(frozen=True, slots=True)
class Violation:
    path: Path
    line: int
    imported: str

    def render(self, root: Path) -> str:
        return f"{self.path.relative_to(root)}:{self.line}: forbidden deep import {self.imported}"


def find_violations(root: Path = SOURCE_ROOT) -> list[Violation]:
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        source_context = _source_context(path, root)
        if source_context is None and path != root / "router.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for imported, line in _absolute_imports(tree):
            target_context = _target_context(imported)
            if target_context is None or target_context == source_context:
                continue
            public_contracts = {
                f"modules.{target_context}.public",
                f"modules.{target_context}.contracts",
            }
            if imported not in public_contracts:
                violations.append(Violation(path, line, imported))
    return violations


def _source_context(path: Path, root: Path) -> str | None:
    relative = path.relative_to(root)
    if len(relative.parts) >= 3 and relative.parts[0] == "modules":
        return relative.parts[1]
    return None


def _target_context(imported: str) -> str | None:
    parts = imported.split(".")
    return parts[1] if len(parts) >= 2 and parts[0] == "modules" else None


def _absolute_imports(tree: ast.AST) -> list[tuple[str, int]]:
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            imports.append((node.module, node.lineno))
    return imports


def main() -> int:
    violations = find_violations()
    if violations:
        for violation in violations:
            print(violation.render(SOURCE_ROOT), file=sys.stderr)
        return 1
    print("Backend public module-boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
