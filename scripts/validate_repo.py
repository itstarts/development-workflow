#!/usr/bin/env python3
"""Validate the development-workflow repository without network access."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "evaluations" / "registry.json"
MANAGED_PROFILES = {"creation-only", "creation-plus-current-red"}
MANAGED_STAGES = {"baseline-only", "implemented", "review-approved"}
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
    path: Path, skill_name: str, label: str, errors: list[str]
) -> Optional[dict]:
    if not path.is_file():
        errors.append(f"{skill_name}: {label} result is required")
        return None
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        errors.append(f"{skill_name}: {label} result is malformed")
        return None
    if not isinstance(result, dict):
        errors.append(f"{skill_name}: {label} result is malformed")
        return None
    return result


def load_evaluation_registry(errors: list[str]) -> dict[str, dict[str, str]]:
    if not REGISTRY_PATH.is_file():
        errors.append("evaluation registry is required")
        return {}
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        errors.append("evaluation registry is malformed")
        return {}
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        errors.append("evaluation registry is malformed")
        return {}
    skills = payload.get("skills")
    if not isinstance(skills, dict):
        errors.append("evaluation registry is malformed")
        return {}
    result: dict[str, dict[str, str]] = {}
    for skill_name, entry in skills.items():
        if not isinstance(skill_name, str) or not isinstance(entry, dict):
            errors.append("evaluation registry is malformed")
            continue
        mode = entry.get("evaluation_mode")
        profile = entry.get("evidence_profile")
        stage = entry.get("stage")
        if mode == "managed":
            if profile not in MANAGED_PROFILES or stage not in MANAGED_STAGES:
                errors.append(f"{skill_name}: evaluation registry entry is invalid")
                continue
        elif mode == "imported":
            if profile != "imported-reviewed" or stage != "review-approved":
                errors.append(f"{skill_name}: evaluation registry entry is invalid")
                continue
        else:
            errors.append(f"{skill_name}: evaluation registry entry is invalid")
            continue
        result[skill_name] = {
            "evaluation_mode": mode,
            "evidence_profile": profile,
            "stage": stage,
        }
    return result


def validate_managed_evaluation(
    skill_name: str,
    profile: str,
    stage: str,
    evidence_only: bool,
    errors: list[str],
) -> None:
    evaluation_root = ROOT / "evaluations" / skill_name
    skill_root = ROOT / "skills" / skill_name
    if stage == "baseline-only" and skill_root.exists():
        errors.append(f"{skill_name}: baseline-only stage cannot expose a skill")
    if stage != "baseline-only" and not (skill_root / "SKILL.md").is_file():
        errors.append(f"{skill_name}: implemented stage requires the skill")

    rubric_path = evaluation_root / "rubric.json"
    rubric_payload = None
    if rubric_path.is_file():
        try:
            rubric_payload = json.loads(rubric_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors.append(f"{skill_name}: rubric is malformed")
        else:
            if not isinstance(rubric_payload, dict) or not isinstance(
                rubric_payload.get("criteria"), list
            ):
                errors.append(f"{skill_name}: rubric is malformed")
    else:
        errors.append(f"{skill_name}: rubric is required")

    expected_case_criteria: dict[str, set[str]] = {}
    rubric_criteria = (
        rubric_payload.get("criteria", [])
        if isinstance(rubric_payload, dict)
        and isinstance(rubric_payload.get("criteria"), list)
        else []
    )
    for criterion in rubric_criteria:
        if not isinstance(criterion, dict):
            continue
        criterion_id = criterion.get("id")
        applies_to = criterion.get("applies_to")
        if not isinstance(criterion_id, str) or not isinstance(applies_to, list):
            continue
        for case_id in applies_to:
            if isinstance(case_id, str):
                expected_case_criteria.setdefault(case_id, set()).add(criterion_id)
    case_file_ids: list[str] = []
    for case_path in sorted((evaluation_root / "cases").glob("*.md")):
        match = re.match(r"([0-9]+)-", case_path.name)
        if match is None:
            errors.append(f"{skill_name}: case filename is malformed: {case_path.name}")
            continue
        case_file_ids.append(match.group(1))
    if set(case_file_ids) != set(expected_case_criteria) or len(case_file_ids) != len(
        expected_case_criteria
    ):
        errors.append(f"{skill_name}: case files must exactly match the rubric")

    audit = load_structured_result(
        evaluation_root / "baseline" / "pre-creation-audit.json",
        skill_name,
        "pre-creation audit",
        errors,
    )
    if audit is not None:
        if audit.get("evidence_role") != "pre-creation-audit":
            errors.append(f"{skill_name}: pre-creation audit evidence_role is invalid")
        if audit.get("red_observed") is not True:
            errors.append(f"{skill_name}: pre-creation audit must record RED")
        recorded_valid_red = audit.get("valid_red_cases")
        valid_audit_cases = (
            isinstance(recorded_valid_red, list)
            and bool(recorded_valid_red)
            and all(isinstance(case_id, str) for case_id in recorded_valid_red)
        )
        if not valid_audit_cases:
            errors.append(f"{skill_name}: pre-creation audit needs valid RED cases")
        audit_ids = set(recorded_valid_red) if valid_audit_cases else set()
        audit_cases = audit.get("cases")
        if not isinstance(audit_cases, list):
            errors.append(f"{skill_name}: pre-creation audit cases are malformed")

    baseline = load_structured_result(
        evaluation_root / "baseline" / "result.json",
        skill_name,
        "baseline",
        errors,
    )
    if baseline is not None:
        if baseline.get("evidence_role") != "migration-baseline":
            errors.append(
                f"{skill_name}: baseline evidence_role must be migration-baseline"
            )
        if baseline.get("all_runs_valid") is not True:
            errors.append(f"{skill_name}: migration baseline runs must be valid")
        if baseline.get("failures_observed") is not True:
            errors.append(f"{skill_name}: migration baseline must record failures")

    baseline_case_map: dict[str, dict] = {}
    baseline_failed = False
    if baseline is not None:
        baseline_cases = baseline.get("cases")
        if isinstance(baseline_cases, list):
            for case in baseline_cases:
                if not isinstance(case, dict) or not isinstance(case.get("id"), str):
                    errors.append(f"{skill_name}: baseline cases are malformed")
                    continue
                case_id = case["id"]
                if case_id in baseline_case_map:
                    errors.append(f"{skill_name}: baseline cases are duplicated")
                    continue
                baseline_case_map[case_id] = case
                if case.get("valid") is not True:
                    errors.append(f"{skill_name}: baseline case {case_id} is invalid")
                failed = case.get("failed_criteria")
                if not isinstance(failed, list) or not all(
                    isinstance(item, str) for item in failed
                ):
                    errors.append(
                        f"{skill_name}: baseline case {case_id} failed criteria are malformed"
                    )
                    continue
                if not set(failed).issubset(expected_case_criteria.get(case_id, set())):
                    errors.append(
                        f"{skill_name}: baseline case {case_id} failed criteria are unknown"
                    )
                baseline_failed = baseline_failed or bool(failed)
        else:
            errors.append(f"{skill_name}: baseline cases are malformed")

        baseline_case_ids = set(baseline_case_map)
        expected_case_ids = set(expected_case_criteria)
        if profile == "creation-only" and baseline_case_ids != expected_case_ids:
            errors.append(f"{skill_name}: baseline cases must exactly match the rubric")
        if profile == "creation-plus-current-red" and not baseline_case_ids.issubset(
            expected_case_ids
        ):
            errors.append(
                f"{skill_name}: baseline cases must be a subset of the current rubric"
            )
        if baseline.get("failures_observed") is True and not baseline_failed:
            errors.append(f"{skill_name}: migration baseline has no observed case failure")
        for case_id in baseline_case_map:
            if not (evaluation_root / "baseline" / f"{case_id}-output.md").is_file():
                errors.append(f"{skill_name}: baseline case {case_id} output is required")

    if audit is not None and baseline is not None:
        if not audit_ids.issubset(set(baseline_case_map)):
            errors.append(f"{skill_name}: pre-creation audit cases must exist in baseline")

    if profile == "creation-plus-current-red":
        migration_red = load_structured_result(
            evaluation_root / "migration-red" / "result.json",
            skill_name,
            "migration-red",
            errors,
        )
        if migration_red is not None:
            if migration_red.get("evidence_role") != "current-skill-red":
                errors.append(
                    f"{skill_name}: migration-red evidence_role must be current-skill-red"
                )
            if migration_red.get("red_observed") is not True:
                errors.append(f"{skill_name}: migration-red must record RED")
            if migration_red.get("valid") is not True:
                errors.append(f"{skill_name}: migration-red run must be valid")
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
                    f"{skill_name}: migration-red selected case evidence is incomplete"
                )
            elif not set(failed_criteria).issubset(
                expected_case_criteria.get(selected_red_case, set())
            ):
                errors.append(
                    f"{skill_name}: migration-red failed criteria are unknown"
                )

    if stage != "baseline-only":
        green = load_structured_result(
            evaluation_root / "green" / "result.json",
            skill_name,
            "green",
            errors,
        )
        if green is not None:
            if green.get("evidence_role") != "green":
                errors.append(f"{skill_name}: green evidence_role must be green")
            if green.get("all_runs_valid") is not True:
                errors.append(f"{skill_name}: green runs must all be valid")
            if green.get("all_required_passed") is not True:
                errors.append(
                    f"{skill_name}: green result must record all_required_passed true"
                )
            if stage == "review-approved" and green.get("review_status") != "approved":
                errors.append(
                    f"{skill_name}: green evidence must have approved independent review"
                )
            if stage == "review-approved" and (
                not isinstance(green.get("reviewer"), str)
                or not green.get("reviewer", "").strip()
                or not isinstance(green.get("reviewed_at"), str)
                or re.fullmatch(r"\d{4}-\d{2}-\d{2}", green.get("reviewed_at", ""))
                is None
            ):
                errors.append(
                    f"{skill_name}: green evidence approval metadata is incomplete"
                )
            if stage == "implemented" and not evidence_only:
                errors.append(f"{skill_name}: implemented evidence is not review-approved")

            cases = green.get("cases")
            case_map = {
                case.get("id"): case
                for case in cases
                if isinstance(case, dict) and isinstance(case.get("id"), str)
            } if isinstance(cases, list) else {}
            if set(case_map) != set(expected_case_criteria) or len(case_map) != len(
                cases if isinstance(cases, list) else []
            ):
                errors.append(f"{skill_name}: green cases must exactly match the rubric")
            else:
                for case_id, expected_criteria in expected_case_criteria.items():
                    case = case_map[case_id]
                    if not (
                        evaluation_root / "green" / f"{case_id}-output.md"
                    ).is_file():
                        errors.append(
                            f"{skill_name}: green case {case_id} output is required"
                        )
                    if case.get("valid") is not True:
                        errors.append(f"{skill_name}: green case {case_id} is invalid")
                    passed = case.get("passed_criteria")
                    if (
                        not isinstance(passed, list)
                        or not all(isinstance(item, str) for item in passed)
                        or set(passed) != expected_criteria
                    ):
                        errors.append(
                            f"{skill_name}: green case {case_id} criteria are incomplete"
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


def validate(evidence_only: Optional[str] = None) -> list[str]:
    errors: list[str] = []

    for relative in REQUIRED_ROOT_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    docs_root = ROOT / "docs"
    if docs_root.is_dir():
        unsupported_docs_namespaces = sorted(
            path.name
            for path in docs_root.iterdir()
            if path.is_dir() and path.name not in {"requirements", "specs", "plans"}
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
    registry = load_evaluation_registry(errors)
    if evidence_only is not None:
        entry = registry.get(evidence_only)
        if entry is None or entry.get("evaluation_mode") != "managed":
            errors.append(f"{evidence_only}: evidence-only target is not managed")
        elif entry.get("stage") != "implemented":
            errors.append(f"{evidence_only}: evidence-only requires implemented stage")

    for skill_name, entry in registry.items():
        if entry["evaluation_mode"] != "managed":
            continue
        if evidence_only is not None and skill_name != evidence_only:
            continue
        validate_managed_evaluation(
            skill_name,
            entry["evidence_profile"],
            entry["stage"],
            evidence_only == skill_name,
            errors,
        )

    evaluation_dirs = {
        path.name
        for path in (ROOT / "evaluations").iterdir()
        if path.is_dir() and path.name != "__pycache__"
    }
    managed_names = {
        name
        for name, entry in registry.items()
        if entry["evaluation_mode"] == "managed"
    }
    for orphan in sorted(evaluation_dirs - managed_names):
        errors.append(f"{orphan}: orphan evaluation evidence is not registered")

    active_skills = sorted(
        path
        for path in skills_root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )
    if not active_skills:
        errors.append("no active skill found")

    active_skill_names = {path.name for path in active_skills}
    for unregistered in sorted(active_skill_names - set(registry)):
        errors.append(f"{unregistered}: active skill is not registered")
    for missing in sorted(
        name
        for name, entry in registry.items()
        if entry["stage"] != "baseline-only" and name not in active_skill_names
    ):
        errors.append(f"{missing}: registered skill is missing")

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


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-only")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    errors = validate(args.evidence_only)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
