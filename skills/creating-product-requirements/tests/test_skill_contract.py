import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


class CreatingProductRequirementsContractTests(unittest.TestCase):
    def test_stable_topic_is_one_non_reserved_ascii_kebab_value_everywhere(self):
        text = (
            read("SKILL.md")
            + read("references/discovery-and-confidence.md")
            + read("references/document-contract.md")
            + read("references/review-and-handoff.md")
            + read("assets/prd-template.md")
        ).casefold()
        for required in (
            "non-reserved lowercase ascii kebab-case",
            "same topic",
            "<stable-kebab-topic>",
            "null, unknown, and pending are reserved",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_frontmatter_has_only_name_and_trigger_description(self):
        metadata = parse_frontmatter(read("SKILL.md"))
        self.assertEqual({"name", "description"}, set(metadata))
        self.assertEqual("creating-product-requirements", metadata["name"])
        description = metadata["description"]
        self.assertTrue(description.startswith("Use when"))
        for trigger in (
            "product requirements",
            "prd",
            "product scope",
            "user scenarios",
            "acceptance criteria",
        ):
            with self.subTest(trigger=trigger):
                self.assertIn(trigger, description.casefold())

    def test_required_resources_are_linked_and_exist(self):
        skill = read("SKILL.md")
        for relative_path in (
            "references/discovery-and-confidence.md",
            "references/document-contract.md",
            "references/review-and-handoff.md",
            "assets/prd-template.md",
        ):
            with self.subTest(relative_path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())
                self.assertIn(relative_path, skill)

    def test_scope_and_stable_topic_are_mandatory(self):
        text = (read("SKILL.md") + read("references/discovery-and-confidence.md")).casefold()
        for required in (
            "product",
            "phase",
            "feature",
            "one stable topic",
            "do not combine",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_confidence_and_user_confirmation_are_independent_gates(self):
        text = (read("SKILL.md") + read("references/discovery-and-confidence.md")).casefold()
        for required in (
            "at least 95",
            "requirements-understanding summary",
            "explicitly confirms",
            "does not replace",
            "do not create the prd",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_default_and_explicit_path_priority_are_fixed(self):
        text = read("references/discovery-and-confidence.md").casefold()
        self.assertIn(
            "docs/requirements/yyyy-mm-dd-<stable-kebab-topic>.md", text
        )
        self.assertIn("explicit user path", text)
        self.assertIn("existing repository convention", text)
        self.assertIn("preserve the absolute candidate path", text)

    def test_prd_boundary_excludes_technical_design(self):
        text = (read("references/document-contract.md") + read("assets/prd-template.md")).casefold()
        for excluded in (
            "architecture",
            "api",
            "database",
            "code files",
            "implementation tasks",
        ):
            with self.subTest(excluded=excluded):
                self.assertIn(excluded, text)
        self.assertIn("product-visible constraints", text)

    def test_independent_review_and_user_approval_are_distinct(self):
        text = (read("SKILL.md") + read("references/review-and-handoff.md")).casefold()
        for required in (
            "fresh read-only reviewer",
            "does not equal user approval",
            "explicitly approves the current prd",
            "specification_gate",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)
        self.assertIn("open questions", text)
        self.assertIn("verification gaps", text)

    def test_read_only_handoff_does_not_reopen_approved_content_review(self):
        text = read("references/review-and-handoff.md").casefold()
        self.assertIn("do not re-litigate", text)
        self.assertIn("report specification_gate open", text)
        self.assertIn("material change", text)

    def test_unknown_pending_and_material_change_mappings_are_explicit(self):
        text = read("references/review-and-handoff.md").casefold()
        for required in (
            "pending",
            "unknown",
            "duplicate",
            "conflicting",
            "material change",
            "reset",
            "reassess",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)
        self.assertIn("remove stale reviewer identity", text)
        self.assertIn("approval and review dates", text)

    def test_every_reply_ends_with_fixed_eight_field_handoff(self):
        text = read("references/review-and-handoff.md").casefold()
        for field in (
            "requirements_path",
            "requirements_topic",
            "requirements_scope",
            "understanding_confidence",
            "understanding_user_confirmation",
            "requirements_user_approval",
            "requirements_independent_review",
            "specification_gate",
        ):
            with self.subTest(field=field):
                self.assertEqual(1, text.count(f"{field}:"))
        self.assertIn("every user-facing response", text)

    def test_runtime_boundary_forbids_downstream_and_external_actions(self):
        text = (read("SKILL.md") + read("references/review-and-handoff.md")).casefold()
        for forbidden in (
            "do not create a design spec",
            "do not create an implementation plan",
            "do not implement target code",
            "do not call sibling skills",
            "do not create or manage a user-visible task/thread",
            "do not install",
            "do not commit",
            "do not push",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertIn(forbidden, text)

    def test_prd_template_starts_with_truthful_pending_approvals(self):
        template = read("assets/prd-template.md")
        self.assertTrue(template.startswith("---\n"))
        metadata = parse_frontmatter(template)
        self.assertEqual("product-requirements", metadata["document_type"])
        self.assertEqual("<scope-type>", metadata["scope_type"])
        self.assertEqual("approved", metadata["understanding_user_confirmation"])
        self.assertEqual("pending", metadata["user_approval"])
        self.assertEqual("pending", metadata["independent_review"])


if __name__ == "__main__":
    unittest.main()
