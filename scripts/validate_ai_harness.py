#!/usr/bin/env python3
"""Validate the independent Codex and Claude harnesses."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11 local tooling
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
AGENTS = {"backend-engineer", "frontend-engineer", "test-reviewer", "infra-reviewer", "code-reviewer"}
SKILLS = {
    "project-ai-feature", "project-backend-ddd", "project-frontend-module",
    "project-production-infra", "project-quality-gate", "project-testing",
    "project-product-manager", "project-business-analyst",
    "team-agent-orchestration", "ui-ux-pro-max",
}
CONCEPTS = {
    "subagent", "KISS", "YAGNI", "SOLID", "DRY", "600", "repository",
    "Unit of Work", "mobile-first", "compose.yaml", "project-product-manager",
    "project-business-analyst", "team-agent-orchestration", "ui-ux-pro-max",
}


def main() -> int:
    errors: list[str] = []
    codex_path = ROOT / ".codex/config.toml"
    claude_path = ROOT / ".claude/CLAUDE.md"
    for path in (codex_path, claude_path):
        if not path.is_file():
            errors.append(f"missing harness rules: {path.relative_to(ROOT)}")

    codex_rules = ""
    if codex_path.is_file():
        try:
            with codex_path.open("rb") as handle:
                codex_rules = str(tomllib.load(handle).get("developer_instructions", ""))
        except tomllib.TOMLDecodeError as exc:
            errors.append(f"invalid .codex/config.toml: {exc}")
    claude_rules = claude_path.read_text(encoding="utf-8") if claude_path.is_file() else ""
    for concept in CONCEPTS:
        if concept.lower() not in codex_rules.lower():
            errors.append(f"Codex rules miss concept: {concept}")
        if concept.lower() not in claude_rules.lower():
            errors.append(f"Claude rules miss concept: {concept}")

    forbidden = [
        *ROOT.glob("AGENTS.md"), *ROOT.glob("CLAUDE.md"),
        *ROOT.glob("backend/**/AGENTS.md"), *ROOT.glob("backend/**/CLAUDE.md"),
        *ROOT.glob("frontend/**/AGENTS.md"), *ROOT.glob("frontend/**/CLAUDE.md"),
    ]
    for path in forbidden:
        errors.append(f"scattered rule file is forbidden: {path.relative_to(ROOT)}")

    codex_agents = {path.stem for path in (ROOT / ".codex/agents").glob("*.toml")}
    claude_agents = {path.stem for path in (ROOT / ".claude/agents").glob("*.md")}
    for name in sorted(AGENTS - codex_agents):
        errors.append(f"missing Codex subagent: {name}")
    for name in sorted(AGENTS - claude_agents):
        errors.append(f"missing Claude subagent: {name}")
    for path in (ROOT / ".codex/agents").glob("*.toml"):
        with path.open("rb") as handle:
            agent = tomllib.load(handle)
        if ".codex/config.toml" not in str(agent.get("developer_instructions", "")):
            errors.append(f"Codex subagent does not load strict rules: {path.name}")
    for path in (ROOT / ".claude/agents").glob("*.md"):
        if ".claude/CLAUDE.md" not in path.read_text(encoding="utf-8"):
            errors.append(f"Claude subagent does not load strict rules: {path.name}")

    codex_skills = {path.parent.name for path in (ROOT / ".codex/skills").glob("*/SKILL.md")}
    for name in sorted(SKILLS - codex_skills):
        errors.append(f"missing project skill: {name}")
    for name in sorted(codex_skills):
        if not (ROOT / ".claude/skills" / name).exists():
            errors.append(f"missing Claude skill link: {name}")

    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    print("AI harness validation passed: strict independent rules, subagents, and skills are wired.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
