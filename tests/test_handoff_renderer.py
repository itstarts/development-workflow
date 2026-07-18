import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "creating-product-requirements",
    "creating-development-specs-and-plans",
    "generating-development-prompts",
)
SCRIPTS = tuple(ROOT / "skills" / name / "scripts" / "render_handoff.py" for name in SKILLS)


def requirements_canonical(**overrides):
    canonical = {
        "requirements_path": "/workspace/docs/requirements/order-approval.md",
        "requirements_topic": "order-approval",
        "requirements_scope": "feature",
        "understanding_confidence": 97,
        "understanding_user_confirmation": "approved",
        "requirements_user_approval": "approved",
        "requirements_independent_review": "approved",
        "specification_gate": "open",
    }
    canonical.update(overrides)
    return canonical


def workflow_canonical(**overrides):
    canonical = {
        "requirements_path": "/workspace/docs/requirements/order-approval.md",
        "requirements_topic": "order-approval",
        "requirements_scope": "feature",
        "requirements_understanding_confidence": 97,
        "requirements_understanding_confirmation": "approved",
        "requirements_user_approval": "approved",
        "requirements_independent_review": "approved",
        "specification_gate": "open",
        "spec_path": "/workspace/docs/specs/order-approval-design.md",
        "spec_user_approval": "approved",
        "spec_independent_review": "approved",
        "plan_path": "/workspace/docs/plans/order-approval.md",
        "plan_review_status": "approved",
        "implementation_gate": "open",
    }
    canonical.update(overrides)
    return canonical


def payload(schema="requirements", view="full", canonical=None, stage=None, next_step=None):
    return {
        "schema_version": 1,
        "handoff_schema": schema,
        "view": view,
        "canonical": canonical if canonical is not None else requirements_canonical(),
        "stage": stage,
        "next_step": next_step,
    }


def run(script, value):
    raw = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode("utf-8")
    return subprocess.run(
        [sys.executable, str(script)], input=raw, capture_output=True, check=False
    )


class HandoffRendererRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(
            all(script.is_file() for script in SCRIPTS),
            "the three render_handoff.py copies are the missing target interfaces",
        )

    def assert_failure(self, value, exit_code, code, errors):
        result = run(SCRIPTS[0], value)
        self.assertEqual(exit_code, result.returncode, result.stderr.decode("utf-8", "replace"))
        self.assertEqual(b"", result.stdout)
        self.assertEqual(
            {"code": code, "errors": errors},
            json.loads(result.stderr.decode("utf-8")),
        )
        self.assertTrue(result.stderr.endswith(b"\n"))
        self.assertNotIn(b"\r", result.stderr)

    def test_three_production_copies_are_byte_identical(self):
        contents = [script.read_bytes() for script in SCRIPTS]
        self.assertTrue(all(content == contents[0] for content in contents[1:]))

    def test_all_copies_render_identical_compact_bytes(self):
        value = payload(
            view="compact",
            stage="需求澄清",
            next_step="确认审批范围",
        )
        results = [run(script, value) for script in SCRIPTS]

        self.assertTrue(all(result.returncode == 0 for result in results))
        self.assertTrue(all(result.stdout == results[0].stdout for result in results[1:]))
        self.assertEqual(
            "当前阶段：需求澄清\n主题：order-approval\n下一步：确认审批范围\n".encode("utf-8"),
            results[0].stdout,
        )
        self.assertTrue(all(result.stderr == b"" for result in results))

    def test_compact_topic_uses_canonical_null_and_unknown_mappings(self):
        for topic, expected in ((None, "未确定"), ("unknown", "未知")):
            with self.subTest(topic=topic):
                canonical = requirements_canonical(
                    requirements_path=None,
                    requirements_topic=topic,
                    requirements_scope=None,
                    understanding_confidence="unknown",
                    understanding_user_confirmation="unknown",
                    requirements_user_approval="pending",
                    requirements_independent_review="unknown",
                    specification_gate="blocked",
                )
                result = run(
                    SCRIPTS[0],
                    payload(
                        view="compact",
                        canonical=canonical,
                        stage="需求澄清",
                        next_step="继续澄清",
                    ),
                )
                self.assertEqual(0, result.returncode, result.stderr.decode("utf-8"))
                self.assertIn(f"主题：{expected}\n".encode("utf-8"), result.stdout)

    def test_workflow_full_view_has_exact_fourteen_lines(self):
        result = run(
            SCRIPTS[0],
            payload(schema="workflow", canonical=workflow_canonical()),
        )

        self.assertEqual(0, result.returncode, result.stderr.decode("utf-8"))
        self.assertEqual(
            "需求文档：/workspace/docs/requirements/order-approval.md\n"
            "需求主题：order-approval\n"
            "需求范围：功能\n"
            "需求理解置信度：97\n"
            "需求理解确认：已确认\n"
            "需求文档用户批准：已批准\n"
            "需求文档独立评审：已通过\n"
            "技术规格门禁：已开放\n"
            "技术规格：/workspace/docs/specs/order-approval-design.md\n"
            "技术规格用户批准：已批准\n"
            "技术规格独立评审：已通过\n"
            "实施计划：/workspace/docs/plans/order-approval.md\n"
            "计划评审状态：已通过\n"
            "实施门禁：已开放\n".encode("utf-8"),
            result.stdout,
        )
        self.assertNotIn(b"\r", result.stdout)

    def test_requirements_null_and_unknown_values_render_contextually(self):
        canonical = requirements_canonical(
            requirements_path=None,
            requirements_topic="unknown",
            requirements_scope=None,
            understanding_confidence="unknown",
            understanding_user_confirmation="unknown",
            requirements_user_approval="pending",
            requirements_independent_review="unknown",
            specification_gate="blocked",
        )
        result = run(SCRIPTS[0], payload(canonical=canonical))

        self.assertEqual(0, result.returncode, result.stderr.decode("utf-8"))
        self.assertEqual(
            "需求文档：未确定\n需求主题：未知\n需求范围：未确定\n"
            "需求理解置信度：未知\n需求理解确认：未知\n"
            "需求文档用户批准：待批准\n需求文档独立评审：未知\n"
            "技术规格门禁：未开放\n".encode("utf-8"),
            result.stdout,
        )

    def test_workflow_plan_state_respects_null_and_non_null_context(self):
        missing = workflow_canonical(
            spec_path=None,
            spec_user_approval="pending",
            spec_independent_review="pending",
            plan_path=None,
            plan_review_status="not-approved",
            implementation_gate="blocked",
        )
        missing_result = run(SCRIPTS[0], payload(schema="workflow", canonical=missing))
        self.assertEqual(0, missing_result.returncode, missing_result.stderr.decode("utf-8"))
        self.assertIn("实施计划：尚未创建\n计划评审状态：未开始\n".encode("utf-8"), missing_result.stdout)

        existing = dict(missing)
        existing["plan_path"] = "/workspace/docs/plans/order-approval.md"
        existing["plan_review_status"] = "unknown"
        existing_result = run(SCRIPTS[0], payload(schema="workflow", canonical=existing))
        self.assertEqual(0, existing_result.returncode, existing_result.stderr.decode("utf-8"))
        self.assertIn("计划评审状态：未知\n".encode("utf-8"), existing_result.stdout)

    def test_invalid_json_preflight_rejects_utf8_bom_syntax_numbers_and_multiple_values(self):
        vectors = (
            (b"\xff", ": invalid_utf8"),
            (b"\xef\xbb\xbf{}", ": bom"),
            (b"{", ": invalid_syntax"),
            (b'{"value":NaN}', ": nonstandard_number"),
            (b'{"value":Infinity}', ": nonstandard_number"),
            (b'{"value":-Infinity}', ": nonstandard_number"),
            (b"{} {}", ": invalid_syntax"),
        )
        for raw, error in vectors:
            with self.subTest(raw=raw):
                self.assert_failure(raw, 2, "invalid_json", [error])

    def test_duplicate_and_surrogate_preflight_uses_rfc6901_and_stable_order(self):
        duplicate = (
            b'{"schema_version":1,"handoff_schema":"requirements","view":"full",'
            b'"canonical":{"z/z":1,"z/z":2,"a~b":1,"a~b":2},'
            b'"stage":null,"next_step":null}'
        )
        self.assert_failure(
            duplicate,
            2,
            "invalid_json",
            ["/canonical/a~0b: duplicate", "/canonical/z~1z: duplicate"],
        )

        surrogate = (
            b'{"schema_version":1,"handoff_schema":"requirements","view":"full",'
            b'"canonical":{"requirements_path":"\\ud800"},'
            b'"stage":null,"next_step":null}'
        )
        self.assert_failure(
            surrogate,
            2,
            "invalid_json",
            ["/canonical/requirements_path: surrogate"],
        )

    def test_top_level_errors_precede_canonical_errors_and_are_ordered(self):
        value = payload()
        del value["schema_version"]
        value["view"] = "wide"
        value["z"] = True
        value["a"] = True
        self.assert_failure(
            value,
            3,
            "invalid_input",
            [
                "/schema_version: missing",
                "/view: invalid_value",
                "/a: unexpected",
                "/z: unexpected",
            ],
        )

    def test_canonical_shape_and_values_are_exact_and_ordered(self):
        canonical = requirements_canonical()
        del canonical["requirements_path"]
        canonical["requirements_scope"] = "epic"
        canonical["understanding_confidence"] = True
        canonical["z"] = 1
        canonical["a"] = 1
        self.assert_failure(
            payload(canonical=canonical),
            4,
            "invalid_canonical",
            [
                "/canonical/requirements_path: missing",
                "/canonical/requirements_scope: invalid_value",
                "/canonical/understanding_confidence: wrong_type",
                "/canonical/a: unexpected",
                "/canonical/z: unexpected",
            ],
        )

    def test_topic_path_and_next_step_reject_reserved_and_forbidden_characters(self):
        for topic, reason in (("pending", "reserved"), ("Order-Approval", "invalid_value")):
            with self.subTest(topic=topic):
                self.assert_failure(
                    payload(canonical=requirements_canonical(requirements_topic=topic, specification_gate="blocked")),
                    4,
                    "invalid_canonical",
                    [f"/canonical/requirements_topic: {reason}"],
                )

        for path_value, reason in (
            ("", "empty"),
            (" padded ", "invalid_value"),
            ("line\u2028break", "forbidden_character"),
            ("line\u0085break", "forbidden_character"),
            ("line\nbreak", "line_break"),
        ):
            with self.subTest(path_value=path_value):
                self.assert_failure(
                    payload(canonical=requirements_canonical(requirements_path=path_value, specification_gate="blocked")),
                    4,
                    "invalid_canonical",
                    [f"/canonical/requirements_path: {reason}"],
                )

        for next_step, reason in (
            ("", "empty"),
            ("x" * 201, "out_of_range"),
            ("line\nstep", "line_break"),
            ("line\u2029step", "forbidden_character"),
        ):
            with self.subTest(next_step=next_step):
                self.assert_failure(
                    payload(view="compact", stage="需求澄清", next_step=next_step),
                    7,
                    "invalid_compact",
                    [f"/next_step: {reason}"],
                )

    def test_gate_truth_tables_reject_inconsistent_claims(self):
        blocked_requirements = requirements_canonical(
            requirements_user_approval="pending", specification_gate="open"
        )
        self.assert_failure(
            payload(canonical=blocked_requirements),
            5,
            "gate_conflict",
            ["/canonical/specification_gate: conflict"],
        )

        blocked_workflow = workflow_canonical(
            plan_review_status="not-approved", implementation_gate="open"
        )
        self.assert_failure(
            payload(schema="workflow", canonical=blocked_workflow),
            5,
            "gate_conflict",
            ["/canonical/implementation_gate: conflict"],
        )

    def test_full_and_compact_context_rules_are_fail_closed(self):
        full = payload(stage="需求澄清", next_step="继续")
        self.assert_failure(
            full,
            7,
            "invalid_compact",
            ["/stage: invalid_value", "/next_step: invalid_value"],
        )
        compact = payload(view="compact", stage="未知阶段", next_step="继续")
        self.assert_failure(
            compact,
            7,
            "invalid_compact",
            ["/stage: invalid_value"],
        )


if __name__ == "__main__":
    unittest.main()
