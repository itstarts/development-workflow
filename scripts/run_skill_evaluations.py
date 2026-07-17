#!/usr/bin/env python3
"""Run isolated Codex skill evaluations and preserve local raw evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
PUBLISHABLE_ENTRIES = ("SKILL.md", "agents", "assets", "references", "scripts")
MODEL_KEYS = ("model_provider", "model", "model_reasoning_effort")
PROVIDER_KEYS = ("name", "base_url", "wire_api", "requires_openai_auth")
EVIDENCE_ROLES = ("current-skill-red", "migration-baseline", "green")
SANDBOX_DENIAL_MARKERS = (
    "sandbox: deny",
    "deny file-read",
    "deny file-write",
)
SKILL_NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SCENARIO_KEYS = {
    "schema_version",
    "repository_mode",
    "nested_git_roots",
    "unreadable_paths",
    "codex_home_files",
}
CODEX_HOME_RULE_FILES = {"AGENTS.md", "AGENTS.override.md"}


class EvaluationBlocked(RuntimeError):
    """Raised when isolation or runtime prerequisites are unavailable."""


@dataclass(frozen=True)
class FixtureScenario:
    """Validated declarative state for one isolated evaluation fixture."""

    repository_mode: str
    nested_git_roots: tuple[Path, ...]
    unreadable_paths: tuple[Path, ...]
    codex_home_files: dict[str, Path]


def evaluation_root(skill_name: str) -> Path:
    """Return the versioned evidence root for one validated skill name."""
    if SKILL_NAME_PATTERN.fullmatch(skill_name) is None:
        raise EvaluationBlocked(f"invalid skill name: {skill_name}")
    return ROOT / "evaluations" / skill_name


def resolve_case_path(skill_name: str, case_path: Path) -> Path:
    """Resolve a case only when it belongs to the selected skill evidence root."""
    resolved = case_path.resolve()
    cases_root = (evaluation_root(skill_name) / "cases").resolve()
    if os.path.commonpath((str(resolved), str(cases_root))) != str(cases_root):
        raise EvaluationBlocked(
            f"evaluation case does not belong to selected skill {skill_name}"
        )
    if not resolved.is_file():
        raise EvaluationBlocked("evaluation case is unavailable")
    return resolved


def _candidate_skill_name(skill_dir: Path) -> str:
    skill_path = skill_dir / "SKILL.md"
    if not skill_path.is_file():
        raise EvaluationBlocked("candidate skill is missing SKILL.md")
    text = skill_path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if match is None:
        raise EvaluationBlocked("candidate skill frontmatter is malformed")
    names = [
        line.split(":", 1)[1].strip()
        for line in match.group(1).splitlines()
        if line.startswith("name:")
    ]
    if len(names) != 1 or SKILL_NAME_PATTERN.fullmatch(names[0]) is None:
        raise EvaluationBlocked("candidate skill name is malformed")
    return names[0]


def validate_phase_inputs(
    phase: str, skill_name: str, skill_dir: Optional[Path]
) -> None:
    """Enforce which evidence roles may receive a candidate skill."""
    evaluation_root(skill_name)
    if phase not in EVIDENCE_ROLES:
        raise EvaluationBlocked(f"unsupported evidence role: {phase}")
    if phase == "migration-baseline" and skill_dir is not None:
        raise EvaluationBlocked("migration-baseline cannot receive a target skill")
    if phase in {"current-skill-red", "green"} and (
        skill_dir is None or not (skill_dir / "SKILL.md").is_file()
    ):
        raise EvaluationBlocked(f"{phase} requires a candidate skill directory")
    if skill_dir is not None:
        candidate_name = _candidate_skill_name(skill_dir)
        if skill_dir.name != skill_name or candidate_name != skill_name:
            raise EvaluationBlocked(
                f"candidate skill {skill_dir.name}/{candidate_name} does not match {skill_name}"
            )


def _sandbox_quote(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace('"', '\\"')


def _subpath_rules(paths: Sequence[Path]) -> str:
    unique = sorted({_sandbox_quote(path) for path in paths})
    return "\n".join(f'    (subpath "{path}")' for path in unique)


def _xcrun_cache_rules() -> str:
    roots = {
        str(Path(tempfile.gettempdir())),
        str(Path(tempfile.gettempdir()).resolve()),
    }
    return "\n".join(
        f'    (regex #"^{re.escape(root)}/xcrun_db(-[A-Za-z0-9]+)?$")'
        for root in sorted(roots)
    )


def build_sandbox_profile(
    fixture_root: Path,
    codex_home: Path,
    skill_root: Optional[Path],
    runtime_read_roots: Sequence[Path],
) -> str:
    """Build a deny-by-default macOS sandbox profile for an evaluation agent."""
    read_rules = _subpath_rules(runtime_read_roots)
    read_only_skill = ""
    if skill_root is not None:
        read_only_skill = (
            "\n(allow file-read*\n"
            f'    (subpath "{_sandbox_quote(skill_root)}"))\n'
            "(deny file-write*\n"
            f'    (subpath "{_sandbox_quote(skill_root)}"))'
        )
    return (
        "(version 1)\n"
        "(deny default)\n"
        "(allow process*)\n"
        "(allow signal)\n"
        "(allow sysctl-read)\n"
        "(allow mach-lookup)\n"
        "(allow network-outbound)\n"
        "(allow file-read-metadata)\n"
        "(allow file-read*\n"
        '    (literal "/")\n'
        f"{read_rules})\n"
        "(allow file-read* file-write*\n"
        f'    (subpath "{_sandbox_quote(fixture_root)}")\n'
        f'    (subpath "{_sandbox_quote(codex_home)}"))\n'
        '(allow file-write* (literal "/dev/null"))\n'
        "(allow file-read* file-write*\n"
        f"{_xcrun_cache_rules()})"
        f"{read_only_skill}\n"
    )


def build_codex_command(fixture_root: Path, output_path: Path) -> list[str]:
    """Return the structured Codex CLI command used inside the outer sandbox."""
    return [
        "codex",
        "exec",
        "--ignore-user-config",
        "--skip-git-repo-check",
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        str(fixture_root),
        "-o",
        str(output_path),
        "-",
    ]


def build_evaluation_prompt(
    case_text: str, skill_name: str, staged_skill: Optional[Path]
) -> str:
    """Add only isolation boundaries and the optional staged-skill invocation."""
    parts = [
        "Isolation context: The current working directory is the fixture repository root. "
        "Do not inspect or search any parent directory. Use only repository files under "
        "the current working directory, the staged skill path supplied below, and any "
        "scenario-staged AGENTS.md or AGENTS.override.md at this isolated Codex home when "
        "the request names that target. Do not inspect any other Codex-home file or any "
        "real user home."
    ]
    if staged_skill is not None:
        parts.append(
            f"Use ${skill_name} at "
            f"{staged_skill} to handle this request."
        )
    parts.append(case_text)
    return "\n\n".join(parts)


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def build_shell_environment_overrides(
    runtime_bin: Path, codex_home: Path
) -> list[str]:
    """Build a minimal documented shell environment policy for agent tools."""
    path_value = os.pathsep.join((str(runtime_bin), "/usr/bin", "/bin"))
    inline = (
        "{ PATH = "
        f"{_toml_string(path_value)}, HOME = {_toml_string(str(codex_home))}, "
        f"TMPDIR = {_toml_string(str(codex_home / 'tmp'))}, "
        f"ZDOTDIR = {_toml_string(str(codex_home))} }}"
    )
    return [
        'shell_environment_policy.inherit="none"',
        "shell_environment_policy.ignore_default_excludes=false",
        f"shell_environment_policy.set={inline}",
    ]


def load_provider_overrides(config_path: Path) -> list[str]:
    """Extract only model selection and transport settings from a Codex config."""
    if not config_path.is_file():
        raise EvaluationBlocked("Codex provider config is unavailable")
    top_level: dict[str, str] = {}
    providers: dict[str, dict[str, str]] = {}
    current_provider: Optional[str] = None
    section_pattern = re.compile(r"\[model_providers\.([A-Za-z0-9_-]+)\]")
    assignment_pattern = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)")
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        section = section_pattern.fullmatch(line)
        if section:
            current_provider = section.group(1)
            providers.setdefault(current_provider, {})
            continue
        if line.startswith("["):
            current_provider = None
            continue
        assignment = assignment_pattern.fullmatch(line)
        if assignment is None:
            continue
        key, raw_value = assignment.groups()
        if current_provider is None and key in MODEL_KEYS:
            if key in top_level:
                raise EvaluationBlocked(f"duplicate model config key: {key}")
            top_level[key] = raw_value
        elif current_provider is not None and key in PROVIDER_KEYS:
            if key in providers[current_provider]:
                raise EvaluationBlocked(f"duplicate provider config key: {key}")
            providers[current_provider][key] = raw_value

    provider_raw = top_level.get("model_provider")
    if provider_raw is None:
        raise EvaluationBlocked("model_provider is missing from Codex config")
    try:
        provider_name = json.loads(provider_raw)
    except json.JSONDecodeError as error:
        raise EvaluationBlocked("model_provider must be a quoted string") from error
    if not isinstance(provider_name, str) or provider_name not in providers:
        raise EvaluationBlocked("selected model provider config is missing")

    overrides = [f"{key}={top_level[key]}" for key in MODEL_KEYS if key in top_level]
    overrides.extend(
        f"model_providers.{provider_name}.{key}={providers[provider_name][key]}"
        for key in PROVIDER_KEYS
        if key in providers[provider_name]
    )
    return overrides


def _nested_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _nested_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nested_strings(child)


def scan_trace(events: Iterable[dict], forbidden_roots: Sequence[Path]) -> list[str]:
    """Find observable forbidden paths and sandbox denials in JSONL events."""
    forbidden = [str(path.resolve()) for path in forbidden_roots]
    problems: list[str] = []
    for index, event in enumerate(events):
        item = event.get("item")
        if (
            event.get("type") == "item.completed"
            and isinstance(item, dict)
            and item.get("status") == "failed"
            and item.get("type") == "file_change"
        ):
            problems.append(f"event {index} contains failed file_change")
        for value in _nested_strings(event):
            for root in forbidden:
                if root and root in value:
                    problems.append(f"event {index} references forbidden path {root}")
            lowered = value.casefold()
            if any(marker in lowered for marker in SANDBOX_DENIAL_MARKERS):
                problems.append(f"event {index} contains sandbox denial")
    return sorted(set(problems))


def scan_trace_warnings(events: Iterable[dict]) -> list[str]:
    """Summarize recovered command failures without copying commands or output."""
    warnings: list[str] = []
    for index, event in enumerate(events):
        item = event.get("item")
        if (
            event.get("type") == "item.completed"
            and isinstance(item, dict)
            and item.get("status") == "failed"
            and item.get("type") == "command_execution"
        ):
            exit_code = item.get("exit_code", "unknown")
            warnings.append(
                f"event {index} contains failed command_execution (exit {exit_code})"
            )
    return sorted(set(warnings))


def _copy_publishable_skill(skill_dir: Path, destination: Path) -> None:
    destination.mkdir(parents=True)
    for entry_name in PUBLISHABLE_ENTRIES:
        source = skill_dir / entry_name
        if not source.exists():
            continue
        if source.is_symlink():
            raise EvaluationBlocked(f"skill payload contains symlink: {entry_name}")
        target = destination / entry_name
        if source.is_dir():
            shutil.copytree(
                source,
                target,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store"),
            )
        else:
            shutil.copy2(source, target)


def stage_codex_home(
    source_home: Path, target_home: Path, skill_dir: Optional[Path]
) -> None:
    """Create a minimal isolated Codex home without exposing credential contents."""
    auth_source = source_home / "auth.json"
    if not auth_source.is_file():
        raise EvaluationBlocked("Codex authentication file is unavailable")
    target_home.mkdir(parents=True)
    auth_target = target_home / "auth.json"
    shutil.copyfile(auth_source, auth_target)
    auth_target.chmod(stat.S_IRUSR | stat.S_IWUSR)
    if skill_dir is not None:
        _copy_publishable_skill(
            skill_dir.resolve(), target_home / "skills" / skill_dir.name
        )


def stage_runtime_shims(codex_home: Path) -> Path:
    """Expose deterministic system tools before user-managed PATH entries."""
    bin_dir = codex_home / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    shims = {
        "python": Path("/usr/bin/python3"),
        "python3": Path("/usr/bin/python3"),
        "git": Path("/usr/bin/git"),
    }
    ripgrep = shutil.which("rg")
    if ripgrep:
        shims["rg"] = Path(ripgrep).resolve()
    node = shutil.which("node")
    if node:
        shims["node"] = Path(node).resolve()
    for name, target in shims.items():
        if not target.is_file():
            raise EvaluationBlocked(f"required system tool is unavailable: {target}")
        (bin_dir / name).symlink_to(target)
    (codex_home / ".zprofile").write_text(
        'export PATH="$HOME/bin:/usr/bin:/bin"\n', encoding="utf-8"
    )
    return bin_dir


def _copy_fixture(
    case_path: Path, fixture_root: Path, selected_evaluation_root: Path
) -> None:
    evaluation_boundary = selected_evaluation_root.parent.parent
    common = selected_evaluation_root / "fixtures" / "common"
    _reject_symlink_ancestry(common, evaluation_boundary, "common fixture")
    if not common.is_dir():
        raise EvaluationBlocked("common evaluation fixture is unavailable")
    _reject_tree_symlinks(common, "common fixture")
    shutil.copytree(common, fixture_root)
    overlay = selected_evaluation_root / "fixtures" / case_path.stem
    _reject_symlink_ancestry(overlay, evaluation_boundary, "case fixture")
    if overlay.is_dir():
        _reject_tree_symlinks(overlay, "case fixture")
        shutil.copytree(overlay, fixture_root, dirs_exist_ok=True)


def _reject_symlink_ancestry(path: Path, boundary: Path, label: str) -> None:
    try:
        path.relative_to(boundary)
    except ValueError as error:
        raise EvaluationBlocked(f"{label} is outside its allowed root") from error
    current = path
    while True:
        if current.is_symlink():
            raise EvaluationBlocked(f"{label} cannot use a symlink")
        if current == boundary:
            return
        current = current.parent


def _reject_tree_symlinks(root: Path, label: str) -> None:
    if root.is_symlink():
        raise EvaluationBlocked(f"{label} cannot use a symlink")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise EvaluationBlocked(f"{label} cannot contain a symlink")


def _relative_fixture_path(
    value: str,
    *,
    case_path: Path,
    selected_evaluation_root: Path,
    field: str,
) -> Path:
    relative = Path(value)
    if (
        not value
        or relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise EvaluationBlocked(f"{field} contains an invalid relative path")

    fixture_roots = (
        selected_evaluation_root / "fixtures" / "common",
        selected_evaluation_root / "fixtures" / case_path.stem,
    )
    evaluation_boundary = selected_evaluation_root.parent.parent
    for root in fixture_roots:
        _reject_symlink_ancestry(
            root, evaluation_boundary, f"{field} path"
        )
    matching_sources = [
        root / relative
        for root in fixture_roots
        if (root / relative).exists() or (root / relative).is_symlink()
    ]
    if not matching_sources:
        raise EvaluationBlocked(f"{field} path is unavailable: {value}")
    for source in matching_sources:
        current = source
        while current != current.parent:
            if current.is_symlink():
                raise EvaluationBlocked(f"{field} path cannot use a symlink: {value}")
            if current in fixture_roots:
                break
            current = current.parent
        if not source.is_file() and not source.is_dir():
            raise EvaluationBlocked(f"{field} path must be a regular file or directory")
    return relative


def _codex_home_source(
    value: str,
    *,
    case_path: Path,
    selected_evaluation_root: Path,
) -> Path:
    relative = Path(value)
    if (
        not value
        or relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise EvaluationBlocked("codex_home_files contains an invalid source path")
    scenario_files_root = (
        selected_evaluation_root
        / "fixtures"
        / "scenario-files"
    )
    expected_root = scenario_files_root / case_path.stem
    source = ROOT / relative
    _reject_symlink_ancestry(source, ROOT, "codex_home_files source")
    try:
        source.relative_to(expected_root)
    except ValueError as error:
        raise EvaluationBlocked(
            "codex_home_files source is outside the case allowlist"
        ) from error
    current = source
    while True:
        if current.is_symlink():
            raise EvaluationBlocked("codex_home_files source cannot use a symlink")
        if current == scenario_files_root:
            break
        current = current.parent
    resolved_root = expected_root.resolve()
    resolved_source = source.resolve()
    try:
        resolved_source.relative_to(resolved_root)
    except ValueError as error:
        raise EvaluationBlocked(
            "codex_home_files source is outside the case allowlist"
        ) from error
    if not source.is_file():
        raise EvaluationBlocked("codex_home_files source must be a regular file")
    return resolved_source


def load_fixture_scenario(
    case_path: Path, selected_evaluation_root: Path
) -> FixtureScenario:
    """Load and validate one optional per-case fixture scenario."""
    scenario_path = (
        selected_evaluation_root
        / "fixtures"
        / "scenarios"
        / f"{case_path.stem}.json"
    )
    _reject_symlink_ancestry(
        scenario_path,
        selected_evaluation_root.parent.parent,
        "fixture scenario",
    )
    if scenario_path.is_symlink() or not scenario_path.is_file():
        if not scenario_path.exists() and not scenario_path.is_symlink():
            return FixtureScenario("git", (), (), {})
        raise EvaluationBlocked("fixture scenario must be a regular file")
    try:
        payload = json.loads(scenario_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvaluationBlocked("fixture scenario is malformed") from error
    if not isinstance(payload, dict) or set(payload) - SCENARIO_KEYS:
        raise EvaluationBlocked("fixture scenario is malformed")
    if payload.get("schema_version") != 1:
        raise EvaluationBlocked("fixture scenario schema_version must be 1")
    repository_mode = payload.get("repository_mode")
    if repository_mode not in {"git", "non-git"}:
        raise EvaluationBlocked("fixture scenario repository_mode is invalid")

    path_lists: dict[str, tuple[Path, ...]] = {}
    for field in ("nested_git_roots", "unreadable_paths"):
        values = payload.get(field, [])
        if not isinstance(values, list) or not all(
            isinstance(value, str) for value in values
        ):
            raise EvaluationBlocked(f"fixture scenario {field} must be a string array")
        resolved = tuple(
            _relative_fixture_path(
                value,
                case_path=case_path,
                selected_evaluation_root=selected_evaluation_root,
                field=field,
            )
            for value in values
        )
        if len(set(resolved)) != len(resolved):
            raise EvaluationBlocked(f"fixture scenario {field} contains duplicates")
        path_lists[field] = resolved

    raw_home_files = payload.get("codex_home_files", {})
    if not isinstance(raw_home_files, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in raw_home_files.items()
    ):
        raise EvaluationBlocked("fixture scenario codex_home_files must be an object")
    if set(raw_home_files) - CODEX_HOME_RULE_FILES:
        raise EvaluationBlocked("fixture scenario codex_home_files key is invalid")
    home_files = {
        name: _codex_home_source(
            value,
            case_path=case_path,
            selected_evaluation_root=selected_evaluation_root,
        )
        for name, value in raw_home_files.items()
    }
    return FixtureScenario(
        repository_mode,
        path_lists["nested_git_roots"],
        path_lists["unreadable_paths"],
        home_files,
    )


def _initialize_fixture_repository(fixture_root: Path) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Evaluation Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Evaluation Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    }
    commands = (
        ["git", "init", "-q"],
        ["git", "add", "."],
        ["git", "commit", "-q", "--allow-empty", "-m", "fixture"],
    )
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=fixture_root,
            env=env,
            text=True,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise EvaluationBlocked(
                f"fixture git setup failed at {command[1]}: {completed.stderr.strip()}"
            )


def prepare_fixture_repositories(
    fixture_root: Path, scenario: FixtureScenario
) -> None:
    """Create only the Git roots declared by a validated fixture scenario."""
    if scenario.repository_mode == "git":
        _initialize_fixture_repository(fixture_root)
    for relative in scenario.nested_git_roots:
        nested = fixture_root / relative
        if nested.is_symlink() or not nested.is_dir():
            raise EvaluationBlocked("nested_git_roots path is not a regular directory")
        _initialize_fixture_repository(nested)


def stage_scenario_codex_home(
    codex_home: Path, scenario: FixtureScenario
) -> None:
    """Inject only the declared AGENTS files into an isolated Codex home."""
    for name, source in scenario.codex_home_files.items():
        destination = codex_home / name
        if destination.exists():
            raise EvaluationBlocked(f"isolated Codex home target already exists: {name}")
        shutil.copy2(source, destination)


def apply_unreadable_paths(
    fixture_root: Path, scenario: FixtureScenario
) -> list[tuple[Path, int]]:
    """Make declared fixture paths unreadable and retain modes for cleanup."""
    original_modes: list[tuple[Path, int]] = []
    for relative in scenario.unreadable_paths:
        target = fixture_root / relative
        if target.is_symlink() or (not target.is_file() and not target.is_dir()):
            raise EvaluationBlocked("unreadable_paths target is unavailable")
        mode = stat.S_IMODE(target.stat().st_mode)
        original_modes.append((target, mode))
        target.chmod(0)
    return original_modes


def restore_path_modes(original_modes: Sequence[tuple[Path, int]]) -> None:
    """Restore fixture permissions after an isolated evaluation run."""
    for target, mode in reversed(original_modes):
        target.chmod(mode)


def _runtime_read_roots(codex_path: Path) -> list[Path]:
    roots = [
        Path("/System"),
        Path("/Library"),
        Path("/usr"),
        Path("/bin"),
        Path("/sbin"),
        Path("/private/etc"),
        Path("/private/var/db"),
        Path("/dev"),
        Path("/opt"),
    ]
    node = shutil.which("node")
    if node:
        roots.append(Path(node).resolve().parent.parent)
    else:
        roots.append(codex_path.resolve().parent)
    ripgrep = shutil.which("rg")
    if ripgrep:
        roots.append(Path(ripgrep).resolve().parent)
    return [path for path in roots if path.exists()]


def _parse_jsonl(stdout: str) -> tuple[list[dict], list[str]]:
    events: list[dict] = []
    errors: list[str] = []
    for index, line in enumerate(stdout.splitlines()):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"stdout line {index + 1} is not JSON")
            continue
        if not isinstance(event, dict):
            errors.append(f"stdout line {index + 1} is not an object")
            continue
        events.append(event)
    if not events:
        errors.append("JSONL trace contains no events")
    return events, errors


def collaboration_session_count(codex_home: Path) -> int:
    """Count isolated session records without exposing their names or content."""
    sessions_root = codex_home / "sessions"
    if not sessions_root.is_dir():
        return 0
    return sum(1 for path in sessions_root.rglob("*.jsonl") if path.is_file())


def copy_isolated_session_records(codex_home: Path, output_root: Path) -> int:
    """Preserve ignored raw collaboration records under identifier-free names."""
    sessions_root = codex_home / "sessions"
    records = (
        sorted(path for path in sessions_root.rglob("*.jsonl") if path.is_file())
        if sessions_root.is_dir()
        else []
    )
    if not records:
        return 0
    target_root = output_root / "collaboration-sessions"
    target_root.mkdir(parents=True, exist_ok=True)
    for index, source in enumerate(records, start=1):
        shutil.copyfile(source, target_root / f"session-{index:02d}.jsonl")
    return len(records)


def _write_local_result(
    output_root: Path,
    *,
    result: dict[str, Any],
    stdout: str = "",
    stderr: str = "",
    final_message: str = "",
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "trace.jsonl").write_text(stdout, encoding="utf-8")
    (output_root / "stderr.txt").write_text(stderr, encoding="utf-8")
    (output_root / "final.md").write_text(final_message, encoding="utf-8")
    (output_root / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_result(
    *,
    phase: str,
    case_name: str,
    exit_code: int,
    contaminations: Sequence[str],
    warnings: Sequence[str],
) -> dict[str, Any]:
    """Build the minimum operational record needed to accept or reject a run."""
    unique_contaminations = sorted(set(contaminations))
    return {
        "schema_version": 1,
        "phase": phase,
        "evidence_role": phase,
        "case": case_name,
        "valid": not unique_contaminations,
        "exit_code": exit_code,
        "contaminations": unique_contaminations,
        "warnings": list(warnings),
    }


def run_evaluation(
    skill_name: str,
    phase: str,
    case_path: Path,
    output_root: Path,
    skill_dir: Optional[Path],
) -> int:
    validate_phase_inputs(phase, skill_name, skill_dir)
    selected_evaluation_root = evaluation_root(skill_name)
    sandbox_exec = Path("/usr/bin/sandbox-exec")
    codex = shutil.which("codex")
    if not sandbox_exec.is_file():
        raise EvaluationBlocked("sandbox-exec is unavailable")
    if not codex:
        raise EvaluationBlocked("codex CLI is unavailable")

    case_path = resolve_case_path(skill_name, case_path)
    source_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()

    with tempfile.TemporaryDirectory(prefix="dw-skill-eval-") as temporary:
        temp_root = Path(temporary)
        fixture_root = temp_root / "fixture"
        codex_home = temp_root / "codex-home"
        _copy_fixture(case_path, fixture_root, selected_evaluation_root)
        scenario = load_fixture_scenario(case_path, selected_evaluation_root)
        prepare_fixture_repositories(fixture_root, scenario)
        stage_codex_home(source_home, codex_home, skill_dir)
        stage_scenario_codex_home(codex_home, scenario)
        runtime_bin = stage_runtime_shims(codex_home)
        (codex_home / "tmp").mkdir()
        staged_skill = (
            codex_home / "skills" / skill_dir.name if skill_dir is not None else None
        )
        final_path = codex_home / "final.md"
        profile = build_sandbox_profile(
            fixture_root,
            codex_home,
            staged_skill,
            _runtime_read_roots(Path(codex)),
        )
        prompt = build_evaluation_prompt(
            case_path.read_text(encoding="utf-8"), skill_name, staged_skill
        )
        command = build_codex_command(fixture_root, final_path)
        provider_overrides = load_provider_overrides(source_home / "config.toml")
        shell_overrides = build_shell_environment_overrides(runtime_bin, codex_home)
        all_overrides = [*provider_overrides, *shell_overrides]
        command[2:2] = [
            item
            for override in all_overrides
            for item in ("-c", override)
        ]
        command[0] = str(Path(codex).resolve())
        outer_command = [str(sandbox_exec), "-p", profile, *command]
        env = {
            **os.environ,
            "CODEX_HOME": str(codex_home),
            "HOME": str(codex_home),
            "TMPDIR": str(codex_home / "tmp"),
            "PATH": os.pathsep.join((str(runtime_bin), "/usr/bin", "/bin")),
        }
        original_modes = apply_unreadable_paths(fixture_root, scenario)
        try:
            completed = subprocess.run(
                outer_command,
                input=prompt,
                cwd=fixture_root,
                env=env,
                text=True,
                capture_output=True,
            )
        finally:
            restore_path_modes(original_modes)
        events, parse_errors = _parse_jsonl(completed.stdout)
        contaminations = scan_trace(events, [ROOT, source_home])
        warnings = scan_trace_warnings(events)
        contaminations.extend(parse_errors)
        final_message = (
            final_path.read_text(encoding="utf-8") if final_path.is_file() else ""
        )
        if not final_message.strip():
            contaminations.append("final response is missing")
        if completed.returncode != 0:
            contaminations.append(f"codex exited with {completed.returncode}")
        if any(
            marker in completed.stderr.casefold()
            for marker in SANDBOX_DENIAL_MARKERS
        ):
            contaminations.append("stderr contains sandbox denial")
        result = build_result(
            phase=phase,
            case_name=case_path.name,
            exit_code=completed.returncode,
            contaminations=contaminations,
            warnings=warnings,
        )
        _write_local_result(
            output_root,
            result=result,
            stdout=completed.stdout,
            stderr=completed.stderr,
            final_message=final_message,
        )
        (output_root / "collaboration-session-count.txt").write_text(
            f"{collaboration_session_count(codex_home)}\n", encoding="utf-8"
        )
        copy_isolated_session_records(codex_home, output_root)
        return 0 if result["valid"] else 2


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-name", required=True)
    parser.add_argument("--phase", required=True, choices=EVIDENCE_ROLES)
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--skill-dir", type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        return run_evaluation(
            args.skill_name, args.phase, args.case, args.output_root, args.skill_dir
        )
    except EvaluationBlocked as error:
        _write_local_result(
            args.output_root,
            result={
                "schema_version": 1,
                "phase": args.phase,
                "case": args.case.name,
                "valid": False,
                "blocked": str(error),
            },
        )
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
