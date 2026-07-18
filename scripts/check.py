#!/usr/bin/env python3
"""Run stage-aware development-workflow checks with deterministic reporting."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shlex
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "evaluations" / "registry.json"


class PreflightError(Exception):
    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class Check:
    label: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class CheckResult:
    check: Check
    status: str
    returncode: Optional[int]
    duration: float
    stdout: str
    stderr: str


def positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--skill", action="append", default=[])
    mode.add_argument("--full", action="store_true")
    parser.add_argument("--timeout-seconds", type=positive_integer, default=300)
    parser.add_argument("--skill-validator", type=Path)
    parser.add_argument("--plugin-validator", type=Path)
    return parser.parse_args(argv)


def load_registry() -> dict[str, dict]:
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PreflightError("input_error", "evaluation registry is malformed") from error
    if not isinstance(payload, dict):
        raise PreflightError("input_error", "evaluation registry is malformed")
    skills = payload.get("skills")
    if payload.get("schema_version") != 1 or not isinstance(skills, dict):
        raise PreflightError("input_error", "evaluation registry is malformed")
    for name, entry in skills.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            raise PreflightError("input_error", "evaluation registry is malformed")
        if entry.get("stage") not in {"baseline-only", "implemented", "review-approved"}:
            raise PreflightError("input_error", f"{name}: registry stage is invalid")
    return skills


def select_targets(args: argparse.Namespace, registry: dict[str, dict]) -> list[str]:
    if args.full:
        targets = sorted(
            name for name, entry in registry.items() if entry.get("stage") != "baseline-only"
        )
        not_approved = [
            name for name in targets if registry[name].get("stage") != "review-approved"
        ]
        if not_approved:
            raise PreflightError(
                "input_error",
                "full checks require every exposed skill to be review-approved: "
                + ", ".join(not_approved),
            )
        return targets

    targets = sorted(set(args.skill))
    for name in targets:
        entry = registry.get(name)
        if entry is None:
            raise PreflightError("input_error", f"unknown skill: {name}")
        if entry.get("stage") == "baseline-only":
            raise PreflightError(
                "input_error", f"{name}: baseline-only skill cannot be checked"
            )
    return targets


def ordinary_readable_file(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    return (
        stat.S_ISREG(mode)
        and not stat.S_ISLNK(mode)
        and os.access(path, os.R_OK)
    )


def resolve_validator(
    explicit: Optional[Path], relative: Path, label: str
) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit.expanduser())
    else:
        codex_home = os.environ.get("CODEX_HOME")
        if codex_home:
            candidates.append(Path(codex_home).expanduser() / relative)
        fallback = Path.home() / ".codex" / relative
        if not candidates or fallback != candidates[0]:
            candidates.append(fallback)

    for candidate in candidates:
        if ordinary_readable_file(candidate):
            return candidate.absolute()
        if explicit is not None:
            break
    rendered = str(candidates[0]) if candidates else str(relative)
    raise PreflightError(
        "capability_error", f"{label} validator is unavailable or unsafe: {rendered}"
    )


def build_checks(
    args: argparse.Namespace,
    registry: dict[str, dict],
    targets: Sequence[str],
    skill_validator: Path,
    plugin_validator: Optional[Path],
) -> list[Check]:
    python = sys.executable
    checks = [
        Check(
            "repo-tests",
            (python, "-m", "unittest", "discover", "-s", "tests", "-v"),
        )
    ]
    for name in targets:
        checks.append(
            Check(
                f"skill-tests:{name}",
                (
                    python,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    f"skills/{name}/tests",
                    "-v",
                ),
            )
        )

    if args.full:
        checks.append(
            Check(
                "repository-validator:full",
                (python, "scripts/validate_repo.py", "--require-freshness"),
            )
        )
    else:
        for name in targets:
            stage = registry[name]["stage"]
            target_flag = "--evidence-only" if stage == "implemented" else "--reviewed-skill"
            checks.append(
                Check(
                    f"repository-validator:{name}",
                    (
                        python,
                        "scripts/validate_repo.py",
                        target_flag,
                        name,
                        "--require-freshness",
                    ),
                )
            )

    for name in targets:
        checks.append(
            Check(
                f"skill-validator:{name}",
                (python, str(skill_validator), f"skills/{name}"),
            )
        )
    if args.full:
        assert plugin_validator is not None
        checks.append(
            Check(
                "plugin-validator",
                (python, str(plugin_validator), "."),
            )
        )
    return checks


def run_check(check: Check, timeout: int) -> CheckResult:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(check.argv),
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        return CheckResult(
            check,
            "TIMEOUT",
            None,
            time.monotonic() - started,
            error.stdout or "",
            error.stderr or "",
        )
    except OSError as error:
        return CheckResult(
            check,
            "ERROR",
            None,
            time.monotonic() - started,
            "",
            str(error),
        )
    return CheckResult(
        check,
        "PASS" if completed.returncode == 0 else "FAIL",
        completed.returncode,
        time.monotonic() - started,
        completed.stdout,
        completed.stderr,
    )


def run_checks(checks: Sequence[Check], timeout: int) -> list[CheckResult]:
    if not checks:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(checks)) as executor:
        futures = [executor.submit(run_check, check, timeout) for check in checks]
        return [future.result() for future in futures]


def report(results: Sequence[CheckResult]) -> None:
    for result in results:
        command = shlex.join(result.check.argv)
        suffix = (
            f"exit={result.returncode}" if result.returncode is not None else "exit=none"
        )
        print(
            f"[{result.status}] {result.check.label} "
            f"({result.duration:.3f}s; {suffix}) {command}"
        )
        if result.status != "PASS":
            for stream_name, content in (("stdout", result.stdout), ("stderr", result.stderr)):
                if content:
                    print(f"  {stream_name}: {content.rstrip()}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        args = parse_args(argv)
        registry = load_registry()
        targets = select_targets(args, registry)
        skill_validator = resolve_validator(
            args.skill_validator,
            Path("skills/.system/skill-creator/scripts/quick_validate.py"),
            "skill",
        )
        plugin_validator = (
            resolve_validator(
                args.plugin_validator,
                Path("skills/.system/plugin-creator/scripts/validate_plugin.py"),
                "plugin",
            )
            if args.full
            else None
        )
        checks = build_checks(
            args, registry, targets, skill_validator, plugin_validator
        )
    except PreflightError as error:
        print(f"{error.kind}: {error}", file=sys.stderr)
        return 2

    results = run_checks(checks, args.timeout_seconds)
    report(results)
    return 0 if all(result.status == "PASS" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
