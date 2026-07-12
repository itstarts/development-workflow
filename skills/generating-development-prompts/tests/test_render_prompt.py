import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_prompt.py"


def evidence(value, source="session", certainty="confirmed"):
    return {"value": value, "source": source, "certainty": certainty}


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
        "model": {
            "identity": evidence("gpt-example"),
            "current_effort": evidence("high"),
            "supported_efforts": evidence(["low", "medium", "high", "xhigh"], "official-docs"),
            "subagent_overrides_supported": evidence(True),
            "role_efforts": {
                "main": evidence("high", "explicit"),
                "implementation": evidence("medium", "default"),
                "review": evidence("high", "default"),
                "final": evidence("xhigh", "default"),
            },
        },
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
            ("model", []),
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
            "模型与 reasoning effort",
            "权限边界",
            "主代理执行合同",
            "完成条件与报告",
        )
        positions = [output.index(marker) for marker in markers]
        self.assertEqual(sorted(positions), positions)

    def test_success_contains_context_roles_permissions_and_execution_contract(self):
        output = self.render_raw(valid_payload()).stdout
        for expected in (
            "/workspace/example/docs/spec.md",
            "/workspace/example/docs/plan.md",
            "/Users/example/AGENTS.md",
            "/workspace/example/AGENTS.md",
            "feat/login",
            "0123456789abcdef",
            "## main",
            "主代理：high",
            "实现子代理：medium",
            "任务评审与集成评审：high",
            "最终全量评审：xhigh",
            "create-development-branch",
            "push",
            "测试驱动开发",
            "系统化调试",
            "独立评审",
            "修复所有发现",
            "复审",
            "最终全量评审",
            "验证证据",
            "只有最终全量评审通过且验证证据完整后，才报告完成",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, output)

    def test_unavailable_subagent_override_embeds_portable_final_reviewer_template(self):
        payload = valid_payload()
        payload["model"]["subagent_overrides_supported"] = evidence(False)

        output = self.render_raw(payload).stdout

        self.assertIn("建立或确认目标项目的 .codex/agents/final-reviewer.toml", output)
        self.assertIn('name = "final-reviewer"', output)
        self.assertIn('sandbox_mode = "read-only"', output)
        self.assertIn("developer_instructions", output)
        self.assertNotIn("TASK6_APPROVED_HEAD", output)
        self.assertNotIn("07-real-tools-trial.json", output)

    def test_unknown_subagent_override_embeds_portable_final_reviewer_template(self):
        payload = valid_payload()
        payload["model"]["subagent_overrides_supported"] = evidence(
            None, "unconfirmed", "unknown"
        )

        output = self.render_raw(payload).stdout

        self.assertIn("建立或确认目标项目的 .codex/agents/final-reviewer.toml", output)
        self.assertIn('name = "final-reviewer"', output)
        self.assertIn('sandbox_mode = "read-only"', output)

    def test_confirmed_subagent_override_does_not_emit_project_role_template(self):
        output = self.render_raw(valid_payload()).stdout

        self.assertNotIn("建立或确认目标项目的 .codex/agents/final-reviewer.toml", output)
        self.assertNotIn('name = "final-reviewer"', output)

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

    def test_model_evidence_records_require_valid_types_and_enums(self):
        cases = (
            ("identity", {"value": "gpt", "source": "memory", "certainty": "confirmed"}),
            ("identity", {"value": "gpt", "source": "session", "certainty": "likely"}),
            ("identity", {"value": "gpt", "source": [], "certainty": "confirmed"}),
            ("identity", {"value": "gpt", "source": "session", "certainty": []}),
            ("identity", {"value": 5, "source": "session", "certainty": "confirmed"}),
            ("current_effort", {"value": [], "source": "session", "certainty": "confirmed"}),
            ("supported_efforts", {"value": "high", "source": "official-docs", "certainty": "confirmed"}),
            ("supported_efforts", {"value": ["high", 1], "source": "official-docs", "certainty": "confirmed"}),
            ("subagent_overrides_supported", {"value": "false", "source": "session", "certainty": "confirmed"}),
        )
        for field, record in cases:
            with self.subTest(field=field, record=record):
                payload = valid_payload()
                payload["model"][field] = record
                self.assert_rejected(payload, "invalid_input")

    def test_role_effort_records_require_nonempty_string_values(self):
        for value in (None, "", 1):
            with self.subTest(value=value):
                payload = valid_payload()
                payload["model"]["role_efforts"]["implementation"] = evidence(value)
                self.assert_rejected(payload, "invalid_input")

    def test_effort_values_and_evidence_consistency_are_strict(self):
        mutations = (
            lambda item: item["model"].update(current_effort=evidence("turbo")),
            lambda item: item["model"]["role_efforts"].update(main=evidence("turbo")),
            lambda item: item["model"].update(identity=evidence(None)),
            lambda item: item["model"].update(current_effort=evidence(None)),
            lambda item: item["model"].update(supported_efforts=evidence(None)),
            lambda item: item["model"].update(subagent_overrides_supported=evidence(None)),
            lambda item: item["model"].update(
                supported_efforts=evidence([], "official-docs", "confirmed")
            ),
            lambda item: item["model"].update(
                supported_efforts=evidence(["high", "turbo"], "official-docs", "confirmed")
            ),
            lambda item: item["model"].update(
                identity=evidence(None, "unconfirmed", "confirmed")
            ),
            lambda item: item["model"].update(
                identity=evidence("invented-model", "unconfirmed", "unknown")
            ),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                payload = valid_payload()
                mutate(payload)
                self.assert_rejected(payload, "invalid_input")

    def test_unknown_supported_efforts_can_retain_a_valid_nonempty_list(self):
        payload = valid_payload()
        payload["model"]["supported_efforts"] = evidence(
            ["low", "medium", "high"], "local-config", "unknown"
        )

        completed = self.render_raw(payload)

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("最终全量评审：xhigh", completed.stdout)
        self.assertIn("支持状态不确定", completed.stdout)

    def test_mixed_model_sources_and_current_effort_remain_field_specific(self):
        payload = valid_payload()
        payload["model"].update(
            {
                "identity": evidence("gpt-example", "local-config"),
                "current_effort": evidence("low", "session"),
                "supported_efforts": evidence(["low", "high", "xhigh"], "official-docs"),
                "subagent_overrides_supported": evidence(True, "session"),
            }
        )
        payload["model"]["role_efforts"]["main"] = evidence("high", "explicit")
        output = self.render_raw(payload).stdout
        self.assertIn("模型 identity：gpt-example（来源：local-config；确定性：confirmed）", output)
        self.assertIn("当前会话 effort：low（来源：session；确定性：confirmed）", output)
        self.assertIn("主代理：high", output)
        self.assertNotIn("当前会话 effort：high", output)

    def test_unknown_model_capabilities_are_marked_uncertain_and_keep_xhigh_target(self):
        payload = valid_payload()
        payload["model"]["identity"] = evidence(None, "unconfirmed", "unknown")
        payload["model"]["current_effort"] = evidence(None, "unconfirmed", "unknown")
        payload["model"]["supported_efforts"] = evidence(None, "unconfirmed", "unknown")
        payload["model"]["subagent_overrides_supported"] = evidence(None, "unconfirmed", "unknown")
        output = self.render_raw(payload).stdout
        self.assertIn("不确定", output)
        self.assertIn("最终全量评审：xhigh", output)
        self.assertIn("确认", output)
        self.assertIn("不得声称可以对子代理单独配置", output)

    def test_unknown_supported_efforts_list_does_not_authorize_downgrade(self):
        payload = valid_payload()
        payload["model"]["supported_efforts"] = evidence(["low", "medium", "high"], "local-config", "unknown")
        output = self.render_raw(payload).stdout
        self.assertIn("最终全量评审：xhigh", output)
        self.assertIn("支持状态不确定", output)

    def test_confirmed_supported_efforts_without_xhigh_use_highest_confirmed(self):
        payload = valid_payload()
        payload["model"]["supported_efforts"] = evidence(["low", "high", "medium"], "official-docs", "confirmed")
        output = self.render_raw(payload).stdout
        self.assertIn("最终全量评审：high", output)
        self.assertIn("xhigh", output)
        self.assertIn("最高已确认 effort", output)

    def test_confirmed_supported_efforts_with_xhigh_keep_requested_target(self):
        payload = valid_payload()
        output = self.render_raw(payload).stdout
        self.assertIn("最终全量评审：xhigh", output)
        self.assertNotIn("降为", output)

    def test_confirmed_capabilities_do_not_replace_non_xhigh_explicit_final_effort(self):
        payload = valid_payload()
        payload["model"]["supported_efforts"] = evidence(
            ["low", "medium", "high"], "official-docs", "confirmed"
        )
        payload["model"]["role_efforts"]["final"] = evidence("medium", "explicit")
        output = self.render_raw(payload).stdout
        self.assertIn("最终全量评审：medium", output)
        self.assertNotIn("最终全量评审：high", output)

    def test_confirmed_false_subagent_override_requires_session_switch_pause(self):
        payload = valid_payload()
        payload["model"]["subagent_overrides_supported"] = evidence(False, "session", "confirmed")
        output = self.render_raw(payload).stdout
        self.assertIn("无法对子代理单独配置", output)
        self.assertIn("最终全量评审前暂停", output)
        self.assertIn("等待用户切换当前会话", output)

    def test_confirmed_true_subagent_override_does_not_require_project_role_or_thread_switch(self):
        output = self.render_raw(valid_payload()).stdout

        for inherited_gate in (
            "final-reviewer",
            ".codex/agents/final-reviewer.toml",
            "等待用户把当前线程切换",
            "等待用户切换当前会话",
            "只有切换完成后才启动",
            "继承当前线程的 xhigh effort",
        ):
            with self.subTest(inherited_gate=inherited_gate):
                self.assertNotIn(inherited_gate, output)

    def test_unavailable_or_unknown_subagent_override_uses_project_role_after_thread_switch(self):
        for override in (
            evidence(False, "session", "confirmed"),
            evidence(None, "unconfirmed", "unknown"),
        ):
            with self.subTest(override=override):
                payload = valid_payload()
                payload["model"]["subagent_overrides_supported"] = override

                completed = self.render_raw(payload)

                self.assertEqual(0, completed.returncode, completed.stderr)
                output = completed.stdout
                ordered_markers = (
                    "主线程暂停",
                    (
                        "确认项目级 .codex/agents/final-reviewer.toml 已自动发现、"
                        'sandbox_mode = "read-only" 且未固定 model 或 model_reasoning_effort'
                    ),
                    "等待用户把当前线程切换到最终目标 effort（xhigh）",
                    "只有切换完成后才启动 final-reviewer",
                    "final-reviewer 继承当前线程的 xhigh effort",
                )
                positions = [output.index(marker) for marker in ordered_markers]
                self.assertEqual(sorted(positions), positions)

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

    def test_null_unknown_repository_and_model_values_are_rendered_without_invention(self):
        payload = valid_payload()
        payload["repository"].update(
            status="not-a-repository", root=None, branch=None, head=None, worktree_kind="unknown"
        )
        payload["model"]["identity"] = evidence(None, "unconfirmed", "unknown")
        completed = self.render_raw(payload)
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertGreaterEqual(completed.stdout.count("null（不确定）"), 4)
        self.assertNotIn("gpt-example", completed.stdout)
        self.assertIn("实施前停止", completed.stdout)
        self.assertIn("Git 仓库", completed.stdout)

    def test_unavailable_worktree_status_is_not_invented_as_clean(self):
        for repository_status in ("not-a-repository", "ok"):
            with self.subTest(repository_status=repository_status):
                payload = valid_payload()
                payload["repository"]["status"] = repository_status
                payload["repository"]["status_short_branch"] = ""
                if repository_status == "not-a-repository":
                    payload["repository"].update(
                        root=None, branch=None, head=None, worktree_kind="unknown"
                    )

                completed = self.render_raw(payload)

                self.assertEqual(0, completed.returncode, completed.stderr)
                self.assertIn("工作区状态：null（不确定）", completed.stdout)
                self.assertNotIn("工作区状态：（clean）", completed.stdout)


if __name__ == "__main__":
    unittest.main()
