#!/usr/bin/env python3
"""Validate discovered context and render one development prompt to stdout."""

import json
import sys
from pathlib import Path
from string import Template
from typing import Any, Dict, List


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "assets" / "development-prompt.md"
FINAL_REVIEWER_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1] / "assets" / "final-reviewer.toml"
)
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
    "model": dict,
    "permissions": dict,
}
MODEL_SOURCES = {
    "explicit",
    "session",
    "local-config",
    "official-docs",
    "default",
    "unconfirmed",
}
MODEL_CERTAINTIES = {"confirmed", "unknown"}
EFFORT_ORDER = ("minimal", "low", "medium", "high", "xhigh")
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


def validate_evidence(record: Any, path: str, value_kind: str) -> None:
    if not isinstance(record, dict):
        raise InputError("invalid_input", [f"{path} must be object"])
    if set(record) != {"value", "source", "certainty"}:
        raise InputError("invalid_input", [f"{path} must contain value, source, and certainty"])
    source = record["source"]
    certainty = record["certainty"]
    if not isinstance(source, str) or source not in MODEL_SOURCES:
        raise InputError("invalid_input", [f"{path}.source is not recognized"])
    if not isinstance(certainty, str) or certainty not in MODEL_CERTAINTIES:
        raise InputError("invalid_input", [f"{path}.certainty is not recognized"])
    value = record["value"]
    if value_kind == "nullable_identity":
        valid = value is None or (isinstance(value, str) and bool(value.strip()))
    elif value_kind == "nullable_effort":
        valid = value is None or value in EFFORT_ORDER
    elif value_kind == "effort":
        valid = value in EFFORT_ORDER
    elif value_kind == "nullable_effort_list":
        valid = value is None or (
            isinstance(value, list)
            and all(item in EFFORT_ORDER for item in value)
        )
    elif value_kind == "nullable_bool":
        valid = value is None or isinstance(value, bool)
    else:
        valid = False
    if not valid:
        raise InputError("invalid_input", [f"{path}.value has invalid type"])
    if certainty == "confirmed" and value is None:
        raise InputError("invalid_input", [f"{path}.value cannot be null when confirmed"])
    if value_kind == "nullable_effort_list" and certainty == "confirmed" and not value:
        raise InputError("invalid_input", [f"{path}.value cannot be empty when confirmed"])
    if source == "unconfirmed" and not (certainty == "unknown" and value is None):
        raise InputError(
            "invalid_input",
            [f"{path} with unconfirmed source must have unknown certainty and null value"],
        )


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

    model = payload["model"]
    evidence_kinds = {
        "identity": "nullable_identity",
        "current_effort": "nullable_effort",
        "supported_efforts": "nullable_effort_list",
        "subagent_overrides_supported": "nullable_bool",
    }
    for field, kind in evidence_kinds.items():
        validate_evidence(model.get(field), f"input.model.{field}", kind)
    roles = require_type(model, "role_efforts", dict, "input.model")
    for role in ("main", "implementation", "review", "final"):
        validate_evidence(
            roles.get(role), f"input.model.role_efforts.{role}", "effort"
        )

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


def display(value: Any) -> str:
    if value is None:
        return "null（不确定）"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ", ".join(safe_text(item) for item in value)
    return safe_text(value)


def safe_text(value: Any) -> str:
    """Return a reversible, single-line JSON-string representation without quotes."""
    encoded = json.dumps(str(value), ensure_ascii=False)[1:-1]
    return (
        encoded.replace("\u2028", r"\u2028")
        .replace("\u2029", r"\u2029")
        .replace("`", r"\u0060")
    )


def evidence_text(name: str, item: Dict[str, Any]) -> str:
    return (
        f"{name}：{display(item.get('value'))}"
        f"（来源：{safe_text(item.get('source'))}；"
        f"确定性：{safe_text(item.get('certainty'))}）"
    )


def role_value(model: Dict[str, Any], role: str) -> str:
    return display(model["role_efforts"][role].get("value"))


def inherited_final_review_sequence(effective: str) -> str:
    role_template = FINAL_REVIEWER_TEMPLATE_PATH.read_text(encoding="utf-8").rstrip()
    return (
        "最终全量评审执行顺序：主线程暂停；在启动前建立或确认目标项目的 "
        ".codex/agents/final-reviewer.toml，内容必须与下列可移植模板一致；"
        "确认项目级 .codex/agents/final-reviewer.toml 已自动发现、"
        'sandbox_mode = "read-only" 且未固定 model 或 model_reasoning_effort；'
        f"等待用户把当前线程切换到最终目标 effort（{effective}），即等待用户切换当前会话；"
        "只有切换完成后才启动 final-reviewer；"
        f"final-reviewer 继承当前线程的 {effective} effort。"
        "\nfinal-reviewer.toml 模板开始\n"
        + role_template
        + "\nfinal-reviewer.toml 模板结束"
    )


def final_effort_and_gate(model: Dict[str, Any]) -> tuple:
    requested = model["role_efforts"]["final"]["value"]
    supported = model["supported_efforts"]
    effective = requested
    gates = []
    if (
        requested == "xhigh"
        and supported["certainty"] == "confirmed"
        and isinstance(supported["value"], list)
    ):
        values = supported["value"]
        if "xhigh" not in values:
            ranked = [effort for effort in EFFORT_ORDER if effort in values]
            if ranked:
                effective = ranked[-1]
                gates.append(
                    f"xhigh 已确认不受支持，最终全量评审使用最高已确认 effort：{effective}。"
                )
            else:
                gates.append("已确认的 effort 列表没有可排序值；最终全量评审前暂停并请求用户确认配置。")
    elif requested == "xhigh":
        gates.append(
            "xhigh 支持状态不确定：保留 xhigh 目标，最终全量评审前确认支持范围，未确认前不得开始最终评审。"
        )

    overrides = model["subagent_overrides_supported"]
    if overrides["certainty"] == "confirmed" and overrides["value"] is False:
        gates.append(
            "平台已确认无法对子代理单独配置 effort，最终全量评审前暂停。"
            + inherited_final_review_sequence(effective)
        )
    elif overrides["certainty"] == "unknown" or overrides["value"] is None:
        gates.append(
            "子代理 effort 覆盖能力不确定，不得声称可以对子代理单独配置；"
            "按无覆盖能力处理并在最终全量评审前暂停。"
            + inherited_final_review_sequence(effective)
        )
    return effective, "\n".join(gates) or "最终全量评审前确认最终 effort 配置满足目标。"


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
    model = payload["model"]
    target = payload["request"]["target_branch"]
    branch_gate = (
        "目标分支未指定：修改前根据计划与仓库规则派生开发分支名；不得直接使用 main 或 master，仓库状态不允许建分支时停止。"
        if target is None
        else "修改前确认目标开发分支符合仓库规则，且不得直接在 main 或 master 上开发。"
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
    model_lines = "\n".join(
        evidence_text(label, model[field])
        for field, label in (
            ("identity", "模型 identity"),
            ("current_effort", "当前会话 effort"),
            ("supported_efforts", "已确认支持的 effort"),
            ("subagent_overrides_supported", "子代理单独覆盖能力"),
        )
    )
    plan_gate = (
        "计划评审已明确批准。"
        if plan_review["status"] == "approved"
        else "计划评审未明确批准：实施前停止修改，取得明确批准后再继续。"
    )
    final_effort, model_gate = final_effort_and_gate(model)
    allowed, forbidden = effective_permissions(payload["permissions"])
    worktree_status = (
        safe_text(repository["status_short_branch"])
        if repository["status"] == "ok" and repository["status_short_branch"]
        else display(None)
    )
    values = {
        "goal_line": f"开发目标：{safe_text(payload['request']['goal'])}",
        "spec_path": safe_text(documents["spec"]["path"]),
        "spec_source": safe_text(documents["spec"]["source"]),
        "plan_path": safe_text(documents["plan"]["path"]),
        "plan_source": safe_text(documents["plan"]["source"]),
        "plan_review": safe_text(plan_review["status"]),
        "workdir": safe_text(repository["workdir"]),
        "repository_root": display(repository["root"]),
        "target_branch": display(target),
        "current_branch": display(repository["branch"]),
        "head": display(repository["head"]),
        "worktree_kind": safe_text(repository["worktree_kind"]),
        "worktree_status": worktree_status,
        "repository_gate": repository_gate,
        "branch_gate": branch_gate,
        "rules": rule_lines,
        "plan_gate": plan_gate,
        "model_evidence": model_lines,
        "main_effort": role_value(model, "main"),
        "implementation_effort": role_value(model, "implementation"),
        "review_effort": role_value(model, "review"),
        "final_effort": final_effort,
        "model_gate": model_gate,
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
