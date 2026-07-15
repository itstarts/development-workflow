#!/usr/bin/env python3
"""Inspect one PRD as a deterministic prerequisite for technical specification work."""

import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


SCOPES = ("product", "phase", "feature")
APPROVAL_STATES = ("pending", "approved")
KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
TOPIC_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
RESERVED_TOPICS = {"null", "unknown", "pending"}


def stable_topic(value: str) -> str:
    if TOPIC_PATTERN.fullmatch(value) is None or value in RESERVED_TOPICS:
        raise argparse.ArgumentTypeError(
            "expected topic must be a non-reserved kebab-case stable topic"
        )
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect an approved product requirements document."
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--requirements", required=True)
    parser.add_argument("--expected-topic", required=True, type=stable_topic)
    parser.add_argument("--expected-scope", required=True, choices=SCOPES)
    return parser.parse_args()


def inside(root: Path, candidate: Path) -> bool:
    try:
        return os.path.commonpath((str(root), str(candidate))) == str(root)
    except ValueError:
        return False


def empty_payload(
    repo_root: Path,
    requirements_path: Path,
    expected_topic: str,
    expected_scope: str,
) -> Dict[str, object]:
    return {
        "schema_version": 1,
        "repo_root": str(repo_root),
        "requirements_path": str(requirements_path),
        "expected_topic": expected_topic,
        "expected_scope": expected_scope,
        "document_type": None,
        "requirements_topic": None,
        "requirements_scope": None,
        "understanding_confidence": None,
        "understanding_user_confirmation": "unknown",
        "requirements_user_approval": "unknown",
        "requirements_independent_review": "unknown",
        "status": "unknown",
        "specification_gate": "blocked",
        "issues": [],
    }


def parse_frontmatter(
    text: str,
) -> Tuple[Optional[Dict[str, str]], List[str], Set[str]]:
    if not text.startswith("---\n"):
        return None, ["missing_frontmatter"], set()
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, ["malformed_frontmatter"], set()

    fields: Dict[str, str] = {}
    issues: List[str] = []
    unreliable_keys: Set[str] = set()
    for raw_line in text[4:end].splitlines():
        if not raw_line or raw_line[:1].isspace() or ":" not in raw_line:
            issues.append("malformed_frontmatter")
            continue
        key, value = raw_line.split(":", 1)
        value = value.strip()
        if KEY_PATTERN.fullmatch(key) is None or not value:
            issues.append("malformed_frontmatter")
            continue
        if key in fields:
            issues.append("duplicate_key")
            unreliable_keys.add(key)
            continue
        if value[:1] in {"'", '"', "[", "{"} or value in {"|", ">"}:
            issues.append("unsupported_metadata_value")
            unreliable_keys.add(key)
            continue
        fields[key] = value
    return fields, sorted(set(issues)), unreliable_keys


def inspect(args: argparse.Namespace) -> Dict[str, object]:
    repo_root = Path(args.repo_root).expanduser().resolve()
    supplied = Path(args.requirements).expanduser()
    requirements_path = (
        supplied.resolve()
        if supplied.is_absolute()
        else (repo_root / supplied).resolve()
    )
    payload = empty_payload(
        repo_root, requirements_path, args.expected_topic, args.expected_scope
    )
    issues = payload["issues"]
    assert isinstance(issues, list)

    git_marker = repo_root / ".git"
    if not repo_root.is_dir() or not (git_marker.is_dir() or git_marker.is_file()):
        issues.append("invalid_repo_root")
        return payload
    if not inside(repo_root, requirements_path):
        issues.append("outside_repo")
        return payload
    if not requirements_path.exists():
        issues.append("missing_file")
        return payload
    if not requirements_path.is_file():
        issues.append("not_a_file")
        return payload

    try:
        text = requirements_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        issues.append("unreadable_file")
        return payload

    fields, parse_issues, unreliable_keys = parse_frontmatter(text)
    issues.extend(parse_issues)
    if fields is None:
        return payload

    globally_unreliable = "malformed_frontmatter" in parse_issues

    def field(name: str) -> Optional[str]:
        if globally_unreliable or name in unreliable_keys:
            return None
        return fields.get(name)

    document_type = field("document_type")
    topic = field("topic")
    scope = field("scope_type")
    confidence_text = field("understanding_confidence")
    confirmation = field("understanding_user_confirmation")
    user_approval = field("user_approval")
    independent_review = field("independent_review")

    topic_is_valid = (
        topic is not None
        and TOPIC_PATTERN.fullmatch(topic) is not None
        and topic not in RESERVED_TOPICS
    )
    scope_is_valid = scope in SCOPES
    confirmation_is_valid = confirmation in APPROVAL_STATES
    user_approval_is_valid = user_approval in APPROVAL_STATES
    independent_review_is_valid = independent_review in APPROVAL_STATES

    payload["document_type"] = document_type
    payload["requirements_topic"] = (
        topic if topic_is_valid and topic == args.expected_topic else "unknown"
    )
    payload["requirements_scope"] = (
        scope if scope_is_valid and scope == args.expected_scope else "unknown"
    )
    payload["understanding_user_confirmation"] = (
        confirmation if confirmation_is_valid else "unknown"
    )
    payload["requirements_user_approval"] = (
        user_approval if user_approval_is_valid else "unknown"
    )
    payload["requirements_independent_review"] = (
        independent_review if independent_review_is_valid else "unknown"
    )

    confidence: Optional[int] = None
    if confidence_text is not None:
        try:
            confidence = int(confidence_text)
        except ValueError:
            pass
    confidence_is_valid = confidence is not None and 0 <= confidence <= 100
    payload["understanding_confidence"] = confidence if confidence_is_valid else None

    if document_type != "product-requirements":
        issues.append("invalid_document_type")
    if topic is None and "topic" not in unreliable_keys:
        issues.append("missing_topic")
    elif not topic_is_valid:
        issues.append("invalid_topic")
    elif topic != args.expected_topic:
        issues.append("topic_mismatch")
    if not scope_is_valid:
        issues.append("invalid_scope")
    elif scope != args.expected_scope:
        issues.append("scope_mismatch")
    if not confidence_is_valid:
        issues.append("invalid_confidence")
    if not all(
        (
            confirmation_is_valid,
            user_approval_is_valid,
            independent_review_is_valid,
        )
    ):
        issues.append("invalid_approval_state")

    issues[:] = sorted(set(issues))
    unreliable = any(
        issue
        for issue in issues
        if issue
        not in {
            "confidence_below_threshold",
            "understanding_confirmation_pending",
            "user_approval_pending",
            "independent_review_pending",
        }
    )
    if unreliable:
        return payload

    if confidence is not None and confidence < 95:
        issues.append("confidence_below_threshold")
    if confirmation == "pending":
        issues.append("understanding_confirmation_pending")
    if user_approval == "pending":
        issues.append("user_approval_pending")
    if independent_review == "pending":
        issues.append("independent_review_pending")
    issues[:] = sorted(set(issues))

    if issues:
        payload["status"] = "not-approved"
        return payload

    payload["status"] = "approved"
    payload["specification_gate"] = "open"
    return payload


def main() -> int:
    args = parse_args()
    payload = inspect(args)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
