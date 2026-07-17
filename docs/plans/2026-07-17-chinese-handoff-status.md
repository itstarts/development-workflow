---
document_type: implementation-plan
topic: chinese-handoff-status
spec_path: docs/specs/2026-07-17-chinese-handoff-status-design.md
spec_user_approval: approved
review_status: approved
reviewer: independent-plan-reviewer
reviewed_at: 2026-07-17
---

# 工作流交接状态中文化实施计划

**目标：** 在保留英文 canonical 机器契约和当前未提交交接优化基线的前提下，使三个工作流 skill 只展示语境自然、顺序稳定的中文八字段或十四字段状态块，并以自动化测试和单实例 Codex 客户端复制验证证明提示词正文未被污染。

**架构：** 各 skill 先按现有规则构造、验证并冻结英文 canonical 快照，再在任何下游选择、会话路由或 renderer 调用前预生成并完整校验自身所需的中文视图；成功后向下游继续传递英文 canonical，回复末尾只复用同一中文视图。三个 skill 保持自包含，仓库测试锁定重叠映射一致性，不新增共享运行时依赖。

**技术栈：** Markdown skill 契约、Python 3.9+ `unittest`、现有本地 skill evaluation runner、仓库 validator、官方 skill/plugin validator、Codex 单实例客户端与 macOS 本地剪贴板。

## 全局约束

- 实施基线是当前 `codex/workflow-handoff-optimization` 未提交工作树，不是 `HEAD`。开始前和每个 Task 后检查当前 diff；不得 reset、覆盖、清理或切换到遗漏既有交接优化的基线，不得回滚用户或前序任务变更。
- 严格按 Task 0 到 Task 5 顺序执行。Task 1 至 Task 3 每次只修改一个 skill；当前 skill 完成 RED、GREEN、定向验证和独立评审并复审至 `APPROVED` 后，才能进入下一个 skill。
- 修改 skill 前完整读取根 `AGENTS.md`、`skills/AGENTS.md`、目标 skill 及其测试，并使用 `skill-creator` 的维护流程。不得读取兄弟 skill 安装目录或依赖插件缓存。
- 每个行为任务使用 TDD：先新增或收紧测试与评估判据，运行并保存符合预期的 RED；再做最小生产修改，运行 GREEN；不得通过放宽判据、删除有效测试或吞掉映射失败制造通过。
- 英文 canonical 字段、允许值、八到十四字段转换、文档元数据、门禁计算和 skill 间传递保持不变。中文状态块只是单向视图，不得成为反向解析或第二状态源。
- 中文视图必须在任何下游能力选择、自动会话路由或 `render_prompt.py` 调用前完整校验。映射失败不修改 canonical 或文档元数据，不输出部分中文、混合块或英文 fallback，也不执行本次自动转移。
- 保持 `render_prompt.py` stdin/stdout 字节级合同和动态 fence 算法不变。自动 `new-session` 路由的中文十四字段块位于 renderer 代码框之外；手动提示词请求没有可靠上游快照时仍只返回 renderer stdout。
- 不添加或升级依赖，不下载浏览器，不启动本地开发服务，不启动第二个 Codex 客户端，不创建或操作用户可见任务，不 commit、push、merge、rebase、tag、release 或发布，不安装到真实 `CODEX_HOME`。仅允许使用现有 `.venv`、`work/` 下被忽略的本地评估证据、`/private/tmp` 临时文件和临时隔离 `CODEX_HOME` staging。
- 每次委派前检查当前会话实际加载的个人全局 custom agents，按 `name` 和 `description` 选择职责最具体者；记录实际使用的 agent name。存在匹配但无法按 name 启动时，停止该次委派并报告能力缺口。

### Task 0: 冻结当前未提交集成基线与执行门

**精确文件：**

- Create: 无
- Modify: 无
- Test: `docs/requirements/2026-07-17-chinese-handoff-status.md`
- Test: `docs/specs/2026-07-17-chinese-handoff-status-design.md`
- Test: 当前 Git 工作树与三个受影响 skill、评估、测试和公开文档

**接口：**

- Consumes: 已批准 PRD、已批准技术规格、当前分支、`git status --short --branch`、当前未提交 diff、禁止操作边界。
- Produces: 一份仅存在于当前执行证据中的受保护基线清单，确认当前分支不是 `main`/`master`、PRD 与 spec 批准链有效、计划任务可安全叠加且没有需要回滚的重叠来源不明变更。

**测试方式：** 本任务不修改生产行为，不适用 RED/GREEN。它是所有后续写入的确定性前置门。

- [ ] 实施：完整读取适用规则、批准文档、当前三个 skill 及测试；记录当前分支和所有既有 modified/deleted/untracked 路径，特别标记三个 skill、评估、`docs/workflow.md`、`CHANGELOG.md`、`tests/test_repository_contract.py` 为受保护重叠基线。
- [ ] 验证：运行 `git status --short --branch`；预期分支为 `codex/workflow-handoff-optimization`，并保留已识别的未提交 handoff 优化。
- [ ] 验证：运行 `git diff --check`；预期退出码 0。
- [ ] 验证：运行 `.venv/bin/python skills/creating-development-specs-and-plans/scripts/inspect_product_requirements.py --repo-root . --requirements docs/requirements/2026-07-17-chinese-handoff-status.md --expected-topic chinese-handoff-status --expected-scope feature`；预期 `status: approved` 且技术规格门禁开放。不得用真实安装副本代替当前仓库检查器。
- [ ] 验证：检查 spec frontmatter；预期用户批准和独立评审均为 `approved`，来源路径与 topic 一致。
- [ ] 文档同步：无需修改文档；基线和权限边界已固化在本计划与批准规格中。
- [ ] 任务级独立评审：由未参与实施的评审者只读核对批准链、分支、受保护重叠文件和权限边界；有疑点时停止后续写入，直到同一评审者 `APPROVED`。

### Task 1: 中文化 PRD 八字段交接并保持 canonical 下游输入

**精确文件：**

- Create: `evaluations/creating-product-requirements/cases/10-chinese-handoff-status.md`
- Create: `evaluations/creating-product-requirements/fixtures/10-chinese-handoff-status/docs/requirements/2026-07-15-order-approval.md`
- Create: `evaluations/creating-product-requirements/migration-red/10-output.md`
- Create: `evaluations/creating-product-requirements/green/10-output.md`
- Modify: `skills/creating-product-requirements/SKILL.md`
- Modify: `skills/creating-product-requirements/references/review-and-handoff.md`
- Modify: `skills/creating-product-requirements/tests/test_skill_contract.py`
- Modify: `evaluations/creating-product-requirements/rubric.json`
- Modify: `evaluations/creating-product-requirements/migration-red/result.json`
- Modify: `evaluations/creating-product-requirements/green/result.json`
- Modify: `evaluations/registry.json`
- Modify: `evaluations/creating-product-requirements/green/01-output.md`
- Modify: `evaluations/creating-product-requirements/green/02-output.md`
- Modify: `evaluations/creating-product-requirements/green/03-output.md`
- Modify: `evaluations/creating-product-requirements/green/04-output.md`
- Modify: `evaluations/creating-product-requirements/green/05-output.md`
- Modify: `evaluations/creating-product-requirements/green/06-output.md`
- Modify: `evaluations/creating-product-requirements/green/07-output.md`
- Modify: `evaluations/creating-product-requirements/green/08-output.md`
- Modify: `evaluations/creating-product-requirements/green/09-output.md`
- Test: `skills/creating-product-requirements/tests/test_skill_contract.py`

**接口：**

- Consumes: 现有 canonical 八字段、PRD inspector 结果、approved transition 和本规格的八字段标签/值/`unknown`/空值映射。
- Produces: 回复末尾唯一八行中文纯文本视图；下游 `creating-development-specs-and-plans` 仍接收冻结的英文 canonical 八字段，中文映射校验失败时不选择下游。

**测试方式：** 先用本地契约测试和 case 10 固定中文后缀、全角冒号、字段顺序、单一块、合法 `unknown` 逐字段覆盖及 fail-closed；观察当前英文输出失败，再做最小 skill 规则修改。

- [ ] RED：开始修改时先把 registry 中本 skill 的 stage 设为 `implemented`，把旧 GREEN review 状态设为 `pending` 并删除旧 reviewer/date，使旧批准明确失效；然后在 `test_skill_contract.py` 增加八字段中文标签顺序、语境值、topic/scope/confidence/confirmation/requirements approval/review 的合法 `unknown`、空路径/主题、无英文用户可见后缀、canonical 下游传递和映射前置校验断言，新增 case 10 与 rubric criterion。
- [ ] Verify RED：运行 `.venv/bin/python -m unittest discover -s skills/creating-product-requirements/tests -v`；预期新增中文交接测试因当前英文字段合同失败，既有无关测试仍通过。
- [ ] Verify RED：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase current-skill-red --case evaluations/creating-product-requirements/cases/10-chinese-handoff-status.md --skill-dir skills/creating-product-requirements --output-root work/evaluations/creating-product-requirements/current-red-10`；预期输出仍为英文八字段并命中新中文 criterion 的可观察失败。将脱敏选中输出与结构化 RED 结果写入版本化 evidence，保留旧 RED 文件。
- [ ] GREEN：最小修改 `SKILL.md` 和 `references/review-and-handoff.md`，明确 canonical 构造/验证/冻结、中文视图预生成与完整性校验、成功后下游选择、映射失败例外和唯一中文八字段输出；不增加脚本或依赖。
- [ ] REFACTOR：只消除目标 skill 内重复措辞；保持自包含，不抽取跨 skill 运行时依赖。完成后冻结本 Task 最终生产文本，独立评审前保持 registry 为 `implemented`、GREEN review 为 `pending`；以下全部 Verify GREEN 均针对该最终版本。
- [ ] Verify GREEN：运行 `.venv/bin/python -m unittest discover -s skills/creating-product-requirements/tests -v`；预期全部通过。
- [ ] Verify GREEN：使用全新 evaluation Agent 分别对当前全部 case 运行 `--phase green`。精确 case 清单为 `01-confidence-gate.md`、`02-summary-confirmation.md`、`03-scope-and-topic.md`、`04-prd-technical-boundary.md`、`05-review-and-approval.md`、`06-path-priority.md`、`07-existing-prd-unknown.md`、`08-approved-handoff.md`、`09-approved-auto-spec-transition.md`、`10-chinese-handoff-status.md`，均位于 `evaluations/creating-product-requirements/cases/`；每次固定使用 `--skill-dir skills/creating-product-requirements`，输出目录依次为 `work/evaluations/creating-product-requirements/green-01` 至 `green-10`。预期十个 case 均生成新的原始输出、脱敏版本化输出和结构化判据，所有用户可见八字段均为中文，既有产品门禁仍通过；最终 `green/result.json` 精确汇总 01–10。
- [ ] Verify GREEN：在 registry 仍为 `implemented` 且 GREEN review 仍为 `pending` 时运行 `.venv/bin/python scripts/validate_repo.py --evidence-only creating-product-requirements`；预期 current RED、01–10 完整 GREEN 和 rubric 对齐。
- [ ] 文档同步：本任务只更新目标 skill 自包含契约和其评估证据；公共跨 skill 文档留到 Task 4。
- [ ] 任务级独立评审：由未参与实现的独立评审者检查 Task 1 最新 diff、RED/GREEN 原始证据、approved transition、合法 `unknown` 和无兄弟依赖；修复后重跑验证并由同一评审者复审。只有评审 `APPROVED` 后，主代理才写回 GREEN reviewer/date 并把 registry stage 设为 `review-approved`，运行 `.venv/bin/python scripts/validate_repo.py`；同一评审者再核验最新元数据、diff 与严格 validator 为 `APPROVED`，才能进入 Task 2。

### Task 2: 中文化技术规格与计划十四字段交接

**精确文件：**

- Create: `evaluations/creating-development-specs-and-plans/cases/14-chinese-handoff-status.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/14-chinese-handoff-status/docs/requirements/2026-07-12-order-approval.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/14-chinese-handoff-status/docs/specs/2026-07-12-order-approval-design.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/14-chinese-handoff-status/docs/plans/2026-07-12-order-approval.md`
- Create: `evaluations/creating-development-specs-and-plans/migration-red/14-output.md`
- Create: `evaluations/creating-development-specs-and-plans/green/14-output.md`
- Modify: `skills/creating-development-specs-and-plans/SKILL.md`
- Modify: `skills/creating-development-specs-and-plans/references/review-and-handoff.md`
- Modify: `skills/creating-development-specs-and-plans/tests/test_skill_contract.py`
- Modify: `evaluations/creating-development-specs-and-plans/rubric.json`
- Modify: `evaluations/creating-development-specs-and-plans/migration-red/result.json`
- Modify: `evaluations/creating-development-specs-and-plans/green/result.json`
- Modify: `evaluations/registry.json`
- Modify: `evaluations/creating-development-specs-and-plans/green/01-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/02-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/03-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/04-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/05-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/06-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/07-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/08-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/09-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/10-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/11-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/12-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/13-output.md`
- Test: `skills/creating-development-specs-and-plans/tests/test_skill_contract.py`
- Test: `skills/creating-development-specs-and-plans/tests/test_inspect_product_requirements.py`

**接口：**

- Consumes: 经 PRD inspector 验证的英文 canonical 前八字段、spec 用户/独立评审状态、plan 路径与三态评审状态、双门状态。
- Produces: 回复末尾唯一十四行中文纯文本视图；英文 canonical 快照仍用于路由，plan 未创建/未通过/已通过/未知按 `plan_path` 与 `plan_review_status` 联合映射。

**测试方式：** 先固定十四字段中文后缀和 plan 跨字段语义，确认当前英文合同 RED；再只修改当前 skill 的自包含交接规则。

- [ ] RED：开始修改时先把 registry 中本 skill 的 stage 设为 `implemented`，把旧 GREEN review 设为 `pending` 并删除旧 reviewer/date；然后新增字段顺序与中文标签断言，逐项覆盖 requirements 合法 `unknown`、spec approval/review 仅允许 `pending | approved`、可靠默认路径、plan `null + not-approved` 为“未开始”、既有计划 `not-approved/approved/unknown` 为“未通过/已通过/未知”，以及映射失败在路由能力选择前关闭。
- [ ] Verify RED：运行 `.venv/bin/python -m unittest discover -s skills/creating-development-specs-and-plans/tests -v`；预期新增中文十四字段测试因当前英文合同失败。
- [ ] Verify RED：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase current-skill-red --case evaluations/creating-development-specs-and-plans/cases/14-chinese-handoff-status.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/current-red-14`；预期观察英文十四字段或缺少映射前置校验的失败，并保存脱敏 evidence。
- [ ] GREEN：最小修改 `SKILL.md` 和 `references/review-and-handoff.md`，保留英文 canonical schema 与门禁计算，增加中文十四字段视图、逐字段允许集、plan 联合映射、映射失败例外和下游路由前预校验。
- [ ] REFACTOR：保持本 skill 自包含，复用其现有 canonical 字段表，不读取 PRD 或 prompt skill 源码；完成后冻结最终生产文本，独立评审前不写 `review-approved`，以下全部 Verify GREEN 均针对该最终版本。
- [ ] Verify GREEN：运行 `.venv/bin/python -m unittest discover -s skills/creating-development-specs-and-plans/tests -v`；预期全部通过。
- [ ] Verify GREEN：使用全新 evaluation Agent 分别对当前全部 case 运行 `--phase green`。精确 case 清单为 `01-approval-gate.md`、`02-explicit-paths.md`、`03-review-pressure.md`、`04-default-paths.md`、`05-unknown-review.md`、`06-approved-handoff.md`、`07-spec-review-blocked.md`、`08-ambiguous-topic.md`、`09-prd-required.md`、`10-prd-state-validation.md`、`11-technical-spec-boundary.md`、`12-approved-plan-auto-routing.md`、`13-downstream-prd-revalidation-failure.md`、`14-chinese-handoff-status.md`，均位于 `evaluations/creating-development-specs-and-plans/cases/`；每次固定使用 `--skill-dir skills/creating-development-specs-and-plans`，输出目录依次为 `work/evaluations/creating-development-specs-and-plans/green-01` 至 `green-14`。预期十四个 case 均生成新的原始输出、脱敏版本化输出和结构化判据，中文十四字段与既有门禁同时满足；最终 `green/result.json` 精确汇总 01–14。
- [ ] Verify GREEN：在 registry 为 `implemented`、GREEN review 为 `pending` 时运行 `.venv/bin/python scripts/validate_repo.py --evidence-only creating-development-specs-and-plans`；预期 current RED、01–14 完整 GREEN 与 rubric 对齐。
- [ ] 文档同步：本任务只更新当前 skill 与评估证据；公共文档留到 Task 4。
- [ ] 任务级独立评审：由未参与实现的独立评审者检查 plan 联合状态、spec 允许集、下游 PRD 复验失败、实施门禁和 RED/GREEN；修复、验证并由同一评审者复审。只有评审 `APPROVED` 后写回 GREEN reviewer/date、把 registry 设为 `review-approved`，运行严格 `.venv/bin/python scripts/validate_repo.py`，并由同一评审者再次核验最新元数据、diff 与严格结果为 `APPROVED`，才能进入 Task 3。

### Task 3: 中文化自动会话路由后缀并保护提示词复制边界

**精确文件：**

- Create: `evaluations/generating-development-prompts/cases/04-chinese-handoff-and-copy-stress.md`
- Create: `evaluations/generating-development-prompts/migration-red/04-output.md`
- Create: `evaluations/generating-development-prompts/green/04-output.md`
- Modify: `skills/generating-development-prompts/SKILL.md`
- Modify: `skills/generating-development-prompts/references/session-routing-policy.md`
- Modify: `skills/generating-development-prompts/tests/test_skill_contract.py`
- Modify: `skills/generating-development-prompts/tests/test_render_prompt.py`
- Modify: `evaluations/generating-development-prompts/rubric.json`
- Modify: `evaluations/generating-development-prompts/migration-red/result.json`
- Modify: `evaluations/generating-development-prompts/green/result.json`
- Modify: `evaluations/registry.json`
- Modify: `evaluations/generating-development-prompts/green/01-output.md`
- Modify: `evaluations/generating-development-prompts/green/02-output.md`
- Modify: `evaluations/generating-development-prompts/green/03-output.md`
- Test: `skills/generating-development-prompts/tests/test_skill_contract.py`
- Test: `skills/generating-development-prompts/tests/test_render_prompt.py`
- Preserve unchanged: `skills/generating-development-prompts/scripts/render_prompt.py`
- Preserve unchanged: `skills/generating-development-prompts/assets/development-prompt.md`

**接口：**

- Consumes: 已验证英文 canonical 十四字段快照、三态路由证据、renderer JSON 输入和动态 fence stdout。
- Produces: `current-session`、`new-session`、`blocked` 自动路由均以同一预验证中文十四字段视图结束；`new-session` 代码框正文与 renderer stdout 内部正文逐字一致，状态块在 fence 外；无上游快照的手动请求行为不变。

**测试方式：** 先在 skill 合同、renderer 回归和 case 04 中固定“先映射校验、后路由/renderer”“中文后缀在 fence 外”“动态 fence 内正文逐字不变”，确认当前英文后缀 RED；生产修改只限 skill/policy 文本，不修改 renderer。

- [ ] RED：开始修改时先把 registry 中本 skill 的 stage 设为 `implemented`，把旧 GREEN review 设为 `pending` 并删除旧 reviewer/date；然后增加三条自动路由的中文后缀契约、唯一字段行、最后一行、映射失败无 renderer 调用、手动请求兼容断言，在 `test_render_prompt.py` 使用中文、English、café、naïve、Δ、🚀、全角标点、长路径和连续反引号压力正文，按动态 fence 提取 body 并逐字比较。
- [ ] Verify RED：运行 `.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v`；预期 skill 中文后缀新增测试失败，既有 renderer 字节级正文测试保持通过，从而证明 RED 原因不是 renderer 回归。
- [ ] Verify RED：运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name generating-development-prompts --phase current-skill-red --case evaluations/generating-development-prompts/cases/04-chinese-handoff-and-copy-stress.md --skill-dir skills/generating-development-prompts --output-root work/evaluations/generating-development-prompts/current-red-04`；预期输出仍为英文十四字段或未在路由前验证中文映射，并保存脱敏 evidence。
- [ ] GREEN：最小修改 `SKILL.md` 与 `session-routing-policy.md`，在自动路由前预生成并验证中文视图，成功后执行三态路由并复用该视图；不修改 `render_prompt.py` 或 prompt template。
- [ ] REFACTOR：保持 policy 自包含，删除重复或可能让 renderer 承担状态渲染的措辞；完成后冻结最终生产文本，独立评审前不写 `review-approved`，以下全部 Verify GREEN 均针对该最终版本。
- [ ] Verify GREEN：运行 `.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v`；预期全部通过，renderer 压力正文逐字一致。
- [ ] Verify GREEN：使用全新 evaluation Agent 分别对 `evaluations/generating-development-prompts/cases/01-current-session.md`、`02-new-session.md`、`03-blocked.md`、`04-chinese-handoff-and-copy-stress.md` 运行 `--phase green`，固定使用 `--skill-dir skills/generating-development-prompts`，输出目录依次为 `work/evaluations/generating-development-prompts/green-01` 至 `green-04`。预期四个 case 均生成新的原始输出、脱敏版本化输出和结构化判据，三态中文后缀、动态 fence 与复制正文合同同时满足；最终 `green/result.json` 精确汇总 01–04。
- [ ] Verify GREEN：在 registry 为 `implemented`、GREEN review 为 `pending` 时运行 `.venv/bin/python scripts/validate_repo.py --evidence-only generating-development-prompts`；预期 current RED、01–04 完整 GREEN 与 rubric 对齐。
- [ ] 文档同步：本任务只更新 prompt skill 与评估证据；公开 breaking 说明留到 Task 4。
- [ ] 任务级独立评审：由未参与实现的独立评审者检查三态路由、映射前置门、renderer 未改、动态 fence/Unicode/反引号证据和手动兼容；修复、验证并由同一评审者复审。只有评审 `APPROVED` 后写回 GREEN reviewer/date、把 registry 设为 `review-approved`，运行严格 `.venv/bin/python scripts/validate_repo.py`，并由同一评审者再次核验最新元数据、diff 与严格结果为 `APPROVED`，才能进入 Task 4。

### Task 4: 锁定跨 skill 一致性并同步公开契约

**精确文件：**

- Create: 无
- Modify: `tests/test_repository_contract.py`
- Modify: `docs/workflow.md`
- Modify: `CHANGELOG.md`
- Modify: `README.md`（仅当现有用户入口需要最小状态显示说明；否则保持不变并记录证据）
- Test: `tests/test_repository_contract.py`
- Test: `tests/test_skill_evaluation_runner.py`

**接口：**

- Consumes: 三个已分别评审通过的自包含映射契约、版本化 GREEN 输出、现有英文 canonical 八到十四字段转换和 plugin 公共文档。
- Produces: 仓库级跨 skill 映射一致性门；公开文档明确“canonical 英文不变、用户状态块中文化、旧英文输入兼容、映射失败例外、renderer stdout 不变”的 breaking 边界。

**测试方式：** 先让仓库测试期望中文版本化后缀和三个 skill 重叠映射一致，确认旧英文仓库断言 RED；再更新公共契约并只读验证 Task 1–3 已批准的真实评估元数据，不在本任务改写它们。

- [ ] RED：更新或新增仓库测试，比较三个 skill 的重叠 canonical 字段中文标签和值，验证八/十四字段中文顺序、全角冒号、唯一性、最后一行、无用户可见英文字段后缀，并保留内部英文 canonical 映射与旧输入兼容断言。
- [ ] Verify RED：运行 `.venv/bin/python -m unittest tests.test_repository_contract -v`；预期旧英文版本化输出或未同步文档造成新增断言失败，失败范围与本功能一致。
- [ ] GREEN：同步 `docs/workflow.md` 与 `CHANGELOG.md`；CHANGELOG 将 breaking 变化限定为用户可见 handoff/status-block 回复后缀，明确 `render_prompt.py` stdout 字节合同、机器 canonical 和旧英文输入不变。检查 README 后只做必要的最小同步。不得修改 Task 1–3 已评审的 GREEN result 或 registry；若发现必须修改，返回对应 Task、失效其批准并交回原评审者复审。
- [ ] REFACTOR：移除重复映射断言的机械重复，但保留每个 skill 独立契约测试与仓库一致性门；不抽取运行时共享依赖。完成后冻结 Task 4 最终版本，以下 Verify GREEN 均针对该版本。
- [ ] Verify GREEN：运行 `.venv/bin/python -m unittest tests.test_repository_contract tests.test_skill_evaluation_runner -v`；预期全部通过。
- [ ] Verify GREEN：运行 `.venv/bin/python scripts/validate_repo.py`；预期三个 skill 均保持 `review-approved`、完整 evidence 与公共文档契约一致。
- [ ] 文档同步：完成 `docs/workflow.md`、`CHANGELOG.md` 和必要的 README 同步；不得把功能描述为已安装或已发布。
- [ ] 任务级独立评审：由未参与实现的独立评审者检查三 skill 一致性、breaking 边界、评估元数据和公共文档；修复、验证并由同一评审者复审至 `APPROVED`，再进入 Task 5。

### Task 5: 隔离 staging、单实例客户端复制与最终整体验证

**精确文件：**

- Create: 无版本化文件
- Modify: 无生产文件；如最终评审要求修复，回到对应 Task 的精确文件并重跑该 Task 全部验证
- Test: 三个受影响 skill 及其 tests、evaluations、`tests/test_repository_contract.py`、`tests/test_skill_evaluation_runner.py`
- Test: `scripts/validate_repo.py`
- Test: `.codex-plugin/plugin.json`
- Test: 当前单实例 Codex 客户端和本机剪贴板

**接口：**

- Consumes: Task 1 至 Task 4 最新完整 diff、全部 RED/GREEN 与任务评审证据、Unicode/长路径/连续反引号压力样本、当前已运行的 Codex 客户端。
- Produces: 临时隔离安装一致性证据、完整仓库验证、真实一键复制逐字比对证据和未参与实现者的整体 `APPROVED`；不产生 commit、真实安装或发布状态。

**测试方式：** 本任务不新增行为，运行完整回归和真实客户端验收。任何失败都先定位到对应 Task，修复后重跑受影响 Task 验证和同一评审者复审，再重新执行最终验证。

- [ ] 实施：确认 Task 1 至 Task 4 均有真实 `APPROVED`，当前 diff 仍包含原 workflow-handoff 基线且没有越权文件。运行 `.venv/bin/python -m unittest tests.test_repository_contract.RepositoryContractTests.test_skill_payloads_stage_independently_and_together tests.test_repository_contract.RepositoryContractTests.test_skill_staging_refuses_existing_destination_without_overwrite -v`；预期仓库 staging 合同把五个 skill 独立及整体放入全新临时目录、拒绝覆盖既有目标且不接触真实 `CODEX_HOME`。
- [ ] 验证：使用 `.venv/bin/python`（预期 Python 3.9）依次运行 `.venv/bin/python -m unittest discover -s skills/creating-product-requirements/tests -v`、`.venv/bin/python -m unittest discover -s skills/creating-development-specs-and-plans/tests -v`、`.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v`、`.venv/bin/python -m unittest discover -s skills/implementing-bounded-changes/tests -v`、`.venv/bin/python -m unittest discover -s skills/managing-agents-rules/tests -v`；预期全部通过。
- [ ] 验证：运行 `.venv/bin/python --version` 和 `python3.14 --version`，记录实际 3.9/3.14 解释器。依次运行 `python3.14 -m unittest discover -s skills/creating-product-requirements/tests -v`、`python3.14 -m unittest discover -s skills/creating-development-specs-and-plans/tests -v`、`python3.14 -m unittest discover -s skills/generating-development-prompts/tests -v`、`python3.14 -m unittest discover -s skills/implementing-bounded-changes/tests -v`、`python3.14 -m unittest discover -s skills/managing-agents-rules/tests -v`，再运行 `python3.14 -m unittest discover -s tests -v`；预期全部通过。不得为补齐 Python 3.14 环境安装 PyYAML 或其它依赖；如现有环境因缺少计划要求依赖而无法完成强制矩阵，记录准确错误并阻断完成。
- [ ] 验证：运行 `.venv/bin/python -m unittest discover -s tests -v`；预期仓库完整测试通过。
- [ ] 验证：运行 `.venv/bin/python scripts/validate_repo.py`；预期严格仓库验证通过且三个修改 skill 的 GREEN 评审元数据真实为 approved。
- [ ] 验证：依次运行 `.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/creating-product-requirements`、`.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/creating-development-specs-and-plans`、`.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/generating-development-prompts`、`.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/implementing-bounded-changes`、`.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/managing-agents-rules`；预期全部成功。
- [ ] 验证：运行 `.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" .`；预期完整五-skill plugin 验证成功。
- [ ] 验证：运行 `git diff --check`；预期退出码 0。再次运行 `git status --short --branch` 并与 Task 0 受保护基线比较；预期没有回滚既有 handoff 优化、没有越权生成物或真实安装副本。
- [ ] 验证：使用 Task 3 的压力 payload 生成 renderer 输出，按动态 fence 提取并保存在 `/private/tmp` 的预期正文；在当前会话展示该唯一代码框。复用当前已运行的单实例 Codex 客户端及其复制按钮，不启动第二个客户端或服务；复制后用本机 `pbpaste` 读取剪贴板，并对预期正文与实际正文执行逐字比较。预期完全一致，且实际内容不含外层 fence、`text` 语言标记、中文状态块、前导空格或末尾解释；剪贴板内容不得发送外部服务。
- [ ] 验证：若 UI 控制、复制按钮、剪贴板读取或逐字比较任一不可用，记录为阻断或明确未验证，不得用 renderer 单元测试替代真实客户端证据，也不得宣称整体完成。
- [ ] 文档同步：核对 README、`docs/workflow.md`、`CHANGELOG.md` 只陈述当前仓库事实；不写入“已安装”“已发布”或真实客户端验证通过，除非本 Task 已取得对应证据。
- [ ] 任务级独立评审：由未参与 Task 1 至 Task 4 实现的独立整体评审者检查批准范围、保护基线、完整 diff、测试、评估、临时 staging、单实例复制证据和禁止操作；发现问题时由同一评审者复审修订版，直到 `APPROVED`。只有整体验证和最终复审均通过后才可报告完成。

## 最终验证

- 保留每个 Task 的 RED 失败命令、符合预期的失败原因、GREEN 命令与结果、实际评审 agent name 和最终 verdict；不得用摘要替代原始可观察证据。
- 完整验证命令为五个 skill 在 Python 3.9 与 Python 3.14 下的测试、两个 staging 合同测试、`tests/` 全量测试、严格 `scripts/validate_repo.py`、五个官方 quick validator、完整 plugin validator 和 `git diff --check`；全部必须使用当前工作树新鲜运行结果。Python 3.14 的强制命令因现有依赖不可用而失败时不得安装依赖或静默跳过，必须阻断并报告。
- staging 仅使用全新临时 `CODEX_HOME`，验证后不复制到真实 `CODEX_HOME`。不得安装依赖、启动服务、创建第二个 Codex 实例、commit、push、tag、release 或发布。
- 客户端验收必须复用当前单实例，通过真实复制按钮取得剪贴板内容，并与 renderer 动态 fence 内正文逐字一致。无法取得这项证据时，最终状态只能是未完成或明确未验证，不能报告全部完成。
- 最终整体评审必须覆盖三个修改 skill 的完整 case GREEN 与 RED 证据、未修改的两个 skill 回归、Python 3.9/3.14 矩阵、五-skill staging/plugin、公开文档、当前未提交基线和禁止操作。整体评审未 `APPROVED` 时不得进入实施交接。
