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


class SkillContractTests(unittest.TestCase):
    def test_frontmatter_has_only_name_and_description(self):
        metadata = parse_frontmatter(read("SKILL.md"))
        self.assertEqual({"name", "description"}, set(metadata))
        self.assertEqual("generating-development-prompts", metadata["name"])

    def test_description_covers_all_trigger_phrases(self):
        description = parse_frontmatter(read("SKILL.md"))["description"].lower()
        trigger_phrases = (
            ("new-session development prompt", "new session development prompt", "新会话开发提示词"),
            ("spec and plan", "规格与计划", "规格和计划"),
            ("main agent", "主代理"),
            ("subagents", "subagent", "子代理"),
            ("copyable codex development task instructions", "可复制的 codex 开发任务指令"),
        )
        for equivalents in trigger_phrases:
            with self.subTest(equivalents=equivalents):
                self.assertTrue(
                    any(phrase in description for phrase in equivalents),
                    f"description must contain one of {equivalents!r}",
                )

    def test_required_resources_are_linked_and_exist(self):
        skill = read("SKILL.md")
        for relative_path in (
            "scripts/discover_context.py",
            "scripts/render_prompt.py",
            "assets/development-prompt.md",
            "assets/final-reviewer.toml",
            "references/discovery-policy.md",
            "references/model-permission-policy.md",
        ):
            with self.subTest(relative_path=relative_path):
                self.assertTrue(
                    (ROOT / relative_path).is_file(),
                    f"required resource is missing: {relative_path}",
                )
                self.assertIn(relative_path, skill)

    def test_success_contract_requires_prompt_only(self):
        skill = read("SKILL.md").lower()
        self.assertIn("return the renderer stdout verbatim", skill)
        self.assertIn("do not create a task or thread", skill)
        self.assertIn("blocking clarification", skill)

    def test_success_contract_keeps_renderer_stdout_as_complete_reply_when_wrapper_requested(self):
        skill = read("SKILL.md").lower()
        self.assertIn(
            "renderer stdout remains the complete reply even when the user requests a presentation wrapper",
            skill,
        )
        self.assertIn("markdown code fence", skill)

    def test_no_pause_preference_conflict_is_encoded_instead_of_clarified(self):
        for relative_path in ("SKILL.md", "references/model-permission-policy.md"):
            with self.subTest(relative_path=relative_path):
                policy = read(relative_path).lower()
                self.assertIn(
                    "a request to run end-to-end without pausing is a preference, not a blocking ambiguity",
                    policy,
                )
                self.assertIn(
                    "encode the mandatory pause and current-thread switch gate in the generated prompt",
                    policy,
                )

    def test_execution_contract_contains_all_required_gates(self):
        template_path = ROOT / "assets/development-prompt.md"
        self.assertTrue(template_path.is_file(), "execution template is missing")
        template = template_path.read_text(encoding="utf-8").lower()
        required_gates = (
            ("read the specification, plan, and every applicable agents.md", "读取规格、计划和所有适用的 agents.md"),
            ("test-driven development", "测试驱动开发"),
            ("systematic debugging", "系统化调试"),
            ("independent review", "独立评审"),
            ("fix every finding", "修复所有发现"),
            ("re-review", "复审"),
            ("final full review", "最终全量评审"),
            ("verification evidence", "验证证据"),
            ("only report completion", "才报告完成"),
        )
        for equivalents in required_gates:
            with self.subTest(equivalents=equivalents):
                self.assertTrue(
                    any(phrase in template for phrase in equivalents),
                    f"execution template must contain one of {equivalents!r}",
                )

    def test_no_placeholder_text_remains(self):
        production_files = (
            ROOT / "SKILL.md",
            ROOT / "assets/development-prompt.md",
            ROOT / "assets/final-reviewer.toml",
            ROOT / "references/discovery-policy.md",
            ROOT / "references/model-permission-policy.md",
            ROOT / "scripts/discover_context.py",
            ROOT / "scripts/render_prompt.py",
        )
        for path in production_files:
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), f"production file is missing: {path}")
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"\b(?:TODO|TBD|PLACEHOLDER)\b")


if __name__ == "__main__":
    unittest.main()
