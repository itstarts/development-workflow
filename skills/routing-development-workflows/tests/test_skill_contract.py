import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class RoutingDevelopmentWorkflowsContractTests(unittest.TestCase):
    def test_trigger_is_only_for_ambiguous_dw_entry(self):
        skill = read("SKILL.md")
        match = re.match(r"\A---\n(.*?)\n---\n", skill, re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group(1).casefold()

        self.assertIn("development request", frontmatter)
        self.assertIn("fast", frontmatter)
        self.assertIn("standard", frontmatter)
        self.assertIn("full", frontmatter)
        self.assertIn("route", frontmatter)

    def test_exactly_four_routes_and_explicit_entry_stays_outside_router(self):
        text = (read("SKILL.md") + read("references/routing-policy.md")).casefold()

        self.assertIn("fast | standard | full | blocked", text)
        self.assertIn("explicit workflow entry", text)
        self.assertIn("do not reclassify", text)
        self.assertIn("outside this router's applicability", text)
        self.assertNotIn("workflow_route: bypass", text)
        self.assertNotRegex(text, r"workflow_route:[^\n]*bypass")
        self.assertIn("creating-product-requirements", text)
        self.assertIn("creating-development-specs-and-plans", text)
        self.assertIn("generating-development-prompts", text)
        self.assertIn("implementing-bounded-changes", text)

    def test_fast_requires_every_gate_and_unknown_goes_standard(self):
        policy = read("references/routing-policy.md").casefold()

        for phrase in (
            "explicit implementation approval",
            "observable result",
            "local and ordinarily reversible",
            "focused validation",
            "repository rules",
            "every fast condition",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, policy)
        self.assertIn("any material routing fact is unknown", policy)
        self.assertIn("route to `standard`", policy)

    def test_full_route_uses_material_risk_facts(self):
        policy = read("references/routing-policy.md").casefold()

        for boundary in (
            "public contract",
            "data model",
            "migration",
            "permission",
            "security",
            "money",
            "concurrency",
            "transaction",
            "consistency",
            "external state",
            "cross-module core rule",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, policy)

    def test_router_emits_stable_handoff_without_downstream_work(self):
        skill = read("SKILL.md").casefold()

        self.assertIn(
            "workflow_route: fast | standard | full | blocked",
            skill,
        )
        for field in (
            "workflow_route",
            "scope_summary",
            "risk_facts",
            "implementation_approval",
            "destination_capability",
            "next_action",
        ):
            with self.subTest(field=field):
                self.assertIn(field, skill)
        for boundary in (
            "do not create a prd",
            "do not create a technical specification",
            "do not create an implementation plan",
            "do not modify production files",
            "runtime-exposed capability",
            "do not read sibling skill source",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, skill)

    def test_scope_expansion_requires_reclassification(self):
        policy = read("references/routing-policy.md").casefold()

        self.assertIn("stop the current route", policy)
        self.assertIn("reclassify", policy)
        self.assertIn("do not reuse the earlier approval", policy)


if __name__ == "__main__":
    unittest.main()
