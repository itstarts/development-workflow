#!/usr/bin/env python3
"""Discover repository context without modifying the target repository."""

import argparse
import datetime
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


DATE_PATTERN = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")
TOKEN_PATTERN = re.compile(r"[\w]+", re.UNICODE)
MARKDOWN_PATH_PATTERN = re.compile(r"[\w./-]+\.md\b", re.IGNORECASE)
ASCII_KEY_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
STABLE_TOPIC_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
RESERVED_TOPICS = {"null", "unknown", "pending"}
CHINESE_PLAN_KEYS = {
    "文档类型": "document_type",
    "主题": "topic",
    "技术规格": "spec_path",
    "技术规格用户批准": "spec_user_approval",
    "评审模式": "review_mode",
    "计划评审状态": "review_status",
    "计划评审角色": "reviewer",
    "计划评审日期": "reviewed_at",
}


@dataclass(frozen=True)
class Candidate:
    path: Path
    exact: int
    coverage: float
    date: str
    mtime_ns: int
    content: str


@dataclass(frozen=True)
class MetadataRecord:
    language: str
    fields: dict


class GitUnavailableError(Exception):
    """Raised when the Git executable cannot be started."""


def run_git(workdir: Path, args: List[str]) -> Optional[str]:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=str(workdir), text=True, capture_output=True
        )
    except OSError as error:
        raise GitUnavailableError(str(error)) from error
    if completed.returncode != 0:
        return None
    return completed.stdout.rstrip("\n")


def repository_context(workdir: Path) -> dict:
    root_text = run_git(workdir, ["rev-parse", "--show-toplevel"])
    if root_text is None:
        return {
            "status": "not-a-repository",
            "workdir": str(workdir),
            "root": None,
            "branch": None,
            "head": None,
            "worktree_kind": "unknown",
            "status_short_branch": "",
        }

    branch = run_git(workdir, ["branch", "--show-current"])
    head = run_git(workdir, ["rev-parse", "HEAD"])
    status = run_git(workdir, ["status", "--short", "--branch"])
    git_dir_text = run_git(workdir, ["rev-parse", "--git-dir"])
    common_dir_text = run_git(workdir, ["rev-parse", "--git-common-dir"])
    worktree_kind = "unknown"
    if git_dir_text is not None and common_dir_text is not None:
        git_dir = (workdir / git_dir_text).resolve()
        common_dir = (workdir / common_dir_text).resolve()
        worktree_kind = "main" if git_dir == common_dir else "linked"

    return {
        "status": "ok",
        "workdir": str(workdir),
        "root": str(Path(root_text).resolve()),
        "branch": branch or None,
        "head": head or None,
        "worktree_kind": worktree_kind,
        "status_short_branch": status or "",
    }


def missing_documents() -> dict:
    return {
        "spec": {"path": None, "source": "missing"},
        "plan": {
            "path": None,
            "source": "missing",
            "review": {
                "status": "unknown",
                "reviewer": None,
                "reviewed_at": None,
                "implementation_gate": "unknown",
            },
        },
    }


def discover_rules(repository: dict) -> List[dict]:
    if repository["status"] != "ok":
        return []
    root = Path(repository["root"])
    workdir = Path(repository["workdir"])
    try:
        relative = workdir.relative_to(root)
    except ValueError:
        return []
    directories = [root]
    current = root
    for component in relative.parts:
        current = current / component
        directories.append(current)
    rules = []
    root_resolved = root.resolve()
    for directory in directories:
        path = directory / "AGENTS.md"
        try:
            if path.is_symlink():
                continue
            resolved = path.resolve()
            resolved.relative_to(root_resolved)
            if not path.is_file():
                continue
        except (OSError, ValueError):
            continue
        rules.append(
            {
                "path": str(resolved),
                "source": "filesystem",
                "precedence": len(rules),
            }
        )
    return rules


def tokens(value: str) -> List[str]:
    return [token.casefold() for token in TOKEN_PATTERN.findall(value)]


def first_heading(content: str) -> str:
    for line in content.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1)
    return ""


def valid_date(path: Path) -> str:
    match = DATE_PATTERN.search(path.name)
    if not match:
        return ""
    value = match.group(1)
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return ""
    return value


def candidate_for(path: Path, topic: str) -> Candidate:
    content = path.read_text(encoding="utf-8")
    topic_tokens = tokens(topic)
    heading_tokens = tokens(first_heading(content))
    filename_tokens = tokens(DATE_PATTERN.sub("", path.stem))
    while filename_tokens and filename_tokens[-1] in {
        "design",
        "spec",
        "specification",
        "plan",
    }:
        filename_tokens.pop()
    searchable = set(heading_tokens + filename_tokens)
    exact = int(
        bool(topic_tokens)
        and (heading_tokens == topic_tokens or filename_tokens == topic_tokens)
    )
    coverage = (
        len(set(topic_tokens) & searchable) / len(set(topic_tokens))
        if topic_tokens
        else 0.0
    )
    return Candidate(
        path=path.resolve(),
        exact=exact,
        coverage=coverage,
        date=valid_date(path),
        mtime_ns=path.stat().st_mtime_ns,
        content=content,
    )


def candidates_in(directory: Path, topic: str, repository_root: Path) -> List[Candidate]:
    if not directory.is_dir():
        return []
    candidates = []
    for path in sorted(directory.glob("*.md")):
        try:
            resolved = path.resolve()
            resolved.relative_to(repository_root.resolve())
            if path.is_symlink():
                continue
            candidates.append(candidate_for(path, topic))
        except (OSError, UnicodeError, ValueError):
            continue
    return candidates


def references(candidate: Candidate, other: Candidate) -> bool:
    content = candidate.content.casefold()
    return other.path.name.casefold() in content or str(other.path).casefold() in content


def reference_strength(spec: Candidate, plan: Candidate) -> int:
    forward = references(spec, plan)
    backward = references(plan, spec)
    if forward and backward:
        return 2
    return int(forward or backward)


def single_score(candidate: Candidate, other: Candidate, kind: str) -> tuple:
    spec, plan = (other, candidate) if kind == "plan" else (candidate, other)
    return (
        candidate.exact,
        candidate.coverage,
        reference_strength(spec, plan),
        candidate.date,
        candidate.mtime_ns,
    )


def candidate_score(candidate: Candidate) -> tuple:
    return (
        candidate.exact,
        candidate.coverage,
        candidate.date,
        candidate.mtime_ns,
    )


def select_unpaired(candidates: Sequence[Candidate], field: str) -> Tuple[Optional[Candidate], List[dict], int]:
    if not candidates:
        return None, [], 0
    best = max(candidate_score(candidate) for candidate in candidates)
    winners = [candidate for candidate in candidates if candidate_score(candidate) == best]
    if len(winners) > 1:
        return None, [
            {"field": field, "candidates": [str(item.path) for item in winners]}
        ], 2
    return winners[0], [], 0


def pair_score(spec: Candidate, plan: Candidate) -> tuple:
    return (
        min(spec.exact, plan.exact),
        spec.exact + plan.exact,
        min(spec.coverage, plan.coverage),
        spec.coverage + plan.coverage,
        reference_strength(spec, plan),
        max(spec.date, plan.date),
        min(spec.date, plan.date),
        max(spec.mtime_ns, plan.mtime_ns),
        min(spec.mtime_ns, plan.mtime_ns),
    )


def document_entry(candidate: Optional[Candidate], source: str) -> dict:
    return {"path": str(candidate.path) if candidate else None, "source": source}


def unknown_review() -> dict:
    return {
        "status": "unknown",
        "reviewer": None,
        "reviewed_at": None,
        "implementation_gate": "unknown",
    }


def scalar_value(line: str) -> Optional[Tuple[str, str]]:
    if not line or line[:1].isspace():
        return None
    match = re.fullmatch(r"([^:\s][^:]*):[ \t]*(.+?)", line)
    if not match:
        return None
    key = match.group(1)
    value = match.group(2).strip()
    if not value or value[0] in "'\"[{|>&*!" or value[-1] in "'\"]}":
        return None
    return key, value


def ascii_scalar_record(lines: Sequence[str]) -> Optional[dict]:
    records = {}
    for line in lines:
        parsed = scalar_value(line)
        if parsed is None:
            return None
        raw_key, value = parsed
        if ASCII_KEY_PATTERN.fullmatch(raw_key) is None:
            return None
        key = raw_key.casefold()
        if key in records:
            return None
        records[key] = value
    return records


def frontmatter_record(lines: Sequence[str]) -> Optional[MetadataRecord]:
    fields = {}
    language = None
    for line in lines:
        parsed = scalar_value(line)
        if parsed is None:
            return None
        raw_key, value = parsed
        if ASCII_KEY_PATTERN.fullmatch(raw_key) is not None:
            current_language = "english-legacy"
            semantic_key = raw_key.casefold()
        elif raw_key in CHINESE_PLAN_KEYS:
            current_language = "chinese-current"
            semantic_key = CHINESE_PLAN_KEYS[raw_key]
        else:
            return None
        if language is not None and current_language != language:
            return None
        language = current_language
        if semantic_key in fields:
            return None
        fields[semantic_key] = value
    if language is None:
        return None
    return MetadataRecord(language=language, fields=fields)


def review_from_records(records: Optional[dict], frontmatter: bool) -> dict:
    if records is None:
        return unknown_review()
    status_key = "review_status" if frontmatter else "review-status"
    reviewer_key = "reviewer"
    reviewed_at_key = "reviewed_at" if frontmatter else "reviewed-at"
    if status_key not in records:
        return unknown_review()
    raw_status = records[status_key]
    status = "approved" if raw_status.casefold() == "approved" else "not-approved"
    return {
        "status": status,
        "reviewer": records.get(reviewer_key),
        "reviewed_at": records.get(reviewed_at_key),
        "implementation_gate": "open" if status == "approved" else "blocked",
    }


def valid_iso_date(value: str) -> bool:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def review_from_frontmatter(record: Optional[MetadataRecord]) -> dict:
    if record is None:
        return unknown_review()
    if record.language == "english-legacy":
        return review_from_records(record.fields, frontmatter=True)

    fields = record.fields
    required = {
        "document_type",
        "topic",
        "spec_path",
        "spec_user_approval",
        "review_status",
    }
    if not required.issubset(fields):
        return unknown_review()
    if fields["document_type"] != "实施计划":
        return unknown_review()
    topic = fields["topic"]
    if (
        STABLE_TOPIC_PATTERN.fullmatch(topic) is None
        or topic in RESERVED_TOPICS
    ):
        return unknown_review()
    if not fields["spec_path"]:
        return unknown_review()

    spec_user_approval = fields["spec_user_approval"]
    review_mode = fields.get("review_mode")
    if spec_user_approval not in {"待批准", "已批准"}:
        return unknown_review()
    if review_mode not in {None, "技术包", "逐级"}:
        return unknown_review()
    if spec_user_approval == "待批准" and review_mode != "技术包":
        return unknown_review()

    raw_status = fields["review_status"]
    reviewer = fields.get("reviewer")
    reviewed_at = fields.get("reviewed_at")
    if raw_status == "待评审":
        if reviewer is not None or reviewed_at is not None:
            return unknown_review()
        return {
            "status": "not-approved",
            "reviewer": None,
            "reviewed_at": None,
            "implementation_gate": "blocked",
        }
    if raw_status == "已通过":
        if reviewer is None or reviewed_at is None or not valid_iso_date(reviewed_at):
            return unknown_review()
        return {
            "status": "approved",
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "implementation_gate": (
                "open" if spec_user_approval == "已批准" else "blocked"
            ),
        }
    return unknown_review()


def parse_review(candidate: Optional[Candidate]) -> dict:
    if candidate is None:
        return unknown_review()
    content = candidate.content
    if content.startswith("---\n"):
        lines = content.splitlines()
        try:
            closing = lines.index("---", 1)
        except ValueError:
            return unknown_review()
        return review_from_frontmatter(frontmatter_record(lines[1:closing]))

    metadata_lines = []
    for line in content.splitlines():
        if not line.strip():
            continue
        if len(metadata_lines) >= 20:
            break
        if re.match(r"^(?:#|```|~~~)", line):
            break
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*:[ \t]*.+?", line):
            break
        metadata_lines.append(line)
    return review_from_records(ascii_scalar_record(metadata_lines), frontmatter=False)


def plan_entry(candidate: Optional[Candidate], source: str) -> dict:
    entry = document_entry(candidate, source)
    entry["review"] = parse_review(candidate)
    return entry


def explicit_candidate(value: str, workdir: Path, topic: str) -> Optional[Candidate]:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = workdir / path
    try:
        if not path.is_file():
            return None
        return candidate_for(path, topic)
    except (OSError, UnicodeError):
        return None


def distinct_markdown_references(candidate: Candidate, selected: Candidate) -> bool:
    references_found = {
        Path(match).name.casefold()
        for match in MARKDOWN_PATH_PATTERN.findall(candidate.content)
    }
    return bool(references_found - {selected.path.name.casefold()})


def discover_documents(
    workdir: Path, repository: dict, topic: str, spec_value: str, plan_value: str
) -> Tuple[dict, List[dict], List[str], List[str], int]:
    ambiguities = []
    errors = []
    warnings = []
    explicit_spec = explicit_candidate(spec_value, workdir, topic) if spec_value else None
    explicit_plan = explicit_candidate(plan_value, workdir, topic) if plan_value else None
    if spec_value and explicit_spec is None:
        errors.append(f"explicit spec is not a readable file: {spec_value}")
    if plan_value and explicit_plan is None:
        errors.append(f"explicit plan is not a readable file: {plan_value}")
    if errors:
        return missing_documents(), ambiguities, errors, warnings, 3

    root = Path(repository["root"]) if repository["root"] else workdir
    specs = candidates_in(root / "docs" / "specs", topic, root)
    plans = candidates_in(root / "docs" / "plans", topic, root)

    if explicit_spec and explicit_plan:
        if distinct_markdown_references(explicit_spec, explicit_plan) or distinct_markdown_references(
            explicit_plan, explicit_spec
        ):
            warnings.append("explicit documents reference different Markdown files")
        return {
            "spec": document_entry(explicit_spec, "explicit"),
            "plan": plan_entry(explicit_plan, "explicit"),
        }, ambiguities, errors, warnings, 0

    if explicit_spec:
        if not plans:
            return {
                "spec": document_entry(explicit_spec, "explicit"),
                "plan": plan_entry(None, "missing"),
            }, ambiguities, errors, warnings, 0
        scored = [(single_score(plan, explicit_spec, "plan"), plan) for plan in plans]
        best = max(score for score, _ in scored)
        winners = [candidate for score, candidate in scored if score == best]
        if len(winners) > 1:
            ambiguities.append(
                {"field": "plan", "candidates": [str(item.path) for item in winners]}
            )
            return {
                "spec": document_entry(explicit_spec, "explicit"),
                "plan": plan_entry(None, "missing"),
            }, ambiguities, errors, warnings, 2
        return {
            "spec": document_entry(explicit_spec, "explicit"),
            "plan": plan_entry(winners[0], "discovered"),
        }, ambiguities, errors, warnings, 0

    if explicit_plan:
        if not specs:
            return {
                "spec": document_entry(None, "missing"),
                "plan": plan_entry(explicit_plan, "explicit"),
            }, ambiguities, errors, warnings, 0
        scored = [(single_score(spec, explicit_plan, "spec"), spec) for spec in specs]
        best = max(score for score, _ in scored)
        winners = [candidate for score, candidate in scored if score == best]
        if len(winners) > 1:
            ambiguities.append(
                {"field": "spec", "candidates": [str(item.path) for item in winners]}
            )
            return {
                "spec": document_entry(None, "missing"),
                "plan": plan_entry(explicit_plan, "explicit"),
            }, ambiguities, errors, warnings, 2
        return {
            "spec": document_entry(winners[0], "discovered"),
            "plan": plan_entry(explicit_plan, "explicit"),
        }, ambiguities, errors, warnings, 0

    if not specs or not plans:
        spec, spec_ambiguities, spec_exit = select_unpaired(specs, "spec")
        plan, plan_ambiguities, plan_exit = select_unpaired(plans, "plan")
        return {
            "spec": document_entry(spec, "discovered" if spec else "missing"),
            "plan": plan_entry(plan, "discovered" if plan else "missing"),
        }, spec_ambiguities + plan_ambiguities, errors, warnings, max(spec_exit, plan_exit)
    scored_pairs = [(pair_score(spec, plan), spec, plan) for spec in specs for plan in plans]
    best = max(score for score, _, _ in scored_pairs)
    winners = [(spec, plan) for score, spec, plan in scored_pairs if score == best]
    if len(winners) > 1:
        paths = sorted({str(item.path) for pair in winners for item in pair})
        ambiguities.append({"field": "document_pair", "candidates": paths})
        return missing_documents(), ambiguities, errors, warnings, 2
    spec, plan = winners[0]
    return {
        "spec": document_entry(spec, "discovered"),
        "plan": plan_entry(plan, "discovered"),
    }, ambiguities, errors, warnings, 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--topic")
    parser.add_argument("--request", default="")
    parser.add_argument("--spec")
    parser.add_argument("--plan")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workdir = Path(args.cwd).expanduser().resolve()
    if not workdir.is_dir():
        payload = {
            "schema_version": 1,
            "repository": {
                "status": "not-a-repository",
                "workdir": str(workdir),
                "root": None,
                "branch": None,
                "head": None,
                "worktree_kind": "unknown",
                "status_short_branch": "",
            },
            "rules": [],
            "documents": missing_documents(),
            "ambiguities": [],
            "errors": [f"explicit cwd is not a readable directory: {args.cwd}"],
            "warnings": [],
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 3
    try:
        repository = repository_context(workdir)
    except GitUnavailableError as error:
        payload = {
            "schema_version": 1,
            "repository": {
                "status": "not-a-repository",
                "workdir": str(workdir),
                "root": None,
                "branch": None,
                "head": None,
                "worktree_kind": "unknown",
                "status_short_branch": "",
            },
            "rules": [],
            "documents": missing_documents(),
            "ambiguities": [],
            "errors": [f"Git unavailable: {error}"],
            "warnings": [],
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 3
    effective_topic = args.topic if args.topic is not None else args.request
    documents, ambiguities, errors, warnings, exit_code = discover_documents(
        workdir, repository, effective_topic, args.spec, args.plan
    )
    payload = {
        "schema_version": 1,
        "repository": repository,
        "rules": discover_rules(repository),
        "documents": documents,
        "ambiguities": ambiguities,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
