#!/usr/bin/env python3
"""Validate the development-workflow repository without network access."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLANNED_SKILL = "creating-development-specs-and-plans"
REQUIRED_ROOT_FILES = (
    "AGENTS.md",
    "skills/AGENTS.md",
    "tests/AGENTS.md",
    "evaluations/AGENTS.md",
    ".codex-plugin/plugin.json",
    ".codex/agents/skill-reviewer.toml",
    ".codex/agents/final-reviewer.toml",
    ".codex/agents/workflow-final-reviewer.toml",
    "README.md",
    "CHANGELOG.md",
    "requirements-dev.txt",
)
PRODUCTION_DIRS = ("agents", "assets", "references", "scripts")
NON_PUBLISHABLE_DIR_NAMES = {"__pycache__"}
NON_PUBLISHABLE_FILE_NAMES = {".DS_Store"}
NON_PUBLISHABLE_FILE_SUFFIXES = {".pyc", ".pyo", ".pyd"}
PLACEHOLDER_PATTERN = re.compile(
    r"\b(?:TODO|TBD|PLACEHOLDER|example_(?:script|reference|asset))\b",
    re.IGNORECASE,
)


def load_skill_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing frontmatter at byte zero")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"{path}: unclosed frontmatter")
    fields: dict[str, str] = {}
    for raw_line in text[4:end].splitlines():
        if ":" not in raw_line:
            raise ValueError(f"{path}: invalid frontmatter line {raw_line!r}")
        key, value = raw_line.split(":", 1)
        fields[key.strip()] = value.strip()
    if set(fields) != {"name", "description"}:
        raise ValueError(f"{path}: frontmatter must contain only name and description")
    return fields


def production_files(skill_root: Path) -> list[Path]:
    found = {skill_root / "SKILL.md"}
    for directory_name in PRODUCTION_DIRS:
        directory = skill_root / directory_name
        if directory.is_dir():
            found.update(
                path
                for path in directory.rglob("*")
                if path.is_file()
                and not NON_PUBLISHABLE_DIR_NAMES.intersection(
                    path.relative_to(directory).parts[:-1]
                )
                and path.name not in NON_PUBLISHABLE_FILE_NAMES
                and path.suffix.lower() not in NON_PUBLISHABLE_FILE_SUFFIXES
            )
    return sorted(found)


def validate() -> list[str]:
    errors: list[str] = []

    for relative in REQUIRED_ROOT_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    manifest_path = ROOT / ".codex-plugin" / "plugin.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid plugin manifest: {exc}")
        else:
            if manifest.get("name") != "development-workflow":
                errors.append("plugin name must be development-workflow")
            if manifest.get("skills") != "./skills/":
                errors.append("plugin skills path must be ./skills/")
            if not re.fullmatch(r"\d+\.\d+\.\d+", str(manifest.get("version", ""))):
                errors.append("plugin version must be strict semver")

    skills_root = ROOT / "skills"
    planned = skills_root / PLANNED_SKILL
    if planned.exists():
        errors.append(
            f"{PLANNED_SKILL} must not enter plugin skills before the baseline gate"
        )

    active_skills = sorted(
        path
        for path in skills_root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )
    if not active_skills:
        errors.append("no active skill found")

    for skill_root in active_skills:
        try:
            fields = load_skill_frontmatter(skill_root / "SKILL.md")
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue
        if fields["name"] != skill_root.name:
            errors.append(f"{skill_root.name}: directory and frontmatter name differ")
        if not fields["description"].startswith("Use when"):
            errors.append(f"{skill_root.name}: description must start with 'Use when'")
        if not (skill_root / "agents" / "openai.yaml").is_file():
            errors.append(f"{skill_root.name}: missing agents/openai.yaml")
        for path in production_files(skill_root):
            if path.is_symlink():
                errors.append(f"{path.relative_to(ROOT)}: symlinks are not publishable")
                continue
            text = path.read_text(encoding="utf-8")
            if PLACEHOLDER_PATTERN.search(text):
                errors.append(f"{path.relative_to(ROOT)}: placeholder text remains")
            if "/Users/" in text or "~/.codex/plugins/cache/" in text:
                errors.append(f"{path.relative_to(ROOT)}: machine-local path remains")

    asset_path = (
        skills_root
        / "generating-development-prompts"
        / "assets"
        / "final-reviewer.toml"
    )
    project_role_path = ROOT / ".codex" / "agents" / "final-reviewer.toml"
    if asset_path.is_file() and project_role_path.is_file():
        if asset_path.read_bytes() != project_role_path.read_bytes():
            errors.append("project final-reviewer must match the bundled skill asset")

    for role_name in ("skill-reviewer", "final-reviewer", "workflow-final-reviewer"):
        path = ROOT / ".codex" / "agents" / f"{role_name}.toml"
        if not path.is_file():
            continue
        role_text = path.read_text(encoding="utf-8")
        if not re.search(
            r'^sandbox_mode\s*=\s*"read-only"\s*$',
            role_text,
            re.MULTILINE,
        ):
            errors.append(f"{path.relative_to(ROOT)}: sandbox_mode must be read-only")
        if re.search(
            r"^(?:model|model_reasoning_effort)\s*=",
            role_text,
            re.MULTILINE,
        ):
            errors.append(f"{path.relative_to(ROOT)}: model and effort must remain unpinned")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
