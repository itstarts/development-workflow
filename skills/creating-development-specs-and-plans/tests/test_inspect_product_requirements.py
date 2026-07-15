import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional, Union


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "inspect_product_requirements.py"


def prd(**overrides: str) -> str:
    fields = {
        "document_type": "product-requirements",
        "topic": "order-approval",
        "scope_type": "feature",
        "understanding_confidence": "97",
        "understanding_user_confirmation": "approved",
        "user_approval": "approved",
        "independent_review": "approved",
    }
    fields.update(overrides)
    metadata = "\n".join(f"{key}: {value}" for key, value in fields.items())
    return f"---\n{metadata}\n---\n\n# Order Approval Requirements\n"


class InspectProductRequirementsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repository"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        self.requirements = self.root / "docs" / "requirements" / "order.md"
        self.requirements.parent.mkdir(parents=True)

    def tearDown(self):
        self.temporary.cleanup()

    def run_inspector(
        self, path: Optional[Union[Path, str]] = None, **kwargs: str
    ):
        command = [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(kwargs.get("repo_root", self.root)),
            "--requirements",
            str(path if path is not None else self.requirements),
            "--expected-topic",
            kwargs.get("expected_topic", "order-approval"),
            "--expected-scope",
            kwargs.get("expected_scope", "feature"),
        ]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        payload = json.loads(completed.stdout) if completed.stdout.strip() else None
        return completed, payload

    def test_approved_prd_opens_gate_and_returns_stable_schema(self):
        self.requirements.write_text(prd(), encoding="utf-8")

        completed, payload = self.run_inspector(Path("docs/requirements/order.md"))

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(
            {
                "schema_version",
                "repo_root",
                "requirements_path",
                "expected_topic",
                "expected_scope",
                "document_type",
                "requirements_topic",
                "requirements_scope",
                "understanding_confidence",
                "understanding_user_confirmation",
                "requirements_user_approval",
                "requirements_independent_review",
                "status",
                "specification_gate",
                "issues",
            },
            set(payload),
        )
        self.assertEqual(str(self.root.resolve()), payload["repo_root"])
        self.assertEqual(str(self.requirements.resolve()), payload["requirements_path"])
        self.assertEqual("approved", payload["status"])
        self.assertEqual("open", payload["specification_gate"])
        self.assertEqual([], payload["issues"])

    def test_reliable_pending_is_not_approved(self):
        self.requirements.write_text(prd(user_approval="pending"), encoding="utf-8")

        completed, payload = self.run_inspector()

        self.assertEqual(0, completed.returncode)
        self.assertEqual("not-approved", payload["status"])
        self.assertEqual("blocked", payload["specification_gate"])

    def test_duplicate_or_illegal_metadata_is_unknown(self):
        self.requirements.write_text(
            prd().replace(
                "independent_review: approved",
                "independent_review: approved\nindependent_review: changes-requested",
            ),
            encoding="utf-8",
        )

        completed, payload = self.run_inspector()

        self.assertEqual(0, completed.returncode)
        self.assertEqual("unknown", payload["status"])
        self.assertIn("duplicate_key", payload["issues"])
        self.assertEqual("unknown", payload["requirements_independent_review"])

    def test_missing_frontmatter_and_illegal_values_are_unknown(self):
        self.requirements.write_text("# No metadata\n", encoding="utf-8")
        _, missing = self.run_inspector()

        self.requirements.write_text(
            prd(
                scope_type="component",
                user_approval="yes",
                independent_review="changes-requested",
            ),
            encoding="utf-8",
        )
        _, illegal = self.run_inspector()

        self.assertEqual("unknown", missing["status"])
        self.assertIn("missing_frontmatter", missing["issues"])
        self.assertEqual("unknown", illegal["status"])
        self.assertIn("invalid_scope", illegal["issues"])
        self.assertIn("invalid_approval_state", illegal["issues"])
        self.assertEqual("unknown", illegal["requirements_scope"])
        self.assertEqual("unknown", illegal["requirements_user_approval"])
        self.assertEqual("unknown", illegal["requirements_independent_review"])

    def test_low_confidence_or_pending_summary_is_not_approved(self):
        self.requirements.write_text(
            prd(
                understanding_confidence="90",
                understanding_user_confirmation="pending",
            ),
            encoding="utf-8",
        )

        completed, payload = self.run_inspector()

        self.assertEqual(0, completed.returncode)
        self.assertEqual("not-approved", payload["status"])

    def test_expected_topic_or_scope_mismatch_is_unknown(self):
        self.requirements.write_text(prd(), encoding="utf-8")

        _, topic = self.run_inspector(expected_topic="inventory-alert")
        _, scope = self.run_inspector(expected_scope="phase")

        self.assertEqual("unknown", topic["status"])
        self.assertIn("topic_mismatch", topic["issues"])
        self.assertEqual("unknown", topic["requirements_topic"])
        self.assertEqual("unknown", scope["status"])
        self.assertIn("scope_mismatch", scope["issues"])
        self.assertEqual("unknown", scope["requirements_scope"])

    def test_out_of_range_confidence_is_unknown_and_not_echoed(self):
        for confidence in ("-1", "101"):
            self.requirements.write_text(
                prd(understanding_confidence=confidence), encoding="utf-8"
            )

            completed, payload = self.run_inspector()

            with self.subTest(confidence=confidence):
                self.assertEqual(0, completed.returncode)
                self.assertEqual("unknown", payload["status"])
                self.assertIsNone(payload["understanding_confidence"])
                self.assertIn("invalid_confidence", payload["issues"])

    def test_reserved_document_topic_is_unknown(self):
        self.requirements.write_text(prd(topic="unknown"), encoding="utf-8")

        completed, payload = self.run_inspector()

        self.assertEqual(0, completed.returncode)
        self.assertEqual("unknown", payload["status"])
        self.assertEqual("unknown", payload["requirements_topic"])
        self.assertIn("invalid_topic", payload["issues"])

    def test_missing_file_is_unknown_but_preserves_resolved_path(self):
        missing = Path("docs/requirements/missing.md")

        completed, payload = self.run_inspector(missing)

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str((self.root / missing).resolve()), payload["requirements_path"])
        self.assertEqual("unknown", payload["status"])
        self.assertIn("missing_file", payload["issues"])

    def test_paths_outside_repo_and_symlink_escape_are_unknown(self):
        outside = Path(self.temporary.name) / "outside.md"
        outside.write_text(prd(), encoding="utf-8")
        link = self.root / "docs" / "requirements" / "link.md"
        link.symlink_to(outside)

        _, absolute = self.run_inspector(outside)
        _, escaped = self.run_inspector(link)

        self.assertEqual("unknown", absolute["status"])
        self.assertIn("outside_repo", absolute["issues"])
        self.assertEqual("unknown", escaped["status"])
        self.assertIn("outside_repo", escaped["issues"])

    def test_parent_traversal_escape_is_unknown(self):
        outside = Path(self.temporary.name) / "outside.md"
        outside.write_text(prd(), encoding="utf-8")

        _, payload = self.run_inspector(Path("..") / "outside.md")

        self.assertEqual("unknown", payload["status"])
        self.assertIn("outside_repo", payload["issues"])

    def test_non_file_requirements_path_is_unknown(self):
        self.requirements.mkdir()

        completed, payload = self.run_inspector()

        self.assertEqual(0, completed.returncode)
        self.assertEqual("unknown", payload["status"])
        self.assertIn("not_a_file", payload["issues"])

    def test_invalid_utf8_requirements_file_is_unknown(self):
        self.requirements.write_bytes(b"\xff\xfe\x00")

        completed, payload = self.run_inspector()

        self.assertEqual(0, completed.returncode)
        self.assertEqual("unknown", payload["status"])
        self.assertIn("unreadable_file", payload["issues"])

    def test_non_git_root_is_unknown(self):
        non_git = Path(self.temporary.name) / "non-git"
        non_git.mkdir()
        document = non_git / "requirements.md"
        document.write_text(prd(), encoding="utf-8")

        completed, payload = self.run_inspector(document, repo_root=str(non_git))

        self.assertEqual(0, completed.returncode)
        self.assertEqual("unknown", payload["status"])
        self.assertIn("invalid_repo_root", payload["issues"])

    def test_worktree_git_file_is_accepted(self):
        (self.root / ".git").rmdir()
        (self.root / ".git").write_text(
            "gitdir: /tmp/example-worktree-git-dir\n", encoding="utf-8"
        )
        self.requirements.write_text(prd(), encoding="utf-8")

        completed, payload = self.run_inspector()

        self.assertEqual(0, completed.returncode)
        self.assertEqual("approved", payload["status"])

    def test_cli_usage_error_returns_two(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)], text=True, capture_output=True, check=False
        )
        self.assertEqual(2, completed.returncode)

    def test_illegal_expected_scope_is_a_usage_error(self):
        self.requirements.write_text(prd(), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo-root",
                str(self.root),
                "--requirements",
                str(self.requirements),
                "--expected-topic",
                "order-approval",
                "--expected-scope",
                "component",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(2, completed.returncode)

    def test_empty_or_reserved_expected_topic_is_a_usage_error(self):
        self.requirements.write_text(prd(), encoding="utf-8")
        for topic in ("", "null", "unknown", "pending", "Order Approval"):
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo-root",
                    str(self.root),
                    "--requirements",
                    str(self.requirements),
                    "--expected-topic",
                    topic,
                    "--expected-scope",
                    "feature",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            with self.subTest(topic=topic):
                self.assertEqual(2, completed.returncode)


if __name__ == "__main__":
    unittest.main()
