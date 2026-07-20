#!/usr/bin/env python3
"""Validate the development-workflow repository without network access."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "evaluations" / "registry.json"
MANAGED_PROFILES = {"creation-only", "creation-plus-current-red"}
IMPORTED_PROFILES = {"imported-reviewed", "imported-plus-current-red"}
MANAGED_STAGES = {"baseline-only", "implemented", "review-approved"}
REQUIRED_ROOT_FILES = (
    "AGENTS.md",
    "skills/AGENTS.md",
    "tests/AGENTS.md",
    "evaluations/AGENTS.md",
    ".codex-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
    ".codex/agents/skill-reviewer.toml",
    ".codex/agents/final-reviewer.toml",
    ".codex/agents/workflow-final-reviewer.toml",
    "README.md",
    "docs/release-notes.md",
    "CHANGELOG.md",
    "requirements-dev.txt",
)
PUBLIC_SKILL_DOCUMENTS = (
    "README.md",
    "docs/install.md",
    "docs/workflow.md",
    "docs/agent-development.md",
    "CHANGELOG.md",
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
    r"OPENAI_API_KEY\s*[:=]\s*\S+|(?:^|[^A-Za-z])sk-[A-Za-z0-9]{10}|(?:task|thread)[_ /-]?id\s*[:=]\s*[\"']?[0-9a-f-]{8,}",
    re.IGNORECASE,
)
EVALUATION_MACHINE_LOCAL_PATH_PATTERN = re.compile(
    r"(?:"
    r"(?:[A-Za-z]:)?[\\/]+Users[\\/]+"
    r"|/(?:private/)?var/folders/"
    r"|/(?:private/)?tmp/"
    r"|/home/[^/\s]+/"
    r")",
    re.IGNORECASE,
)
EVALUATION_WORKSPACE_PATH_PATTERN = re.compile(r"/workspace/[A-Za-z0-9._~/-]+")
EVALUATION_SYNTHETIC_ROOT = "/workspace/fixture"


def contains_sensitive_or_machine_local_evaluation_text(text: str) -> bool:
    if EVALUATION_SENSITIVE_PATTERN.search(text):
        return True
    if EVALUATION_MACHINE_LOCAL_PATH_PATTERN.search(text):
        return True
    for match in EVALUATION_WORKSPACE_PATH_PATTERN.finditer(text):
        path = match.group(0).rstrip("/")
        if path != EVALUATION_SYNTHETIC_ROOT and not path.startswith(
            EVALUATION_SYNTHETIC_ROOT + "/"
        ):
            return True
    return False


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


def validate_plugin_marketplace(
    path: Path, manifest: Optional[dict], errors: list[str]
) -> None:
    try:
        marketplace = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid plugin marketplace: {exc}")
        return

    if not isinstance(marketplace, dict):
        errors.append("invalid plugin marketplace: root must be an object")
        return
    if marketplace.get("name") != "development-workflow":
        errors.append("invalid plugin marketplace: name must be development-workflow")
    interface = marketplace.get("interface")
    if not isinstance(interface, dict) or interface.get("displayName") != (
        "Development Workflow (dw)"
    ):
        errors.append("invalid plugin marketplace: displayName is missing or incorrect")

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1 or not isinstance(
        plugins[0] if plugins else None, dict
    ):
        errors.append("invalid plugin marketplace: exactly one plugin entry is required")
        return

    entry = plugins[0]
    manifest_name = manifest.get("name") if isinstance(manifest, dict) else None
    if entry.get("name") != "development-workflow" or (
        manifest_name is not None and entry.get("name") != manifest_name
    ):
        errors.append("invalid plugin marketplace: plugin name must match the manifest")
    manifest_version = manifest.get("version") if isinstance(manifest, dict) else None
    expected_ref = (
        f"v{manifest_version}"
        if isinstance(manifest_version, str) and manifest_version
        else None
    )
    if entry.get("source") != {
        "source": "url",
        "url": "https://github.com/itstarts/development-workflow.git",
        "ref": expected_ref,
    }:
        errors.append(
            "invalid plugin marketplace: Git source must use the manifest version tag"
        )
    if entry.get("policy") != {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }:
        errors.append("invalid plugin marketplace: install policy is missing or incorrect")
    if entry.get("category") != "Productivity":
        errors.append("invalid plugin marketplace: category must be Productivity")


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
            if profile not in IMPORTED_PROFILES or (
                profile == "imported-reviewed" and stage != "review-approved"
            ) or (
                profile == "imported-plus-current-red"
                and stage not in {"implemented", "review-approved"}
            ):
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


def rubric_case_criteria(
    evaluation_root: Path, skill_name: str, errors: list[str]
) -> dict[str, set[str]]:
    rubric_path = evaluation_root / "rubric.json"
    try:
        payload = json.loads(rubric_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    criteria = payload.get("criteria") if isinstance(payload, dict) else None
    if not isinstance(criteria, list):
        return {}
    result: dict[str, set[str]] = {}
    for criterion in criteria:
        if not isinstance(criterion, dict):
            continue
        criterion_id = criterion.get("id")
        applies_to = criterion.get("applies_to")
        if not isinstance(criterion_id, str) or not isinstance(applies_to, list):
            continue
        for case_id in applies_to:
            if isinstance(case_id, str):
                result.setdefault(case_id, set()).add(criterion_id)
    return result


def selected_case_file(evaluation_root: Path, case_id: str) -> Optional[Path]:
    candidates = sorted((evaluation_root / "cases").glob(f"{case_id}-*.md"))
    return candidates[0] if len(candidates) == 1 else None


def validate_fresh_cases(
    skill_name: str,
    evaluation_root: Path,
    expected_case_criteria: dict[str, set[str]],
    selected_red_case: Optional[str],
    green: dict,
    case_map: dict[str, dict],
    errors: list[str],
) -> list[str]:
    value = green.get("fresh_cases")
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) for item in value)
        or len(value) != len(set(value))
    ):
        errors.append(f"{skill_name}: green fresh_cases must be a non-empty unique list")
        return []
    if selected_red_case is not None and selected_red_case not in value:
        errors.append(f"{skill_name}: green fresh_cases must include the current RED case")
    for case_id in value:
        case_path = selected_case_file(evaluation_root, case_id)
        if (
            case_id not in expected_case_criteria
            or case_id not in case_map
            or case_path is None
            or not (evaluation_root / "green" / f"{case_id}-output.md").is_file()
        ):
            errors.append(f"{skill_name}: green fresh case {case_id} is incomplete")
    return value


def validate_managed_evaluation(
    skill_name: str,
    profile: str,
    stage: str,
    evidence_only: bool,
    errors: list[str],
    require_creation_evidence: bool = True,
) -> None:
    evaluation_root = ROOT / "evaluations" / skill_name
    skill_root = ROOT / "skills" / skill_name
    if require_creation_evidence and stage == "baseline-only" and (skill_root / "SKILL.md").is_file():
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

    audit = None
    baseline = None
    audit_ids: set[str] = set()
    if require_creation_evidence:
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

    selected_red_case: Optional[str] = None
    if profile in {"creation-plus-current-red", "imported-plus-current-red"}:
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
            if green.get("target_skill_loaded") is not True:
                errors.append(f"{skill_name}: green target skill must be loaded")
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
            if stage == "implemented" and green.get("review_status") != "pending":
                errors.append(
                    f"{skill_name}: implemented green evidence review must be pending"
                )
            if stage == "implemented" and (
                green.get("reviewer") is not None or green.get("reviewed_at") is not None
            ):
                errors.append(
                    f"{skill_name}: implemented green evidence must remove stale review metadata"
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
            if profile in {"creation-plus-current-red", "imported-plus-current-red"}:
                validate_fresh_cases(
                    skill_name,
                    evaluation_root,
                    expected_case_criteria,
                    selected_red_case,
                    green,
                    case_map,
                    errors,
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
            if contains_sensitive_or_machine_local_evaluation_text(text):
                errors.append(
                    f"{path.relative_to(ROOT)}: evaluation evidence contains sensitive or machine-local text"
                )


def run_git(args: Sequence[str], text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=text,
        capture_output=True,
        check=False,
    )


def git_worktree_available() -> bool:
    result = run_git(["rev-parse", "--is-inside-work-tree"])
    return result.returncode == 0 and result.stdout.strip() == "true"


def changed_paths() -> set[str]:
    paths: set[str] = set()
    for args in (
        ("diff", "--name-only", "--no-renames", "-z"),
        ("diff", "--cached", "--name-only", "--no-renames", "-z"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ):
        result = run_git(args, text=False)
        if result.returncode != 0:
            continue
        for raw in result.stdout.split(b"\0"):
            if raw:
                paths.add(raw.decode("utf-8", "surrogateescape"))
    return paths


def production_path_matches(path: str, skill_name: str) -> bool:
    prefix = f"skills/{skill_name}/"
    if not path.startswith(prefix):
        return False
    relative = path[len(prefix) :]
    if relative == "SKILL.md":
        return True
    return any(relative.startswith(f"{directory}/") for directory in PRODUCTION_DIRS)


def last_commit_for_paths(paths: Sequence[str]) -> Optional[str]:
    if not paths:
        return None
    result = run_git(
        [
            "log",
            "--full-history",
            "--simplify-merges",
            "--topo-order",
            "-1",
            "--format=%H",
            "HEAD",
            "--",
            *paths,
        ]
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def last_production_commit(skill_name: str) -> Optional[str]:
    result = run_git(
        ["log", "--format=@@%H", "--name-status", "--find-renames", "HEAD"]
    )
    if result.returncode != 0:
        return None
    current: Optional[str] = None
    for line in result.stdout.splitlines():
        if line.startswith("@@"):
            current = line[2:]
            continue
        if not current or "\t" not in line:
            continue
        fields = line.split("\t")
        paths = fields[1:]
        if any(production_path_matches(path, skill_name) for path in paths):
            return current
    return None


def is_ancestor(older: Optional[str], newer: Optional[str]) -> bool:
    if older is None or newer is None:
        return False
    result = run_git(["merge-base", "--is-ancestor", older, newer])
    return result.returncode == 0


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def freshness_evidence(skill_name: str) -> Optional[dict]:
    evaluation_root = ROOT / "evaluations" / skill_name
    try:
        red = json.loads(
            (evaluation_root / "migration-red" / "result.json").read_text(
                encoding="utf-8"
            )
        )
        green = json.loads(
            (evaluation_root / "green" / "result.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None
    selected = red.get("selected_case")
    fresh_cases = green.get("fresh_cases")
    if not isinstance(selected, str) or not isinstance(fresh_cases, list) or not all(
        isinstance(item, str) for item in fresh_cases
    ):
        return None
    case_path = selected_case_file(evaluation_root, selected)
    if case_path is None:
        return None
    return {
        "selected": selected,
        "fresh_cases": fresh_cases,
        "criterion": [
            relative(evaluation_root / "rubric.json"),
            relative(case_path),
        ],
        "red_result": relative(evaluation_root / "migration-red" / "result.json"),
        "red_output": relative(
            evaluation_root / "migration-red" / f"{selected}-output.md"
        ),
        "green_result": relative(evaluation_root / "green" / "result.json"),
        "green_outputs": [
            relative(evaluation_root / "green" / f"{case_id}-output.md")
            for case_id in fresh_cases
        ],
    }


def committed_freshness_failures(
    skill_name: str, evidence: dict, clean_stage_count: int
) -> list[str]:
    criterion_commit = last_commit_for_paths(evidence["criterion"])
    red_commit = last_commit_for_paths(
        [evidence["red_result"], evidence["red_output"]]
    )
    production_commit = last_production_commit(skill_name)
    green_commits = [last_commit_for_paths([path]) for path in evidence["green_outputs"]]
    result_commit = last_commit_for_paths([evidence["green_result"]])
    head_result = run_git(["rev-parse", "HEAD"])
    head = head_result.stdout.strip() if head_result.returncode == 0 else None

    failures: list[str] = []
    if clean_stage_count >= 2 and not is_ancestor(criterion_commit, red_commit):
        failures.append("criterion<=current-red")
    if clean_stage_count >= 3 and not is_ancestor(red_commit, production_commit):
        failures.append("current-red<=production")
    if clean_stage_count >= 4:
        for index, green_commit in enumerate(green_commits):
            if not is_ancestor(production_commit, green_commit):
                failures.append(
                    f"production<=green-output:{evidence['fresh_cases'][index]}"
                )
    if clean_stage_count >= 5:
        for index, green_commit in enumerate(green_commits):
            if not is_ancestor(green_commit, result_commit):
                failures.append(
                    f"green-output:{evidence['fresh_cases'][index]}<=green-result-review"
                )
        if not is_ancestor(result_commit, head):
            failures.append("green-result-review<=HEAD")
    return failures


def validate_worktree_freshness(
    skill_name: str,
    evidence: dict,
    paths: set[str],
    errors: list[str],
    messages: list[str],
) -> bool:
    production_changed = any(
        production_path_matches(path, skill_name) for path in paths
    )
    criterion_changed = any(path in paths for path in evidence["criterion"])
    red_paths = [evidence["red_result"], evidence["red_output"]]
    red_changes = [path in paths for path in red_paths]
    green_changes = [path in paths for path in evidence["green_outputs"]]
    result_changed = evidence["green_result"] in paths
    if not any(
        [
            criterion_changed,
            *red_changes,
            production_changed,
            *green_changes,
            result_changed,
        ]
    ):
        return False

    missing: list[str] = []
    if any(red_changes) and not all(red_changes):
        if not red_changes[0]:
            missing.append("current-red-result")
        if not red_changes[1]:
            missing.append("current-red-output")
    if any(green_changes) and not all(green_changes):
        for changed, path in zip(green_changes, evidence["green_outputs"]):
            if not changed:
                missing.append(f"green-output:{Path(path).name}")

    dirty_stages = [
        criterion_changed,
        any(red_changes),
        production_changed,
        any(green_changes),
        result_changed,
    ]
    first_dirty = dirty_stages.index(True)
    for index in range(first_dirty, len(dirty_stages)):
        if dirty_stages[index]:
            continue
        if index == 1:
            missing.extend(["current-red-result", "current-red-output"])
        elif index == 2:
            missing.append("production")
        elif index == 3:
            missing.extend(
                f"green-output:{Path(path).name}"
                for path in evidence["green_outputs"]
            )
        elif index == 4:
            missing.append("green-result-review")
    if missing:
        errors.append(
            f"{skill_name}: worktree evidence bundle is incomplete; missing "
            + ", ".join(dict.fromkeys(missing))
        )
        return True

    failures = committed_freshness_failures(skill_name, evidence, first_dirty)
    if failures:
        errors.append(
            f"{skill_name}: worktree evidence clean prefix is stale or incomparable: "
            + ", ".join(failures)
        )
        return True
    messages.append(f"{skill_name}: freshness worktree-current")
    return True


def validate_clean_freshness(
    skill_name: str,
    evidence: dict,
    errors: list[str],
    messages: list[str],
) -> None:
    failures = committed_freshness_failures(skill_name, evidence, 5)
    if failures:
        errors.append(
            f"{skill_name}: clean freshness evidence is missing, stale, or incomparable: "
            + ", ".join(failures)
        )
    else:
        messages.append(f"{skill_name}: freshness clean-current")


def validate_creation_only_freshness(
    skill_name: str,
    paths: set[str],
    errors: list[str],
    messages: list[str],
) -> None:
    production_changed = any(
        production_path_matches(path, skill_name) for path in paths
    )
    production_commit = last_production_commit(skill_name)
    if production_changed and production_commit is None:
        skill_root = ROOT / "skills" / skill_name
        evaluation_root = ROOT / "evaluations" / skill_name
        required = {
            relative(path)
            for path in production_files(skill_root)
        }
        if evaluation_root.is_dir():
            required.update(
                relative(path)
                for path in evaluation_root.rglob("*")
                if path.is_file()
            )
        required.add("evaluations/registry.json")
        missing = sorted(required - paths)
        if missing:
            errors.append(
                f"{skill_name}: worktree creation evidence bundle is incomplete; missing "
                + ", ".join(missing)
            )
        else:
            messages.append(
                f"{skill_name}: freshness worktree-creation-current"
            )
        return
    if production_changed:
        errors.append(
            f"{skill_name}: production changed after creation-only evidence; upgrade to a current-red profile"
        )
        return
    result_path = f"evaluations/{skill_name}/green/result.json"
    result_commit = last_commit_for_paths([result_path])
    if production_commit is None or result_commit is None:
        errors.append(f"{skill_name}: creation-only freshness evidence is incomplete")
    elif not is_ancestor(production_commit, result_commit):
        errors.append(
            f"{skill_name}: production is newer than creation-only GREEN/review evidence; upgrade the profile"
        )
    else:
        messages.append(f"{skill_name}: freshness clean-current")


def validate_skill_freshness(
    skill_name: str,
    entry: dict[str, str],
    require_freshness: bool,
    errors: list[str],
    messages: list[str],
) -> None:
    if entry["stage"] == "baseline-only":
        return
    if not git_worktree_available():
        message = f"{skill_name}: freshness unverified-non-git"
        if require_freshness:
            errors.append(message)
        else:
            messages.append(message)
        return

    paths = changed_paths()
    if entry["evidence_profile"] in {
        "creation-plus-current-red",
        "imported-plus-current-red",
    }:
        evidence = freshness_evidence(skill_name)
        if evidence is None:
            errors.append(f"{skill_name}: freshness evidence structure is incomplete")
            return
        if validate_worktree_freshness(
            skill_name, evidence, paths, errors, messages
        ):
            return
        validate_clean_freshness(skill_name, evidence, errors, messages)
        return
    validate_creation_only_freshness(skill_name, paths, errors, messages)


def validate(
    evidence_only: Optional[str] = None,
    reviewed_skill: Optional[str] = None,
    require_freshness: bool = False,
    freshness_messages: Optional[list[str]] = None,
) -> list[str]:
    errors: list[str] = []
    messages = freshness_messages if freshness_messages is not None else []

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

    manifest: Optional[dict] = None
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

    marketplace_path = ROOT / ".agents" / "plugins" / "marketplace.json"
    if marketplace_path.is_file():
        validate_plugin_marketplace(marketplace_path, manifest, errors)

    skills_root = ROOT / "skills"
    registry = load_evaluation_registry(errors)
    target_skill = evidence_only or reviewed_skill
    if target_skill is not None:
        entry = registry.get(target_skill)
        if entry is None or not (
            entry.get("evaluation_mode") == "managed"
            or entry.get("evidence_profile") == "imported-plus-current-red"
        ):
            errors.append(f"{target_skill}: target has no current evidence profile")
        elif evidence_only is not None and entry.get("stage") != "implemented":
            errors.append(f"{target_skill}: evidence-only requires implemented stage")
        elif reviewed_skill is not None and entry.get("stage") != "review-approved":
            errors.append(f"{target_skill}: reviewed-skill requires review-approved stage")

    for skill_name, entry in registry.items():
        has_current_evidence = (
            entry["evaluation_mode"] == "managed"
            or entry["evidence_profile"] == "imported-plus-current-red"
        )
        if not has_current_evidence:
            continue
        if target_skill is not None and skill_name != target_skill:
            continue
        validate_managed_evaluation(
            skill_name,
            entry["evidence_profile"],
            entry["stage"],
            evidence_only == skill_name,
            errors,
            require_creation_evidence=entry["evaluation_mode"] == "managed",
        )
        validate_skill_freshness(
            skill_name, entry, require_freshness, errors, messages
        )

    evaluation_dirs = {
        path.name
        for path in (ROOT / "evaluations").iterdir()
        if path.is_dir() and path.name != "__pycache__"
    }
    registered_evidence_names = {
        name
        for name, entry in registry.items()
        if entry["evaluation_mode"] == "managed"
        or entry["evidence_profile"] == "imported-plus-current-red"
    }
    for orphan in sorted(evaluation_dirs - registered_evidence_names):
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

    review_approved_skill_names = sorted(
        name for name, entry in registry.items() if entry["stage"] == "review-approved"
    )
    for relative in PUBLIC_SKILL_DOCUMENTS:
        document = ROOT / relative
        if not document.is_file():
            errors.append(f"public skill document is missing: {relative}")
            continue
        text = document.read_text(encoding="utf-8")
        for skill_name in review_approved_skill_names:
            if skill_name not in text:
                errors.append(
                    f"{skill_name}: review-approved skill is missing from {relative}"
                )

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
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--evidence-only")
    target.add_argument("--reviewed-skill")
    parser.add_argument("--require-freshness", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    freshness_messages: list[str] = []
    errors = validate(
        args.evidence_only,
        args.reviewed_skill,
        args.require_freshness,
        freshness_messages,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    for message in freshness_messages:
        print(message)
    print("repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
