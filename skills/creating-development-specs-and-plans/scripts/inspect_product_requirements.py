#!/usr/bin/env python3
"""Inspect one PRD as a deterministic prerequisite for technical specification work."""

import argparse
import datetime
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
PRD_ENGLISH_KEYS = {
    "document_type",
    "topic",
    "scope_type",
    "understanding_confidence",
    "understanding_user_confirmation",
    "user_approval",
    "approved_at",
    "independent_review",
    "independent_reviewer",
    "independent_reviewed_at",
}
PRD_CHINESE_KEYS = {
    "文档类型": "document_type",
    "主题": "topic",
    "范围类型": "scope_type",
    "理解置信度": "understanding_confidence",
    "需求理解确认": "understanding_user_confirmation",
    "用户批准": "user_approval",
    "批准日期": "approved_at",
    "独立评审": "independent_review",
    "独立评审角色": "independent_reviewer",
    "独立评审日期": "independent_reviewed_at",
}
PRD_CHINESE_VALUES = {
    "document_type": {"产品需求": "product-requirements"},
    "scope_type": {"产品": "product", "阶段": "phase", "功能": "feature"},
    "understanding_user_confirmation": {"已确认": "approved"},
    "user_approval": {"待批准": "pending", "已批准": "approved"},
    "independent_review": {"待评审": "pending", "已通过": "approved"},
}


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
) -> Tuple[Optional[Dict[str, str]], List[str], Set[str], Optional[str]]:
    if not text.startswith("---\n"):
        return None, ["missing_frontmatter"], set(), None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, ["malformed_frontmatter"], set(), None

    fields: Dict[str, str] = {}
    issues: List[str] = []
    unreliable_keys: Set[str] = set()
    schema_languages: Set[str] = set()
    for raw_line in text[4:end].splitlines():
        if not raw_line or raw_line[:1].isspace() or ":" not in raw_line:
            issues.append("malformed_frontmatter")
            continue
        raw_key, value = raw_line.split(":", 1)
        value = value.strip()
        language: Optional[str] = None
        if raw_key in PRD_CHINESE_KEYS:
            key = PRD_CHINESE_KEYS[raw_key]
            language = "chinese-current"
        elif KEY_PATTERN.fullmatch(raw_key) is not None:
            key = raw_key
            if raw_key in PRD_ENGLISH_KEYS:
                language = "english-legacy"
        else:
            issues.append("malformed_frontmatter")
            continue
        if not value:
            issues.append("malformed_frontmatter")
            unreliable_keys.add(key)
            continue
        if language is not None:
            schema_languages.add(language)
        if key in fields:
            issues.append("duplicate_key")
            unreliable_keys.add(key)
            continue
        if value[:1] in {"'", '"', "[", "{"} or value in {"|", ">"}:
            issues.append("unsupported_metadata_value")
            unreliable_keys.add(key)
            continue
        fields[key] = value
    schema: Optional[str] = None
    if len(schema_languages) > 1:
        issues.append("mixed_schema")
        schema = "mixed_schema"
    elif schema_languages:
        schema = next(iter(schema_languages))
    return fields, sorted(set(issues)), unreliable_keys, schema


def valid_iso_date(value: Optional[str]) -> bool:
    if value is None or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


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

    fields, parse_issues, unreliable_keys, schema = parse_frontmatter(text)
    issues.extend(parse_issues)
    if fields is None:
        return payload

    globally_unreliable = any(
        issue in parse_issues for issue in ("malformed_frontmatter", "mixed_schema")
    )

    def field(name: str) -> Optional[str]:
        if globally_unreliable or name in unreliable_keys:
            return None
        return fields.get(name)

    def normalized_field(name: str) -> Optional[str]:
        value = field(name)
        if value is None or schema != "chinese-current":
            return value
        aliases = PRD_CHINESE_VALUES.get(name)
        if aliases is None:
            return value
        normalized = aliases.get(value)
        if normalized is None:
            issues.append("unsupported_localized_value")
            unreliable_keys.add(name)
        return normalized

    document_type = normalized_field("document_type")
    topic = field("topic")
    scope = normalized_field("scope_type")
    confidence_text = field("understanding_confidence")
    confirmation = normalized_field("understanding_user_confirmation")
    user_approval = normalized_field("user_approval")
    independent_review = normalized_field("independent_review")

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

    if schema == "chinese-current" and not globally_unreliable:
        approved_at = field("approved_at")
        reviewer = field("independent_reviewer")
        reviewed_at = field("independent_reviewed_at")
        if user_approval == "approved":
            if not valid_iso_date(approved_at):
                issues.append("invalid_approval_metadata")
        elif user_approval == "pending" and approved_at is not None:
            issues.append("invalid_approval_metadata")
        if independent_review == "approved":
            if reviewer is None or not valid_iso_date(reviewed_at):
                issues.append("invalid_review_metadata")
        elif independent_review == "pending" and (
            reviewer is not None or reviewed_at is not None
        ):
            issues.append("invalid_review_metadata")

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
