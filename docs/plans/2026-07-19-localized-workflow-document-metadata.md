---
document_type: implementation-plan
topic: localized-workflow-document-metadata
spec_path: docs/specs/2026-07-19-localized-workflow-document-metadata-design.md
spec_user_approval: approved
review_status: approved
reviewer: spec-plan-reviewer
reviewed_at: 2026-07-19
---

# 工作流文档元数据中文化实施计划

**目标：** 让本功能生效后从头创建的 PRD、技术规格和实施计划使用完整中文 frontmatter，同时保持历史英文文档、英文 canonical handoff、门禁真值表和现有 CLI/JSON 兼容。

**架构：** 三个 Skill 各自在运行时边界内维护最小 alias normalization。Authoring Skill 按新建/既有文档选择中文或历史英文 schema；PRD inspector 在 raw frontmatter 阶段归一化；prompt discovery 对完整中文 plan 校验固定字段和生命周期，同时保留英文 review-only/header 兼容。Skill 之间不共享运行时模块。

**技术栈：** Markdown/YAML frontmatter、Python 3.9/3.14、`unittest`、现有 isolated evaluation runner、仓库 validator 与官方 Skill/plugin validator；不新增依赖。

## 全局约束

- 开始生产修改前使用 `skill-creator` 完整读取并遵循当前 Skill 维护流程，同时执行 `managing-agents-rules` 的项目根规则前置检查；本计划不授权修改真实安装副本。
- 当前 worktree 已包含上一批通过评审但未提交的 Skill、评估、文档和 validator 变更。所有任务基于当前内容增量修改，不回滚、覆盖或重新归因已有变更。
- 当前 PRD、技术规格和本计划均创建于功能实现前，属于 `english-legacy`，实施时保持英文 frontmatter，不以本功能为由迁移。
- 只有功能生效后从头创建的 PRD/spec/plan 写中文 schema；既有英文文档在正文维护、批准失效、批准和重新评审时继续写英文。
- 英文 requirements 八字段、workflow 十四字段、renderer 字节、gate truth table、CLI 参数和 JSON 输出字段不变；不修改三个 `render_handoff.py`。
- 中文 key 只在 raw frontmatter 阶段通过精确白名单接受；未知 Unicode key、mixed schema、semantic duplicate、malformed 或不受支持值失败关闭。
- Prompt discovery 只对 `chinese-current` plan 要求完整字段和一致生命周期；`english-legacy` frontmatter 保持 review-only，legacy header 继续只接受英文。
- 严格执行 RED→GREEN：每个受影响 Skill 先新增失败合同/前向场景并保存 RED，再修改该 Skill 的生产内容；不得批量完成三个 Skill 后补写证据。
- `implemented` 且 GREEN bundle 尚未完成时只做上述 JSON stage/review 断言，不运行默认 strict repository validator。每个 Skill 完成 GREEN bundle 后使用对应 Task 中列出的精确 `scripts/check.py --skill` 命令；该入口按 registry stage 自动采用 evidence-only freshness。review metadata 写回并恢复 `review-approved` 后，再运行 strict targeted/full 门。
- 每项任务保留批准规格的 Outcome ID、Guarantee ID、精确测试、命令和可观察断言。任何范围、公共契约或兼容边界变化先停止并重新请求用户批准。
- 不添加依赖，不启动服务，不操作用户可见 task/thread，不安装到真实 `CODEX_HOME`，不 commit、push、tag、release。

## 实施验证偏差（2026-07-19）

用户在实施中批准最小收尾：不再新增或补跑本计划列出的 agent-driven evaluation case `22`～`26` 与 `07`，不为绕过平台外发限制修改 evaluation runner、freshness validator 或 provider 配置。对应行为改由确定性 parser/contract/cross-skill 测试、受影响范围回归和同一名独立 `skill-reviewer` 的完整 diff 评审与复审覆盖。交付不得把既有或并发遗留 evaluation 输出表述为本次新鲜 GREEN 证据；统一 freshness 门若仅因这些未形成的 evaluation bundle 失败，按已知未验证项如实报告。

### Task 1: PRD authoring 中文 schema 与历史英文写回

**精确文件：**

- Modify: `skills/creating-product-requirements/references/document-contract.md`
- Modify: `skills/creating-product-requirements/assets/prd-template.md`
- Modify: `skills/creating-product-requirements/tests/test_skill_contract.py`
- Modify: `tests/test_repository_contract.py`
- Create: `evaluations/creating-product-requirements/cases/17-localized-prd-approval-writeback.md`
- Create: `evaluations/creating-product-requirements/cases/18-legacy-english-prd-rereview.md`
- Create: `evaluations/creating-product-requirements/cases/19-localized-prd-write-reconciliation.md`
- Create: `evaluations/creating-product-requirements/fixtures/17-localized-prd-approval-writeback/README.md`
- Create: `evaluations/creating-product-requirements/fixtures/17-localized-prd-approval-writeback/docs/requirements/2026-07-19-localized-metadata.md`
- Create: `evaluations/creating-product-requirements/fixtures/18-legacy-english-prd-rereview/README.md`
- Create: `evaluations/creating-product-requirements/fixtures/18-legacy-english-prd-rereview/docs/requirements/2026-07-19-localized-metadata.md`
- Create: `evaluations/creating-product-requirements/fixtures/19-localized-prd-write-reconciliation/README.md`
- Create: `evaluations/creating-product-requirements/fixtures/19-localized-prd-write-reconciliation/docs/requirements/2026-07-19-localized-metadata.md`
- Modify: `evaluations/creating-product-requirements/rubric.json`
- Create: `evaluations/creating-product-requirements/migration-red/17-output.md`
- Create: `evaluations/creating-product-requirements/migration-red/18-output.md`
- Create: `evaluations/creating-product-requirements/migration-red/19-output.md`
- Modify: `evaluations/creating-product-requirements/migration-red/result.json`
- Create: `evaluations/creating-product-requirements/green/17-output.md`
- Create: `evaluations/creating-product-requirements/green/18-output.md`
- Create: `evaluations/creating-product-requirements/green/19-output.md`
- Modify: `evaluations/creating-product-requirements/green/result.json`
- Modify: `evaluations/registry.json`

**接口：**

- Consumes: 已批准 PRD 的 PRD 字段/生命周期映射，现有 stable topic、理解确认、独立评审和用户批准门禁。
- Produces: 新 PRD 单套中文 schema；existing english-legacy PRD 同 schema 写回；O-01、O-12～O-19、O-21、O-22 的 authoring 合同。

**保证追踪：**

- 覆盖保证：`G-01`、`G-05`、`G-06`、`G-07`。
- 覆盖结果：`O-01`、`O-11`、`O-12`～`O-19`、`O-21`、`O-22` 中适用于 PRD authoring 的分支。
- 精确测试：`CreatingProductRequirementsContractTests.test_prd_template_uses_complete_chinese_frontmatter_contract`、`test_existing_english_documents_keep_their_schema`、`test_authoring_write_outcomes_require_readback_reconciliation`、`RepositoryContractTests.test_localized_document_frontmatter_and_canonical_handoff_contracts_are_separate`，以及 cases `17`～`19`。
- 可观察断言：新模板只含完整中文 PRD keys/values；中文批准写回保持中文并保留技术值；历史英文重评保持英文；已有目标/前置失败无写入；未知写入先重读并分成已应用、未应用、仍未知。

**测试方式：** 先补合同断言和三个 cases，运行当前 Skill 取得 RED；再修改 document contract/template，取得单元测试与新鲜 GREEN。

- [ ] RED：新增上述三个合同测试、跨 Skill 分离测试、cases、fixtures 和 rubric 判据；生产文件保持不变。
- [ ] Verify RED：先让 `RepositoryContractTests.test_localized_document_frontmatter_and_canonical_handoff_contracts_are_separate` 只固定 Task 1 的 PRD 中文 schema、english-legacy 与英文 canonical 分离边界；运行 `.venv/bin/python tests/test_repository_contract.py RepositoryContractTests.test_localized_document_frontmatter_and_canonical_handoff_contracts_are_separate`，预期因 PRD production 尚未修改而失败。
- [ ] Verify RED：运行 `.venv/bin/python skills/creating-product-requirements/tests/test_skill_contract.py CreatingProductRequirementsContractTests.test_prd_template_uses_complete_chinese_frontmatter_contract CreatingProductRequirementsContractTests.test_existing_english_documents_keep_their_schema CreatingProductRequirementsContractTests.test_authoring_write_outcomes_require_readback_reconciliation`；预期因英文模板和缺失 schema/writeback 合同失败。
- [ ] Verify RED：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase current-skill-red --case evaluations/creating-product-requirements/cases/17-localized-prd-approval-writeback.md --skill-dir skills/creating-product-requirements --output-root work/evaluations/creating-product-requirements/current-red-17`；预期中文批准写回缺失。
- [ ] Verify RED：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase current-skill-red --case evaluations/creating-product-requirements/cases/18-legacy-english-prd-rereview.md --skill-dir skills/creating-product-requirements --output-root work/evaluations/creating-product-requirements/current-red-18`；预期历史英文 schema 保持合同缺失。
- [ ] Verify RED：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase current-skill-red --case evaluations/creating-product-requirements/cases/19-localized-prd-write-reconciliation.md --skill-dir skills/creating-product-requirements --output-root work/evaluations/creating-product-requirements/current-red-19`；预期未知写入核对分支缺失。
- [ ] 证据失效：在首次修改 `document-contract.md` 或 `prd-template.md` 前，将 `evaluations/registry.json` 中 `creating-product-requirements` 的 stage 改为 `implemented`；把其 `green/result.json` 的 `review_status` 改为 `pending` 并移除旧 `reviewer`、`reviewed_at`，保留其它 Skill 当前状态。
- [ ] 验证阶段：运行 `.venv/bin/python -c 'import json; from pathlib import Path; registry=json.loads(Path("evaluations/registry.json").read_text()); green=json.loads(Path("evaluations/creating-product-requirements/green/result.json").read_text()); assert registry["skills"]["creating-product-requirements"]["stage"] == "implemented"; assert green["review_status"] == "pending"; assert "reviewer" not in green and "reviewed_at" not in green'`；预期只确认 stage/review invalidation 已写对。此时 GREEN bundle 尚未完成，不运行默认 strict validator。
- [ ] GREEN：更新 `document-contract.md` 与 `prd-template.md`，写明新建中文、既有英文、同 schema 写回及 `O-13`～`O-19` 核对分支；不修改 Skill trigger 或 UI metadata。
- [ ] Verify GREEN：运行上述单元测试命令；预期全部通过。
- [ ] Verify GREEN：重跑 `.venv/bin/python tests/test_repository_contract.py RepositoryContractTests.test_localized_document_frontmatter_and_canonical_handoff_contracts_are_separate`；预期 Task 1 已固定的边界通过。
- [ ] Verify GREEN：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase green --case evaluations/creating-product-requirements/cases/17-localized-prd-approval-writeback.md --skill-dir skills/creating-product-requirements --output-root work/evaluations/creating-product-requirements/green-17`；预期中文生命周期写回通过且 canonical 不变。
- [ ] Verify GREEN：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase green --case evaluations/creating-product-requirements/cases/18-legacy-english-prd-rereview.md --skill-dir skills/creating-product-requirements --output-root work/evaluations/creating-product-requirements/green-18`；预期英文文档保持原 schema。
- [ ] Verify GREEN：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase green --case evaluations/creating-product-requirements/cases/19-localized-prd-write-reconciliation.md --skill-dir skills/creating-product-requirements --output-root work/evaluations/creating-product-requirements/green-19`；预期已应用、未应用、仍未知三分支可观察且不重复写入。
- [ ] REFACTOR：移除重复表述，保持详细 schema 在一层 reference、确定性模板在 asset；重跑 `.venv/bin/python scripts/check.py --skill creating-product-requirements`。
- [ ] 文档同步：本任务只更新 Skill 内 contract/evidence；公共文档留到 Task 4 统一同步。

### Task 2: Spec/plan authoring 与 PRD raw-stage inspector

**精确文件：**

- Modify: `skills/creating-development-specs-and-plans/SKILL.md`
- Modify: `skills/creating-development-specs-and-plans/references/document-contracts.md`
- Modify: `skills/creating-development-specs-and-plans/references/review-and-handoff.md`
- Modify: `skills/creating-development-specs-and-plans/assets/spec-template.md`
- Modify: `skills/creating-development-specs-and-plans/assets/plan-template.md`
- Modify: `skills/creating-development-specs-and-plans/scripts/inspect_product_requirements.py`
- Modify: `skills/creating-development-specs-and-plans/tests/test_inspect_product_requirements.py`
- Modify: `skills/creating-development-specs-and-plans/tests/test_skill_contract.py`
- Modify: `tests/test_repository_contract.py`
- Create: `evaluations/creating-development-specs-and-plans/cases/22-localized-spec-plan-review-writeback.md`
- Create: `evaluations/creating-development-specs-and-plans/cases/23-legacy-english-spec-rereview.md`
- Create: `evaluations/creating-development-specs-and-plans/cases/24-legacy-english-plan-rereview.md`
- Create: `evaluations/creating-development-specs-and-plans/cases/25-localized-spec-metadata-fail-closed.md`
- Create: `evaluations/creating-development-specs-and-plans/cases/26-localized-spec-plan-write-reconciliation.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/22-localized-spec-plan-review-writeback/README.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/22-localized-spec-plan-review-writeback/docs/requirements/2026-07-19-localized-metadata.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/22-localized-spec-plan-review-writeback/docs/specs/2026-07-19-localized-metadata-design.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/22-localized-spec-plan-review-writeback/docs/plans/2026-07-19-localized-metadata.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/23-legacy-english-spec-rereview/README.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/23-legacy-english-spec-rereview/docs/requirements/2026-07-19-localized-metadata.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/23-legacy-english-spec-rereview/docs/specs/2026-07-19-localized-metadata-design.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/24-legacy-english-plan-rereview/README.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/24-legacy-english-plan-rereview/docs/requirements/2026-07-19-localized-metadata.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/24-legacy-english-plan-rereview/docs/specs/2026-07-19-localized-metadata-design.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/24-legacy-english-plan-rereview/docs/plans/2026-07-19-localized-metadata.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/25-localized-spec-metadata-fail-closed/README.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/25-localized-spec-metadata-fail-closed/docs/requirements/2026-07-19-localized-metadata.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/25-localized-spec-metadata-fail-closed/docs/specs/2026-07-19-localized-metadata-design.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/26-localized-spec-plan-write-reconciliation/README.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/26-localized-spec-plan-write-reconciliation/docs/requirements/2026-07-19-localized-metadata.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/26-localized-spec-plan-write-reconciliation/docs/specs/2026-07-19-localized-metadata-design.md`
- Modify: `evaluations/creating-development-specs-and-plans/rubric.json`
- Create: `evaluations/creating-development-specs-and-plans/migration-red/22-output.md`
- Create: `evaluations/creating-development-specs-and-plans/migration-red/23-output.md`
- Create: `evaluations/creating-development-specs-and-plans/migration-red/24-output.md`
- Create: `evaluations/creating-development-specs-and-plans/migration-red/25-output.md`
- Create: `evaluations/creating-development-specs-and-plans/migration-red/26-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/migration-red/result.json`
- Create: `evaluations/creating-development-specs-and-plans/green/22-output.md`
- Create: `evaluations/creating-development-specs-and-plans/green/23-output.md`
- Create: `evaluations/creating-development-specs-and-plans/green/24-output.md`
- Create: `evaluations/creating-development-specs-and-plans/green/25-output.md`
- Create: `evaluations/creating-development-specs-and-plans/green/26-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/result.json`
- Modify: `evaluations/registry.json`

**接口：**

- Consumes: 完整中文或历史英文 PRD/spec/plan frontmatter、显式 PRD topic/scope、当前英文 inspector JSON 和十四字段 canonical。
- Produces: raw-stage PRD key/value normalization；新 spec/plan 中文模板；existing english-legacy 同 schema 写回；不可靠中文 spec 阻断 plan。

**保证追踪：**

- 覆盖保证：`G-01`、`G-02`、`G-03`、`G-05`、`G-06`、`G-07`、`G-08`。
- 覆盖结果：`O-02`～`O-06`、`O-11`～`O-22` 中适用于 PRD inspector 与 spec/plan workflow 的分支。
- 精确测试：`InspectProductRequirementsTests.test_approved_chinese_prd_opens_gate`、`test_legacy_english_prd_still_opens_gate`、`test_mixed_or_duplicate_localized_prd_is_unknown`；`CreatingSpecsAndPlansContractTests.test_spec_and_plan_templates_use_complete_chinese_frontmatter_contract`、`test_existing_english_documents_keep_their_schema`、`test_authoring_write_outcomes_require_readback_reconciliation`、`test_mixed_localized_spec_blocks_plan`；cases `22`～`26`。
- 可观察断言：中文/英文 PRD 得到相同 approved/open JSON；unknown Unicode、mixed/duplicate/unsupported 失败关闭；新模板完整中文；中文和英文 lifecycle 写回保持原 schema；残缺中文 spec 不创建 plan；持久化未知先核对。

**测试方式：** 先新增 parser/contract tests 与五个 cases 取得 RED，再修改 raw parser、Skill contracts 和模板；不改变 inspector CLI/JSON 或 renderer。

- [ ] RED：新增上述 parser/contract tests、cases、fixtures 和 rubric 判据；保留现有生产代码。
- [ ] RED：在 `RepositoryContractTests.test_localized_document_frontmatter_and_canonical_handoff_contracts_are_separate` 中先扩展 spec/plan schema 与 PRD inspector 边界；运行 `.venv/bin/python tests/test_repository_contract.py RepositoryContractTests.test_localized_document_frontmatter_and_canonical_handoff_contracts_are_separate`，预期因 Task 2 production 尚未修改而失败。
- [ ] Verify RED：运行 `.venv/bin/python skills/creating-development-specs-and-plans/tests/test_inspect_product_requirements.py InspectProductRequirementsTests.test_approved_chinese_prd_opens_gate InspectProductRequirementsTests.test_legacy_english_prd_still_opens_gate InspectProductRequirementsTests.test_mixed_or_duplicate_localized_prd_is_unknown`；预期中文与 mixed-schema cases 失败，既有英文 case 继续通过。
- [ ] Verify RED：运行 `.venv/bin/python skills/creating-development-specs-and-plans/tests/test_skill_contract.py CreatingSpecsAndPlansContractTests.test_spec_and_plan_templates_use_complete_chinese_frontmatter_contract CreatingSpecsAndPlansContractTests.test_existing_english_documents_keep_their_schema CreatingSpecsAndPlansContractTests.test_authoring_write_outcomes_require_readback_reconciliation CreatingSpecsAndPlansContractTests.test_mixed_localized_spec_blocks_plan`；预期因英文模板和缺失双 schema 合同失败。
- [ ] Verify RED：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase current-skill-red --case evaluations/creating-development-specs-and-plans/cases/22-localized-spec-plan-review-writeback.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/current-red-22`；预期中文 spec/plan lifecycle 写回缺失。
- [ ] Verify RED：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase current-skill-red --case evaluations/creating-development-specs-and-plans/cases/23-legacy-english-spec-rereview.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/current-red-23`；预期英文 spec 重评保持合同缺失。
- [ ] Verify RED：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase current-skill-red --case evaluations/creating-development-specs-and-plans/cases/24-legacy-english-plan-rereview.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/current-red-24`；预期英文 plan 重评保持合同缺失。
- [ ] Verify RED：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase current-skill-red --case evaluations/creating-development-specs-and-plans/cases/25-localized-spec-metadata-fail-closed.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/current-red-25`；预期不可靠中文 spec 未被确定性阻断。
- [ ] Verify RED：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase current-skill-red --case evaluations/creating-development-specs-and-plans/cases/26-localized-spec-plan-write-reconciliation.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/current-red-26`；预期写入核对三分支缺失。
- [ ] 证据失效：在首次修改 Skill production 前，将 `evaluations/registry.json` 中 `creating-development-specs-and-plans` 的 stage 改为 `implemented`；把其 `green/result.json` 的 `review_status` 改为 `pending` 并移除旧 `reviewer`、`reviewed_at`，不改变其它 Skill 的真实状态。
- [ ] 验证阶段：运行 `.venv/bin/python -c 'import json; from pathlib import Path; registry=json.loads(Path("evaluations/registry.json").read_text()); green=json.loads(Path("evaluations/creating-development-specs-and-plans/green/result.json").read_text()); assert registry["skills"]["creating-development-specs-and-plans"]["stage"] == "implemented"; assert green["review_status"] == "pending"; assert "reviewer" not in green and "reviewed_at" not in green'`；预期只确认 stage/review invalidation，尚未形成 GREEN 时不运行默认 strict validator。
- [ ] GREEN：在 raw parser 内仅允许现有 ASCII key 或精确中文白名单，分类 language、归一化 semantic key 后再检测重复；保留未知 ASCII legacy 字段兼容和现有 JSON issues。
- [ ] GREEN：更新 `SKILL.md`、两个 references 与两个 templates，写明中文新建、英文历史写回、spec 输入失败关闭、write/readback 分支；不修改 `render_handoff.py`。
- [ ] Verify GREEN：运行上述两个单元测试命令；预期全部通过，并重跑各自完整 unittest discovery。
- [ ] Verify GREEN：重跑 `.venv/bin/python tests/test_repository_contract.py RepositoryContractTests.test_localized_document_frontmatter_and_canonical_handoff_contracts_are_separate`；预期 Task 1+2 的累计边界通过。
- [ ] Verify GREEN：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase green --case evaluations/creating-development-specs-and-plans/cases/22-localized-spec-plan-review-writeback.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/green-22`；预期中文 spec/plan lifecycle 写回通过。
- [ ] Verify GREEN：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase green --case evaluations/creating-development-specs-and-plans/cases/23-legacy-english-spec-rereview.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/green-23`；预期英文 spec 保持原 schema。
- [ ] Verify GREEN：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase green --case evaluations/creating-development-specs-and-plans/cases/24-legacy-english-plan-rereview.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/green-24`；预期英文 plan 保持原 schema。
- [ ] Verify GREEN：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase green --case evaluations/creating-development-specs-and-plans/cases/25-localized-spec-metadata-fail-closed.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/green-25`；预期 mixed/残缺中文 spec 不创建 plan。
- [ ] Verify GREEN：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase green --case evaluations/creating-development-specs-and-plans/cases/26-localized-spec-plan-write-reconciliation.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/green-26`；预期已应用、未应用、仍未知分支可观察且不采用部分批准。
- [ ] REFACTOR：集中本 Skill 内 alias 表和 normalization，避免分散字符串替换；重跑 `.venv/bin/python scripts/check.py --skill creating-development-specs-and-plans`。
- [ ] 文档同步：本任务只更新 Skill 内 contract/evidence；公共文档留到 Task 4。

### Task 3: Prompt discovery 完整中文 plan 与英文 legacy 兼容

**精确文件：**

- Modify: `skills/generating-development-prompts/references/discovery-policy.md`
- Modify: `skills/generating-development-prompts/scripts/discover_context.py`
- Modify: `skills/generating-development-prompts/tests/test_discover_context.py`
- Modify: `skills/generating-development-prompts/tests/test_skill_contract.py`
- Modify: `tests/test_repository_contract.py`
- Create: `evaluations/generating-development-prompts/cases/07-localized-plan-frontmatter.md`
- Create: `evaluations/generating-development-prompts/fixtures/07-localized-plan-frontmatter/docs/plans/2026-07-17-example.md`
- Modify: `evaluations/generating-development-prompts/rubric.json`
- Create: `evaluations/generating-development-prompts/migration-red/07-output.md`
- Modify: `evaluations/generating-development-prompts/migration-red/result.json`
- Create: `evaluations/generating-development-prompts/green/07-output.md`
- Modify: `evaluations/generating-development-prompts/green/result.json`
- Modify: `evaluations/registry.json`

**接口：**

- Consumes: `chinese-current` plan 完整固定字段/生命周期，english-legacy review-only frontmatter，现有英文 legacy header。
- Produces: 不变的 `documents.plan.review` JSON：`approved | not-approved | unknown`、原 reviewer、原 reviewed_at。

**保证追踪：**

- 覆盖保证：`G-03`、`G-04`、`G-05`。
- 覆盖结果：`O-07`～`O-11` 中 plan discovery 与 canonical 保持分支。
- 精确测试：`DiscoverContextReviewTests.test_chinese_plan_frontmatter_maps_review_lifecycle`、`test_mixed_or_invalid_chinese_plan_metadata_is_unknown`、`test_incomplete_chinese_plan_or_approved_without_review_metadata_is_unknown`、`test_chinese_legacy_header_is_not_accepted`、既有 `test_frontmatter_approved_includes_optional_metadata`；`SkillContractTests.test_discovery_policy_separates_chinese_frontmatter_from_english_header`；case `07`。
- 可观察断言：完整中文已通过→approved，完整中文待评审→not-approved，残缺/混合/非法→unknown，英文 legacy 行为不变，中文 header 仍 unknown，canonical handoff 不变。

**测试方式：** 先写中文 frontmatter、残缺 lifecycle、mixed、header 与 policy tests 取得 RED，再拆分 raw frontmatter/header parser 并实现最小 plan alias normalization。

- [ ] RED：新增上述五个边界测试、policy test、case、fixture overlay 和 rubric 判据；生产脚本/policy 不变。
- [ ] RED：在同一 repository contract test 中先扩展完整中文 plan、英文 review-only、ASCII-only header 和 canonical 分离断言；运行 `.venv/bin/python tests/test_repository_contract.py RepositoryContractTests.test_localized_document_frontmatter_and_canonical_handoff_contracts_are_separate`，预期因 Task 3 production 尚未修改而失败。
- [ ] Verify RED：运行 `.venv/bin/python skills/generating-development-prompts/tests/test_discover_context.py DiscoverContextReviewTests.test_chinese_plan_frontmatter_maps_review_lifecycle DiscoverContextReviewTests.test_mixed_or_invalid_chinese_plan_metadata_is_unknown DiscoverContextReviewTests.test_incomplete_chinese_plan_or_approved_without_review_metadata_is_unknown DiscoverContextReviewTests.test_chinese_legacy_header_is_not_accepted DiscoverContextReviewTests.test_frontmatter_approved_includes_optional_metadata`；预期中文 cases RED，既有英文 case GREEN。
- [ ] Verify RED：运行 `.venv/bin/python skills/generating-development-prompts/tests/test_skill_contract.py SkillContractTests.test_discovery_policy_separates_chinese_frontmatter_from_english_header`；预期 policy 仍只声明英文 frontmatter 而失败。
- [ ] Verify RED：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name generating-development-prompts --phase current-skill-red --case evaluations/generating-development-prompts/cases/07-localized-plan-frontmatter.md --skill-dir skills/generating-development-prompts --output-root work/evaluations/generating-development-prompts/current-red-07`；预期无法从完整中文 plan 得到 approved 或错误接受残缺输入。
- [ ] 证据失效：在首次修改 `discovery-policy.md` 或 `discover_context.py` 前，将 `evaluations/registry.json` 中 `generating-development-prompts` 的 stage 改为 `implemented`；把其 `green/result.json` 的 `review_status` 改为 `pending` 并移除旧 `reviewer`、`reviewed_at`，保留 imported evidence profile 与其它字段。
- [ ] 验证阶段：运行 `.venv/bin/python -c 'import json; from pathlib import Path; registry=json.loads(Path("evaluations/registry.json").read_text()); green=json.loads(Path("evaluations/generating-development-prompts/green/result.json").read_text()); assert registry["skills"]["generating-development-prompts"]["stage"] == "implemented"; assert green["review_status"] == "pending"; assert "reviewer" not in green and "reviewed_at" not in green'`；预期只确认 imported Skill 的 stage/review invalidation，GREEN 完成前不运行默认 strict validator。
- [ ] GREEN：拆分 frontmatter raw parser 与 ASCII-only header parser；只对白名单中文 key 做 classification/normalization；完整校验中文 plan，保留英文 review-only。
- [ ] GREEN：同步 `discovery-policy.md` 的非对称双 schema 与失败关闭合同。
- [ ] Verify GREEN：重跑上述两个单元测试命令；再运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name generating-development-prompts --phase green --case evaluations/generating-development-prompts/cases/07-localized-plan-frontmatter.md --skill-dir skills/generating-development-prompts --output-root work/evaluations/generating-development-prompts/green-07`；预期所有断言和 case 通过，JSON shape/renderer 不变。
- [ ] Verify GREEN：重跑 `.venv/bin/python tests/test_repository_contract.py RepositoryContractTests.test_localized_document_frontmatter_and_canonical_handoff_contracts_are_separate`；预期三 Skill 累计边界全部通过。
- [ ] REFACTOR：保持 alias/value maps 局部、确定性且不与其它 Skill import；重跑 `.venv/bin/python scripts/check.py --skill generating-development-prompts`。
- [ ] 文档同步：本任务只更新 Skill 内 policy/evidence；公共文档留到 Task 4。

### Task 4: 跨 Skill 契约、证据、双版本验证与最终评审

**精确文件：**

- Verify only: `tests/test_repository_contract.py`
- Modify: `docs/workflow.md`
- Modify: `CHANGELOG.md`
- Modify: `evaluations/creating-product-requirements/green/result.json`
- Modify: `evaluations/creating-development-specs-and-plans/green/result.json`
- Modify: `evaluations/generating-development-prompts/green/result.json`
- Modify: `evaluations/registry.json`
- Verify only: `.codex-plugin/plugin.json`
- Verify only: `README.md`
- Verify only: `docs/install.md`

**接口：**

- Consumes: Tasks 1～3 的最新 production、RED/GREEN raw evidence、版本化 outputs、rubrics 和当前未提交基线。
- Produces: 三 Skill 映射一致性、英文 canonical 分离、freshness/review metadata、完整五 Skill plugin 和安装边界的最终证据。

**保证追踪：**

- 覆盖保证：`G-01`～`G-08`。
- 覆盖结果：`O-01`～`O-22`。
- 精确测试：`RepositoryContractTests.test_localized_document_frontmatter_and_canonical_handoff_contracts_are_separate`；`HandoffRendererRepositoryTests.test_workflow_full_view_has_exact_fourteen_lines`、`test_gate_truth_tables_reject_inconsistent_claims`；三个受影响 Skill 全部 tests/evaluations；仓库全部 tests；官方 Skill/plugin validator。
- 可观察断言：每个 Outcome/Guarantee 双向覆盖；三个 Skill 重叠映射一致；renderer 和 gate bytes 不变；三个 targeted checks、Python 3.9/3.14、full plugin 门和安装 payload 校验通过；历史文档无迁移 diff。

**测试方式：** 三个 Skill 先以 `implemented` stage 完成 GREEN、定向和双版本验证；随后进行一次最新完整 diff 的风险批次评审。只有评审者批准当前候选后才写回新的 review metadata 与 `review-approved` stage，再运行 targeted/full 门，并由同一评审者复核写回后的最新 diff 与 full 证据。

- [ ] 证据核对：确认同一 repository contract test 已在 Tasks 1～3 各自生产修改前先扩展并取得对应 RED，且每个 Task 的 GREEN 后重新通过；不得以 Task 4 补写一次性测试代替分阶段证据。
- [ ] GREEN：更新 `docs/workflow.md` 与 `CHANGELOG.md` 的当前事实；更新三个 rubric/result 的真实 `fresh_cases`，但三个 `green/result.json` 继续保持 `review_status: pending`，registry 继续保持三个目标 Skill 为 `implemented`，不得预填 reviewer/date 或 `review-approved`。
- [ ] Verify GREEN：运行 `.venv/bin/python tests/test_repository_contract.py RepositoryContractTests.test_localized_document_frontmatter_and_canonical_handoff_contracts_are_separate`；预期通过。
- [ ] 验证：运行 `.venv/bin/python tests/test_handoff_renderer.py HandoffRendererRepositoryTests.test_workflow_full_view_has_exact_fourteen_lines HandoffRendererRepositoryTests.test_gate_truth_tables_reject_inconsistent_claims`；预期 renderer 字节和 gate truth table 不变。
- [ ] 验证：分别运行 `.venv/bin/python scripts/check.py --skill creating-product-requirements`、`.venv/bin/python scripts/check.py --skill creating-development-specs-and-plans`、`.venv/bin/python scripts/check.py --skill generating-development-prompts`；预期 repository tests、目标 Skill tests、freshness 和官方 validator 全部通过。
- [ ] 验证：使用 `python3.9 -m unittest discover -s skills/creating-product-requirements/tests -v`、`python3.9 -m unittest discover -s skills/creating-development-specs-and-plans/tests -v`、`python3.9 -m unittest discover -s skills/generating-development-prompts/tests -v`，再用 `python3.14` 重复三条；预期六个 suite 全部通过。
- [ ] 验证：运行 `git diff --check`；预期当前完整 diff 没有格式错误。此时不得运行 `.venv/bin/python scripts/check.py --full`，因为三个目标 Skill 尚未取得本次独立评审、仍为 `implemented`。
- [ ] no-migration 核对：运行 `git status --short -- docs/requirements docs/specs docs/plans`；预期仅三条 `??`，分别为本主题 PRD、spec、plan。
- [ ] no-migration 核对：运行 `git ls-files --others --exclude-standard -- docs/requirements docs/specs docs/plans`；预期精确输出 `docs/plans/2026-07-19-localized-workflow-document-metadata.md`、`docs/requirements/2026-07-19-localized-workflow-document-metadata.md`、`docs/specs/2026-07-19-localized-workflow-document-metadata-design.md`，无其它未跟踪文档。
- [ ] no-migration 核对：运行 `git diff -- docs/requirements docs/specs docs/plans`；预期没有历史 tracked 文档的本地化 diff。该命令不用于证明 untracked 文件内容，必须与前两条和直接读取联合判断。
- [ ] no-migration 核对：分别运行 `sed -n '1,18p' docs/requirements/2026-07-19-localized-workflow-document-metadata.md`、`sed -n '1,20p' docs/specs/2026-07-19-localized-workflow-document-metadata-design.md`、`sed -n '1,12p' docs/plans/2026-07-19-localized-workflow-document-metadata.md`；预期三份当前 untracked 文档仍使用 english-legacy frontmatter，批准/评审事实与当前阶段一致。
- [ ] 风险批次评审：由一名未参与实施的 `skill-reviewer` 检查当前最新完整 diff、全部 RED/GREEN、三个 `implemented` targeted checks、双版本证据、跨 Skill 映射、plugin/安装边界测试和 no-migration 证据。存在 finding 时修复、重跑受影响验证并由同一评审者复审；在其明确批准当前候选前不写回 review metadata。
- [ ] 评审写回：取得上述 reviewer 对当前候选的真实 `APPROVED` 后，把三个目标 `green/result.json` 分别更新为 `review_status: approved`、generic `reviewer: skill-reviewer` 和当前日期，并将 `evaluations/registry.json` 中三个目标 stage 改回 `review-approved`；不改变未受影响 Skill。
- [ ] 写回后验证：分别重跑 `.venv/bin/python scripts/check.py --skill creating-product-requirements`、`.venv/bin/python scripts/check.py --skill creating-development-specs-and-plans`、`.venv/bin/python scripts/check.py --skill generating-development-prompts`；预期三个 review-approved freshness 门通过。
- [ ] 完整门：仅在全部 exposed Skill 均为 `review-approved` 后运行 `.venv/bin/python scripts/check.py --full`；预期 repository tests、五 Skill tests、strict freshness、官方 Skill validators 和 plugin validator 全部通过。
- [ ] 最终复审：把评审元数据写回 diff、targeted/full 输出和 no-migration 复核交回同一 `skill-reviewer`。若有 finding，修复并重跑受影响门；同一评审者对最新完整 diff 给出最终 `APPROVED` 后停止。
- [ ] 文档同步：核对 README、安装文档和 plugin manifest 当前事实；没有安装、版本、公开命令或发布边界变化时保持不动。

## 实施评审策略

- 默认只设置一个整体风险批次，始终由同一名未参与实施的 `skill-reviewer` 负责。其先评审三个目标 Skill 处于 `implemented` 时的最新完整候选和定向/双版本证据；批准后才允许写回 review metadata，随后检查 targeted/full 门和写回后的最新 diff，给出最终 verdict。
- 中间里程碑评审：无。虽然本任务改变跨 Skill 文档契约，但三个 Skill 没有共享运行时代码；每个 Task 已通过独立 RED/GREEN 和定向门控制风险，后续 Task 不依赖尚未验证的共享基础。任务数量不增加评审门。
- 候选评审发现的范围内问题由实施者修复，在 `implemented` stage 重跑受影响测试、evaluation 和 targeted 门，再由同一评审者复审。评审元数据写回后的问题则重跑 affected targeted/full 门并继续由同一评审者复审。最终收到 `APPROVED` 后立即停止，不追加第二评审者。

## 最终验证

- PRD inspector：中文 approved 与英文 approved 输入得到相同英文 JSON；mixed、duplicate、unknown Unicode、unsupported value 均 unknown/blocked。
- Authoring：新 PRD/spec/plan 完整中文；中文 lifecycle 写回保持中文；历史英文 PRD/spec/plan 的维护、失效与重新评审保持英文。
- Plan discovery：完整中文 approved/pending 分别映射 approved/not-approved；残缺、mixed、非法或缺角色/日期映射 unknown；英文 review-only/header 行为不变。
- Persistence：已有目标、前置失败、明确未应用、不确定完成与三类 readback reconciliation 对应 `O-13`～`O-19`，不重复写入、不采用部分批准。
- Traceability：逐项核对 `O-01`～`O-22`、`G-01`～`G-08`、精确 tests、commands、assertions；无遗漏保证、孤立 Outcome 或孤立必需测试。
- Regression：三个 targeted checks、六个 Python 3.9/3.14 suites、`.venv/bin/python scripts/check.py --full`、`git diff --check` 全部通过。
- Integration：英文八/十四字段、三个 renderer、gate truth table、prompt JSON、plugin manifest 和安装边界保持兼容。
- Review：同一独立 reviewer 先批准 `implemented` 候选，后核对 review metadata 写回和 targeted/full 证据；最新完整 diff 最终获得 `APPROVED`，且所有评审修订后的受影响验证已经重新通过。
