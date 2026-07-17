---
document_type: implementation-plan
topic: workflow-handoff-optimization
spec_path: docs/specs/2026-07-17-workflow-handoff-optimization-design.md
spec_user_approval: approved
review_status: approved
reviewer: independent-plan-reviewer
reviewed_at: 2026-07-17
---

# 开发工作流交接体验优化实施计划

**目标：** 在保持五个 skill 独立安装、既有审批门禁和未发布 `0.1.0` 边界的前提下，完成中文文档、两段自动衔接、三态会话路由、单一可复制提示词代码框及项目 Agent 覆盖评估。

**架构：** 不新增编排服务。主 Agent 使用已验证的 requirements 八字段和 spec/plan 十四字段顺序切换独立 skill；仓库发现脚本继续只提供客观证据，会话路由由新策略引用当前上下文和可验证能力作出三态判断；renderer 只负责生成动态 Markdown fence 的完整提示词代码框。

**技术栈：** Markdown skill 与模板、Python 3.9+ 标准库脚本、`unittest`、仓库 evaluation runner、官方 skill/plugin validator、Codex 独立只读评审角色。

## 全局约束

- 开始任何 skill 修改前必须使用系统 `skill-creator`，完整遵循其当前维护流程；不得修改 `~/.codex/skills` 中的已安装副本。
- 严格按 Task 0 → Task 1 → Task 2 → Task 3 顺序实施。Task 0 只扩展隔离 evaluation staging；一个 skill 未完成 RED、GREEN、定向验证、前向证据、独立 `skill-reviewer` 评审和严格仓库验证前，不得修改下一个 skill。
- 每个行为变化先取得符合预期的失败测试和 current-skill RED，再做最小生产修改；不得用放宽判据、删除有效测试或静默兜底制造 GREEN。
- 自动衔接只由主 Agent 根据显式交接字段选择下游能力；skill 不读取兄弟源码、兄弟安装目录或固定本机路径。
- PRD/spec/plan frontmatter、八字段、十四字段、PRD inspector 和 discovery JSON schema 保持兼容；转换失败按批准 spec 的前后阶段规则报告。
- plugin 保持五个 skill 和未发布版本 `0.1.0`；不安装到真实 `CODEX_HOME`，不 commit、push、merge、rebase、tag、release 或发布。
- 本阶段不修改 `.codex/agents/*.toml`、`agent-rules` 或个人全局 Agent 安装状态。
- 一键复制必须取得真实 Codex 客户端证据；无法验证时不得报告整体完成。

### Task 0：让 evaluation runner 支持组合 skill 隔离运行

**精确文件：**

- Modify: `scripts/run_skill_evaluations.py`
- Modify: `tests/test_skill_evaluation_runner.py`

**接口：**

- Consumes: 一个 `--skill-dir` 目标 skill，以及零到多个重复的 `--additional-skill-dir` 辅助 skill 目录。
- Produces: 同一临时 `CODEX_HOME` 中彼此独立 staged 且全部只读的多个 skill；evaluation prompt 把目标 skill 作为初始 workflow，并显式列出可在交接发生后按 skill 名称选择的辅助 skill 与允许路径；结构化 result 记录已 staged 的辅助 skill 名称，便于组合证据审计。

**测试方式：** 先增加参数、名称冲突、重复目录、非 publishable/symlink、staging 内容、sandbox 和 result 记录测试并观察 RED；再复用现有 `_copy_publishable_skill` 对每个目录分别复制。辅助 skill 只能来自显式参数，不扫描仓库或真实安装目录。`build_sandbox_profile` 接收全部 staged skill roots，对目标和每个辅助 payload 显式禁止写入，同时保留临时 home 必要输出目录可写。

- [ ] RED：在 `test_skill_evaluation_runner.py` 增加重复 `--additional-skill-dir` 解析、目标/辅助名称冲突、非法目录、多个 publishable payload 同时 staged、全部 staged roots 只读、必要输出目录可写、isolation prompt allowlist、结构化 result 记录和未传辅助参数保持兼容的测试；运行 `.venv/bin/python -m unittest discover -s tests -p 'test_skill_evaluation_runner.py' -v`，预期新增测试失败。
- [ ] GREEN：为 runner 增加可重复的 `--additional-skill-dir`，逐个验证目录名与 frontmatter name、拒绝重复/冲突/symlink，并把辅助 skill staged 到同一临时 `CODEX_HOME/skills`；`build_sandbox_profile` 对所有 staged roots 增加 `deny file-write*`。isolation prompt 只把目标 skill 作为初始调用，但列出辅助 skill 名称和允许路径，说明仅在目标 workflow 触发交接后按名称选择，不允许手工搜索、修改或导入兄弟源码；不改变单 skill 默认行为和 phase 语义。
- [ ] Verify GREEN：运行 `.venv/bin/python -m unittest discover -s tests -p 'test_skill_evaluation_runner.py' -v` 和 `.venv/bin/python scripts/validate_repo.py`，预期全部通过。
- [ ] REFACTOR：复用现有目录验证、复制和 sandbox deny 生成函数，避免目标/辅助 skill 两套安全逻辑；确认 prompt 不包含 rubric、expected、RED 失败分析或其它 skill 外的 Codex-home 内容；重新运行目标测试。
- [ ] 文档同步：runner 是仓库开发工具，公开工作流文档无需增加 CLI 细节；组合命令在 Task 4 和本 plan 中作为恢复入口。
- [ ] 任务级独立评审：由未参与实现的 reviewer 检查 runner 参数边界、临时 home 隔离、默认兼容和测试；修复、验证并复审至 `APPROVED` 后才进入 Task 1。

### Task 1：让 PRD skill 输出中文并在批准后进入技术规格流程

**精确文件：**

- Modify: `skills/creating-product-requirements/SKILL.md`
- Modify: `skills/creating-product-requirements/references/document-contract.md`
- Modify: `skills/creating-product-requirements/references/review-and-handoff.md`
- Modify: `skills/creating-product-requirements/assets/prd-template.md`
- Modify: `skills/creating-product-requirements/tests/test_skill_contract.py`
- Modify: `evaluations/registry.json`
- Modify: `evaluations/creating-product-requirements/rubric.json`
- Create: `evaluations/creating-product-requirements/cases/09-approved-auto-spec-transition.md`
- Create: `evaluations/creating-product-requirements/fixtures/09-approved-auto-spec-transition/docs/requirements/2026-07-15-order-approval.md`
- Create: `evaluations/creating-product-requirements/migration-red/09-output.md`
- Create: `evaluations/creating-product-requirements/migration-red/result.json`
- Create: `evaluations/creating-product-requirements/green/09-output.md`
- Modify: `evaluations/creating-product-requirements/green/result.json`
- Verify only: `skills/creating-product-requirements/agents/openai.yaml`

**接口：**

- Consumes: 已验证的 approved PRD、requirements 八字段、当前运行时暴露的下游 skill 能力。
- Produces: 中文 PRD；未转换时以八字段结束；批准后把显式 path/topic/scope 及完整八字段交给下游，成功转换后的最终十四字段按规格映射保留八字段值。

**测试方式：** 先增加失败合同和 case 09，确认现有 skill 仍使用英文模板、把 PRD 当绝对终点且不会尝试下游转换；再最小修改 skill、引用和模板。case 09 在只安装目标 skill 的隔离环境中使用已批准 PRD，GREEN 应明确报告下游能力不可用并保持真实八字段，证明单独安装不会猜测安装路径。组合转换留给 Task 4 集成回归。

- [ ] RED：在 `test_skill_contract.py` 增加中文模板、批准后自动转换、未转换八字段结尾、下游转换由十四字段接管、禁止兄弟路径依赖的断言；运行 `.venv/bin/python -m unittest discover -s skills/creating-product-requirements/tests -v`，预期新增测试因现有绝对终端边界和英文模板失败。
- [ ] RED：把 `creating-product-requirements` registry profile 从 `creation-only` 调整为 `creation-plus-current-red`，冻结 case 09 与 rubric 判据；在生产修改前运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase current-skill-red --case evaluations/creating-product-requirements/cases/09-approved-auto-spec-transition.md --skill-dir skills/creating-product-requirements --output-root work/evaluations/creating-product-requirements/current-red-09`，确认有效 RED，并将脱敏后的选中输出和结构化结果写入 `migration-red/`。
- [ ] GREEN：将 PRD 模板标题、章节和占位说明改为中文；收缩 sibling 禁止边界，定义八字段构造、下游选择、能力缺口和最终合同接管，不让 PRD skill 自己编写 spec。
- [ ] GREEN 状态：在运行 GREEN 前把 registry `stage` 设为 `implemented`，并让 `green/result.json` 保持 `review_status: pending`、无 reviewer/date；不得在评审前预填批准。
- [ ] REFACTOR：删除重复或相互冲突的“每个回复必须八字段结尾”表述，确保未转换回复和成功转换回复只有一个最终合同；REFACTOR 完成后才生成任何 GREEN 前向证据。
- [ ] 定向 GREEN：运行 `.venv/bin/python -m unittest discover -s skills/creating-product-requirements/tests -v` 和 `.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/creating-product-requirements`，预期通过；此时尚不运行 evidence-only。
- [ ] GREEN 前向：使用与 RED 不同的全新 Agent 运行同一 case 09 的 `--phase green`，输出到 `work/evaluations/creating-product-requirements/green-09`；脱敏保存 `green/09-output.md`，更新 `green/result.json`，不得向 Agent 暴露 expected 或 RED 失败分析。
- [ ] GREEN 证据门：确认 rubric 的全部 GREEN case、版本化输出和 `green/result.json` 已完整后，运行 `.venv/bin/python scripts/validate_repo.py --evidence-only creating-product-requirements`，预期在 `stage: implemented` 且 review pending 下通过；严格 validator 仍应阻塞。
- [ ] 文档同步：本 Task 只维护 skill 内引用和模板；公共 README/workflow/CHANGELOG 延后到 Task 4，避免另一个 skill 尚未实现时发布不完整事实。
- [ ] 任务级独立评审：使用未参与实现的 `skill-reviewer` 检查最新 Task 1 diff、RED/GREEN 原始证据、八到十四字段边界、自包含性和 `openai.yaml` 一致性；修复、重新验证并由同一评审者复审至 `APPROVED`。
- [ ] 评审写回门：评审批准最新版本后立即把通用 reviewer/date 写入 `green/result.json`、设 `review_status: approved`，并把 registry `stage` 改回 `review-approved`；运行严格 `.venv/bin/python scripts/validate_repo.py`，让同一 reviewer 确认元数据与最新证据一致。只有该命令通过且复核确认后才进入 Task 2。

### Task 2：让 spec/plan skill 输出中文并在十四字段完成后进入会话路由

**精确文件：**

- Modify: `skills/creating-development-specs-and-plans/SKILL.md`
- Modify: `skills/creating-development-specs-and-plans/references/document-contracts.md`
- Modify: `skills/creating-development-specs-and-plans/references/review-and-handoff.md`
- Modify: `skills/creating-development-specs-and-plans/assets/spec-template.md`
- Modify: `skills/creating-development-specs-and-plans/assets/plan-template.md`
- Modify: `skills/creating-development-specs-and-plans/tests/test_skill_contract.py`
- Modify: `evaluations/registry.json`
- Modify: `evaluations/creating-development-specs-and-plans/rubric.json`
- Create: `evaluations/creating-development-specs-and-plans/cases/12-approved-plan-auto-routing.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/12-approved-plan-auto-routing/docs/requirements/2026-07-12-order-approval.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/12-approved-plan-auto-routing/docs/specs/2026-07-12-order-approval-design.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/12-approved-plan-auto-routing/docs/plans/2026-07-12-order-approval.md`
- Create: `evaluations/creating-development-specs-and-plans/migration-red/12-output.md`
- Delete after case 12 is valid and selected: `evaluations/creating-development-specs-and-plans/migration-red/09-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/migration-red/result.json`
- Create: `evaluations/creating-development-specs-and-plans/green/12-output.md`
- Create: `evaluations/creating-development-specs-and-plans/cases/13-downstream-prd-revalidation-failure.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/13-downstream-prd-revalidation-failure/docs/requirements/2026-07-12-order-approval.md`
- Create: `evaluations/creating-development-specs-and-plans/green/13-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/result.json`
- Verify only: `skills/creating-development-specs-and-plans/agents/openai.yaml`

**接口：**

- Consumes: approved PRD 显式 path/topic/scope、spec 双批准、plan 真实评审状态、十四字段。
- Produces: 中文 spec/plan；任何阻塞或未转换回复保持完整十四字段；全部门禁打开后先验证十四字段，再让主 Agent 进入会话路由，并要求路由最终回复仍以相同十四字段结束。

**测试方式：** case 12 使用 approved PRD/spec/plan，现有 skill 会停在十四字段终点形成 RED；GREEN 在只安装目标 skill 时必须先给出真实十四字段，再报告下游路由能力缺口，不读取 prompt skill 路径。模板合同同时验证中文标题、章节、标签和占位说明，frontmatter 不变。

- [ ] RED：增加中文模板、plan approved 后自动路由、十四字段先验证、路由后十四字段结尾、门禁未开不路由、进入下游后 PRD 复验失败仍十四字段和默认 path 保留测试；运行 `.venv/bin/python -m unittest discover -s skills/creating-development-specs-and-plans/tests -v`，预期新增断言失败。
- [ ] RED：冻结 case 12、case 13 与 rubric，运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase current-skill-red --case evaluations/creating-development-specs-and-plans/cases/12-approved-plan-auto-routing.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/current-red-12`，确认现有 skill 停在终端交接；用脱敏 case 12 更新当前 `migration-red` 选中证据。只有 case 12 输出和 result 已有效保存且 selected 后，才删除旧 `09-output.md`，使目录只保留当前选中 RED。
- [ ] GREEN：本地化 spec/plan 模板；收缩绝对 sibling 禁止边界；实现“门禁校验 → 十四字段快照 → 下游选择/能力缺口”合同，不改变 PRD inspector、plan 三态 review 或双门公式。
- [ ] GREEN 状态：生产修改完成后把 registry `stage` 设为 `implemented`，`green/result.json` 保持 review pending；运行前不得沿用旧 review-approved 证明当前 GREEN。
- [ ] REFACTOR：合并重复的 terminal/runtime boundary 文字，确保十四字段在自动路由前后只有一份权威快照；REFACTOR 完成后才运行定向 GREEN 和前向场景。
- [ ] 定向 GREEN：运行 `.venv/bin/python -m unittest discover -s skills/creating-development-specs-and-plans/tests -v` 和官方 `quick_validate.py`，预期通过；此时尚不运行 evidence-only。
- [ ] GREEN 前向：用不同的全新 Agent 对 case 12、case 13 分别运行 `--phase green`，输出到对应 `work/evaluations/creating-development-specs-and-plans/green-1x`；脱敏更新 `green/12-output.md`、`green/13-output.md` 和 `green/result.json`。case 13 必须证明进入下游后的 PRD 复验失败仍输出完整十四字段、保留可靠路径并关闭双门。
- [ ] GREEN 证据门：全部 rubric case、GREEN 输出和 result 保存后运行 `.venv/bin/python scripts/validate_repo.py --evidence-only creating-development-specs-and-plans`，预期在 implemented/review pending 下通过；严格 validator 仍应阻塞。
- [ ] 文档同步：本 Task 只维护 skill 内合同和模板；公共文档延后到 Task 4。
- [ ] 任务级独立评审：使用新的未参与实现 `skill-reviewer` 检查 Task 2 最新 diff、PRD inspector 不回退、十四字段真实性、RED/GREEN 和自包含性；修复、验证并复审至 `APPROVED`。
- [ ] 评审写回门：批准后立即更新 Task 2 `green/result.json` 的通用 reviewer/date 和 `review_status: approved`，把 registry `stage` 恢复为 `review-approved`；运行严格 validator 并由同一 reviewer 确认。通过后才进入 Task 3。

### Task 3：扩展 prompt skill 为三态会话路由并输出单一代码框

**精确文件：**

- Modify: `skills/generating-development-prompts/SKILL.md`
- Modify: `skills/generating-development-prompts/agents/openai.yaml`
- Create: `skills/generating-development-prompts/references/session-routing-policy.md`
- Modify: `skills/generating-development-prompts/scripts/render_prompt.py`
- Modify: `skills/generating-development-prompts/tests/test_skill_contract.py`
- Modify: `skills/generating-development-prompts/tests/test_render_prompt.py`
- Verify only: `skills/generating-development-prompts/scripts/discover_context.py`
- Verify only: `skills/generating-development-prompts/tests/test_discover_context.py`
- Modify: `evaluations/registry.json`
- Modify: `scripts/validate_repo.py`
- Modify: `tests/test_repository_contract.py`
- Create: `evaluations/generating-development-prompts/rubric.json`
- Create: `evaluations/generating-development-prompts/cases/01-current-session.md`
- Create: `evaluations/generating-development-prompts/cases/02-new-session.md`
- Create: `evaluations/generating-development-prompts/cases/03-blocked.md`
- Create: `evaluations/generating-development-prompts/fixtures/common/AGENTS.md`
- Create: `evaluations/generating-development-prompts/fixtures/common/docs/specs/2026-07-17-example-design.md`
- Create: `evaluations/generating-development-prompts/fixtures/common/docs/plans/2026-07-17-example.md`
- Create: `evaluations/generating-development-prompts/migration-red/01-output.md`
- Create: `evaluations/generating-development-prompts/migration-red/result.json`
- Create: `evaluations/generating-development-prompts/green/01-output.md`
- Create: `evaluations/generating-development-prompts/green/02-output.md`
- Create: `evaluations/generating-development-prompts/green/03-output.md`
- Create: `evaluations/generating-development-prompts/green/result.json`

**接口：**

- Consumes: 自动路径的已验证十四字段、当前会话上下文、discovery JSON、权限/工具/Agent 可用事实；或手动路径的显式 prompt 请求。
- Produces: `current-session | new-session | blocked` 结论与中文理由；仅 `new-session` 或显式请求产生 renderer 代码框；自动路径最终仍以原十四字段结束；手动路径不伪造十四字段。
- Renderer consumes: 现有 `schema_version: 1` JSON stdin。
- Renderer produces: 仅一个动态反引号 fence 的 Markdown `text` 代码框和末尾换行；错误 stderr、退出码与 stdout 为空合同保持。

**测试方式：** 先用合同测试和三个前向 case 固定路由优先级。为已导入并评审的 prompt skill 增加 `imported-plus-current-red` 维护证据 profile：只要求当前 RED、GREEN、rubric/cases，不伪造从零创建 baseline；validator 和仓库测试必须先 RED。renderer 用比正文最长连续反引号多一个的 fence，测试 Unicode、嵌套深度、反引号内容和无部分输出。

- [ ] RED：在 `test_skill_contract.py` 固定三态路由、跨会话 `blocked` 证据、当前会话限制不得外推、手动未批准 plan 兼容、自动路径十四字段结尾和单一代码框合同；运行 prompt skill 定向 unittest，预期失败。
- [ ] RED：在 `test_render_prompt.py` 将成功输出期望改为一个动态 fence 代码框，增加正文含 3～6 个连续反引号、Unicode、现有嵌套深度和错误 stdout 为空用例；运行 `.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v`，确认失败原因来自普通正文输出。
- [ ] RED：先在 `tests/test_repository_contract.py` 增加 `imported-plus-current-red` registry/证据正反合同并运行目标测试，确认当前 validator 拒绝新 profile；再最小扩展 `scripts/validate_repo.py`，使该 profile 支持 `implemented → review-approved`、`--evidence-only` 和严格 review gate，只校验 rubric、case、current-red、GREEN 和 review，不要求 imported skill 的虚构创建 baseline。
- [ ] RED 前向：冻结三个 case 与 rubric；在生产 skill 修改前对 case 01 运行 `--phase current-skill-red` 到 `work/evaluations/generating-development-prompts/current-red-01`，确认现有 skill 总是生成提示词而未建议当前会话；保存脱敏选中 RED。
- [ ] GREEN：新增 `session-routing-policy.md`，按批准 spec 定义输入、三态优先级、跨会话阻塞证据、理由和十四字段保留；调整 SKILL description/workflow/output contract，只有新会话或显式请求才渲染。
- [ ] GREEN：修改 renderer，在完整模板正文生成后计算动态 fence 并输出单一 `text` 代码框；不得修改 discovery CLI、JSON schema 或新增输入大小限制。
- [ ] GREEN：使用 `skill-creator` 规定的 UI metadata 生成流程更新 `agents/openai.yaml`，确保 description 与新增路由触发一致，frontmatter 仍只有 `name` 和 `description`。
- [ ] GREEN 状态：将 prompt registry 改为 `evaluation_mode: imported`、`evidence_profile: imported-plus-current-red`、`stage: implemented`，GREEN review 保持 pending；不得伪造 baseline 或预填评审。
- [ ] REFACTOR：消除旧的“renderer stdout 无包装且永远是完整回复”冲突表述，保持手动路径最简；REFACTOR 完成后才运行定向 GREEN 和三个前向场景。
- [ ] 定向 GREEN：运行 prompt 全部 unittest、官方 `quick_validate.py` 和 discovery 既有测试，预期通过且 `schema_version: 1` 不变；此时尚不运行 evidence-only。
- [ ] GREEN 前向：使用与 RED 不同的全新 Agent 分别运行 case 01、02、03 的 `--phase green`，保存到 `work/evaluations/generating-development-prompts/green-0x`；脱敏写入三个 GREEN 输出和 result，确认 current 不生成 prompt、new 生成一个代码框、blocked 不自动生成。
- [ ] GREEN 证据门：全部 prompt rubric case、GREEN 输出和 result 保存后运行 `.venv/bin/python scripts/validate_repo.py --evidence-only generating-development-prompts`，预期在 imported-plus-current-red/implemented/review pending 下通过；严格 validator 仍应阻塞。
- [ ] 文档同步：本 Task 只维护 prompt skill 内引用与 metadata；公开迁移说明延后 Task 4。
- [ ] 任务级独立评审：使用新的未参与实现 `skill-reviewer` 检查路由证据、动态 fence、breaking stdout、旧手动能力、evaluation profile 和自包含性；修复、重新验证并复审至 `APPROVED`。
- [ ] 评审写回门：批准后立即写入 prompt `green/result.json` reviewer/date、设 review approved，并把 imported profile stage 设为 `review-approved`；运行严格 validator 并由同一 reviewer 确认。通过后才进入 Task 4。

### Task 4：完成跨 skill 集成合同、公开文档与 Agent 评估

**精确文件：**

- Modify: `tests/test_repository_contract.py`
- Modify: `README.md`
- Modify: `docs/workflow.md`
- Modify: `docs/install.md`
- Modify: `docs/agent-development.md`
- Modify: `CHANGELOG.md`
- Modify: `.codex-plugin/plugin.json`
- Verify only: `.codex/agents/skill-reviewer.toml`
- Verify only: `.codex/agents/final-reviewer.toml`
- Verify only: `.codex/agents/workflow-final-reviewer.toml`

**接口：**

- Consumes: 三个已独立评审通过的 skill 合同、八字段、十四字段、三态路由、项目级 Agent 配置。
- Produces: 可离线回归的跨 skill 合同；公开的连续工作流和 breaking stdout 迁移说明；三个项目级 Agent 的逐角色保留结论；保持五-skill、`0.1.0` plugin manifest。

**测试方式：** 先为跨 skill 映射、自动转换、中文模板、manifest 和公开文档增加失败断言，再同步文档。测试不得通过导入兄弟 skill 模块实现耦合；只读取公开文档合同或调用现有公共 CLI。

- [ ] RED：在 `tests/test_repository_contract.py` 增加八字段到十四字段精确映射、进入下游前后复验失败、十四字段到路由、三个模板中文标题、renderer breaking 迁移说明、manifest `0.1.0` 与五-skill 不变的测试；运行目标测试并确认文档/集成断言失败。
- [ ] GREEN：更新 `docs/workflow.md`，明确 PRD→spec 和 plan→routing 两段自动衔接、单一最终 handoff、三态路由和手动提示词兼容。
- [ ] GREEN：更新 `README.md` skill 表和三步工作流；更新 `docs/install.md`，说明完整自动链需要三个 skill 同时可用，单 skill 安装仍完成本职并报告下游能力缺口。
- [ ] GREEN：更新 `CHANGELOG.md` 未发布 `0.1.0` 的三个 skill 与 Repository 条目，明确 renderer stdout breaking change 和“提取唯一代码框内容”的迁移方式。
- [ ] GREEN：最小更新 `.codex-plugin/plugin.json` description、longDescription 和 defaultPrompt；保持 `skills: ./skills/`、五个 skill 和 version `0.1.0`。
- [ ] GREEN：在 `docs/agent-development.md` 增加三个项目级 Agent 的稳定可用性、职责、输入、输出、边界、批准条件比较表，结论均为保留；不得修改 Agent TOML。
- [ ] 组合运行一：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase green --case evaluations/creating-product-requirements/cases/09-approved-auto-spec-transition.md --skill-dir skills/creating-product-requirements --additional-skill-dir skills/creating-development-specs-and-plans --additional-skill-dir skills/generating-development-prompts --output-root work/evaluations/workflow-handoff-integration/prd-to-spec`。要求 result valid，最终回复由十四字段接管、前八项按映射保留且每个字段只出现一次；失败时停止文档完成声明并回到对应 skill 修复、验证和复审。
- [ ] 组合运行二：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase green --case evaluations/creating-development-specs-and-plans/cases/12-approved-plan-auto-routing.md --skill-dir skills/creating-development-specs-and-plans --additional-skill-dir skills/generating-development-prompts --additional-skill-dir skills/creating-product-requirements --output-root work/evaluations/workflow-handoff-integration/plan-to-routing`。要求先产生已验证十四字段，再进入三态路由，最终十四字段只出现一次；原始 trace/final/result 保存在忽略的 `work/` 供 Task 4 与最终评审检查。
- [ ] Verify GREEN：运行 `.venv/bin/python -m unittest discover -s tests -v`、`.venv/bin/python scripts/validate_repo.py`、`git diff --check` 和 plugin validator，预期全部通过。
- [ ] 文档同步：检查 README、install、workflow、agent development、CHANGELOG 和 manifest 的当前事实一致，不添加发布、tag、真实安装或外部仓库操作说明。
- [ ] 任务级独立评审：使用新的未参与实现 reviewer 检查跨 skill 公共合同、semver 判断、迁移说明、Agent 评估和无配置删除；修复、验证并由同一评审者复审至 `APPROVED`。

### Task 5：执行完整验证、隔离安装检查、客户端复制验证和最终门禁

**精确文件：**

- Verify only: `evaluations/creating-product-requirements/green/result.json`
- Verify only: `evaluations/creating-development-specs-and-plans/green/result.json`
- Verify only: `evaluations/generating-development-prompts/green/result.json`
- Verify only: `evaluations/registry.json`
- Verify only: all files changed by Tasks 1–4
- Do not modify: `.codex/agents/*.toml`
- Do not modify: any real `${CODEX_HOME:-$HOME/.codex}` installation target

**接口：**

- Consumes: 最新完整 diff、三个 skill 的 RED/GREEN 与 task review、仓库和 plugin 验证结果。
- Produces: Python 3.9/3.14 可复现验证证据、临时 staging 的独立/组合 skill 验证、真实 Codex 客户端复制结果、完整五-skill plugin 最终评审结论。

**测试方式：** 先完成三个 skill 各自评审结果写回并重新验证，再运行仓库规定的全量命令。临时安装只写入 `/tmp` 或其它隔离 `CODEX_HOME`，不得覆盖真实安装。客户端复制验证必须比较复制内容与 renderer 内部提示词正文；无法操作或比较时标记阻塞。

- [ ] 评审状态复核：确认三个 `green/result.json` 已在各自 Task 内由真实评审写为 approved，registry 三项 stage 均为 `review-approved`，且每次写回后已有同一 reviewer 复核和严格 validator 通过；Task 5 不首次落盘或补造这些证据。
- [ ] 全量 unittest：运行 `.venv/bin/python -m unittest discover -s tests -v` 以及五个 skill 各自的 unittest discover，预期全部通过。
- [ ] 仓库与官方 validator：运行 `.venv/bin/python scripts/validate_repo.py`、五个 skill 的官方 `quick_validate.py`、`.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" .` 和 `git diff --check`，预期全部通过。
- [ ] Python 维护矩阵：在可用的 Python 3.9 与 Python 3.14 环境重复运行仓库测试和 validator；缺少任一解释器时记录为未验证，不伪造兼容结果。
- [ ] 隔离安装：按仓库现有 staging 测试或 skill-installer 的非覆盖方式，把三个受影响 skill 分别和完整五-skill plugin 安装到临时 `CODEX_HOME`；验证单 skill 自包含、组合自动转换合同和安装内容与候选一致，不写真实安装目录。
- [ ] 客户端复制：用 renderer 生成包含长文本、Unicode 和连续反引号的提示词，在实际 Codex 客户端显示单一代码框并执行一键复制；把复制内容与预期正文逐字比较。失败或无法验证时停止完成声明。
- [ ] 完整集成评审：由未参与实现的 `workflow-final-reviewer` 检查批准 PRD/spec/plan、全部 diff、三个 skill 的 RED/GREEN 和任务评审、中文输出、两段自动衔接、三态路由、breaking 迁移、plugin、隔离安装、客户端复制和未解决项；只有 `APPROVED` 才通过最终门。
- [ ] 最终交付：报告关键文件、实际验证命令和结果、评审结论、客户端复制证据、残留风险和未验证项；不 commit、push、安装或发布。

## 最终验证

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate_repo.py
.venv/bin/python -m unittest discover -s skills/creating-product-requirements/tests -v
.venv/bin/python -m unittest discover -s skills/creating-development-specs-and-plans/tests -v
.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v
.venv/bin/python -m unittest discover -s skills/implementing-bounded-changes/tests -v
.venv/bin/python -m unittest discover -s skills/managing-agents-rules/tests -v
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/creating-product-requirements
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/creating-development-specs-and-plans
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/generating-development-prompts
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/implementing-bounded-changes
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/managing-agents-rules
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" .
git diff --check
```

预期结果：所有适用测试和 validator 通过；三个受影响 skill 各自拥有有效 current RED、全新 Agent GREEN 和独立评审；完整五-skill plugin 在隔离安装中保持自包含；真实 Codex 客户端能够一键复制完整提示词正文；无项目 Agent 删除、真实安装、commit 或发布操作。任何缺失证据保持为阻断或未验证，不升级为完成。
