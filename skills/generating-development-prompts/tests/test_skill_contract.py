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


def fenced_text_blocks(text: str) -> list[list[str]]:
    return [
        match.group(1).splitlines()
        for match in re.finditer(r"```text\n(.*?)\n```", text, re.DOTALL)
    ]


def production_files() -> tuple[Path, ...]:
    paths = [ROOT / "SKILL.md"]
    for directory_name in ("agents", "assets", "references", "scripts"):
        directory = ROOT / directory_name
        paths.extend(
            path
            for path in directory.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix not in {".pyc", ".pyo"}
        )
    return tuple(sorted(paths))


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
            ("approved fourteen-field handoff", "已批准十四字段交接"),
            ("session routing", "会话路由"),
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
            "references/discovery-policy.md",
            "references/permission-policy.md",
            "references/session-routing-policy.md",
        ):
            with self.subTest(relative_path=relative_path):
                self.assertTrue(
                    (ROOT / relative_path).is_file(),
                    f"required resource is missing: {relative_path}",
                )
                self.assertIn(relative_path, skill)

    def test_success_contract_routes_before_rendering(self):
        policy_path = ROOT / "references" / "session-routing-policy.md"
        policy = policy_path.read_text(encoding="utf-8").casefold() if policy_path.is_file() else ""
        skill = read("SKILL.md").casefold()
        combined = skill + policy
        for required in (
            "current-session",
            "new-session",
            "blocked",
            "evidence is insufficient",
            "current session lacks",
            "do not infer that a new session has the same limitation",
            "implementation_gate: open",
        ):
            with self.subTest(required=required):
                self.assertIn(required, combined)
        self.assertIn("render only for `new-session`", combined)
        self.assertIn("do not create a task or thread", skill)
        self.assertIn("blocking clarification", skill)

    def test_success_contract_requires_single_renderer_code_fence(self):
        skill = read("SKILL.md").lower()
        self.assertIn("single markdown code fence", skill)
        self.assertIn("dynamic backtick fence", skill)
        self.assertIn("render_prompt.py", skill)
        self.assertIn("stdout verbatim", skill)

    def test_generated_prompt_caps_automatic_final_review_cycles(self):
        template = read("assets/development-prompt.md").casefold()
        for phrase in (
            "连续两轮修复与复审",
            "停止自动循环",
            "实施门禁保持关闭",
            "用户指令不能替代缺失的正确性或评审证据",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, template)

    def test_manual_prompt_request_keeps_unapproved_plan_compatibility(self):
        policy_path = ROOT / "references" / "session-routing-policy.md"
        policy = policy_path.read_text(encoding="utf-8").casefold() if policy_path.is_file() else ""
        combined = read("SKILL.md").casefold() + policy
        for required in (
            "explicit prompt request",
            "not-approved",
            "unknown",
            "implementation gate",
            "do not fabricate",
        ):
            with self.subTest(required=required):
                self.assertIn(required, combined)

    def test_automatic_routing_preserves_upstream_fourteen_field_suffix(self):
        policy_path = ROOT / "references" / "session-routing-policy.md"
        policy = policy_path.read_text(encoding="utf-8").casefold() if policy_path.is_file() else ""
        combined = read("SKILL.md").casefold() + policy
        for required in (
            "fourteen-field snapshot",
            "same snapshot",
            "end with",
            "do not change document approval",
        ):
            with self.subTest(required=required):
                self.assertIn(required, combined)

    def test_automatic_handoff_suffix_is_plain_text_not_a_code_fence(self):
        policy_path = ROOT / "references" / "session-routing-policy.md"
        policy = policy_path.read_text(encoding="utf-8").casefold() if policy_path.is_file() else ""
        for required in (
            "handoff is plain text",
            "never wrap the handoff in a code fence",
            "final non-empty line is `实施门禁",
            "do not repeat any fixed handoff field label",
        ):
            with self.subTest(required=required):
                self.assertIn(required, policy)

    def test_automatic_routes_share_one_renderer_validated_chinese_suffix(self):
        combined = read("SKILL.md") + read("references/session-routing-policy.md")
        lowered = combined.casefold()
        for required in (
            "canonical english snapshot",
            "render_handoff.py",
            "exactly once",
            "before choosing a route",
            "sole presentation validator",
            "same renderer-validated chinese view",
            "`render_prompt.py` stdout before",
            "`render_handoff.py` stdout",
            "outside the dynamic fence",
            "do not reverse-parse",
        ):
            with self.subTest(required=required):
                self.assertIn(required, lowered)
        for route in ("current-session", "new-session", "blocked"):
            with self.subTest(route=route):
                self.assertIn(route, lowered)
        self.assertNotIn("pre-render this authoritative chinese view", lowered)
        self.assertNotIn("before invoking the renderer", lowered)
        self.assertNotIn("do not invoke the renderer", lowered)

    def test_routing_policy_does_not_duplicate_renderer_owned_chinese_mapping(self):
        policy = read("references/session-routing-policy.md")
        self.assertEqual(0, policy.count("需求文档：<"))
        self.assertEqual(0, policy.count("Map requirements scope"))
        self.assertIn("`render_handoff.py` stdout", policy)

    def test_handoff_renderer_failure_stops_routing_and_manual_request_stays_compatible(self):
        combined = (read("SKILL.md") + read("references/session-routing-policy.md")).casefold()
        for required in (
            "handoff renderer failure",
            "machine-readable stderr",
            "only explicit exception",
            "deterministic chinese blocker",
            "does not append a status view",
            "do not choose any route",
            "stop the current automatic routing",
            "manual prompt request without a verified upstream snapshot returns renderer stdout verbatim",
        ):
            with self.subTest(required=required):
                self.assertIn(required, combined)

    def test_production_files_have_no_effort_contract(self):
        forbidden = (
            "reasoning_effort",
            "recommended_effort",
            "new_session_effort",
            "新会话建议",
        )
        for path in production_files():
            text = path.read_text(encoding="utf-8").casefold()
            for phrase in forbidden:
                with self.subTest(path=path.name, phrase=phrase):
                    self.assertNotIn(phrase.casefold(), text)

    def test_execution_contract_contains_all_required_gates(self):
        template_path = ROOT / "assets/development-prompt.md"
        self.assertTrue(template_path.is_file(), "execution template is missing")
        template = template_path.read_text(encoding="utf-8").lower()
        required_gates = (
            ("read the specification, plan, and every applicable agents.md", "读取规格、计划和所有适用的 agents.md"),
            ("global custom agent", "全局子代理"),
            ("repository rules", "仓库规则"),
            ("tdd", "失败测试"),
            ("independent reviewer", "独立评审者"),
            ("re-review", "复审"),
            ("whole-scope review", "整体评审"),
            ("verification evidence", "验证证据"),
            ("only report completion", "才报告完成"),
        )
        for equivalents in required_gates:
            with self.subTest(equivalents=equivalents):
                self.assertTrue(
                    any(phrase in template for phrase in equivalents),
                    f"execution template must contain one of {equivalents!r}",
                )

    def test_execution_contract_batches_review_by_risk_not_task_count(self):
        template = read("assets/development-prompt.md").casefold()
        skill = read("SKILL.md").casefold()
        for required in (
            "每项任务完成与影响范围匹配的验证",
            "不得仅因任务数量",
            "中间里程碑评审",
            "最新完整 diff",
        ):
            with self.subTest(required=required):
                self.assertIn(required, template)
        self.assertIn("task count", skill)
        self.assertIn("latest complete diff", skill)
        self.assertNotIn("独立评审未通过不得进入下一项", template)

    def test_production_files_have_no_framework_name_path_or_derived_workflow(self):
        forbidden = (
            "systematic " + "debugging",
            "系统化" + "调试",
        )
        for path in production_files():
            text = path.read_text(encoding="utf-8").casefold()
            for phrase in forbidden:
                with self.subTest(path=path.name, phrase=phrase):
                    self.assertNotIn(phrase.casefold(), text)

    def test_no_placeholder_text_remains(self):
        for path in production_files():
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), f"production file is missing: {path}")
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"\b(?:TODO|TBD|PLACEHOLDER)\b")

    def test_policies_are_loaded_progressively_by_entry_path(self):
        text = read("SKILL.md").casefold()
        self.assertIn("classify the entry", text)
        self.assertIn("first read only", text)
        self.assertIn("references/discovery-policy.md", text)
        self.assertIn("when a permission matrix is needed", text)
        self.assertIn("references/permission-policy.md", text)
        self.assertIn("only for automatic routing", text)
        self.assertIn("references/session-routing-policy.md", text)
        self.assertIn("manual prompt", text)
        self.assertIn("does not load the routing policy", text)

    def test_automatic_routes_use_full_renderer_and_manual_prompt_stays_renderer_only(self):
        text = (read("SKILL.md") + read("references/session-routing-policy.md")).casefold()
        for phrase in (
            "scripts/render_handoff.py",
            "handoff_schema",
            "workflow",
            "view",
            "full",
            "current-session",
            "new-session",
            "blocked",
            "manual prompt request without a verified upstream snapshot",
            "stdout verbatim",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_agent_inventory_is_session_scoped_with_conditional_refresh(self):
        text = (read("SKILL.md") + read("assets/development-prompt.md")).casefold()
        for phrase in (
            "first delegation",
            "session-scoped inventory",
            "name",
            "description",
            "do not rescan",
            "configuration changed",
            "initial read failed",
            "launch by name fails",
            "observable capability conflict",
            "explicitly requests a refresh",
            "refresh once",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertNotIn("每次委派前检查", text)

    def test_discovery_policy_separates_chinese_frontmatter_from_english_header(self):
        policy = read("references/discovery-policy.md").casefold()
        for required in (
            "chinese-current",
            "english-legacy",
            "complete chinese plan",
            "exact chinese key",
            "semantic duplicate",
            "unsupported localized value",
            "ascii-only legacy header",
            "do not accept chinese metadata in the legacy header",
        ):
            with self.subTest(required=required):
                self.assertIn(required, policy)


if __name__ == "__main__":
    unittest.main()
