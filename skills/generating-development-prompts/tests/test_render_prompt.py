import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_prompt.py"
MODULE_SPEC = importlib.util.spec_from_file_location("render_prompt_under_test", SCRIPT)
assert MODULE_SPEC is not None and MODULE_SPEC.loader is not None
RENDER_PROMPT = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(RENDER_PROMPT)


COPY_STRESS_BODY = """开发目标：验证 Codex 客户端能够完整复制 renderer 生成的长提示词正文。

这是 Unicode 压力样本：中文、English、café、naïve、Δ、🚀、全角标点「交接」。

连续反引号压力片段如下，必须作为正文保留，不能提前闭合外层代码框：
``````

正文完整性段落：请逐字保留路径 docs/specs/2026-07-17-example-design.md、状态 current-session | new-session | blocked，以及 implementation_gate: open。复制结果不得增加外层 fence、语言标记、前导空格或末尾解释。

长文本段落一：工作流先验证 requirements 八字段，再映射为 spec/plan 十四字段，最后依据当前会话、仓库、权限、工具与 Agent 能力执行三态路由。任何阶段都不能凭聊天记忆补造批准状态，也不能把能力缺口伪装为已完成交接。

长文本段落二：当路由结果为 current-session 时，必须等待用户显式实施批准；当结果为 new-session 时，才提供一个可复制代码框；当结果为 blocked 时，必须报告确定性阻塞。无论哪种自动路由结果，十四字段快照都保持不变并位于回复末尾。

长文本段落三：此客户端验证只测试显示与复制，不创建新任务、不安装 skill、不修改真实 CODEX_HOME、不提交、不发布，也不向外部服务发送剪贴板内容。
"""


def valid_payload() -> dict:
    return {
        "schema_version": 1,
        "repository": {
            "status": "ok",
            "workdir": "/workspace/example",
            "root": "/workspace/example",
            "branch": "main",
            "head": "0123456789abcdef",
            "worktree_kind": "main",
            "status_short_branch": "## main\n M local.txt",
        },
        "rules": [
            {"path": "/workspace/example/AGENTS.md", "source": "filesystem", "precedence": 0}
        ],
        "documents": {
            "spec": {"path": "/workspace/example/docs/spec.md", "source": "explicit"},
            "plan": {
                "path": "/workspace/example/docs/plan.md",
                "source": "explicit",
                "review": {
                    "status": "approved",
                    "reviewer": "review-agent",
                    "reviewed_at": "2026-07-11",
                    "implementation_gate": "open",
                },
            },
        },
        "ambiguities": [],
        "errors": [],
        "warnings": [],
        "request": {"goal": "实现安全的登录流程", "target_branch": "feat/login"},
        "session_rules": [
            {"path": "/Users/example/AGENTS.md", "source": "session", "precedence": -1}
        ],
        "permissions": {
            "allowed": ["create-development-branch"],
            "forbidden": ["push"],
            "source": "defaults",
        },
    }


class RenderPromptTests(unittest.TestCase):
    def render_raw(self, payload) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
        )

    def assert_rejected(self, payload, expected_code=None):
        completed = self.render_raw(payload)
        self.assertNotEqual(0, completed.returncode)
        if expected_code:
            error = json.loads(completed.stderr)
            self.assertEqual(expected_code, error["code"])
        self.assertEqual("", completed.stdout)
        self.assertTrue(completed.stderr)
        return completed

    def prompt_body(self, output: str) -> str:
        opening = re.match(r"\A(`{3,})text\n", output)
        self.assertIsNotNone(opening, output)
        fence = opening.group(1)
        self.assertTrue(output.endswith(f"{fence}\n"))
        body = output[opening.end() : -len(fence) - 1]
        self.assertEqual(f"{fence}text\n{body}{fence}\n", output)
        return body

    def test_empty_object_is_rejected_without_partial_stdout(self):
        self.assert_rejected({}, "invalid_input")

    def test_invalid_json_is_rejected_with_machine_readable_stderr(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="not-json",
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(0, completed.returncode)
        self.assertEqual("", completed.stdout)
        error = json.loads(completed.stderr)
        self.assertEqual("invalid_json", error["code"])
        self.assertIsInstance(error["errors"], list)

    def test_deep_json_recursion_is_a_machine_readable_failure_without_traceback(self):
        raw = "[" * 3000 + "0" + "]" * 3000

        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=raw,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(0, completed.returncode)
        self.assertEqual("", completed.stdout)
        self.assertNotIn("Traceback", completed.stderr)
        error = json.loads(completed.stderr)
        self.assertEqual("invalid_json", error["code"])
        self.assertIsInstance(error["errors"], list)

    def test_wrong_required_field_types_are_rejected(self):
        cases = (
            ("schema_version", "1"),
            ("repository", []),
            ("rules", {}),
            ("documents", []),
            ("ambiguities", {}),
            ("errors", {}),
            ("warnings", {}),
            ("request", []),
            ("session_rules", {}),
            ("permissions", []),
        )
        for field, value in cases:
            with self.subTest(field=field):
                payload = valid_payload()
                payload[field] = value
                self.assert_rejected(payload, "invalid_input")

    def test_missing_or_empty_goal_is_rejected(self):
        for value in (None, "", "   ", 1):
            with self.subTest(value=value):
                payload = valid_payload()
                if value is None:
                    payload["request"].pop("goal")
                else:
                    payload["request"]["goal"] = value
                self.assert_rejected(payload, "invalid_input")

    def test_unresolved_ambiguities_or_discovery_errors_are_rejected(self):
        for field in ("ambiguities", "errors"):
            with self.subTest(field=field):
                payload = valid_payload()
                payload[field] = [{"field": "plan", "candidates": ["a", "b"]}]
                self.assert_rejected(payload, "blocked_input")

    def test_missing_spec_or_plan_is_rejected(self):
        for field in ("spec", "plan"):
            with self.subTest(field=field):
                payload = valid_payload()
                payload["documents"][field]["path"] = None
                payload["documents"][field]["source"] = "missing"
                self.assert_rejected(payload, "blocked_input")

    def test_explicit_permission_conflict_is_rejected(self):
        payload = valid_payload()
        payload["permissions"] = {
            "allowed": ["push"],
            "forbidden": ["push"],
            "source": "explicit",
        }
        self.assert_rejected(payload, "permission_conflict")

    def test_nullable_target_branch_generates_branch_derivation_gate(self):
        payload = valid_payload()
        payload["request"]["target_branch"] = None
        completed = self.render_raw(payload)
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual("", completed.stderr)
        body = self.prompt_body(completed.stdout)
        self.assertIn("派生", body)
        self.assertIn("main", body)
        self.assertIn("master", body)

    def test_success_omits_new_session_advice_and_effort(self):
        completed = self.render_raw(valid_payload())

        self.assertEqual(0, completed.returncode, completed.stderr)
        body = self.prompt_body(completed.stdout)
        self.assertNotIn("新会话建议", body)
        self.assertNotIn("effort", body.casefold())

    def test_repository_section_contains_only_implementation_gates(self):
        completed = self.render_raw(valid_payload())
        self.assertEqual(0, completed.returncode, completed.stderr)
        body = self.prompt_body(completed.stdout)
        section = body.split("仓库与分支状态\n", 1)[1].split(
            "\n\n规则与文档优先级", 1
        )[0]

        self.assertIn("仓库状态已识别为 Git 仓库。", section)
        self.assertIn("修改前确认目标开发分支符合仓库规则", section)
        self.assertIn("feat/login", section)
        for removed in (
            "工作目录：",
            "仓库根目录：",
            "目标分支：",
            "当前分支：",
            "HEAD：",
            "worktree：",
            "工作区状态：",
        ):
            with self.subTest(removed=removed):
                self.assertNotIn(removed, section)

    def test_approved_package_review_still_blocks_when_spec_approval_is_pending(self):
        payload = valid_payload()
        payload["documents"]["plan"]["review"]["implementation_gate"] = "blocked"

        completed = self.render_raw(payload)

        self.assertEqual(0, completed.returncode, completed.stderr)
        body = self.prompt_body(completed.stdout)
        self.assertIn("技术包评审已通过", body)
        self.assertIn("技术规格用户批准仍未完成", body)
        self.assertIn("实施前停止修改", body)

    def test_prompt_prefers_matching_agents_from_one_session_inventory(self):
        completed = self.render_raw(valid_payload())
        self.assertEqual(0, completed.returncode, completed.stderr)
        output = self.prompt_body(completed.stdout)

        self.assertIn("全局子代理选择", output)
        for expected in (
            "首次需要委派",
            "会话内清单",
            "name",
            "description",
            "后续委派不重复扫描",
            "按名称启动失败",
            "刷新一次",
            "停止该次委派并报告能力缺口",
            "记录每次委派实际使用的 agent name",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, output)

    def test_success_is_one_copyable_code_block_with_seven_ordered_sections(self):
        completed = self.render_raw(valid_payload())
        self.assertEqual(0, completed.returncode, completed.stderr)
        wrapped = completed.stdout
        output = self.prompt_body(wrapped)
        self.assertEqual("", completed.stderr)
        self.assertTrue(output.startswith("开发目标：实现安全的登录流程"))
        self.assertNotIn("以下是", output)
        self.assertNotIn("发现结果", output)
        self.assertNotIn("```", output)
        self.assertFalse(any(line.startswith("#") for line in output.splitlines()))
        fence = re.match(r"\A(`{3,})text\n", wrapped).group(1)
        self.assertEqual(2, wrapped.count(fence))
        markers = (
            "开发目标与来源文档",
            "仓库与分支状态",
            "规则与文档优先级",
            "权限边界",
            "全局子代理选择",
            "主代理执行合同",
            "完成条件与报告",
        )
        self.assertEqual([], [marker for marker in markers if marker not in output])
        positions = [output.index(marker) for marker in markers]
        self.assertEqual(sorted(positions), positions)

    def test_success_contains_context_permissions_and_execution_contract(self):
        output = self.prompt_body(self.render_raw(valid_payload()).stdout)
        for expected in (
            "/workspace/example/docs/spec.md",
            "/workspace/example/docs/plan.md",
            "/Users/example/AGENTS.md",
            "/workspace/example/AGENTS.md",
            "create-development-branch",
            "push",
            "按照计划和适用的仓库规则实施",
            "与影响范围匹配的验证",
            "验证证据",
            "整体复审通过且验证证据完整后才报告完成",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, output)

    def test_success_requires_generic_independent_review_and_final_rereview(self):
        output = self.prompt_body(self.render_raw(valid_payload()).stdout)

        for expected in (
            "未参与实现的独立评审者",
            "最新完整 diff",
            "不得仅因任务数量",
            "中间里程碑评审",
            "执行首次整体评审",
            "已批准需求是产品范围上限",
            "`BLOCKING_IN_SCOPE`",
            "`SCOPE_CHANGE_REQUIRED`",
            "`NON_BLOCKING_NOTE`",
            "最小范围内修正",
            "复审只检查原阻断项、变更区域和修复引入的回归",
            "整体复审通过且验证证据完整后才报告完成",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, output)
        self.assertNotIn("独立评审未通过不得进入下一项", output)

    def test_success_requires_tdd_and_repeatable_review_loops(self):
        output = self.prompt_body(self.render_raw(valid_payload()).stdout)

        for expected in (
            "先写并运行失败测试",
            "确认失败原因符合预期",
            "再写最小实现",
            "每项任务完成与影响范围匹配的验证",
            "全部计划任务完成并集成后",
            "执行首次整体评审",
            "获得 APPROVED 后停止",
            "连续两轮修复与复审仍未通过",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, output)

    def test_success_omits_removed_framework_derived_workflow(self):
        output = self.prompt_body(self.render_raw(valid_payload()).stdout)

        for removed in (
            "系统化" + "调试",
        ):
            with self.subTest(removed=removed):
                self.assertNotIn(removed, output)

    def test_user_text_and_paths_are_rendered_as_inert_text(self):
        payload = valid_payload()
        payload["request"]["goal"] = "实现 $(touch /tmp/never-run) 与 ${HOME}"
        payload["documents"]["spec"]["path"] = "/tmp/spec; echo unsafe.md"
        completed = self.render_raw(payload)
        self.assertEqual(0, completed.returncode, completed.stderr)
        body = self.prompt_body(completed.stdout)
        self.assertIn("$(touch /tmp/never-run)", body)
        self.assertIn("${HOME}", body)
        self.assertIn("/tmp/spec; echo unsafe.md", body)

    def test_external_strings_are_reversibly_rendered_on_one_line(self):
        payload = valid_payload()
        injected = "\n# injected\n```shell\necho unsafe\n```"
        payload["request"]["goal"] = (
            "普通中文" + injected + "\rquote=\" slash=\\ control=\x01\u2028\u2029"
        )
        payload["documents"]["spec"]["path"] = "/tmp/spec" + injected
        payload["documents"]["plan"]["path"] = "/tmp/plan" + injected
        payload["rules"][0]["path"] = "/tmp/rule" + injected
        payload["permissions"] = {
            "allowed": ["custom" + injected],
            "forbidden": [],
            "source": "explicit",
        }

        completed = self.render_raw(payload)

        self.assertEqual(0, completed.returncode, completed.stderr)
        output = self.prompt_body(completed.stdout)
        self.assertTrue(output.startswith("开发目标：普通中文"))
        self.assertNotIn("\n# injected", output)
        self.assertNotIn("```", output)
        self.assertIn(r"\n# injected", output)
        self.assertIn(r"\u0060\u0060\u0060shell", output)
        self.assertIn(r"\rquote=\" slash=\\ control=\u0001\u2028\u2029", output)
        self.assertFalse(any(line.startswith("#") for line in output.splitlines()))

    def test_default_permission_matrix_is_complete(self):
        output = self.prompt_body(self.render_raw(valid_payload()).stdout)
        for operation in (
            "create-development-branch-or-worktree",
            "create-local-commit",
            "query-official-documentation",
            "install-plan-listed-dependencies",
            "download-plan-required-playwright-browsers",
            "start-local-development-service",
            "run-tests-build-lint-local-validation",
            "push",
            "merge",
            "rebase",
            "tag",
            "release",
            "production-deployment",
            "cloudflare-or-dns-change",
            "unauthorized-secrets-tokens-credentials-or-production-data",
        ):
            with self.subTest(operation=operation):
                self.assertIn(operation, output)

    def test_explicit_permission_can_add_allowed_operation(self):
        payload = valid_payload()
        payload["permissions"] = {
            "allowed": ["run-local-benchmark"],
            "forbidden": [],
            "source": "explicit",
        }
        output = self.prompt_body(self.render_raw(payload).stdout)
        allowed_line = next(line for line in output.splitlines() if line.startswith("允许："))
        self.assertIn("run-local-benchmark", allowed_line)
        self.assertIn("create-local-commit", allowed_line)

    def test_explicit_forbidden_operation_tightens_default_allowance(self):
        payload = valid_payload()
        payload["permissions"] = {
            "allowed": [],
            "forbidden": ["create-local-commit"],
            "source": "explicit",
        }
        output = self.prompt_body(self.render_raw(payload).stdout)
        allowed_line = next(line for line in output.splitlines() if line.startswith("允许："))
        forbidden_line = next(line for line in output.splitlines() if line.startswith("禁止："))
        self.assertNotIn("create-local-commit", allowed_line)
        self.assertIn("create-local-commit", forbidden_line)

    def test_explicit_allow_can_override_default_policy_but_not_platform_approval(self):
        payload = valid_payload()
        payload["permissions"] = {
            "allowed": ["push", "destructive-cleanup"],
            "forbidden": [],
            "source": "explicit",
        }
        output = self.prompt_body(self.render_raw(payload).stdout)
        allowed_line = next(line for line in output.splitlines() if line.startswith("允许："))
        forbidden_line = next(line for line in output.splitlines() if line.startswith("禁止："))
        self.assertIn("push", allowed_line)
        self.assertNotIn("push", forbidden_line)
        self.assertIn("平台安全与审批规则始终优先", output)
        self.assertIn("破坏性操作必须遵循当前会话审批机制", output)

    def test_invalid_permission_source_is_rejected(self):
        payload = valid_payload()
        payload["permissions"]["source"] = "inferred"
        self.assert_rejected(payload, "invalid_input")

    def test_invalid_nested_enums_and_relative_paths_are_rejected(self):
        mutations = (
            lambda item: item["repository"].update(status="maybe"),
            lambda item: item["repository"].update(worktree_kind="secondary"),
            lambda item: item["repository"].update(workdir="relative/path"),
            lambda item: item["documents"]["spec"].update(source="guessed"),
            lambda item: item["documents"]["spec"].update(path="docs/spec.md"),
            lambda item: item["documents"]["plan"]["review"].update(status="accepted"),
            lambda item: item["rules"][0].update(source="session"),
            lambda item: item["session_rules"][0].update(source="filesystem"),
            lambda item: item["session_rules"][0].update(path="AGENTS.md"),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                payload = valid_payload()
                mutate(payload)
                self.assert_rejected(payload, "invalid_input")

    def test_dynamic_fence_is_longer_than_every_body_backtick_run(self):
        body = "中文 start ``` middle `````` end\n"

        output = RENDER_PROMPT.wrap_prompt(body)

        self.assertTrue(output.startswith("```````text\n"))
        self.assertTrue(output.endswith("```````\n"))
        self.assertEqual(body, self.prompt_body(output))

    def test_copy_stress_body_is_extracted_byte_for_byte_with_dynamic_fence(self):
        output = RENDER_PROMPT.wrap_prompt(COPY_STRESS_BODY)

        self.assertTrue(output.startswith("```````text\n"))
        self.assertTrue(output.endswith("```````\n"))
        self.assertEqual(COPY_STRESS_BODY, self.prompt_body(output))
        self.assertIn("中文、English、café、naïve、Δ、🚀、全角标点「交接」", self.prompt_body(output))
        self.assertIn("\n``````\n", self.prompt_body(output))

    def test_cli_copy_stress_body_matches_rendered_body_with_reversible_inert_text(self):
        payload = valid_payload()
        payload["request"]["goal"] = (
            "保留 中文、English、café、naïve、Δ、🚀、全角标点「交接」、"
            "docs/specs/2026-07-17-example-design.md 与六个反引号 ``````"
        )

        completed = self.render_raw(payload)

        self.assertEqual(0, completed.returncode, completed.stderr)
        expected_body = RENDER_PROMPT.render(payload)
        actual_body = self.prompt_body(completed.stdout)
        self.assertEqual(expected_body, actual_body)
        self.assertIn(r"\u0060\u0060\u0060\u0060\u0060\u0060", actual_body)
        self.assertNotIn("``````", actual_body)
        self.assertIn("docs/specs/2026-07-17-example-design.md", actual_body)

    def test_success_output_is_deterministic_and_preserves_unicode_body(self):
        payload = valid_payload()
        payload["request"]["goal"] = "实现中文与 emoji ✅"

        first = self.render_raw(payload)
        second = self.render_raw(payload)

        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertIn("中文与 emoji ✅", self.prompt_body(first.stdout))

    def test_unknown_repository_state_generates_only_the_repository_gate(self):
        payload = valid_payload()
        payload["repository"].update(
            status="not-a-repository", root=None, branch=None, head=None, worktree_kind="unknown"
        )
        completed = self.render_raw(payload)
        self.assertEqual(0, completed.returncode, completed.stderr)
        body = self.prompt_body(completed.stdout)
        self.assertIn("实施前停止", body)
        self.assertIn("Git 仓库", body)
        self.assertNotIn("工作区状态：", body)
        self.assertNotIn("HEAD：", body)

    def test_rendered_prompt_uses_one_session_agent_inventory_with_refresh_triggers(self):
        completed = self.render_raw(valid_payload())

        self.assertEqual(0, completed.returncode, completed.stderr)
        body = self.prompt_body(completed.stdout)
        self.assertIn("首次需要委派", body)
        self.assertIn("会话内清单", body)
        self.assertIn("后续委派不重复扫描", body)
        self.assertIn("配置变化", body)
        self.assertIn("按名称启动失败", body)
        self.assertIn("显式要求刷新", body)
        self.assertIn("刷新一次", body)
        self.assertNotIn("每次委派前检查", body)


if __name__ == "__main__":
    unittest.main()
