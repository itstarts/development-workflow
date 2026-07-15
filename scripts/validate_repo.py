#!/usr/bin/env python3
"""Validate the development-workflow repository without network access."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Optional, Sequence


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
EVALUATION_SENSITIVE_PATTERN = re.compile(
    r"/Users/|OPENAI_API_KEY\s*[:=]\s*\S+|(?:^|[^A-Za-z])sk-[A-Za-z0-9]{10}|(?:task|thread)[_ /-]?id\s*[:=]\s*[\"']?[0-9a-f-]{8,}",
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


def stage_skill_payloads(skill_roots: Sequence[Path], codex_home: Path) -> None:
    """Stage publishable skill files without overwriting an existing skill."""
    destinations = [codex_home / "skills" / skill_root.name for skill_root in skill_roots]
    existing = [destination for destination in destinations if destination.exists()]
    if existing:
        raise FileExistsError(f"skill destination already exists: {existing[0]}")

    for skill_root, destination in zip(skill_roots, destinations):
        for source in production_files(skill_root):
            target = destination / source.relative_to(skill_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def load_structured_result(
    path: Path, label: str, errors: list[str]
) -> Optional[dict]:
    if not path.is_file():
        errors.append(f"{PLANNED_SKILL}: {label} result is required")
        return None
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        errors.append(f"{PLANNED_SKILL}: {label} result is malformed")
        return None
    if not isinstance(result, dict):
        errors.append(f"{PLANNED_SKILL}: {label} result is malformed")
        return None
    return result


def validate() -> list[str]:
    errors: list[str] = []

    for relative in REQUIRED_ROOT_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    docs_root = ROOT / "docs"
    if docs_root.is_dir():
        unsupported_docs_namespaces = sorted(
            path.name
            for path in docs_root.iterdir()
            if path.is_dir() and path.name not in {"specs", "plans"}
        )
        for namespace in unsupported_docs_namespaces:
            errors.append(f"unsupported docs namespace: docs/{namespace}")

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
        evaluation_root = ROOT / "evaluations" / PLANNED_SKILL
        rubric_path = evaluation_root / "rubric.json"
        rubric_payload = None
        if rubric_path.is_file():
            try:
                rubric_payload = json.loads(rubric_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                errors.append(f"{PLANNED_SKILL}: rubric is malformed")
            else:
                if not isinstance(rubric_payload, dict) or not isinstance(
                    rubric_payload.get("criteria"), list
                ):
                    errors.append(f"{PLANNED_SKILL}: rubric is malformed")
        else:
            errors.append(f"{PLANNED_SKILL}: rubric is required")

        expected_case_criteria: dict[str, set[str]] = {}
        if isinstance(rubric_payload, dict):
            for criterion in rubric_payload.get("criteria", []):
                if not isinstance(criterion, dict):
                    continue
                criterion_id = criterion.get("id")
                applies_to = criterion.get("applies_to")
                if not isinstance(criterion_id, str) or not isinstance(applies_to, list):
                    continue
                for case_id in applies_to:
                    if isinstance(case_id, str):
                        expected_case_criteria.setdefault(case_id, set()).add(criterion_id)

        audit_path = evaluation_root / "baseline" / "pre-creation-audit.json"
        audit = load_structured_result(audit_path, "pre-creation audit", errors)
        if audit is not None:
            if audit.get("evidence_role") != "pre-creation-audit":
                errors.append(
                    f"{PLANNED_SKILL}: pre-creation audit evidence_role is invalid"
                )
            if audit.get("red_observed") is not True:
                errors.append(f"{PLANNED_SKILL}: pre-creation audit must record RED")
            recorded_valid_red = audit.get("valid_red_cases")
            if (
                not isinstance(recorded_valid_red, list)
                or not recorded_valid_red
                or not all(isinstance(case_id, str) for case_id in recorded_valid_red)
            ):
                errors.append(
                    f"{PLANNED_SKILL}: pre-creation audit needs valid RED cases"
                )

        baseline_path = (
            evaluation_root
            / "baseline"
            / "result.json"
        )
        baseline = load_structured_result(baseline_path, "baseline", errors)
        if baseline is not None:
            if baseline.get("evidence_role") != "migration-baseline":
                errors.append(
                    f"{PLANNED_SKILL}: baseline evidence_role must be migration-baseline"
                )
            if baseline.get("all_runs_valid") is not True:
                errors.append(f"{PLANNED_SKILL}: migration baseline runs must be valid")
            if baseline.get("failures_observed") is not True:
                errors.append(f"{PLANNED_SKILL}: migration baseline must record failures")

        migration_red_path = evaluation_root / "migration-red" / "result.json"
        migration_red = load_structured_result(
            migration_red_path, "migration-red", errors
        )
        if migration_red is not None:
            if migration_red.get("evidence_role") != "current-skill-red":
                errors.append(
                    f"{PLANNED_SKILL}: migration-red evidence_role must be current-skill-red"
                )
            if migration_red.get("red_observed") is not True:
                errors.append(f"{PLANNED_SKILL}: migration-red must record RED")
            if migration_red.get("valid") is not True:
                errors.append(f"{PLANNED_SKILL}: migration-red run must be valid")
            selected_red_case = migration_red.get("selected_case")
            failed_criteria = migration_red.get("failed_criteria")
            if (
                not isinstance(selected_red_case, str)
                or not isinstance(failed_criteria, list)
                or not failed_criteria
                or not (
                    evaluation_root
                    / "migration-red"
                    / f"{selected_red_case}-output.md"
                ).is_file()
            ):
                errors.append(
                    f"{PLANNED_SKILL}: migration-red selected case evidence is incomplete"
                )

        green_path = (
            evaluation_root
            / "green"
            / "result.json"
        )
        green = load_structured_result(green_path, "green", errors)
        if green is not None:
            if green.get("evidence_role") != "green":
                errors.append(f"{PLANNED_SKILL}: green evidence_role must be green")
            if green.get("all_runs_valid") is not True:
                errors.append(f"{PLANNED_SKILL}: green runs must all be valid")
            if green.get("all_required_passed") is not True:
                errors.append(
                    f"{PLANNED_SKILL}: green result must record all_required_passed true"
                )
            if green.get("review_status") != "approved":
                errors.append(
                    f"{PLANNED_SKILL}: green evidence must have approved independent review"
                )

            cases = green.get("cases")
            case_map = {
                case.get("id"): case
                for case in cases
                if isinstance(case, dict) and isinstance(case.get("id"), str)
            } if isinstance(cases, list) else {}
            if set(case_map) != set(expected_case_criteria) or len(case_map) != len(
                cases if isinstance(cases, list) else []
            ):
                errors.append(
                    f"{PLANNED_SKILL}: green cases must exactly match the rubric"
                )
            else:
                for case_id, expected_criteria in expected_case_criteria.items():
                    case = case_map[case_id]
                    if case.get("valid") is not True:
                        errors.append(f"{PLANNED_SKILL}: green case {case_id} is invalid")
                    passed = case.get("passed_criteria")
                    if not isinstance(passed, list) or set(passed) != expected_criteria:
                        errors.append(
                            f"{PLANNED_SKILL}: green case {case_id} criteria are incomplete"
                        )

        if evaluation_root.is_dir():
            for path in sorted(evaluation_root.rglob("*")):
                if not path.is_file():
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    errors.append(
                        f"{path.relative_to(ROOT)}: evaluation evidence must be UTF-8 text"
                    )
                    continue
                if EVALUATION_SENSITIVE_PATTERN.search(text):
                    errors.append(
                        f"{path.relative_to(ROOT)}: evaluation evidence contains sensitive or machine-local text"
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
