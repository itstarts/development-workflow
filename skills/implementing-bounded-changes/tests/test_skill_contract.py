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
        self.assertIn("no meaningful executable seam", skill)
        self.assertIn("do not manufacture a test", skill)

    def test_validation_and_documentation_are_proportional_and_required(self):
        skill = read_skill().casefold()

        self.assertIn("smallest sufficient validation", skill)
        self.assertIn("do not default to the full test suite", skill)
        self.assertIn("repository rules", skill)
        self.assertIn("update only existing documentation affected", skill)
        self.assertIn("documentation is part of completion", skill)

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

        self.assertIn("final review is a completion gate", skill)
        self.assertIn("one implementation-independent reviewer", skill)
        self.assertIn("do not require per-slice or per-task review", skill)
        self.assertIn("same reviewer", skill)
        self.assertIn("until the reviewer returns approved", skill)
        self.assertIn("once approved, stop reviewing", skill)
        self.assertIn("do not add another reviewer", skill)
        self.assertIn("report the task as blocked", skill)

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
