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


def fenced_text_blocks(text: str) -> list[list[str]]:
    return [
        match.group(1).splitlines()
        for match in re.finditer(r"```text\n(.*?)\n```", text, re.DOTALL)
    ]


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

    def test_standard_route_reviews_spec_and_plan_as_one_package(self):
        text = (
            read("SKILL.md")
            + read("references/document-contracts.md")
            + read("references/review-and-handoff.md")
        ).casefold()

        for phrase in (
            "standard route",
            "technical package",
            "create the plan before spec user approval",
            "one package reviewer",
            "one verdict covers the current spec and plan",
            "technical specification user approval remains pending",
            "synchronize the plan metadata",
            "does not invalidate the package review",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_full_route_keeps_sequential_spec_then_plan_gates(self):
        text = (
            read("SKILL.md")
            + read("references/document-contracts.md")
            + read("references/review-and-handoff.md")
        ).casefold()

        self.assertIn("full route", text)
        self.assertIn("user approves that reviewed spec before creating the plan", text)
        self.assertIn("separate plan reviewer", text)
        self.assertIn("missing or unreliable route", text)

    def test_plan_limits_automatic_review_to_two_unapproved_cycles(self):
        text = (
            read("references/document-contracts.md")
            + read("assets/plan-template.md")
        ).casefold()

        for phrase in (
            "two consecutive repair-and-review cycles",
            "stop automatic repair",
            "implementation gate remains blocked",
            "cannot replace missing correctness or review evidence",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

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
            "approved product requirements",
            "technical specification",
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
            "fix only `blocking_in_scope` findings",
            "re-review",
            "does not equal user approval",
            "explicitly approves the current written spec",
            "material spec change invalidates approval",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_known_unavailable_reviewer_is_not_dispatched_or_waited_on(self):
        text = (read("SKILL.md") + read("references/review-and-handoff.md")).casefold()
        for required in (
            "reviewer is known to be unavailable",
            "do not dispatch",
            "do not wait",
            "keep independent review pending",
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

    def test_compact_clarification_and_full_blocker_are_distinct(self):
        text = read("references/review-and-handoff.md").casefold()
        for required in (
            "ordinary-clarification",
            "exactly three consecutive",
            "blocked response",
            "complete fourteen-field record",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_spec_and_plan_templates_use_chinese_user_facing_content(self):
        spec_template = read("assets/spec-template.md")
        plan_template = read("assets/plan-template.md")
        for required in (
            "# <功能名称>技术规格",
            "## 目标",
            "## 非目标",
            "## 当前证据",
            "## 行为与边界",
            "## 组件与控制流",
            "## API 与技术接口",
            "## 数据模型与实体关系",
            "## 状态转换、迁移边界与一致性",
            "## 错误与不确定性",
            "## 测试与文档",
            "## 验收标准",
            "<说明",
        ):
            with self.subTest(template="spec", required=required):
                self.assertIn(required, spec_template)
        for required in (
            "# <功能名称>实施计划",
            "**目标：**",
            "**架构：**",
            "**技术栈：**",
            "## 全局约束",
            "### Task <编号>: <可独立测试的交付项>",
            "**精确文件：**",
            "**接口：**",
            "**测试方式：**",
            "文档同步",
            "## 实施评审策略",
            "最新完整 diff",
            "里程碑评审",
            "## 最终验证",
        ):
            with self.subTest(template="plan", required=required):
                self.assertIn(required, plan_template)
        self.assertNotIn("## Goals", spec_template)
        self.assertNotIn("**Goal:**", plan_template)

    def test_spec_and_plan_templates_use_complete_chinese_frontmatter_contract(self):
        spec_metadata = parse_frontmatter(read("assets/spec-template.md"))
        self.assertEqual(
            {
                "文档类型": "技术规格",
                "主题": "<stable-topic>",
                "需求文档": "<repository-relative-requirements-path>",
                "需求主题": "<stable-topic>",
                "需求范围": "<产品-阶段-或-功能>",
                "需求理解置信度": "<95-100-整数>",
                "需求理解确认": "已确认",
                "需求文档用户批准": "已批准",
                "需求文档独立评审": "已通过",
                "技术规格门禁": "已开放",
                "技术规格用户批准": "待批准",
                "技术规格独立评审": "待评审",
            },
            spec_metadata,
        )
        plan_metadata = parse_frontmatter(read("assets/plan-template.md"))
        self.assertEqual(
            {
                "文档类型": "实施计划",
                "主题": "<stable-topic>",
                "技术规格": "<repository-relative-spec-path>",
                "技术规格用户批准": "<待批准-或-已批准>",
                "评审模式": "<技术包-或-逐级>",
                "计划评审状态": "待评审",
            },
            plan_metadata,
        )
        contracts = read("references/document-contracts.md")
        for required in (
            "chinese-current",
            "english-legacy",
            "技术规格批准日期",
            "技术规格独立评审角色",
            "技术规格独立评审日期",
            "计划评审角色",
            "计划评审日期",
        ):
            with self.subTest(required=required):
                self.assertIn(required, contracts)

    def test_existing_english_documents_keep_their_schema(self):
        contracts = read("references/document-contracts.md").casefold()
        for required in (
            "english-legacy",
            "existing spec",
            "existing plan",
            "same schema",
            "no implicit migration",
            "do not convert",
            "review_status",
            "independent_review",
        ):
            with self.subTest(required=required):
                self.assertIn(required, contracts)

    def test_authoring_write_outcomes_require_readback_reconciliation(self):
        contracts = read("references/document-contracts.md").casefold()
        for required in (
            "target path already exists",
            "precondition",
            "confirmed not applied",
            "completion result is uncertain",
            "read the target back",
            "exact expected content",
            "original content",
            "partially changed",
            "do not repeat the write",
            "do not use partial approval",
        ):
            with self.subTest(required=required):
                self.assertIn(required, contracts)

    def test_mixed_localized_spec_blocks_plan(self):
        text = (
            read("SKILL.md")
            + read("references/document-contracts.md")
            + read("references/review-and-handoff.md")
        ).casefold()
        for required in (
            "mixed schema",
            "semantic duplicate",
            "malformed",
            "unsupported",
            "complete chinese-current spec",
            "do not create the plan",
            "implementation_gate",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_approved_upstream_handoff_preserves_reliable_default_paths(self):
        text = (
            read("SKILL.md")
            + read("references/discovery-and-clarification.md")
            + read("references/review-and-handoff.md")
        ).casefold()
        for required in (
            "explicit eight-field handoff",
            "requirements_path",
            "requirements_topic",
            "requirements_scope",
            "before the spec or plan exists",
            "reliable default absolute path",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_approved_plan_validates_snapshot_before_session_routing(self):
        text = (read("SKILL.md") + read("references/review-and-handoff.md")).casefold()
        for required in (
            "implementation_gate",
            "validate the complete fourteen-field handoff",
            "freeze one snapshot",
            "generating-development-prompts",
            "runtime-exposed skill capability",
            "same session",
            "capability gap",
            "same fourteen-field snapshot",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)
        self.assertIn("do not route when", text)

    def test_downstream_prd_revalidation_failure_keeps_full_handoff(self):
        text = read("references/review-and-handoff.md").casefold()
        for required in (
            "after this workflow has been selected",
            "revalidation fails",
            "complete fourteen-field handoff",
            "requirements_independent_review",
            "unknown",
            "reliably selected spec and plan paths",
            "implementation_gate: blocked",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_routing_does_not_depend_on_sibling_source_or_installation_paths(self):
        text = (read("SKILL.md") + read("references/review-and-handoff.md")).casefold()
        for required in (
            "do not read sibling skill source",
            "do not inspect sibling skill installation",
            "runtime-exposed skill capability",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_handoff_record_emits_one_value_per_field(self):
        text = read("references/review-and-handoff.md").casefold()
        self.assertIn("reference-only alternatives", text)
        self.assertIn("emit exactly one allowed value", text)
        self.assertIn("never copy the `|`", text)
        self.assertIn("do not repeat any fixed handoff field label", text)
        self.assertIn("plain text, not a markdown code fence", text)
        self.assertIn("last non-empty line", text)

    def test_material_ambiguity_stops_before_document_or_review_work(self):
        text = (
            read("SKILL.md") + read("references/discovery-and-clarification.md")
        ).casefold()
        for required in (
            "one to three",
            "ask only one decisive question",
            "do not write or review either document",
            "complete compact renderer input",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_runtime_contract_forbids_implementation_and_external_side_effects(self):
        text = (read("SKILL.md") + read("references/review-and-handoff.md")).casefold()
        for required in (
            "do not implement target code",
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

    def test_approved_prd_is_required_before_spec_creation(self):
        text = (
            read("SKILL.md")
            + read("references/discovery-and-clarification.md")
            + read("references/document-contracts.md")
        ).casefold()
        for required in (
            "approved product requirements",
            "inspect_product_requirements.py",
            "expected topic",
            "expected scope",
            "do not create or materially modify the spec",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_fixed_handoff_contains_requirements_and_existing_fields(self):
        text = read("references/review-and-handoff.md").casefold()
        for field in (
            "requirements_path",
            "requirements_topic",
            "requirements_scope",
            "requirements_understanding_confidence",
            "requirements_understanding_confirmation",
            "requirements_user_approval",
            "requirements_independent_review",
            "specification_gate",
            "spec_path",
            "spec_user_approval",
            "spec_independent_review",
            "plan_path",
            "plan_review_status",
            "implementation_gate",
        ):
            with self.subTest(field=field):
                self.assertIn(f"{field}:", text)
        self.assertIn("fourteen-field", text)

    def test_fixed_handoff_has_exact_order_and_spec_state_values(self):
        text = read("references/review-and-handoff.md")
        match = re.search(r"```text\n(.*?)\n```", text, re.DOTALL)
        self.assertIsNotNone(match)
        lines = match.group(1).splitlines()
        self.assertEqual(
            [
                "requirements_path",
                "requirements_topic",
                "requirements_scope",
                "requirements_understanding_confidence",
                "requirements_understanding_confirmation",
                "requirements_user_approval",
                "requirements_independent_review",
                "specification_gate",
                "spec_path",
                "spec_user_approval",
                "spec_independent_review",
                "plan_path",
                "plan_review_status",
                "implementation_gate",
            ],
            [line.split(":", 1)[0] for line in lines],
        )
        self.assertEqual(
            "spec_user_approval: pending | approved",
            lines[9],
        )
        self.assertEqual(
            "spec_independent_review: pending | approved",
            lines[10],
        )

    def test_user_visible_chinese_handoff_has_exact_fourteen_field_order(self):
        blocks = fenced_text_blocks(read("references/review-and-handoff.md"))
        self.assertGreaterEqual(len(blocks), 2)
        labels = (
            "需求文档",
            "需求主题",
            "需求范围",
            "需求理解置信度",
            "需求理解确认",
            "需求文档用户批准",
            "需求文档独立评审",
            "技术规格门禁",
            "技术规格",
            "技术规格用户批准",
            "技术规格独立评审",
            "实施计划",
            "计划评审状态",
            "实施门禁",
        )
        self.assertEqual(list(labels), [line.split("：", 1)[0] for line in blocks[1]])
        self.assertTrue(all("：" in line and not line.startswith(" ") for line in blocks[1]))
        text = read("references/review-and-handoff.md").casefold()
        self.assertIn("one authoritative chinese fourteen-field view", text)
        self.assertIn("last non-empty line", text)

    def test_user_visible_values_cover_unknown_and_plan_context_without_changing_spec_schema(self):
        text = read("references/review-and-handoff.md")
        for required in (
            "`product` → `产品`",
            "`phase` → `阶段`",
            "`feature` → `功能`",
            "`pending` → `待确认`",
            "`approved` → `已确认`",
            "`pending` → `待批准`",
            "`approved` → `已批准`",
            "`pending` → `待评审`",
            "`approved` → `已通过`",
            "`blocked` → `未开放`",
            "`open` → `已开放`",
            "`plan_path: null` + `plan_review_status: not-approved` → `计划评审状态：未开始`",
            "existing `plan_path` + `plan_review_status: not-approved` → `计划评审状态：未通过`",
            "existing `plan_path` + `plan_review_status: approved` → `计划评审状态：已通过`",
            "existing `plan_path` + `plan_review_status: unknown` → `计划评审状态：未知`",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)
        for field in (
            "requirements_topic",
            "requirements_scope",
            "requirements_understanding_confidence",
            "requirements_understanding_confirmation",
            "requirements_user_approval",
            "requirements_independent_review",
        ):
            with self.subTest(field=field):
                self.assertRegex(text, rf"`{field}`[^\n]*`unknown`[^\n]*`未知`")
        self.assertIn("`spec_user_approval` and `spec_independent_review` accept only `pending | approved`", text)
        self.assertIn("`spec_path: null` → `技术规格：未确定`", text)
        self.assertIn("`plan_path: null` → `实施计划：尚未创建`", text)
        lowered = text.casefold()
        self.assertIn("canonical english snapshot", lowered)
        self.assertIn("legacy english handoff", lowered)
        self.assertIn("do not reverse-parse", lowered)

    def test_chinese_view_is_validated_before_routing_and_mapping_failure_is_closed(self):
        text = (read("SKILL.md") + read("references/review-and-handoff.md")).casefold()
        for required in (
            "pre-render",
            "before selecting",
            "before session routing",
            "field count",
            "field order",
            "mapping is complete and unique",
            "do not emit a partial chinese view",
            "do not fall back to the english user-visible handoff",
            "do not select the routing capability",
            "retry from the preserved canonical snapshot",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_renderer_failure_is_the_status_suffix_exception_and_reports_a_locator(self):
        text = (read("SKILL.md") + read("references/review-and-handoff.md")).casefold()
        for required in (
            "explicit fail-closed exception",
            "deterministic chinese blocker",
            "does not append a status view",
            "stop the current automatic handoff",
            "identify the unmapped field or failed integrity condition",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_technical_spec_includes_interfaces_and_data_model_when_relevant(self):
        text = (
            read("references/document-contracts.md") + read("assets/spec-template.md")
        ).casefold()
        for required in (
            "api",
            "technical interfaces",
            "data model",
            "entity relationships",
            "migration boundaries",
            "state transitions",
            "consistency",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_templates_start_pending_and_plan_is_parser_compatible(self):
        spec_template = read("assets/spec-template.md")
        plan_template = read("assets/plan-template.md")
        self.assertTrue(spec_template.startswith("---\n"))
        spec_metadata = parse_frontmatter(spec_template)
        self.assertEqual("待批准", spec_metadata["技术规格用户批准"])
        self.assertEqual("待评审", spec_metadata["技术规格独立评审"])
        self.assertEqual("已批准", spec_metadata["需求文档用户批准"])
        self.assertTrue(plan_template.startswith("---\n"))
        self.assertIn("计划评审状态: 待评审", plan_template)
        self.assertIn("技术规格:", plan_template)
        self.assertIn("评审模式:", plan_template)

        self.assertEqual("待评审", parse_frontmatter(plan_template)["计划评审状态"])
        approved = plan_template.replace(
            "计划评审状态: 待评审", "计划评审状态: 已通过", 1
        )
        self.assertEqual("已通过", parse_frontmatter(approved)["计划评审状态"])

    def test_plan_template_requires_docs_and_risk_batched_review(self):
        template = read("assets/plan-template.md").casefold()
        for required in (
            "精确文件",
            "接口",
            "测试方式",
            "当批准的技术规格或仓库规则要求 tdd",
            "文档同步",
            "实施评审策略",
            "不得仅因任务数量",
            "最新完整 diff",
            "里程碑评审",
        ):
            with self.subTest(required=required):
                self.assertIn(required, template)
        self.assertNotIn("任务级独立评审", template)

    def test_spec_and_plan_separate_critical_e2e_from_target_user_acceptance(self):
        contracts = read("references/document-contracts.md").casefold()
        spec_template = read("assets/spec-template.md").casefold()
        plan_template = read("assets/plan-template.md").casefold()

        for required in (
            "repeatable cross-layer technical closure",
            "minimum critical e2e",
            "target-user manual acceptance",
            "usability",
            "content quality",
            "visual experience",
            "acting as the named target-user cohort",
            "developer or reviewer may participate only if",
            "role alone",
            "manual acceptance cannot replace critical technical regression",
            "e2e cannot claim product-experience validation",
        ):
            with self.subTest(contract=required):
                self.assertIn(required, contracts)

        for required in (
            "验收类型与证据",
            "关键 e2e",
            "目标用户人工验收",
            "可重复验证的跨层技术闭环",
            "易用性、内容质量和视觉体验",
            "不得互相替代",
        ):
            with self.subTest(spec_template=required):
                self.assertIn(required, spec_template)

        for required in (
            "关键 e2e 场景",
            "人工验收场景",
            "逐条列出",
            "人工验收不能替代关键技术回归",
            "e2e 不能冒充产品体验验证",
        ):
            with self.subTest(plan_template=required):
                self.assertIn(required, plan_template)

    def test_spec_and_plan_keep_technical_detail_proportional_to_approved_requirements(self):
        contracts = read("references/document-contracts.md").casefold()
        spec_template = read("assets/spec-template.md").casefold()
        plan_template = read("assets/plan-template.md").casefold()

        for required in (
            "approved requirements are the product-scope ceiling",
            "minimum technical decisions",
            "confirmed risk",
            "group outcomes that require the same caller action and produce the same consistency effect",
            "do not enumerate speculative",
            "requirement or confirmed risk",
            "minimum sufficient validation",
            "do not add or replace approved states, identifiers, interfaces, errors, or validation scope",
        ):
            with self.subTest(required=required):
                self.assertIn(required, contracts)

        for required in (
            "关键结果与失败边界（按需）",
            "需求或已确认风险依据",
            "调用方动作",
            "数据或一致性影响",
            "需求与验证追踪",
            "最小技术保证",
            "最小充分验证",
        ):
            with self.subTest(required=required):
                self.assertIn(required, spec_template)
        for forbidden in (
            "每个结果单独一行",
            "不得在同一行合并",
            "保证 id",
            "结果 id",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, spec_template)

        for required in (
            "需求与风险追踪",
            "需求或风险依据",
            "最小实现",
            "定向验证",
            "不得为了追踪而新增",
            "不得新增或替换已批准的状态、标识符、接口、错误分类或验证范围",
        ):
            with self.subTest(required=required):
                self.assertIn(required, plan_template)
        for forbidden in (
            "覆盖保证",
            "覆盖结果",
            "无遗漏保证",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, plan_template)

    def test_review_uses_approved_prd_as_scope_ceiling_and_rechecks_only_the_delta(self):
        review = (
            read("SKILL.md") + read("references/review-and-handoff.md")
        ).casefold()
        for required in (
            "approved prd is the product-scope ceiling",
            "classify each finding",
            "`blocking_in_scope`",
            "`scope_change_required`",
            "`non_blocking_note`",
            "minimum in-scope correction",
            "prior blocking findings",
            "changed regions",
            "regressions caused by the correction",
            "do not fix every finding",
        ):
            with self.subTest(required=required):
                self.assertIn(required, review)

    def test_security_detail_is_required_only_when_relevant(self):
        contracts = read("references/document-contracts.md").casefold()
        template = read("assets/spec-template.md").casefold()
        self.assertIn("only when the requested feature actually touches", contracts)
        self.assertIn("仅在功能需要时", template)
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

    def test_references_are_loaded_progressively_by_stage(self):
        skill = read("SKILL.md").casefold()
        discovery = read("references/discovery-and-clarification.md").casefold()
        self.assertIn("first read only", skill)
        self.assertIn("references/discovery-and-clarification.md", skill)
        self.assertIn("before the first spec or plan write", skill)
        self.assertIn("references/document-contracts.md", skill)
        self.assertIn("before a blocked reply", skill)
        self.assertIn("references/review-and-handoff.md", skill)
        self.assertNotIn("read these files completely before the first substantive reply", skill)
        self.assertIn("ordinary clarification does not load `review-and-handoff.md`", discovery)
        self.assertIn("complete compact renderer input", discovery)
        self.assertIn("requirements_understanding_confidence", discovery)
        self.assertIn("implementation_gate", discovery)
        self.assertIn("plan_review_status: not-approved", discovery)
        self.assertIn("`pending` is not an allowed plan-review value", discovery)
        self.assertIn("reliable independently of a still-missing requirements path", discovery)
        self.assertIn("preserve that topic in canonical state", discovery)
        self.assertIn("never use a shell heredoc", discovery)
        self.assertIn("shell-quote it as one inert argument", discovery)
        self.assertNotIn("end the reply using the classified view from `review-and-handoff.md`", discovery)

    def test_questions_are_dependency_aware_and_capped_at_three(self):
        text = (
            read("SKILL.md") + read("references/discovery-and-clarification.md")
        ).casefold()
        for phrase in (
            "one to three",
            "independent questions",
            "applicability",
            "ask only one decisive question",
            "partial answers",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_reply_classification_keeps_spec_approval_and_progress_full(self):
        text = (read("SKILL.md") + read("references/review-and-handoff.md")).casefold()
        for phrase in (
            "ordinary-clarification",
            "exactly three consecutive lines",
            "checkpoint",
            "spec approval",
            "blocked",
            "routing",
            "progress-only",
            "conservatively use full",
            "scripts/render_handoff.py",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
