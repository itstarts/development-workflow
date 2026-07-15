import ast
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
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


class CreatingSpecsAndPlansContractTests(unittest.TestCase):
    def test_default_paths_are_neutral(self):
        text = read("references/discovery-and-clarification.md")
        self.assertIn("docs/specs/YYYY-MM-DD-<topic>-design.md", text)
        self.assertIn("docs/plans/YYYY-MM-DD-<topic>.md", text)

    def test_spec_review_is_required_before_plan(self):
        text = (read("SKILL.md") + read("references/review-and-handoff.md")).casefold()
        self.assertIn("spec independent review is approved", text)
        self.assertIn("before creating the plan", text)
        self.assertIn("main agent updates", text)

    def test_null_path_state_mapping(self):
        text = read("references/review-and-handoff.md").casefold()
        self.assertIn("spec_path: <absolute path> | null", text)
        self.assertIn("plan_path: null maps to not-approved", text)
        self.assertIn("existing plan", text)

    def test_explicit_paths_survive_content_ambiguity(self):
        text = read("references/discovery-and-clarification.md").casefold()
        self.assertIn("keep reliably selected explicit paths", text)
        self.assertIn("material content question", text)
        self.assertIn("only use `null` when the path itself is unresolved", text)

    def test_rule_discovery_does_not_scan_above_repository_root(self):
        text = read("SKILL.md").casefold()
        self.assertIn("repository root to the working directory", text)
        self.assertIn("never recursively search above the repository root", text)

    def test_skill_tests_do_not_import_sibling_modules(self):
        source = Path(__file__).read_text(encoding="utf-8")
        imported_modules = {
            alias.name
            for node in ast.walk(ast.parse(source))
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("importlib", imported_modules)
        self.assertFalse(any("generating-development-prompts" in name for name in imported_modules))

    def test_frontmatter_has_only_name_and_trigger_description(self):
        metadata = parse_frontmatter(read("SKILL.md"))
        self.assertEqual({"name", "description"}, set(metadata))
        self.assertEqual("creating-development-specs-and-plans", metadata["name"])
        description = metadata["description"]
        self.assertTrue(description.startswith("Use when"))
        for trigger in (
            "development requirements",
            "design",
            "specification",
            "implementation plan",
            "development handoff",
        ):
            with self.subTest(trigger=trigger):
                self.assertIn(trigger, description.casefold())
        for process_summary in ("ask questions", "write spec", "review loop"):
            self.assertNotIn(process_summary, description.casefold())

    def test_required_resources_are_linked_and_exist(self):
        skill = read("SKILL.md")
        resources = (
            "references/discovery-and-clarification.md",
            "references/document-contracts.md",
            "references/review-and-handoff.md",
            "assets/spec-template.md",
            "assets/plan-template.md",
        )
        for relative_path in resources:
            with self.subTest(relative_path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())
                self.assertIn(relative_path, skill)

    def test_spec_review_and_user_approval_are_distinct_hard_gates(self):
        text = (read("SKILL.md") + read("references/review-and-handoff.md")).casefold()
        for required in (
            "fresh read-only spec reviewer",
            "fix every finding",
            "re-review",
            "does not equal user approval",
            "explicitly approves the current written spec",
            "material spec change invalidates approval",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_plan_review_and_three_state_handoff_are_explicit(self):
        text = (read("SKILL.md") + read("references/review-and-handoff.md")).casefold()
        for required in (
            "fresh read-only plan reviewer",
            "pending maps to not-approved",
            "unreliable review metadata maps to unknown",
            "implementation_gate",
            "spec_path",
            "plan_path",
            "absolute paths",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_every_clarification_and_blocker_ends_with_fixed_handoff(self):
        text = read("references/review-and-handoff.md").casefold()
        for required in (
            "every user-facing response",
            "clarification question",
            "blocked response",
            "must end with the complete six-field record",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_handoff_record_emits_one_value_per_field(self):
        text = read("references/review-and-handoff.md").casefold()
        self.assertIn("reference-only alternatives", text)
        self.assertIn("emit exactly one allowed value", text)
        self.assertIn("never copy the `|`", text)

    def test_material_ambiguity_stops_before_document_or_review_work(self):
        text = (
            read("SKILL.md") + read("references/discovery-and-clarification.md")
        ).casefold()
        for required in (
            "one material question",
            "do not write or review either document",
            "immediately end the reply with the fixed handoff record",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_runtime_contract_forbids_implementation_and_external_side_effects(self):
        text = (read("SKILL.md") + read("references/review-and-handoff.md")).casefold()
        for required in (
            "do not implement target code",
            "do not call sibling skills",
            "do not create or manage a user-visible task/thread",
            "do not commit",
            "do not push",
            "do not merge",
            "do not rebase",
            "do not tag",
            "do not release",
            "do not install into the real codex_home",
            "do not change external state",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_templates_start_pending_and_plan_is_parser_compatible(self):
        spec_template = read("assets/spec-template.md")
        plan_template = read("assets/plan-template.md")
        self.assertTrue(spec_template.startswith("---\n"))
        self.assertIn("user_approval: pending", spec_template)
        self.assertNotIn("user_approval: approved", spec_template)
        self.assertTrue(plan_template.startswith("---\n"))
        self.assertIn("review_status: pending", plan_template)
        self.assertIn("spec_path:", plan_template)

        self.assertEqual("pending", parse_frontmatter(plan_template)["review_status"])
        approved = plan_template.replace(
            "review_status: pending", "review_status: approved", 1
        )
        self.assertEqual("approved", parse_frontmatter(approved)["review_status"])

    def test_plan_template_requires_docs_and_task_review(self):
        template = read("assets/plan-template.md").casefold()
        for required in (
            "exact files",
            "interfaces",
            "testing approach",
            "when the approved spec or repository rules require tdd",
            "documentation synchronization",
            "task-level independent review",
        ):
            with self.subTest(required=required):
                self.assertIn(required, template)

    def test_security_detail_is_required_only_when_relevant(self):
        contracts = read("references/document-contracts.md").casefold()
        template = read("assets/spec-template.md").casefold()
        self.assertIn("only when the requested feature actually touches", contracts)
        self.assertIn("only when the feature requires it", template)
        self.assertNotIn("## errors, uncertainty, and safety", template)

    def test_production_files_have_no_placeholders_or_machine_paths(self):
        production = [ROOT / "SKILL.md"]
        for directory in ("agents", "assets", "references", "scripts"):
            path = ROOT / directory
            if path.is_dir():
                production.extend(item for item in path.rglob("*") if item.is_file())
        for path in production:
            with self.subTest(path=path.relative_to(ROOT)):
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"\b(?:TODO|TBD|PLACEHOLDER)\b")
                self.assertNotIn("/Users/", text)
                self.assertNotIn("~/.codex/plugins/cache/", text)


if __name__ == "__main__":
    unittest.main()
