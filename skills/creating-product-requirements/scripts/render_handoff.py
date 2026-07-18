#!/usr/bin/env python3
"""Validate one canonical workflow handoff and render its selected text view."""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Optional, Sequence


TOP_FIELDS = (
    "schema_version",
    "handoff_schema",
    "view",
    "canonical",
    "stage",
    "next_step",
)
REQUIREMENTS_FIELDS = (
    "requirements_path",
    "requirements_topic",
    "requirements_scope",
    "understanding_confidence",
    "understanding_user_confirmation",
    "requirements_user_approval",
    "requirements_independent_review",
    "specification_gate",
)
WORKFLOW_FIELDS = (
    "requirements_path",
    "requirements_topic",
    "requirements_scope",
    "requirements_understanding_confidence",
    "requirements_understanding_confirmation",
    "requirements_user_approval",
    "requirements_independent_review",
    "specification_gate",
    "spec_path",
    "spec_user_approval",
    "spec_independent_review",
    "plan_path",
    "plan_review_status",
    "implementation_gate",
)
STAGES = {"需求澄清", "技术规格澄清", "实施计划澄清"}
TOPIC_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESERVED_TOPICS = {"null", "pending"}
FORBIDDEN_LINE_SEPARATORS = {"\u0085", "\u2028", "\u2029"}


class Pairs(list):
    pass


class InputFailure(Exception):
    def __init__(self, exit_code: int, code: str, errors: Sequence[str]):
        super().__init__(errors[0] if errors else code)
        self.exit_code = exit_code
        self.code = code
        self.errors = list(errors)


class NonstandardNumber(Exception):
    pass


def pointer(parts: Sequence[str]) -> str:
    return "".join("/" + part.replace("~", "~0").replace("/", "~1") for part in parts)


def error(path: Sequence[str], reason: str) -> str:
    return f"{pointer(path)}: {reason}"


def has_surrogate(value: str) -> bool:
    return any(0xD800 <= ord(character) <= 0xDFFF for character in value)


def parse_input(raw: bytes) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise InputFailure(2, "invalid_json", [": bom"])
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as failure:
        raise InputFailure(2, "invalid_json", [": invalid_utf8"]) from failure
    if not text.strip():
        raise InputFailure(2, "invalid_json", [": invalid_syntax"])

    def reject_constant(_: str) -> None:
        raise NonstandardNumber

    try:
        value = json.loads(
            text,
            object_pairs_hook=Pairs,
            parse_constant=reject_constant,
        )
    except NonstandardNumber as failure:
        raise InputFailure(2, "invalid_json", [": nonstandard_number"]) from failure
    except (json.JSONDecodeError, RecursionError) as failure:
        raise InputFailure(2, "invalid_json", [": invalid_syntax"]) from failure

    findings: dict[str, str] = {}

    def record(parts: Sequence[str], reason: str) -> None:
        location = pointer(parts)
        if location not in findings or reason == "duplicate":
            findings[location] = reason

    def walk(item: Any, parts: list[str]) -> None:
        if isinstance(item, Pairs):
            counts: dict[str, int] = {}
            for key, _ in item:
                counts[key] = counts.get(key, 0) + 1
            for key, count in counts.items():
                if count > 1:
                    record(parts + [key], "duplicate")
            for key, nested in item:
                nested_path = parts + [key]
                if has_surrogate(key):
                    record(nested_path, "surrogate")
                walk(nested, nested_path)
        elif isinstance(item, list):
            for index, nested in enumerate(item):
                walk(nested, parts + [str(index)])
        elif isinstance(item, str) and has_surrogate(item):
            record(parts, "surrogate")

    walk(value, [])
    if findings:
        raise InputFailure(
            2,
            "invalid_json",
            [f"{path}: {findings[path]}" for path in sorted(findings)],
        )
    return value


def pairs_to_value(value: Any) -> Any:
    if isinstance(value, Pairs):
        return {key: pairs_to_value(item) for key, item in value}
    if isinstance(value, list):
        return [pairs_to_value(item) for item in value]
    return value


def validate_top(value: Any) -> dict[str, Any]:
    if not isinstance(value, Pairs):
        raise InputFailure(3, "invalid_input", [": wrong_type"])
    data = pairs_to_value(value)
    errors: list[str] = []
    for field in TOP_FIELDS:
        if field not in data:
            errors.append(error([field], "missing"))
            continue
        item = data[field]
        if field == "schema_version":
            if not isinstance(item, int) or isinstance(item, bool):
                errors.append(error([field], "wrong_type"))
            elif item != 1:
                errors.append(error([field], "invalid_value"))
        elif field == "handoff_schema":
            if not isinstance(item, str):
                errors.append(error([field], "wrong_type"))
            elif item not in {"requirements", "workflow"}:
                errors.append(error([field], "invalid_value"))
        elif field == "view":
            if not isinstance(item, str):
                errors.append(error([field], "wrong_type"))
            elif item not in {"compact", "full"}:
                errors.append(error([field], "invalid_value"))
        elif field == "canonical":
            if not isinstance(item, dict):
                errors.append(error([field], "wrong_type"))
        elif item is not None and not isinstance(item, str):
            errors.append(error([field], "wrong_type"))
    for field in sorted(set(data) - set(TOP_FIELDS)):
        errors.append(error([field], "unexpected"))
    if errors:
        raise InputFailure(3, "invalid_input", errors)
    return data


def forbidden_text_reason(value: str) -> Optional[str]:
    if "\r" in value or "\n" in value:
        return "line_break"
    if any(ord(character) < 0x20 for character in value):
        return "forbidden_character"
    if any(character in FORBIDDEN_LINE_SEPARATORS for character in value):
        return "forbidden_character"
    return None


def validate_path(value: Any, path: list[str]) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        return error(path, "wrong_type")
    if not value:
        return error(path, "empty")
    reason = forbidden_text_reason(value)
    if reason:
        return error(path, reason)
    if value.strip() != value:
        return error(path, "invalid_value")
    return None


def validate_topic(value: Any, path: list[str]) -> Optional[str]:
    if value is None or value == "unknown":
        return None
    if not isinstance(value, str):
        return error(path, "wrong_type")
    if value in RESERVED_TOPICS:
        return error(path, "reserved")
    if not TOPIC_PATTERN.fullmatch(value):
        return error(path, "invalid_value")
    return None


def validate_enum(value: Any, allowed: set[str], path: list[str]) -> Optional[str]:
    if not isinstance(value, str):
        return error(path, "wrong_type")
    if value not in allowed:
        return error(path, "invalid_value")
    return None


def validate_confidence(value: Any, path: list[str]) -> Optional[str]:
    if value == "unknown":
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        return error(path, "wrong_type")
    if value < 0 or value > 100:
        return error(path, "out_of_range")
    return None


def validate_canonical(data: dict[str, Any]) -> dict[str, Any]:
    schema = data["handoff_schema"]
    canonical = data["canonical"]
    fields = REQUIREMENTS_FIELDS if schema == "requirements" else WORKFLOW_FIELDS
    errors: list[str] = []
    for field in fields:
        path = ["canonical", field]
        if field not in canonical:
            errors.append(error(path, "missing"))
            continue
        value = canonical[field]
        finding: Optional[str] = None
        if field in {"requirements_path", "spec_path", "plan_path"}:
            finding = validate_path(value, path)
        elif field == "requirements_topic":
            finding = validate_topic(value, path)
        elif field == "requirements_scope":
            finding = validate_enum(value, {"product", "phase", "feature", "unknown"}, path) if value is not None else None
        elif field in {"understanding_confidence", "requirements_understanding_confidence"}:
            finding = validate_confidence(value, path)
        elif field in {"understanding_user_confirmation", "requirements_understanding_confirmation"}:
            finding = validate_enum(value, {"pending", "approved", "unknown"}, path)
        elif field in {"requirements_user_approval", "requirements_independent_review"}:
            finding = validate_enum(value, {"pending", "approved", "unknown"}, path)
        elif field in {"specification_gate", "implementation_gate"}:
            finding = validate_enum(value, {"blocked", "open"}, path)
        elif field in {"spec_user_approval", "spec_independent_review"}:
            finding = validate_enum(value, {"pending", "approved"}, path)
        elif field == "plan_review_status":
            finding = validate_enum(value, {"not-approved", "approved", "unknown"}, path)
            if finding is None and canonical.get("plan_path") is None and value != "not-approved":
                finding = error(path, "conflict")
        if finding:
            errors.append(finding)
    for field in sorted(set(canonical) - set(fields)):
        errors.append(error(["canonical", field], "unexpected"))
    if errors:
        raise InputFailure(4, "invalid_canonical", errors)
    return canonical


def requirements_gate_open(schema: str, canonical: dict[str, Any]) -> bool:
    confidence_field = (
        "understanding_confidence"
        if schema == "requirements"
        else "requirements_understanding_confidence"
    )
    confirmation_field = (
        "understanding_user_confirmation"
        if schema == "requirements"
        else "requirements_understanding_confirmation"
    )
    confidence = canonical[confidence_field]
    return (
        canonical["requirements_path"] is not None
        and isinstance(canonical["requirements_topic"], str)
        and canonical["requirements_topic"] != "unknown"
        and canonical["requirements_scope"] in {"product", "phase", "feature"}
        and isinstance(confidence, int)
        and not isinstance(confidence, bool)
        and confidence >= 95
        and canonical[confirmation_field] == "approved"
        and canonical["requirements_user_approval"] == "approved"
        and canonical["requirements_independent_review"] == "approved"
    )


def validate_gates(schema: str, canonical: dict[str, Any]) -> None:
    errors: list[str] = []
    expected_spec = "open" if requirements_gate_open(schema, canonical) else "blocked"
    if canonical["specification_gate"] != expected_spec:
        errors.append(error(["canonical", "specification_gate"], "conflict"))
    if schema == "workflow":
        expected_implementation = "open" if (
            expected_spec == "open"
            and canonical["spec_path"] is not None
            and canonical["spec_user_approval"] == "approved"
            and canonical["spec_independent_review"] == "approved"
            and canonical["plan_path"] is not None
            and canonical["plan_review_status"] == "approved"
        ) else "blocked"
        if canonical["implementation_gate"] != expected_implementation:
            errors.append(error(["canonical", "implementation_gate"], "conflict"))
    if errors:
        raise InputFailure(5, "gate_conflict", errors)


def validate_view(data: dict[str, Any]) -> None:
    errors: list[str] = []
    stage = data["stage"]
    next_step = data["next_step"]
    if data["view"] == "full":
        if stage is not None:
            errors.append(error(["stage"], "invalid_value"))
        if next_step is not None:
            errors.append(error(["next_step"], "invalid_value"))
    else:
        if not isinstance(stage, str):
            errors.append(error(["stage"], "wrong_type"))
        elif stage not in STAGES:
            errors.append(error(["stage"], "invalid_value"))
        if not isinstance(next_step, str):
            errors.append(error(["next_step"], "wrong_type"))
        elif not next_step:
            errors.append(error(["next_step"], "empty"))
        elif len(next_step) > 200:
            errors.append(error(["next_step"], "out_of_range"))
        else:
            reason = forbidden_text_reason(next_step)
            if reason:
                errors.append(error(["next_step"], reason))
            elif next_step.strip() != next_step:
                errors.append(error(["next_step"], "invalid_value"))
    if errors:
        raise InputFailure(7, "invalid_compact", errors)


def mapped(value: Any, mapping: dict[Any, str], path: str) -> str:
    try:
        return mapping[value]
    except (KeyError, TypeError) as failure:
        raise InputFailure(6, "mapping_error", [f"{path}: missing_mapping"]) from failure


def render_compact(data: dict[str, Any], canonical: dict[str, Any]) -> str:
    topic_value = canonical["requirements_topic"]
    topic = "未确定" if topic_value is None else ("未知" if topic_value == "unknown" else str(topic_value))
    return f"当前阶段：{data['stage']}\n主题：{topic}\n下一步：{data['next_step']}\n"


def render_full(schema: str, canonical: dict[str, Any]) -> str:
    confidence_field = "understanding_confidence" if schema == "requirements" else "requirements_understanding_confidence"
    confirmation_field = "understanding_user_confirmation" if schema == "requirements" else "requirements_understanding_confirmation"
    path_value = lambda value, missing: missing if value is None else str(value)
    topic_value = lambda value: "未确定" if value is None else ("未知" if value == "unknown" else str(value))
    confidence = canonical[confidence_field]
    lines = [
        "需求文档：" + path_value(canonical["requirements_path"], "未确定"),
        "需求主题：" + topic_value(canonical["requirements_topic"]),
        "需求范围：" + mapped(canonical["requirements_scope"], {"product": "产品", "phase": "阶段", "feature": "功能", None: "未确定", "unknown": "未知"}, "/canonical/requirements_scope"),
        "需求理解置信度：" + ("未知" if confidence == "unknown" else str(confidence)),
        "需求理解确认：" + mapped(canonical[confirmation_field], {"pending": "待确认", "approved": "已确认", "unknown": "未知"}, f"/canonical/{confirmation_field}"),
        "需求文档用户批准：" + mapped(canonical["requirements_user_approval"], {"pending": "待批准", "approved": "已批准", "unknown": "未知"}, "/canonical/requirements_user_approval"),
        "需求文档独立评审：" + mapped(canonical["requirements_independent_review"], {"pending": "待评审", "approved": "已通过", "unknown": "未知"}, "/canonical/requirements_independent_review"),
        "技术规格门禁：" + mapped(canonical["specification_gate"], {"blocked": "未开放", "open": "已开放"}, "/canonical/specification_gate"),
    ]
    if schema == "workflow":
        plan_status = "未开始" if canonical["plan_path"] is None else mapped(canonical["plan_review_status"], {"not-approved": "未通过", "approved": "已通过", "unknown": "未知"}, "/canonical/plan_review_status")
        lines.extend(
            [
                "技术规格：" + path_value(canonical["spec_path"], "未确定"),
                "技术规格用户批准：" + mapped(canonical["spec_user_approval"], {"pending": "待批准", "approved": "已批准"}, "/canonical/spec_user_approval"),
                "技术规格独立评审：" + mapped(canonical["spec_independent_review"], {"pending": "待评审", "approved": "已通过"}, "/canonical/spec_independent_review"),
                "实施计划：" + path_value(canonical["plan_path"], "尚未创建"),
                "计划评审状态：" + plan_status,
                "实施门禁：" + mapped(canonical["implementation_gate"], {"blocked": "未开放", "open": "已开放"}, "/canonical/implementation_gate"),
            ]
        )
    return "\n".join(lines) + "\n"


def fail(failure: InputFailure) -> int:
    payload = {"code": failure.code, "errors": failure.errors}
    sys.stderr.buffer.write(
        (json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n").encode("utf-8")
    )
    return failure.exit_code


def main() -> int:
    try:
        parsed = parse_input(sys.stdin.buffer.read())
        data = validate_top(parsed)
        canonical = validate_canonical(data)
        validate_gates(data["handoff_schema"], canonical)
        validate_view(data)
        output = render_compact(data, canonical) if data["view"] == "compact" else render_full(data["handoff_schema"], canonical)
        sys.stdout.buffer.write(output.encode("utf-8", "strict"))
        return 0
    except InputFailure as failure:
        return fail(failure)


if __name__ == "__main__":
    raise SystemExit(main())
