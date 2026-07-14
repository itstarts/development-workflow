#!/usr/bin/env python3
"""Validate discovered context and render one development prompt to stdout."""

import json
import sys
from pathlib import Path
from string import Template
from typing import Any, Dict, List


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "assets" / "development-prompt.md"
TOP_LEVEL_TYPES = {
    "schema_version": int,
    "repository": dict,
    "rules": list,
    "documents": dict,
    "ambiguities": list,
    "errors": list,
    "warnings": list,
    "request": dict,
    "session_rules": list,
    "permissions": dict,
}
DEFAULT_ALLOWED = (
    "create-development-branch-or-worktree",
    "create-local-commit",
    "query-official-documentation",
    "install-plan-listed-dependencies",
    "download-plan-required-playwright-browsers",
    "start-local-development-service",
    "run-tests-build-lint-local-validation",
)
DEFAULT_FORBIDDEN = (
    "push",
    "merge",
    "rebase",
    "tag",
    "release",
    "production-deployment",
    "cloudflare-or-dns-change",
    "unauthorized-secrets-tokens-credentials-or-production-data",
)
MAX_JSON_NESTING = 1000


class InputError(Exception):
    def __init__(self, code: str, errors: List[str]):
        super().__init__(errors[0] if errors else code)
        self.code = code
        self.errors = errors


def json_nesting_exceeds_limit(value: Any, limit: int = MAX_JSON_NESTING) -> bool:
    stack = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > limit:
            return True
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
    return False


def require_type(container: Dict[str, Any], field: str, expected: type, path: str) -> Any:
    value = container.get(field)
    if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
        raise InputError("invalid_input", [f"{path}.{field} must be {expected.__name__}"])
    return value


def require_nullable_string(container: Dict[str, Any], field: str, path: str) -> Any:
    if field not in container:
        raise InputError("invalid_input", [f"{path}.{field} is required"])
    value = container[field]
    if value is not None and not isinstance(value, str):
        raise InputError("invalid_input", [f"{path}.{field} must be string or null"])
    return value


def require_absolute_path(value: str, path: str) -> None:
    if not Path(value).is_absolute():
        raise InputError("invalid_input", [f"{path} must be an absolute path"])


def validate_rule(rule: Any, path: str, expected_source: str) -> None:
    if not isinstance(rule, dict):
        raise InputError("invalid_input", [f"{path} must be object"])
    rule_path = require_type(rule, "path", str, path)
    require_absolute_path(rule_path, f"{path}.path")
    source = require_type(rule, "source", str, path)
    if source != expected_source:
        raise InputError("invalid_input", [f"{path}.source must be {expected_source}"])
    require_type(rule, "precedence", int, path)


def validate(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise InputError("invalid_input", ["input must be a JSON object"])
    for field, expected in TOP_LEVEL_TYPES.items():
        require_type(payload, field, expected, "input")
    if payload["schema_version"] != 1:
        raise InputError("invalid_input", ["input.schema_version must equal 1"])
    if payload["ambiguities"] or payload["errors"]:
        raise InputError("blocked_input", ["discovery ambiguities or errors remain unresolved"])

    request = payload["request"]
    goal = request.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        raise InputError("invalid_input", ["input.request.goal must be a non-empty string"])
    require_nullable_string(request, "target_branch", "input.request")

    repository = payload["repository"]
    for field in ("status", "workdir", "worktree_kind", "status_short_branch"):
        require_type(repository, field, str, "input.repository")
    for field in ("root", "branch", "head"):
        require_nullable_string(repository, field, "input.repository")
    if repository["status"] not in {"ok", "not-a-repository"}:
        raise InputError("invalid_input", ["input.repository.status is not recognized"])
    if repository["worktree_kind"] not in {"main", "linked", "unknown"}:
        raise InputError("invalid_input", ["input.repository.worktree_kind is not recognized"])
    require_absolute_path(repository["workdir"], "input.repository.workdir")
    if repository["root"] is not None:
        require_absolute_path(repository["root"], "input.repository.root")

    for index, rule in enumerate(payload["session_rules"]):
        validate_rule(rule, f"input.session_rules[{index}]", "session")
    for index, rule in enumerate(payload["rules"]):
        validate_rule(rule, f"input.rules[{index}]", "filesystem")

    documents = payload["documents"]
    spec = require_type(documents, "spec", dict, "input.documents")
    plan = require_type(documents, "plan", dict, "input.documents")
    for name, document in (("spec", spec), ("plan", plan)):
        path = require_nullable_string(document, "path", f"input.documents.{name}")
        source = require_type(document, "source", str, f"input.documents.{name}")
        if source not in {"explicit", "discovered", "missing"}:
            raise InputError("invalid_input", [f"input.documents.{name}.source is not recognized"])
        if path is None:
            raise InputError("blocked_input", [f"input.documents.{name}.path is missing"])
        require_absolute_path(path, f"input.documents.{name}.path")
    review = require_type(plan, "review", dict, "input.documents.plan")
    review_status = require_type(review, "status", str, "input.documents.plan.review")
    if review_status not in {"approved", "not-approved", "unknown"}:
        raise InputError("invalid_input", ["input.documents.plan.review.status is not recognized"])
    for field in ("reviewer", "reviewed_at"):
        require_nullable_string(review, field, "input.documents.plan.review")

    permissions = payload["permissions"]
    allowed = require_type(permissions, "allowed", list, "input.permissions")
    forbidden = require_type(permissions, "forbidden", list, "input.permissions")
    source = require_type(permissions, "source", str, "input.permissions")
    if source not in {"defaults", "explicit"}:
        raise InputError("invalid_input", ["input.permissions.source is not recognized"])
    if not all(isinstance(item, str) and item for item in allowed + forbidden):
        raise InputError("invalid_input", ["permission entries must be non-empty strings"])
    conflicts = sorted(set(allowed) & set(forbidden))
    if conflicts:
        raise InputError("permission_conflict", [f"operation is both allowed and forbidden: {item}" for item in conflicts])


def safe_text(value: Any) -> str:
    """Return a reversible, single-line JSON-string representation without quotes."""
    encoded = json.dumps(str(value), ensure_ascii=False)[1:-1]
    return (
        encoded.replace("\u2028", r"\u2028")
        .replace("\u2029", r"\u2029")
        .replace("`", r"\u0060")
    )


def effective_permissions(permissions: Dict[str, Any]) -> tuple:
    allowed = list(DEFAULT_ALLOWED)
    forbidden = list(DEFAULT_FORBIDDEN)

    def append_unique(items: List[str], value: str) -> None:
        if value not in items:
            items.append(value)

    if permissions["source"] == "defaults":
        for item in permissions["allowed"]:
            append_unique(allowed, item)
        for item in permissions["forbidden"]:
            append_unique(forbidden, item)
    else:
        for item in permissions["allowed"]:
            if item in forbidden:
                forbidden.remove(item)
            append_unique(allowed, item)
        for item in permissions["forbidden"]:
            if item in allowed:
                allowed.remove(item)
            append_unique(forbidden, item)
    return allowed, forbidden


def render(payload: Dict[str, Any]) -> str:
    repository = payload["repository"]
    documents = payload["documents"]
    plan_review = documents["plan"]["review"]
    target = payload["request"]["target_branch"]
    branch_gate = (
        "目标分支未指定：修改前根据计划与仓库规则派生开发分支名；不得直接使用 main 或 master，仓库状态不允许建分支时停止。"
        if target is None
        else (
            "修改前确认目标开发分支符合仓库规则；"
            f"显式目标为 {safe_text(target)}；"
            "且不得直接在 main 或 master 上开发。"
        )
    )
    repository_gate = (
        "仓库状态不是 Git 仓库：实施前停止修改，建立或切换到符合任务要求的 Git 仓库并重新核对上下文。"
        if repository["status"] == "not-a-repository"
        else "仓库状态已识别为 Git 仓库。"
    )
    rules = sorted(payload["session_rules"] + payload["rules"], key=lambda item: item["precedence"])
    rule_lines = "\n".join(
        f"- {safe_text(item['path'])}（来源：{safe_text(item['source'])}；"
        f"优先级：{item['precedence']}）"
        for item in rules
    ) or "- 无已发现规则路径；实施前仍须确认当前作用域规则。"
    plan_gate = (
        "计划评审已明确批准。"
        if plan_review["status"] == "approved"
        else "计划评审未明确批准：实施前停止修改，取得明确批准后再继续。"
    )
    allowed, forbidden = effective_permissions(payload["permissions"])
    values = {
        "goal_line": f"开发目标：{safe_text(payload['request']['goal'])}",
        "spec_path": safe_text(documents["spec"]["path"]),
        "spec_source": safe_text(documents["spec"]["source"]),
        "plan_path": safe_text(documents["plan"]["path"]),
        "plan_source": safe_text(documents["plan"]["source"]),
        "plan_review": safe_text(plan_review["status"]),
        "repository_gate": repository_gate,
        "branch_gate": branch_gate,
        "rules": rule_lines,
        "plan_gate": plan_gate,
        "allowed": "、".join(safe_text(item) for item in allowed),
        "forbidden": "、".join(safe_text(item) for item in forbidden),
    }
    template = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template.substitute(values).rstrip() + "\n"


def fail(error: InputError) -> int:
    sys.stderr.write(json.dumps({"code": error.code, "errors": error.errors}, ensure_ascii=False) + "\n")
    return 2


def main() -> int:
    try:
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, UnicodeError, RecursionError) as error:
            raise InputError("invalid_json", [str(error)]) from error
        if json_nesting_exceeds_limit(payload):
            raise InputError(
                "invalid_json",
                [f"JSON nesting exceeds the supported limit of {MAX_JSON_NESTING}"],
            )
        validate(payload)
        output = render(payload)
        sys.stdout.write(output)
        return 0
    except InputError as error:
        return fail(error)
    except (OSError, KeyError, TypeError, ValueError, RecursionError) as error:
        return fail(InputError("internal_error", [str(error)]))


if __name__ == "__main__":
    raise SystemExit(main())
