import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_prompt.py"


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
        self.assertIn("派生", completed.stdout)
        self.assertIn("main", completed.stdout)
        self.assertIn("master", completed.stdout)

    def test_success_omits_new_session_advice_and_effort(self):
        completed = self.render_raw(valid_payload())

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertNotIn("新会话建议", completed.stdout)
        self.assertNotIn("effort", completed.stdout.casefold())

    def test_repository_section_contains_only_implementation_gates(self):
        completed = self.render_raw(valid_payload())
        self.assertEqual(0, completed.returncode, completed.stderr)
        section = completed.stdout.split("仓库与分支状态\n", 1)[1].split(
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

    def test_prompt_prefers_matching_global_custom_agents(self):
        completed = self.render_raw(valid_payload())
        self.assertEqual(0, completed.returncode, completed.stderr)
        output = completed.stdout

        self.assertIn("全局子代理选择", output)
        for expected in (
            "CODEX_HOME/agents",
            "~/.codex/agents",
            "name",
            "description",
            "存在职责匹配时，使用该全局 agent",
            "仅在没有匹配的全局 agent 时使用内置或通用子代理",
            "无法按 name 启动时，停止该次委派并报告能力缺口",
            "记录每次委派实际使用的 agent name",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, output)

    def test_success_is_prompt_only_with_seven_ordered_sections(self):
        completed = self.render_raw(valid_payload())
        self.assertEqual(0, completed.returncode, completed.stderr)
        output = completed.stdout
        self.assertEqual("", completed.stderr)
        self.assertTrue(output.startswith("开发目标：实现安全的登录流程"))
        self.assertNotIn("以下是", output)
        self.assertNotIn("发现结果", output)
        self.assertNotIn("```", output)
        self.assertFalse(any(line.startswith("#") for line in output.splitlines()))
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
        output = self.render_raw(valid_payload()).stdout
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
        output = self.render_raw(valid_payload()).stdout

        for expected in (
            "未参与实现的独立评审者",
            "由同一评审者复审当前版本",
            "独立评审未通过不得进入下一项",
            "执行整体评审",
            "重复修复、验证和整体复审",
            "整体复审通过且验证证据完整后才报告完成",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, output)

    def test_success_requires_tdd_and_repeatable_review_loops(self):
        output = self.render_raw(valid_payload()).stdout

        for expected in (
            "先写并运行失败测试",
            "确认失败原因符合预期",
            "再写最小实现",
            "重复修复、验证和复审，直到 APPROVED",
            "全部计划任务完成并集成后",
            "执行整体评审",
            "重复修复、验证和整体复审，直到 APPROVED",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, output)

    def test_success_omits_removed_framework_derived_workflow(self):
        output = self.render_raw(valid_payload()).stdout

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
        self.assertIn("$(touch /tmp/never-run)", completed.stdout)
        self.assertIn("${HOME}", completed.stdout)
        self.assertIn("/tmp/spec; echo unsafe.md", completed.stdout)

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
        output = completed.stdout
        self.assertTrue(output.startswith("开发目标：普通中文"))
        self.assertNotIn("\n# injected", output)
        self.assertNotIn("```", output)
        self.assertIn(r"\n# injected", output)
        self.assertIn(r"\u0060\u0060\u0060shell", output)
        self.assertIn(r"\rquote=\" slash=\\ control=\u0001\u2028\u2029", output)
        self.assertFalse(any(line.startswith("#") for line in output.splitlines()))

    def test_default_permission_matrix_is_complete(self):
        output = self.render_raw(valid_payload()).stdout
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
        output = self.render_raw(payload).stdout
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
        output = self.render_raw(payload).stdout
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
        output = self.render_raw(payload).stdout
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

    def test_unknown_repository_state_generates_only_the_repository_gate(self):
        payload = valid_payload()
        payload["repository"].update(
            status="not-a-repository", root=None, branch=None, head=None, worktree_kind="unknown"
        )
        completed = self.render_raw(payload)
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("实施前停止", completed.stdout)
        self.assertIn("Git 仓库", completed.stdout)
        self.assertNotIn("工作区状态：", completed.stdout)
        self.assertNotIn("HEAD：", completed.stdout)


if __name__ == "__main__":
    unittest.main()
