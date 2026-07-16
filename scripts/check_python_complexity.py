#!/usr/bin/env python3
"""Enforce hard Python function-size and decision-complexity limits."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MAX_FUNCTION_LINES = 80
MAX_COMPLEXITY = 10
EXCLUDED_PARTS = {".venv", "__pycache__", "migrations"}


class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.value = 1

    def visit_If(self, node: ast.If) -> None:
        self.value += 1
        self.generic_visit(node)

    visit_IfExp = visit_If
    visit_For = visit_If
    visit_AsyncFor = visit_If
    visit_While = visit_If
    visit_Assert = visit_If

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.value += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        self.value += len(node.handlers) + bool(node.orelse) + bool(node.finalbody)
        self.generic_visit(node)

    visit_TryStar = visit_Try

    def visit_Match(self, node: ast.Match) -> None:
        self.value += max(0, len(node.cases) - 1)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.value += len(node.ifs)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef


def iter_functions(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def main() -> int:
    failures: list[str] = []
    if not BACKEND.exists():
        print("Python complexity check skipped: backend directory is absent.")
        return 0

    for path in sorted(BACKEND.rglob("*.py")):
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as error:
            failures.append(f"{path.relative_to(ROOT)}:{error.lineno}: syntax error: {error.msg}")
            continue
        for function in iter_functions(tree):
            end_line = function.end_lineno or function.lineno
            length = end_line - function.lineno + 1
            visitor = ComplexityVisitor()
            for statement in function.body:
                visitor.visit(statement)
            location = f"{path.relative_to(ROOT)}:{function.lineno} {function.name}"
            if length > MAX_FUNCTION_LINES:
                failures.append(f"{location}: {length} lines exceeds {MAX_FUNCTION_LINES}")
            if visitor.value > MAX_COMPLEXITY:
                failures.append(f"{location}: complexity {visitor.value} exceeds {MAX_COMPLEXITY}")

    if failures:
        for failure in failures:
            print(f"ERROR {failure}")
        return 1
    print("Python function-size and complexity check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
