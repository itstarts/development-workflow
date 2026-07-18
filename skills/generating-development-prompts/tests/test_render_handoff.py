import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_handoff.py"


def requirements_payload(view="full"):
    return {
        "schema_version": 1,
        "handoff_schema": "requirements",
        "view": view,
        "canonical": {
            "requirements_path": "/workspace/docs/requirements/order-approval.md",
            "requirements_topic": "order-approval",
            "requirements_scope": "feature",
            "understanding_confidence": 97,
            "understanding_user_confirmation": "approved",
            "requirements_user_approval": "approved",
            "requirements_independent_review": "approved",
            "specification_gate": "open",
        },
        "stage": None,
        "next_step": None,
    }


def run_renderer(payload):
    stdin = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=stdin,
        capture_output=True,
        check=False,
    )


class RenderHandoffTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), "render_handoff.py is the missing target interface")

    def test_compact_view_is_exactly_three_lf_lines(self):
        payload = requirements_payload("compact")
        payload["stage"] = "需求澄清"
        payload["next_step"] = "确认审批人的选择范围"

        result = run_renderer(payload)

        self.assertEqual(0, result.returncode, result.stderr.decode("utf-8"))
        self.assertEqual(
            "当前阶段：需求澄清\n"
            "主题：order-approval\n"
            "下一步：确认审批人的选择范围\n".encode("utf-8"),
            result.stdout,
        )
        self.assertEqual(b"", result.stderr)
        self.assertNotIn(b"\r", result.stdout)

    def test_full_requirements_view_preserves_eight_field_order(self):
        result = run_renderer(requirements_payload())

        self.assertEqual(0, result.returncode, result.stderr.decode("utf-8"))
        self.assertEqual(
            "需求文档：/workspace/docs/requirements/order-approval.md\n"
            "需求主题：order-approval\n"
            "需求范围：功能\n"
            "需求理解置信度：97\n"
            "需求理解确认：已确认\n"
            "需求文档用户批准：已批准\n"
            "需求文档独立评审：已通过\n"
            "技术规格门禁：已开放\n".encode("utf-8"),
            result.stdout,
        )

    def test_gate_conflict_fails_without_partial_stdout(self):
        payload = requirements_payload()
        payload["canonical"]["specification_gate"] = "blocked"

        result = run_renderer(payload)

        self.assertEqual(5, result.returncode)
        self.assertEqual(b"", result.stdout)
        self.assertEqual(
            {"code": "gate_conflict", "errors": ["/canonical/specification_gate: conflict"]},
            json.loads(result.stderr.decode("utf-8")),
        )

    def test_duplicate_nested_key_is_invalid_json(self):
        raw = (
            b'{"schema_version":1,"handoff_schema":"requirements","view":"full",'
            b'"canonical":{"requirements_path":null,"requirements_path":null},'
            b'"stage":null,"next_step":null}'
        )
        result = subprocess.run(
            [sys.executable, str(SCRIPT)], input=raw, capture_output=True, check=False
        )

        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)
        self.assertEqual(
            {"code": "invalid_json", "errors": ["/canonical/requirements_path: duplicate"]},
            json.loads(result.stderr.decode("utf-8")),
        )

    def test_full_rejects_non_null_compact_context(self):
        payload = requirements_payload()
        payload["stage"] = "需求澄清"

        result = run_renderer(payload)

        self.assertEqual(7, result.returncode)
        self.assertEqual(b"", result.stdout)
        self.assertEqual(
            {"code": "invalid_compact", "errors": ["/stage: invalid_value"]},
            json.loads(result.stderr.decode("utf-8")),
        )


if __name__ == "__main__":
    unittest.main()
