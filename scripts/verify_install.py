#!/usr/bin/env python3
"""Compare repository skill payloads with an explicit Codex home without writing it."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "evaluations" / "registry.json"
PUBLISHABLE_DIRS = ("agents", "assets", "references", "scripts")
IGNORED_DIRS = {"__pycache__"}
IGNORED_FILES = {".DS_Store"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".pyd"}
VALID_STAGES = {"baseline-only", "implemented", "review-approved"}


class InputError(Exception):
    pass


def ignored(relative: Path) -> bool:
    return (
        bool(IGNORED_DIRS.intersection(relative.parts[:-1]))
        or relative.name in IGNORED_FILES
        or relative.suffix.lower() in IGNORED_SUFFIXES
    )


def load_registry() -> dict[str, dict]:
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InputError("evaluation registry is malformed") from error
    if not isinstance(payload, dict):
        raise InputError("evaluation registry is malformed")
    skills = payload.get("skills")
    if payload.get("schema_version") != 1 or not isinstance(skills, dict):
        raise InputError("evaluation registry is malformed")
    for name, entry in skills.items():
        if (
            not isinstance(name, str)
            or not isinstance(entry, dict)
            or entry.get("stage") not in VALID_STAGES
        ):
            raise InputError("evaluation registry is malformed")
    return skills


def select_skills(registry: dict[str, dict], requested: Sequence[str]) -> list[str]:
    names = sorted(set(requested)) if requested else sorted(
        name for name, entry in registry.items() if entry.get("stage") != "baseline-only"
    )
    for name in names:
        entry = registry.get(name)
        if entry is None:
            raise InputError(f"unknown skill: {name}")
        if entry.get("stage") == "baseline-only":
            raise InputError(f"baseline-only skill is not installable: {name}")
    return names


def scan_tree(directory: Path, prefix: Path) -> tuple[dict[Path, Path], list[Path]]:
    files: dict[Path, Path] = {}
    non_regular: list[Path] = []
    try:
        entries = sorted(os.scandir(directory), key=lambda item: item.name)
    except OSError as error:
        raise InputError(f"cannot read publishable directory: {prefix.as_posix()}") from error
    for entry in entries:
        relative = prefix / entry.name
        if ignored(relative):
            continue
        try:
            mode = entry.stat(follow_symlinks=False).st_mode
        except OSError as error:
            raise InputError(f"cannot inspect publishable path: {relative.as_posix()}") from error
        path = Path(entry.path)
        if stat.S_ISLNK(mode):
            non_regular.append(relative)
        elif stat.S_ISDIR(mode):
            nested_files, nested_non_regular = scan_tree(path, relative)
            files.update(nested_files)
            non_regular.extend(nested_non_regular)
        elif stat.S_ISREG(mode):
            files[relative] = path
        else:
            non_regular.append(relative)
    return files, non_regular


def payload(root: Path) -> tuple[dict[Path, Path], list[Path]]:
    files: dict[Path, Path] = {}
    non_regular: list[Path] = []
    skill_file = root / "SKILL.md"
    try:
        mode = skill_file.lstat().st_mode
    except FileNotFoundError:
        pass
    except OSError as error:
        raise InputError("cannot inspect publishable path: SKILL.md") from error
    else:
        if stat.S_ISREG(mode):
            files[Path("SKILL.md")] = skill_file
        else:
            non_regular.append(Path("SKILL.md"))

    for name in PUBLISHABLE_DIRS:
        directory = root / name
        try:
            mode = directory.lstat().st_mode
        except FileNotFoundError:
            continue
        except OSError as error:
            raise InputError(f"cannot inspect publishable path: {name}") from error
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            non_regular.append(Path(name))
            continue
        nested_files, nested_non_regular = scan_tree(directory, Path(name))
        files.update(nested_files)
        non_regular.extend(nested_non_regular)
    return files, sorted(non_regular)


def readable_directory(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    return stat.S_ISDIR(mode) and not stat.S_ISLNK(mode) and os.access(path, os.R_OK | os.X_OK)


def compare_skill(name: str, codex_home: Path) -> tuple[list[str], bool]:
    source_root = ROOT / "skills" / name
    target_root = codex_home / "skills" / name
    if not readable_directory(source_root):
        raise InputError(f"{name}: source skill is not a readable ordinary directory")
    if not readable_directory(target_root):
        raise InputError(f"{name}: installed skill is not a readable ordinary directory")

    try:
        source_files, source_non_regular = payload(source_root)
        target_files, target_non_regular = payload(target_root)
    except InputError as error:
        raise InputError(f"{name}: {error}") from error

    type_errors: list[str] = []
    for path in source_non_regular:
        type_errors.append(f"source non-regular: {path.as_posix()}")
    for path in target_non_regular:
        type_errors.append(f"non-regular: {path.as_posix()}")
    if type_errors:
        raise InputError(f"{name}: " + "; ".join(type_errors))

    lines: list[str] = []
    source_paths = set(source_files)
    target_paths = set(target_files)
    for path in sorted(source_paths - target_paths):
        occupied = target_root / path
        try:
            occupied_mode = occupied.lstat().st_mode
        except FileNotFoundError:
            pass
        except OSError as error:
            raise InputError(f"{name}: cannot inspect: {path.as_posix()}") from error
        else:
            if not stat.S_ISREG(occupied_mode):
                raise InputError(f"{name}: non-regular: {path.as_posix()}")
        lines.append(f"{name}: missing: {path.as_posix()}")
    for path in sorted(target_paths - source_paths):
        lines.append(f"{name}: extra: {path.as_posix()}")
    for path in sorted(source_paths & target_paths):
        try:
            same = source_files[path].read_bytes() == target_files[path].read_bytes()
        except OSError as error:
            raise InputError(f"{name}: unreadable: {path.as_posix()}") from error
        if not same:
            lines.append(f"{name}: different: {path.as_posix()}")
    if lines:
        return lines, False
    return [f"{name}: identical"], True


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", required=True, type=Path)
    parser.add_argument("--skill", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        args = parse_args(argv)
        registry = load_registry()
        names = select_skills(registry, args.skill)
    except InputError as error:
        print(f"INPUT_ERROR: {error}", file=sys.stderr)
        return 2

    try:
        comparisons = [compare_skill(name, args.codex_home) for name in names]
    except InputError as error:
        print(f"INPUT_ERROR: {error}", file=sys.stderr)
        return 2

    passed = True
    for lines, identical in comparisons:
        passed = passed and identical
        for line in lines:
            print(line)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
