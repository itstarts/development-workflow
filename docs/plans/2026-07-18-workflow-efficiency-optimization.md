---
document_type: implementation-plan
topic: workflow-efficiency-optimization
spec_path: docs/specs/2026-07-18-workflow-efficiency-optimization-design.md
spec_user_approval: approved
review_status: approved
reviewer: independent-plan-reviewer
reviewed_at: 2026-07-18
---

# 开发工作流效率优化实施计划

**目标：** 在不合并五个 skill、不改变 canonical 英文交接、批准门与三态路由的前提下，完成紧凑澄清、最多三问、references 渐进加载、确定性 handoff renderer、评估新鲜度、会话内 Agent inventory、统一验证和只读安装差异检查，并用本次开发自举验证优化流程。

**架构：** 三个受影响 skill 各自携带字节一致的 `render_handoff.py`，运行时不 import 兄弟 skill；仓库根 `validate_repo.py` 扩展 Git-aware freshness，`check.py` 负责编排 stage-aware 定向/完整验证，`verify_install.py` 只读比较 publishable payload。skill 的自然语言合同继续拥有阶段和门禁语义，确定性显示与校验由本地脚本执行。

**技术栈：** Markdown skill/reference/asset、Python 3.9+ 标准库 CLI、`unittest`、临时 Git fixture、现有 evaluation runner、官方 skill/plugin validator、Codex 只读独立评审角色。

## 全局约束

- 开始任何 production write 前重新确认项目规则并使用 `managing-agents-rules` 完成项目根规则前置检查；开始修改 skill 前完整使用系统 `skill-creator`。只修改本仓库，不修改 `~/.codex/skills` 已安装副本。
- 严格执行 Task 1 → Task 7。所有目标行为先由自动化合同或 current-skill 前向场景形成可观察 RED；生产修改后才运行 GREEN，不通过放宽断言、删除有效场景、静默兜底或刷新日期制造通过。
- 三个受影响 evaluation entry 在 production 修改前进入 `implemented`，当前独立评审 metadata 重置为 pending；只有最新完整 diff 取得真实独立 `APPROVED` 后才恢复 `review-approved`。
- 本计划不设置逐任务或逐 skill 独立评审。Task 1～6 使用自检和定向验证；Task 7 由一名未参与实现的 reviewer 覆盖最新完整 diff、三个 skill、evaluation、plugin、文档与 staging，并由同一 reviewer 对修订复审至 `APPROVED` 后停止。只有后续工作确实被未验证的 freshness 基础阻塞时，才新增一次仅覆盖该基础的中间里程碑评审。
- 本次开发从当前阶段开始 dogfood：只有普通非阻塞澄清使用紧凑三行状态，普通进度不新增状态分类；暂停、阻塞、批准和交接使用完整状态。问题按依赖最多三问，已加载规则不重复读取；新 renderer、freshness、`check.py` 验证通过后立即替代等价人工步骤。
- 文档改动始终纳入独立最终评审。本阶段不实现任何文档免评审，也不实现未来“纯格式或机械型轻量改动免评审”规则。
- 不改变 `discover_context.py`、`render_prompt.py` 的现有 CLI/schema/成功 stdout，不修改 `implementing-bounded-changes` 或 `managing-agents-rules` 的 production 行为，不增加依赖、网络、服务、数据库或持久化运行时状态。
- plugin 保持五个 skill 和未发布 `0.1.0`。不自动 commit、push、merge、rebase、tag、release、发布或写入真实 `CODEX_HOME`。
- `AGENTS.md` 的统一验证入口属于独立规则候选：只有 `managing-agents-rules` 展示证据、分类原因和精确 diff，并取得只对该 diff 有效的新批准后才能修改；拒绝或未批准不阻塞其它已批准范围。

### Task 1：冻结自动化 RED、前向 RED 与 evaluation 中间态

**精确文件：**

- Modify: `skills/creating-product-requirements/tests/test_skill_contract.py`
- Create: `skills/creating-product-requirements/tests/test_render_handoff.py`
- Modify: `skills/creating-development-specs-and-plans/tests/test_skill_contract.py`
- Create: `skills/creating-development-specs-and-plans/tests/test_render_handoff.py`
- Modify: `skills/generating-development-prompts/tests/test_skill_contract.py`
- Modify: `skills/generating-development-prompts/tests/test_render_prompt.py`
- Create: `skills/generating-development-prompts/tests/test_render_handoff.py`
- Create: `tests/test_handoff_renderer.py`
- Create: `tests/test_evidence_freshness.py`
- Create: `tests/test_check.py`
- Create: `tests/test_verify_install.py`
- Modify: `evaluations/registry.json`
- Modify: `evaluations/creating-product-requirements/rubric.json`
- Create: `evaluations/creating-product-requirements/cases/11-ordinary-compact.md`
- Create: `evaluations/creating-product-requirements/cases/12-independent-question-batch.md`
- Create: `evaluations/creating-product-requirements/cases/13-dependent-question.md`
- Create: `evaluations/creating-product-requirements/cases/14-progressive-reference-loading.md`
- Create: `evaluations/creating-product-requirements/cases/15-progress-only-full.md`
- Create: `evaluations/creating-product-requirements/migration-red/11-output.md`
- Modify: `evaluations/creating-product-requirements/migration-red/result.json`
- Modify: `evaluations/creating-product-requirements/green/result.json`
- Modify: `evaluations/creating-development-specs-and-plans/rubric.json`
- Create: `evaluations/creating-development-specs-and-plans/cases/15-ordinary-compact.md`
- Create: `evaluations/creating-development-specs-and-plans/cases/16-independent-question-batch.md`
- Create: `evaluations/creating-development-specs-and-plans/cases/17-dependent-question.md`
- Create: `evaluations/creating-development-specs-and-plans/cases/18-progressive-reference-loading.md`
- Create: `evaluations/creating-development-specs-and-plans/cases/19-spec-approval-full.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/19-spec-approval-full/docs/requirements/2026-07-12-order-approval.md`
- Create: `evaluations/creating-development-specs-and-plans/fixtures/19-spec-approval-full/docs/specs/2026-07-12-order-approval-design.md`
- Create: `evaluations/creating-development-specs-and-plans/migration-red/15-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/migration-red/result.json`
- Modify: `evaluations/creating-development-specs-and-plans/green/result.json`
- Modify: `evaluations/generating-development-prompts/rubric.json`
- Create: `evaluations/generating-development-prompts/cases/05-agent-inventory-refresh.md`
- Create: `evaluations/generating-development-prompts/cases/06-progressive-reference-loading.md`
- Create: `evaluations/generating-development-prompts/migration-red/05-output.md`
- Modify: `evaluations/generating-development-prompts/migration-red/result.json`
- Modify: `evaluations/generating-development-prompts/green/result.json`

**接口：**

- Consumes: 已批准 spec 中的 exact renderer schema、freshness 状态模型、回复分类、问题依赖和 Agent inventory 合同。
- Produces: 因目标脚本/行为尚不存在而失败的离线测试；三个由生产修改前全新 Agent 产生的 current RED；三个 registry entry 的真实 `implemented` 中间态与 pending review metadata。

**测试方式：** 先固定 exact assertions，再运行现有 production。RED 必须来自缺少 `render_handoff.py`、现有所有回复仍为 full、逐问/全量 reference 行为、重复 Agent inventory 或缺少 freshness/check/verify 接口；不得来自 fixture、import 或命令错误。

- [ ] RED：为三个本地 renderer 测试和仓库一致性测试固定 strict UTF-8/no-BOM/LF-only、任意层 duplicate key、`NaN | ±Infinity`、多 JSON value、未配对 surrogate、U+0085/U+2028/U+2029、exact top-level/canonical field set、八到十四字段改名、gate truth table、compact 三行/full bytes、额外字段、RFC 6901 pointer、错误码/排序和无 partial stdout；以 binary subprocess 调用各 skill 自身脚本，不 import 兄弟模块。
- [ ] RED：在三个 `test_skill_contract.py` 及 prompt renderer 测试中固定 ordinary/checkpoint/blocked/routing 分类、需求摘要确认 full、spec 批准请求 full、progress-only 不得 compact 且保守 full、最多三问、渐进 reference、旧英文输入、prompt dynamic fence 不变、Agent inventory 一次读取和条件刷新。
- [ ] RED：在四个新仓库测试文件固定 clean/dirty/non-Git freshness、`implemented | review-approved` 多目标 check 矩阵、validator 路径优先级、timeout/exit code，以及 install payload 的 missing/extra/different/symlink/只读边界。
- [ ] Verify RED：分别运行三个受影响 skill unittest 与四个新仓库测试模块；预期新增用例失败，既有无关用例保持通过，并保存关键失败原因。
- [ ] 前向 RED：冻结新 cases 与 rubric，在 production 修改前分别运行：
  - `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase current-skill-red --case evaluations/creating-product-requirements/cases/11-ordinary-compact.md --skill-dir skills/creating-product-requirements --output-root work/evaluations/creating-product-requirements/current-red-11`
  - `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase current-skill-red --case evaluations/creating-development-specs-and-plans/cases/15-ordinary-compact.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/current-red-15`
  - `.venv/bin/python scripts/run_skill_evaluations.py --skill-name generating-development-prompts --phase current-skill-red --case evaluations/generating-development-prompts/cases/05-agent-inventory-refresh.md --skill-dir skills/generating-development-prompts --output-root work/evaluations/generating-development-prompts/current-red-05`
- [ ] RED 证据：确认三次运行有效且失败命中冻结判据；只把脱敏选中输出写入对应 `migration-red/`，原始 trace 保留在忽略的 `work/`。
- [ ] 中间态：将三个 registry stage 设为 `implemented`；三个 `green/result.json` 的 review 改为 pending 并移除旧 reviewer/date，不删除旧 GREEN 作为历史当前文件，等待 Task 6 以新鲜输出替换。
- [ ] 文档同步：无；本任务只建立测试与评估前置，不改 production 或公开事实。

### Task 2：实现 freshness、统一 check 与只读安装比较基础

**精确文件：**

- Modify: `scripts/validate_repo.py`
- Create: `scripts/check.py`
- Create: `scripts/verify_install.py`
- Test: `tests/test_evidence_freshness.py`
- Test: `tests/test_check.py`
- Test: `tests/test_verify_install.py`
- Verify only: `tests/test_repository_contract.py`

**接口：**

- `validate_repo.py` produces: `--require-freshness`、与 `--evidence-only` 互斥的 `--reviewed-skill`、clean ancestry/dirty bundle/non-Git 的确定结果。
- `check.py` consumes: `--skill` 或 `--full`、`--timeout-seconds`、可选 official validator path；produces: 固定顺序汇总及 `0 | 1 | 2` 退出码。
- `verify_install.py` consumes: 必填 `--codex-home` 与可重复 `--skill`；produces: publishable payload 的 missing/extra/different 分类及 `0 | 1 | 2` 退出码，不修改目标。

**测试方式：** 使用临时 Git 仓库、临时 registry、虚构 validator 和临时 `CODEX_HOME`；不读写真实用户安装，不依赖网络或 plugin cache。

- [ ] GREEN：在 `validate_repo.py` 复用 `production_files()`，实现 spec 的 path categories、`fresh_cases` 结构、clean ancestor chain、dirty worktree bundle、delete/rename/untracked、creation-only 升级、stage-aware 目标参数和确定诊断。
- [ ] GREEN：实现 `check.py` 的前置验证、官方 validator 三层解析、每进程 300 秒默认 timeout、无 shell argv、并发捕获和固定顺序汇总；多 skill 时仓库 tests 只运行一次、stage-aware validator 每目标一次。
- [ ] GREEN：实现 `verify_install.py` 的根 `SKILL.md` 加四个 publishable 子目录边界；忽略约定缓存，边界内 symlink/非普通文件失败关闭，比较过程中保持目标只读。
- [ ] Verify GREEN：运行 `.venv/bin/python -m unittest tests.test_evidence_freshness tests.test_check tests.test_verify_install -v`；预期全部通过。
- [ ] Freshness RED 自举：运行 `.venv/bin/python scripts/validate_repo.py --require-freshness`，预期当前旧 GREEN/评审不能证明三个受影响 production 为新鲜而失败；保留诊断，不把该预期 RED 表述为仓库完成。
- [ ] REFACTOR：共用 registry/publishable path 边界与稳定结果类型，保持三个 CLI 标准库实现、Python 3.9 兼容；重新运行目标测试。
- [ ] 文档同步：公开用法延后 Task 6；本任务只提供已测试基础。

### Task 3：实现三个自包含、字节一致的 handoff renderer

**精确文件：**

- Create: `skills/creating-product-requirements/scripts/render_handoff.py`
- Create: `skills/creating-development-specs-and-plans/scripts/render_handoff.py`
- Create: `skills/generating-development-prompts/scripts/render_handoff.py`
- Test: `skills/creating-product-requirements/tests/test_render_handoff.py`
- Test: `skills/creating-development-specs-and-plans/tests/test_render_handoff.py`
- Test: `skills/generating-development-prompts/tests/test_render_handoff.py`
- Test: `tests/test_handoff_renderer.py`

**接口：**

- Consumes: stdin 单一 JSON object，字段为 `schema_version`、`handoff_schema`、`view`、`canonical`、`stage`、`next_step`。
- Produces: 成功时唯一 compact 三行或 full 八/十四行，全部使用严格 UTF-8、行间 LF 和唯一末尾 LF；失败时 stdout 为空、stderr 单行 JSON 和稳定 `2..7` 退出码。

**测试方式：** 三个 skill 本地测试独立执行自身副本；仓库测试用相同 fixtures 通过 subprocess 比较三份文件 bytes 与 stdout/stderr bytes。

- [ ] GREEN：先实现一份 Python 3.9 标准库 renderer，再通过受控 patch 创建另外两份完全相同副本；不 import 仓库根或兄弟 skill。
- [ ] GREEN：实现无 BOM 严格 UTF-8 JSON parser，拒绝任意层重复 key、非标准数值、多 value 和未配对 surrogate；实现 exact field set/type/value/path/topic/plan context 校验、八到十四字段改名、双 gate truth table、compact 三阶段与 next-step Unicode line-break 边界、full 十四行映射、LF-only 输出、RFC 6901 error pointer 和稳定错误层级。
- [ ] Verify GREEN：运行三个本地 `test_render_handoff.py` 与 `tests.test_handoff_renderer`；预期三份脚本字节一致、相同输入输出一致、非法输入无 partial stdout。
- [ ] REFACTOR：删除 renderer 内重复分支，保持 mappings/data schema 单一；确认 refactor 后三份 bytes 仍一致并重跑目标测试。
- [ ] Freshness 中间结果：严格 freshness 仍应因缺少当前 GREEN bundle 失败；该失败符合 Task 6 前的 `implemented` 状态。
- [ ] 文档同步：无；调用方合同在 Task 4/5 接入，公共说明在 Task 6 同步。

### Task 4：优化 PRD 与 spec/plan 两个文档工作流

**精确文件：**

- Modify: `skills/creating-product-requirements/SKILL.md`
- Modify: `skills/creating-product-requirements/references/discovery-and-confidence.md`
- Modify: `skills/creating-product-requirements/references/review-and-handoff.md`
- Test: `skills/creating-product-requirements/tests/test_skill_contract.py`
- Modify: `skills/creating-development-specs-and-plans/SKILL.md`
- Modify: `skills/creating-development-specs-and-plans/references/discovery-and-clarification.md`
- Modify: `skills/creating-development-specs-and-plans/references/review-and-handoff.md`
- Test: `skills/creating-development-specs-and-plans/tests/test_skill_contract.py`
- Verify only: `skills/creating-product-requirements/references/document-contract.md`
- Verify only: `skills/creating-development-specs-and-plans/references/document-contracts.md`
- Verify only: both skills' `agents/openai.yaml`

**接口：**

- Consumes: 当前完整 canonical 八/十四字段、reply classification、问题依赖、阶段前置条件。
- Produces: ordinary clarification 的 compact 三行，topic 来自 canonical、stage/next_step 来自已验证当前回复上下文；checkpoint/blocked/routing 的现有 full 状态；每轮一至三个互不依赖问题；首次相关动作前才加载对应 reference。

**测试方式：** 合同测试固定 SKILL/reference 的阶段前置和本地 renderer 调用；新鲜 Agent cases 在 Task 6 验证实际回复与 reference read trace。

- [ ] GREEN：PRD skill 首次只加载 discovery；首次写文档前加载 document contract；首次确认、评审、批准、full 状态或下游转换前加载 review/handoff。普通问题最多三项且必须互不依赖，无法分类时保守 full。
- [ ] GREEN：spec/plan skill 使用同一分层原则，保持 inspector、spec 双批准、plan 真实评审和自动路由门；普通技术澄清 compact，批准/阻塞/文档阶段结束/路由 full。
- [ ] GREEN：两个文档 workflow 都把不含澄清问题的 progress-only 回复排除在 `ordinary-clarification` 外；当它不属于其它已定义类型时按现有保守规则使用 full，不新增“普通进度 compact”类型。
- [ ] GREEN：两个 review/handoff references 保留 canonical 与失败边界，但调用本地 renderer，不再重复充当可执行 mapping 权威；旧英文 handoff 继续有效。
- [ ] Verify GREEN：运行两个 skill 的完整 unittest 与各自 `quick_validate.py`；预期通过。运行 `check.py --skill` 此时仍可因 GREEN evidence 未刷新而诚实失败，不将其跳过。
- [ ] REFACTOR：压缩重复说明但不删除阶段所需 hard gate；检查 metadata description 未变时不修改 `openai.yaml`。
- [ ] 文档同步：skill 内合同在本任务完成；公开说明延后 Task 6，避免提前发布未完成整链事实。

### Task 5：优化 prompt skill 的 reference 路由与 Agent inventory

**精确文件：**

- Modify: `skills/generating-development-prompts/SKILL.md`
- Modify: `skills/generating-development-prompts/references/discovery-policy.md`
- Modify: `skills/generating-development-prompts/references/permission-policy.md`
- Modify: `skills/generating-development-prompts/references/session-routing-policy.md`
- Modify: `skills/generating-development-prompts/assets/development-prompt.md`
- Test: `skills/generating-development-prompts/tests/test_skill_contract.py`
- Test: `skills/generating-development-prompts/tests/test_render_prompt.py`
- Verify only: `skills/generating-development-prompts/scripts/discover_context.py`
- Verify only: `skills/generating-development-prompts/scripts/render_prompt.py`
- Verify only: `skills/generating-development-prompts/tests/test_discover_context.py`
- Verify only: `skills/generating-development-prompts/agents/openai.yaml`

**接口：**

- Consumes: 自动十四字段或手动 prompt 入口、discovery 结果、会话权限/Agent 可用事实。
- Produces: 按入口渐进加载的 discovery/permission/routing policy；自动路由前由本地 renderer 验证 full 状态；目标会话首次委派读取一次 Agent inventory，只有明确条件才刷新一次。

**测试方式：** 保持 discovery JSON schema 与 prompt dynamic fence bytes 合同；只改变模板正文中的 Agent inventory/风险批次评审说明和 skill 的 reference 读取时点。

- [ ] GREEN：SKILL 先分类入口并加载 discovery；只有 discovery 成功且需要权限矩阵时加载 permission；只有自动路由、带上游状态的阻塞或 full 状态时加载 routing。手动无上游请求不伪造 compact/full handoff。
- [ ] GREEN：自动三态继续输出完整十四字段，并在路由前调用本地 renderer；不改变 `current-session | new-session | blocked` 判据、手动兼容或 `render_prompt.py` stdout。
- [ ] GREEN：`development-prompt.md` 改为目标会话首次委派读取 `name/description/reliability`，普通后续委派复用；配置变化、读取失败、按名称启动失败、可观察冲突或用户显式要求才刷新一次，仍不可用即报告能力缺口。
- [ ] GREEN：模板继续按风险边界决定可选里程碑评审，集成后只评审最新完整 diff，不因任务数量逐项评审。
- [ ] Verify GREEN：运行 prompt skill 全部 unittest 和 `quick_validate.py`；单独运行 discover tests，确认 schema/退出码不变；运行 renderer 测试确认 full 状态一致。
- [ ] REFACTOR：删除重复 inventory 扫描和无条件 reference 读取表述，保持 skill description 与 `openai.yaml` 一致；无触发描述变化时不修改 metadata。
- [ ] 文档同步：skill 内 reference/asset 完成；公开事实统一在 Task 6 更新。

### Task 6：生成新鲜 GREEN、同步公开文档并处理规则候选

**精确文件：**

- Modify: `evaluations/creating-product-requirements/green/02-output.md`
- Modify: `evaluations/creating-product-requirements/green/05-output.md`
- Modify: `evaluations/creating-product-requirements/green/08-output.md`
- Modify: `evaluations/creating-product-requirements/green/09-output.md`
- Modify: `evaluations/creating-product-requirements/green/10-output.md`
- Create: `evaluations/creating-product-requirements/green/11-output.md`
- Create: `evaluations/creating-product-requirements/green/12-output.md`
- Create: `evaluations/creating-product-requirements/green/13-output.md`
- Create: `evaluations/creating-product-requirements/green/14-output.md`
- Create: `evaluations/creating-product-requirements/green/15-output.md`
- Modify: `evaluations/creating-product-requirements/green/result.json`
- Modify: `evaluations/creating-development-specs-and-plans/green/07-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/12-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/13-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/14-output.md`
- Create: `evaluations/creating-development-specs-and-plans/green/15-output.md`
- Create: `evaluations/creating-development-specs-and-plans/green/16-output.md`
- Create: `evaluations/creating-development-specs-and-plans/green/17-output.md`
- Create: `evaluations/creating-development-specs-and-plans/green/18-output.md`
- Create: `evaluations/creating-development-specs-and-plans/green/19-output.md`
- Modify: `evaluations/creating-development-specs-and-plans/green/result.json`
- Modify: `evaluations/generating-development-prompts/green/01-output.md`
- Modify: `evaluations/generating-development-prompts/green/02-output.md`
- Modify: `evaluations/generating-development-prompts/green/03-output.md`
- Modify: `evaluations/generating-development-prompts/green/04-output.md`
- Create: `evaluations/generating-development-prompts/green/05-output.md`
- Create: `evaluations/generating-development-prompts/green/06-output.md`
- Modify: `evaluations/generating-development-prompts/green/result.json`
- Modify: `README.md`
- Modify: `docs/workflow.md`
- Modify: `docs/agent-development.md`
- Modify: `docs/install.md`
- Modify: `CHANGELOG.md`
- Verify and modify only if final capability text is inaccurate: `.codex-plugin/plugin.json`
- Conditional, only after separate exact-diff approval: `AGENTS.md`

**接口：**

- Consumes: Task 1 固定 rubric/cases、最终 production payload、全新且看不到 expected/RED 分析的 Agents。
- Produces: 三个包含非空 `fresh_cases` 的 pending GREEN result、对应新鲜输出、公开迁移说明、统一验证与只读安装用法，以及可选的已批准项目规则 diff。

**测试方式：** 每个 case 独立运行 evaluation runner，原始 trace 留在 `work/`，版本库只保存脱敏 final；任何 invalid run 重跑时不保留失败 attempt 到版本库。

- [ ] GREEN 前向：为 PRD cases `02,05,08,09,10,11,12,13,14,15`、spec/plan cases `07,12,13,14,15,16,17,18,19`、prompt cases `01,02,03,04,05,06` 分别运行 `--phase green`。每次使用对应 case 文件和目标 `--skill-dir`；output root 精确使用 `work/evaluations/creating-product-requirements/green-{02,05,08,09,10,11,12,13,14,15}`、`work/evaluations/creating-development-specs-and-plans/green-{07,12,13,14,15,16,17,18,19}`、`work/evaluations/generating-development-prompts/green-{01,02,03,04,05,06}` 中与 case id 相同的单一目录，不把 brace 表达式作为一条 runner 参数。
- [ ] 关键 full 证据命令：分别运行 `.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase green --case evaluations/creating-product-requirements/cases/02-summary-confirmation.md --skill-dir skills/creating-product-requirements --output-root work/evaluations/creating-product-requirements/green-02`、`.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase green --case evaluations/creating-product-requirements/cases/15-progress-only-full.md --skill-dir skills/creating-product-requirements --output-root work/evaluations/creating-product-requirements/green-15`、`.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase green --case evaluations/creating-development-specs-and-plans/cases/19-spec-approval-full.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/green-19`；三者必须分别证明摘要确认 full、progress-only 非 compact/full、spec 批准请求 full。
- [ ] GREEN 结果：脱敏替换/新增上述 output；三个 `green/result.json` 的 cases 与 rubric 完整一致，`fresh_cases` 精确记录本轮列表，review 保持 pending，不预填 reviewer/date。
- [ ] 统一定向门：运行 `.venv/bin/python scripts/check.py --skill creating-product-requirements --skill creating-development-specs-and-plans --skill generating-development-prompts`；预期三个 `implemented` 目标通过 stage-aware evidence-only freshness、skill tests、仓库 tests 和 official skill validators。
- [ ] 文档同步：README/workflow 说明固定三行 compact/full、最多三问、渐进加载和兼容边界；agent-development 说明 freshness、统一 check、一次完整评审；install 说明只读 compare 和不覆盖边界；CHANGELOG 在未发布 `0.1.0` 明确“普通澄清由 full 改为三行 compact”的用户可见 breaking change及迁移。
- [ ] Manifest：验证现有 manifest 已准确概述五个 skill 时保持不变；只有描述与最终能力不一致才做最小文字修改，version 和 skill path 不变。
- [ ] 规则候选：通过 `managing-agents-rules` 展示把新统一命令纳入 `AGENTS.md` 维护入口的证据、分类原因和精确 diff；等待用户对该 diff 单独批准。只有批准后才 apply patch 并读回验证；未批准则保持现有 `AGENTS.md`，公开 docs 中的 convenience 命令仍有效。
- [ ] REFACTOR：检查三个 references 不再复制可执行 mapping、公开文档无陈旧“所有普通回复都 full”说明、无 TODO/本机路径/用户 task id；重跑统一定向门。

### Task 7：完整验证、一次独立评审、staging 与完成门

**精确文件：**

- Modify after real reviewer approval: `evaluations/creating-product-requirements/green/result.json`
- Modify after real reviewer approval: `evaluations/creating-development-specs-and-plans/green/result.json`
- Modify after real reviewer approval: `evaluations/generating-development-prompts/green/result.json`
- Modify after real reviewer approval: `evaluations/registry.json`
- Verify only: all files changed by Tasks 1～6
- Do not modify: real `${CODEX_HOME:-$HOME/.codex}` installation

**接口：**

- Consumes: 最新完整 diff、三个 current RED/新鲜 GREEN、stage-aware 定向验证、文档和 plugin evidence。
- Produces: 一个独立 reviewer 的收敛 verdict、三个真实 review-approved evidence、`check.py --full` 结果、Python 3.9/3.14 结果及临时 staging 比较证据。

**测试方式：** 先在 `implemented` 状态完成定向验证、Python 双版本和临时 staging，再评审完整 diff；reviewer 批准后才写 metadata/stage，随后执行 full 验证并让同一 reviewer 复查该写回与最终证据。

- [ ] 工作区检查：读取最新 `git status`、完整 diff、未提交重叠、PRD/spec/plan metadata；重新运行 PRD inspector，确认 topic/scope/approval 未失效。
- [ ] 定向验证：再次运行三个目标的 `check.py --skill ...` 组合命令、`git diff --check` 和 renderer exact bytes 测试；读取 `git status --short`，对其中每个以 `?? ` 标识且属于本任务的路径分别用 argv 运行 `git diff --no-index --check /dev/null -- PATH`。该命令退出码 `1` 且 stderr/stdout 均无 whitespace diagnostic 才算 clean。预期全部通过且 registry 仍为 `implemented`；不为获得 diff 检查而擅自 stage。
- [ ] Python 矩阵：分别用可用 Python 3.9 与 Python 3.14 运行三个目标的 `check.py --skill ...`；缺任一维护版本时保持完成门未满足，不把其它版本通过外推为兼容。
- [ ] 临时 staging：在首次完整评审前，由 `tests.test_verify_install` 的 integration fixture 使用现有 `stage_skill_payloads()` 将三个单 skill 和完整五-skill payload 放入独立临时 `CODEX_HOME`，再调用 `verify_install.py`；预期全部一致、目标只读、extra/different 负例确定失败。不得写真实安装；任何 reviewer finding 导致 publishable payload 变化时必须重跑 staging 后再复审。
- [ ] 首次完整评审：由一名未参与实现的 `workflow-final-reviewer` 检查批准范围、最新完整 diff、skill 触发/渐进加载、renderer、freshness/check/install、三个 RED/GREEN、公开文档、plugin、Python 与已经生成的 staging 证据。修复 findings 后重跑受影响验证及必要 staging，并交回同一 reviewer，直至最新完整 diff `APPROVED`。
- [ ] 评审写回：仅在真实 `APPROVED` 后，把三个 GREEN result 写为 `review_status: approved`，加入 generic reviewer/date，把三个 registry stage 改为 `review-approved`；不记录 Agent run id。
- [ ] 完整验证：运行 `.venv/bin/python scripts/check.py --full`；预期仓库 tests、五个 skill tests、严格 freshness、五个 official skill validators 与 plugin validator 全部实际通过。随后在 Python 3.9/3.14 重跑完整入口。
- [ ] 最终复审：将评审 metadata、完整 check、双版本和 staging 新证据交回同一 reviewer；只有最终 `APPROVED` 且无未解决高风险 finding 才完成。评审到此停止，不新增逐 skill 或重复 reviewer。
- [ ] 最终交付：报告实际 diff、验证命令/结果、评审 verdict、临时 staging、未验证项和真实安装尚未执行；不 commit、push、安装或发布。若用户随后明确授权真实安装，另行执行 staging → compare → 单实例刷新 → 写后 compare，不复用本任务授权。

## 实施评审策略

- 默认：Task 1～6 集成并通过 stage-aware 定向验证后，由一名未参与实现的 reviewer 检查最新完整 diff；修复范围内发现、重跑受影响验证并由同一 reviewer 复审至 `APPROVED`。写回评审 metadata 后完成 full check，再由同一 reviewer 做一次最终证据复核，随后停止。
- 中间里程碑评审：默认无。只有 Task 2 的 freshness 基础经过自动化验证后仍存在会使 Task 3～6 无法判断 evidence stage 的关键疑点，才对 `scripts/validate_repo.py`、`tests/test_evidence_freshness.py` 与相关 CLI contract 设置一次只读基础评审；不因 task 或 skill 数量增加门禁。

## 最终验证

```bash
.venv/bin/python scripts/check.py --skill creating-product-requirements --skill creating-development-specs-and-plans --skill generating-development-prompts
.venv/bin/python scripts/check.py --full
.venv/bin/python skills/creating-development-specs-and-plans/scripts/inspect_product_requirements.py --repo-root . --requirements docs/requirements/2026-07-18-workflow-efficiency-optimization.md --expected-topic workflow-efficiency-optimization --expected-scope phase
.venv/bin/python -m unittest tests.test_handoff_renderer tests.test_evidence_freshness tests.test_check tests.test_verify_install -v
git diff --check
```

在 Python 3.9 与 Python 3.14 环境分别重复定向和完整 `check.py`。预期三个受影响 skill 拥有有效 current RED、包含 exact `fresh_cases` 的新鲜 GREEN、一个覆盖最新完整 diff 的独立评审闭环；所有仓库、五-skill、official validator、plugin 和临时 staging 检查通过；真实安装、commit 与发布仍未执行。任一缺失证据保持为未完成或阻塞。
