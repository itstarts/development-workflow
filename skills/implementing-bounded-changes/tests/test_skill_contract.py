import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "SKILL.md"


def read_skill() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


class ImplementingBoundedChangesContractTests(unittest.TestCase):
    def test_trigger_requires_approved_bounded_implementation_or_fix(self):
        skill = read_skill()
        match = re.match(r"\A---\n(.*?)\n---\n", skill, re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group(1).casefold()

        self.assertIn("user has explicitly approved", frontmatter)
        self.assertIn("bounded", frontmatter)
        self.assertIn("implementation", frontmatter)
        self.assertIn("bug fix", frontmatter)
        self.assertNotIn("prd", frontmatter)
        self.assertNotIn("development prompt", frontmatter)

    def test_workflow_freezes_scope_before_writes(self):
        skill = read_skill().casefold()

        for phrase in (
            "approved goal",
            "change points",
            "implementation approach",
            "non-goals",
            "validation boundary",
            "documentation impact",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)
        freeze = skill.find("freeze the execution scope")
        implementation = skill.find("### 4. implement")
        self.assertGreaterEqual(freeze, 0)
        self.assertGreaterEqual(implementation, 0)
        if freeze >= 0 and implementation >= 0:
            self.assertLess(freeze, implementation)
        self.assertIn("do not create a prd, technical spec, implementation plan", skill)

    def test_scope_expansion_is_a_blocking_user_gate(self):
        skill = read_skill().casefold()

        for boundary in (
            "public contract",
            "dependency",
            "architecture",
            "data model",
            "permission",
            "migration",
            "concurrency",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, skill)
        self.assertIn("stop before making that change", skill)
        self.assertIn("explicit user approval", skill)
        self.assertIn("reviewer suggestions", skill)

    def test_behavior_changes_use_red_green_without_manufactured_tests(self):
        skill = read_skill().casefold()

        self.assertIn("observe the test fail", skill)
        self.assertIn("smallest implementation", skill)
        self.assertIn("let an immediately required parent gate supply the green result", skill)
        self.assertIn("no meaningful executable seam", skill)
        self.assertIn("do not manufacture a test", skill)

    def test_validation_and_documentation_are_proportional_and_required(self):
        skill = read_skill().casefold()

        self.assertIn("smallest sufficient validation", skill)
        self.assertIn("do not default to the full test suite", skill)
        self.assertIn("repository rules", skill)
        self.assertIn("update only existing documentation affected", skill)
        self.assertIn("documentation is part of completion", skill)

    def test_validation_results_are_reused_until_relevant_inputs_change(self):
        skill = read_skill().casefold()

        for phrase in (
            "in-memory validation ledger",
            "do not rerun a passing check",
            "review or agent handoff",
            "invalidate only the affected validation",
            "required parent or final gate once",
            "let the gate supply its green result",
            "inconclusive result",
            "diagnose the cause before retrying",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)

        for relevant_input in (
            "production code",
            "test",
            "fixture",
            "configuration",
            "dependency",
            "validation command",
            "environment",
        ):
            with self.subTest(relevant_input=relevant_input):
                self.assertIn(relevant_input, skill)

    def test_project_validation_mapping_remains_optional_rule_governance_input(self):
        skill = read_skill().casefold()

        for phrase in (
            "reusable project-specific validation mapping",
            "temporary in-memory mapping",
            "do not edit `agents.md`",
            "implementation approval is not rule approval",
            "candidate evidence",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)

    def test_delegation_and_review_must_be_bounded_and_truthful(self):
        skill = read_skill().casefold()

        self.assertIn("sub agent", skill)
        self.assertIn("bounded subtask", skill)
        self.assertIn("main agent retains", skill)
        self.assertIn("implementation-independent reviewer", skill)
        self.assertIn("do not self-approve", skill)
        self.assertIn("do not claim", skill)
        self.assertIn("latest complete diff", skill)

    def test_final_review_is_required_without_over_reviewing(self):
        skill = read_skill().casefold()

        self.assertIn("classify the review requirement", skill)
        self.assertIn("pure documentation, formatting, or deterministic mechanical change", skill)
        self.assertIn("does not change executable behavior", skill)
        self.assertIn("stale, non-normative documentation example", skill)
        self.assertIn("behavior already established by current code and focused tests", skill)
        self.assertIn("normative api, configuration, operational", skill)
        self.assertIn("independent review is not required", skill)
        self.assertIn("inspect the latest complete diff", skill)
        self.assertIn("behavior change", skill)
        self.assertIn("classification is uncertain", skill)
        self.assertIn("repository rules require review", skill)
        self.assertIn("one implementation-independent reviewer", skill)
        self.assertIn("do not require per-slice or per-task review", skill)
        self.assertIn("same reviewer", skill)
        self.assertIn("same reviewer re-check", skill)
        self.assertIn("once approved, stop reviewing", skill)
        self.assertIn("do not add another reviewer", skill)
        self.assertIn("report the task as blocked", skill)

    def test_review_automation_stops_after_two_unapproved_fix_cycles(self):
        skill = read_skill().casefold()

        for phrase in (
            "two consecutive repair-and-review cycles",
            "stop the automatic loop",
            "implementation gate remains blocked",
            "cannot replace missing correctness or review evidence",
            "same reviewer",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)

    def test_completion_report_preserves_failures_and_limits(self):
        skill = read_skill().casefold()

        for field in (
            "changed files",
            "documentation updates",
            "validation commands and results",
            "review result",
            "unresolved limitations",
        ):
            with self.subTest(field=field):
                self.assertIn(field, skill)
        self.assertIn("unrelated pre-existing failures", skill)


if __name__ == "__main__":
    unittest.main()
