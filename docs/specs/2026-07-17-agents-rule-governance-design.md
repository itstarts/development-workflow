---
document_type: design
topic: agents-rule-governance
requirements_path: docs/requirements/2026-07-17-agents-rule-governance.md
requirements_topic: agents-rule-governance
requirements_scope: feature
requirements_understanding_confidence: 97
requirements_understanding_confirmation: approved
requirements_user_approval: approved
requirements_independent_review: approved
specification_gate: open
user_approval: approved
approved_at: 2026-07-17
independent_review: approved
independent_reviewer: independent-spec-reviewer
independent_reviewed_at: 2026-07-17
---

# AGENTS 规则治理技术设计

## Goals

- 新增可独立安装的第五个 skill `managing-agents-rules`，在实质性开发任务开始前和完成时提供低打扰的 AGENTS 规则治理。
- 在修改目标项目前，按项目和当前会话检查根目录 `AGENTS.md`，正确区分 Git 根目录、非 Git 工作区根目录和子目录局部规则。
- 以会话内、按项目隔离的状态控制缺失提示、Git 初始化建议和完成阶段提示，拒绝后不在同一会话重复打扰。
- 仅从当前开发证据形成可复用规则候选，区分项目级和全局范围，并在没有合格候选时保持零提示。
- 对每次项目级或全局规则写入展示当前 diff，取得只覆盖该 diff 的明确批准，并在写入前后验证目标文件状态。
- 保持现有四个 skill 的职责和运行时内容独立；新 skill 不调用兄弟 skill，也不依赖 plugin cache、本机固定路径或 `agent-rules`。

## Non-goals

- 不修改现有四个 skill 的业务流程来嵌入重复的 AGENTS 检查逻辑。
- 不通过安装或首次运行自动修改全局 `AGENTS.md` 来启用新 skill。
- 不读取、修改、同步、安装或验证 `agent-rules` 仓库。
- 不把会话降噪状态持久化到项目文件、用户目录、缓存、数据库或其它跨会话存储。
- 不实现通用规则推荐模型、跨项目历史挖掘、后台监控或自动提交。
- 不改变 Codex 本身的 AGENTS 优先级、skill 选择机制、权限机制或 Git 行为。
- 不为该工作流新增依赖或要求联网服务。

## Current Evidence

- 已批准 PRD `docs/requirements/2026-07-17-agents-rule-governance.md` 固定了首次检查、会话降噪、Git 建议、候选规则门槛、逐次审批、全局直接更新和不触达 `agent-rules` 的产品边界。
- 根目录 `AGENTS.md` 要求创建新 skill 使用系统 `skill-creator`，严格执行 RED→GREEN→REFACTOR，并在新增 skill 后同步仓库 validator、官方 validator、安装测试和 plugin 验证。
- `skills/AGENTS.md` 要求 skill 以 `SKILL.md` 为精炼入口，把详细策略放入一层 `references/`，把 UI 元数据放入 `agents/openai.yaml`，并保持可独立安装、自包含和无本机路径依赖。
- `tests/AGENTS.md` 与 `evaluations/AGENTS.md` 要求测试先于生产行为，使用临时目录和虚构路径，保存无目标 skill 的 RED 与不同新鲜 Agent 的 GREEN 证据，不读取真实用户规则或生产状态。
- 当前四个 skill 均采用 `SKILL.md`、`agents/openai.yaml` 和按需 `references/`、`assets/`、`scripts/`、`tests/` 的自包含目录结构；新功能适合沿用相同发布边界。
- `scripts/validate_repo.py` 以 `evaluations/registry.json` 注册项为 skill/evidence 真源，检查 active skill、评估阶段、frontmatter、UI 元数据、占位符、本机路径和 plugin manifest。
- `tests/test_repository_contract.py`、README、安装文档、工作流文档、Agent 开发指南、CHANGELOG、根规则和最终 reviewer 当前包含“四个 skill”或固定四项清单，新增第五个 skill 时必须同步为当前事实。
- `.codex-plugin/plugin.json` 通过 `"skills": "./skills/"` 暴露整个 skill 目录；无需增加逐项 manifest 路径，但需要更新能力描述。当前版本仍为未发布的 `0.1.0`，本任务不执行发布或版本升级。
- [Codex 官方 AGENTS 发现规则](https://learn.chatgpt.com/docs/agent-configuration/agents-md.md)规定每层优先使用非空 `AGENTS.override.md`，否则使用 `AGENTS.md`。用户已明确选择长期规则优先：本功能以基础 `AGENTS.md` 为持久化目标，检测到 override 时只告警遮蔽状态，除非用户显式指定，否则不建议更新 override。

## Behavior and Boundaries

### Skill 触发边界

- 新 skill 名称固定为 `managing-agents-rules`。
- frontmatter `description` 必须以 `Use when` 开头，并明确覆盖两个触发点：实质性开发任务第一次写入之前，以及该开发任务完成时的规则候选检查。
- 实质性开发包括功能实现、Bug 修复、重构，以及会改变项目行为的测试、配置或工程文档修改。
- 只读分析、解释、评审、状态查询、日志检查、创建分支和纯 Git 操作不触发缺失提示。
- 新 skill 可以与负责实际开发的其它 skill 同时适用，但不得读取、导入或调用兄弟 skill；它只管理规则治理前置门和完成阶段候选。
- skill 安装本身不修改任何项目级或全局规则。是否触发由当前会话中可见的 skill 描述和实际任务类型决定。

### 项目身份与会话状态

- 当前会话维护一个仅存在于对话执行上下文中的逻辑状态表，以规范化项目根路径为项目键，并在项目内为每个逻辑开发任务维护独立任务状态；不得为该状态创建磁盘文件。
- 每个项目跟踪 `project_rules_check`、`git_init_prompt` 和零个或多个 `TaskCompletionState`。
- `project_rules_check` 的逻辑状态为 `unchecked | readable | missing | declined | created | unreadable`；`declined` 在当前会话内关闭该项目的所有项目级创建和更新提示。
- `git_init_prompt` 的逻辑状态为 `unchecked | not-applicable | declined | initialized | failed`；`declined` 在当前会话内关闭该项目的 Git 初始化提示。
- 每个 `TaskCompletionState` 的 `completion_scan` 为 `pending | completed`，保证每个逻辑开发任务只执行一次候选检查，不会被同项目其它未完成任务覆盖。
- 一次用户批准的整体范围或一次集成交付声明对应一个逻辑开发任务；同一请求中的多个实施切片在集成交付时扫描一次，分别交付或并行存在的独立范围使用不同的临时任务键。任务键只存在当前执行上下文，不使用或记录 Codex task/thread 标识符。
- 状态按项目隔离；同一会话进入另一个项目时，从该项目的 `unchecked` 状态开始。新会话不继承旧会话的拒绝或已检查状态。

### 项目根目录与项目级规则检查

- 在首次生产写入前先判断任务是否属于实质性开发，再解析项目根目录并读取适用规则。
- Git 工作区使用 `git rev-parse --show-toplevel` 的成功结果作为规范化项目根目录。
- 当前工作区不属于 Git 仓库时，使用运行时明确提供的工作区根目录；不得把任意当前子目录静默当作工作区根目录。
- 无法可靠取得工作区根目录时，报告阻塞原因，只继续安全的只读诊断，不进入生产文件修改。
- 项目级检查只判断项目根目录的 `AGENTS.md`。子目录 `AGENTS.md` 继续按既有作用域规则生效，但不能替代项目根规则。
- 项目根或适用子目录存在非空 `AGENTS.override.md` 时，仍按 Codex 既有优先级读取并遵守它，但 override 不替代长期项目级 `AGENTS.md` 的存在检查。
- 根目录 `AGENTS.md` 存在且可读时，将项目状态记为 `readable`，不产生缺失提示；新 skill 的检查不替代主 Agent 对所有适用规则的读取。
- 根目录文件存在但不可读时，将状态记为 `unreadable`，报告具体读取失败，不把文件当作缺失、不建议覆盖，并在恢复可读前阻止生产写入。
- 根目录文件缺失时，将状态记为 `missing`，基于实际仓库证据生成最小项目规则建议；不得用通用模板占位符伪造未知命令、技术栈或业务规则。非空 override 同时存在时，提示新建基础文件当前会被遮蔽，只有 override 被删除或置空后才会按默认发现顺序生效。

### 非 Git 项目的 Git 建议

- 非 Git 项目在首次检查时独立建议初始化 Git；项目规则创建和 Git 初始化是两个分别批准的动作。
- `git init` 只有在用户对该动作当次明确批准后才能执行；用户只批准项目规则 diff 不等于批准 Git 初始化。
- 执行 `git init` 时必须把已确认的非 Git 工作区根目录作为工作目录，不得在当前任意子目录初始化仓库。
- 用户拒绝后记录 `declined` 并在当前会话保持静默。执行失败时记录 `failed`、报告可观察错误，不自动重试，也不阻塞已经单独批准的项目规则创建或原开发任务。
- Git 初始化成功后重新确认 Git 根目录，并以该根目录继续当前项目状态；不得丢失同一工作区内已记录的拒绝或检查结果。

### 创建项目级 `AGENTS.md`

- 建议内容只能来自当前仓库中已读取的代码、配置、测试、文档、可用命令和用户明确规则；内容优先覆盖技术栈、构建/验证命令、架构边界、业务约束和工作区保护。
- 提示同时展示目标文件、每条规则的证据和归类理由，以及以不存在文件为基线的 unified diff。
- 用户批准只绑定当次展示的目标路径和 diff。创建前必须再次确认目标仍不存在；如果文件已经出现，旧批准失效，重新读取并展示更新 diff。
- 用户拒绝后将 `project_rules_check` 记为 `declined`，继续用户已经批准的原开发任务，本次会话不再出现项目级创建或更新提示。
- 创建成功后重新读取目标文件，确认展示的内容实际存在且没有附带未批准修改，再将状态记为 `created`；验证失败时报告未完成。

### 开发完成后的候选规则

- 在实际开发、相关文档同步和适用验证完成后，交付回复前执行一次任务级 completion scan；扫描范围只包含该逻辑任务的仓库证据、实际 diff、验证结果、已确认纠正和稳定操作事实。
- 候选必须同时满足：有本次证据支持、可在后续工作重复使用、不属于当前任务临时细节，并能有效减少后续重复确认、错误操作或验证成本。
- 与目标 `AGENTS.md` 已有语义重复、只描述本次结果、仅为推测、属于个人临时偏好或无法说明适用边界的内容直接淘汰。
- 项目技术栈、项目命令、目录/架构边界、业务规则和项目特有验证约束归入项目级候选；跨项目稳定适用的协作、工程、安全和验证原则可以归入全局候选。
- 每条候选都必须附带证据和归类理由。无法确定应归入项目还是全局时不写入，先请求用户选择范围。
- 项目状态为 `declined` 时丢弃项目级提示，但仍可提示一批独立的全局候选。
- 项目级候选的提示和已批准写入必须发生在目标仓库要求的最终独立评审之前，使项目 `AGENTS.md` 进入最新完整 diff、相关验证和最终评审。若项目规则在已有评审之后才改变，则原评审失效，必须重新运行受影响验证并由同一评审渠道复审最新 diff。
- 全局 `AGENTS.md` 位于目标仓库 diff 之外，可以在目标仓库最终评审后单独提示和写入；它不改变目标仓库 diff，但仍需自身的逐次批准和写后验证。
- 目标仓库或当前任务不要求独立评审时，不制造额外评审门；在所有适用验证和文档同步完成后执行 scan 并交付。
- 按目标文件集中提示一次；没有合格候选时不输出“没有候选”等规则治理消息。该逻辑任务完成扫描后，将其任务状态记为 `completed`。

### 全局 `AGENTS.md` 定位

- 先确定当前 Codex home：优先使用运行时明确暴露的 `CODEX_HOME`，未设置时使用 `$HOME/.codex`。长期全局规则的默认目标固定为该目录下的 `AGENTS.md`；不得把具体用户名或机器绝对路径写入 skill。
- 同时检查同一 Codex home 下的 `AGENTS.override.md`。当它存在且非空时，明确告知用户基础 `AGENTS.md` 当前被临时遮蔽，本次写入不会立即成为生效指导；不得因此自动改写 override。
- 只有用户显式指定 `AGENTS.override.md` 为当次目标时，才可以按完全相同的候选、diff、逐次批准和验证流程处理该文件；该显式选择不改变后续默认目标仍为基础 `AGENTS.md`。
- 候选写入前必须确认 Codex home 解析唯一，并校验当次选定目标是现有且可读取的文件：默认选择校验基础 `AGENTS.md`，显式 override 选择只校验现有 `AGENTS.override.md`，不要求基础文件同时存在或可读。向用户展示解析后的实际目标路径和当前遮蔽关系。
- 当次选定目标缺失、不可读或 Codex home 存在冲突时，不创建或猜测全局文件；报告未知项并请用户提供明确路径。显式选择不存在的 override 同样不得自动创建。
- 新 skill 不搜索、读取或更新 `agent-rules`，也不把是否同步该仓库作为当前写入成功条件。

### 逐次批准、写入与验证

- 每批修改先读取目标文件当前内容，过滤已有规则，构造最小 unified diff，并展示目标、候选、证据、归类理由和 diff。
- 项目级与全局修改分别批准；同一目标的不同批次也分别批准。一次批准不延续到下一批、下一任务或下一会话。
- 批准后、写入前再次读取目标并与生成 diff 时的完整内容逐字节比较；不使用固定哈希。内容变化、读取失败或目标身份变化都会使批准失效，必须基于最新状态重新展示并请求批准。
- 写入只应用已批准的最小补丁，保留无关内容和用户已有变更。平台对工作区外写入要求额外权限时，只能在用户已经批准具体 diff 后请求该权限；权限被拒绝时报告未更新。
- 写入后重新读取文件并检查已批准 diff 的预期结果，同时检查实际 diff 没有包含额外修改；只有检查成功才能报告更新完成。
- 候选或 diff 中发现密钥、令牌、凭证、个人隐私或其它不应进入规则文件的敏感内容时，停止该候选，不展示敏感值，也不写入。

## Components and Control Flow

### `skills/managing-agents-rules/SKILL.md`

- 保存精炼的触发条件、工作流顺序、批准门、零提示规则和硬边界。
- 要求先完成前置规则检查，再允许其它开发流程产生首个生产写入；完成阶段只处理规则候选，不接管目标功能实现。
- 明确不得调用兄弟 skill、不得持久化会话状态、不得操作 `agent-rules`、不得把一次批准扩展为长期授权。

### `skills/managing-agents-rules/references/task-lifecycle-and-session-state.md`

- 定义实质性任务分类、项目根解析、项目级文件状态、Git 初始化建议、逻辑状态表和跨项目/跨会话边界。

### `skills/managing-agents-rules/references/rule-candidates-and-scope.md`

- 定义候选证据门槛、去重、项目/全局归类、完成阶段零提示和用户拒绝后的过滤规则。

### `skills/managing-agents-rules/references/approval-and-write-safety.md`

- 定义目标路径解析、diff 展示、逐次批准、批准失效、最小补丁、权限失败、敏感内容和写后验证。

### `skills/managing-agents-rules/agents/openai.yaml`

- 由最终 `SKILL.md` 确定性生成 UI 元数据，display name、short description 和 default prompt 明确该 skill 管理项目级和全局 AGENTS 规则，不承诺自动写入。

### 测试、评估和仓库集成

- `skills/managing-agents-rules/tests/test_skill_contract.py` 检查 frontmatter、触发语、引用完整性、前置/完成阶段、会话状态、逐次批准、全局路径和禁止操作边界。
- `evaluations/managing-agents-rules/` 使用 `creation-only` managed profile，包含冻结 rubric、无目标 skill baseline、GREEN 输出和独立评审元数据。原始 trace 只保存在被忽略的 `work/`。
- 评估场景至少覆盖：已有根规则零提示、缺失规则创建/拒绝、不可读规则阻断、非 Git 初始化批准/拒绝、同会话两个项目隔离、同项目两个独立任务状态、完成阶段项目候选在最终评审前写入、与 `implementing-bounded-changes` 同时适用时的写后验证和最新 diff 复审、无需评审的轻量任务、全局基础文件与 override 遮蔽告警、基础文件缺失或不可读时显式选择现有可读 override、显式选择不存在 override 时拒绝创建、全局候选逐次批准、无候选零提示、目标变化使批准失效、`agent-rules` 禁止边界。
- `evaluations/registry.json` 注册新 skill；`scripts/validate_repo.py` 和 `tests/test_repository_contract.py` 更新为五-skill 真源、打包、安装和文档契约。
- README、`docs/install.md`、`docs/workflow.md`、`docs/agent-development.md`、CHANGELOG、根 `AGENTS.md`、plugin manifest 和 `workflow-final-reviewer.toml` 同步当前五-skill 能力与验证命令。

### 控制流

1. skill 根据当前任务判断是否触发前置检查；不适用时不产生提示。
2. 解析规范化项目根并读取根目录规则状态；不可读或根未知时阻止生产写入。
3. 对缺失项目规则和非 Git 状态分别形成建议；每个动作独立展示并取得批准，拒绝状态写入会话逻辑状态表。
4. 原开发流程在适用规则可读取或缺失提示已处理后继续；新 skill 不执行目标功能开发。
5. 开发、文档同步和适用验证完成后，从当前逻辑任务证据形成并过滤候选，按项目级或全局目标分组。
6. 项目级候选在目标仓库最终评审前读取最新目标、展示 diff、逐次批准、确认基线未变化、应用最小补丁并验证；重新运行受影响验证，如任务要求最终评审，把修改后的最新完整 diff 和验证证据交由该评审渠道检查。
7. 全局候选可以在目标仓库最终评审后单独处理；检查基础目标和 override 遮蔽状态，再按逐次批准和写后验证流程执行。
8. 没有候选或被会话拒绝状态抑制的目标保持静默，对应逻辑任务完成后不重复扫描。

## API and Technical Interfaces

- 公开调用接口是 skill 名称 `$managing-agents-rules`、frontmatter `description` 和 `agents/openai.yaml` UI 元数据；不新增网络 API、命令行 API 或跨 skill import。
- 与开发任务的输入来自当前用户请求、运行时工作区/权限信息、适用规则、仓库证据、当前 diff 和验证结果。
- 用户可见输出只在需要决策或存在合格候选时产生，结构至少包含：触发原因、目标路径、动作、候选规则、证据、归类理由、unified diff、所需的单次批准和失败状态。
- 项目级或全局写入不是隐式接口调用；它们是当前会话内、由用户批准具体 diff 后执行的本地文件修改。
- 仓库发布接口继续由 `.codex-plugin/plugin.json` 的 `skills: ./skills/` 暴露全部 skill。公开安装命令新增 `skills/managing-agents-rules` 路径，但现有单 skill 安装方式不变。

## Data Model and Entity Relationships

本功能不增加持久化业务数据模型。运行时只使用以下会话逻辑实体：

- `ProjectSessionState`
  - `project_root`: 规范化且唯一的项目根路径，用作会话内键。
  - `root_source`: `git | workspace`。
  - `project_rules_check`: `unchecked | readable | missing | declined | created | unreadable`。
  - `git_init_prompt`: `unchecked | not-applicable | declined | initialized | failed`。
- `TaskCompletionState`
  - `task_key`: 当前执行上下文内的临时逻辑键，不是 Codex task/thread 标识符。
  - `scope_summary`: 当前用户批准范围或集成交付范围的简短摘要。
  - `completion_scan`: `pending | completed`。
- `RuleCandidate`
  - `text`: 建议规则正文。
  - `evidence`: 本次开发中的可定位证据摘要。
  - `scope`: `project | global`。
  - `reason`: 复用价值和归类理由。
  - `target_path`: 当前解析并向用户展示的目标文件。
- `ApprovalSnapshot`
  - `target_path`: 用户批准的目标。
  - `baseline_content`: 生成 diff 时读取的完整内容，仅保留于当前执行上下文。
  - `proposed_diff`: 用户实际批准的最小补丁。

实体均不写入磁盘。一个项目对应一个 `ProjectSessionState`，一个项目可以关联多个独立 `TaskCompletionState`；一次任务级 completion scan 可以产生零个或多个 `RuleCandidate`；每批待写候选对应一个独立 `ApprovalSnapshot`。

## State Transitions, Migration Boundaries, and Consistency

- `project_rules_check`：`unchecked → readable | missing | unreadable`；`missing → declined | created`；目标在批准前出现时重新进入 `readable` 路径并使旧批准失效；`unreadable` 只有恢复可读并重新检查后才能进入 `readable`。
- `git_init_prompt`：Git 项目直接 `unchecked → not-applicable`；非 Git 项目经用户选择进入 `declined`，或经执行进入 `initialized | failed`。
- `TaskCompletionState.completion_scan`：每个逻辑开发任务创建时为 `pending`，交付阶段完成候选过滤后转为 `completed`；同一任务不回退，新的独立任务创建新的状态，不覆盖现有任务状态。
- 本功能没有仓库数据迁移、数据库迁移、事务或跨进程并发控制。
- 文件一致性边界是“展示 diff 时的完整基线内容”到“实际写入前的最新内容”。两者不一致时禁止写入并重新审批；这是一种乐观一致性检查，不持有长期文件锁。
- 写入完成与否以写后读取和实际 diff 为准；部分写入、额外修改或无法读取都不能标记为成功。
- 新 skill 加入 plugin 是向后兼容的能力增加，不改变现有四个 skill 的输入/输出合同。由于 `0.1.0` 尚未发布，本任务保持现有 manifest 版本并更新其能力描述；发布版本决策不属于本任务。

## Errors and Uncertainty

- 任务类型无法确定：在首次生产写入前说明判断依据并请求用户确认是否属于实质性开发，不静默跳过可能适用的规则检查。
- Git 根解析失败但运行时工作区根明确：按非 Git 工作区处理；两者都不明确时阻止生产写入并报告未知根目录。
- 项目级规则不可读：报告读取错误，不当作缺失、不覆盖，只允许安全只读诊断。
- 当次选定的全局规则目标缺失、冲突或不可读：不猜测、不创建、不改写其它路径；请求用户提供明确的现有可读目标。
- 非空 `AGENTS.override.md` 遮蔽基础文件：告知当前生效影响，默认仍只建议长期基础 `AGENTS.md`；除非用户显式指定，否则不把 override 作为写入目标。
- 用户拒绝：只更新当前会话对应项目和动作的逻辑状态，不写入拒绝记录文件，不影响其它项目。
- 目标内容变化：批准失效，重新读取、去重、生成 diff 并逐次请求批准。
- 权限升级被拒绝、补丁失败或写后验证失败：明确报告未更新和已知影响，不回退或覆盖用户内容。
- 无法确认候选的证据、复用价值或归属：不将其升级为规则；只有归属会改变而其它条件均满足时才向用户询问范围。
- 运行时无法可靠保存会话状态：不得持久化补偿；说明可能出现重复提示的限制，同时仍保持所有写入逐次批准。

## Testing and Documentation

### TDD 和评估

- 实施必须使用系统 `skill-creator`，先冻结评估 rubric 和虚构场景，再由看不到目标 skill 的新鲜 Agent 运行 baseline，保存有效 RED；目标 skill 目录只能在 baseline 完成后初始化。
- `evaluations/registry.json` 先以 `creation-only`、`stage: baseline-only` 注册并完成 pre-creation audit 与 migration baseline；创建生产 skill 后切换为 `stage: implemented`，此时运行 `--evidence-only managing-agents-rules` 验证 GREEN；独立评审批准并写回 GREEN 元数据后再切换为 `stage: review-approved`。不得在最终状态错误调用只接受 `implemented` 的 evidence-only 模式。
- 在生产 skill 之前新增仓库级和 skill 合同测试并观察目标缺失导致的 RED；不得用语法错误或无关环境失败充当 RED。
- 编写最小 `SKILL.md` 和 references 后运行定向合同测试、官方 `quick_validate.py`、仓库 validator，再由不同的新鲜 Agent 对相同场景运行 GREEN。
- GREEN 输出不得看到 expected、baseline 失败分析或实现结论；版本化材料只保留脱敏场景、判据、选中输出和结构化结果。

### 自动化验证

- 新 skill 定向测试：`.venv/bin/python -m unittest discover -s skills/managing-agents-rules/tests -v`。
- 仓库契约测试：`.venv/bin/python -m unittest discover -s tests -v`。
- 仓库 validator：`.venv/bin/python scripts/validate_repo.py`。
- 新 skill evidence 验证：仅在 registry 为 `stage: implemented` 时运行 `.venv/bin/python scripts/validate_repo.py --evidence-only managing-agents-rules`；切换为 `review-approved` 后运行普通仓库 validator。
- 官方 skill validator：`.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/managing-agents-rules`。
- plugin validator：`.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" .`。
- 最终回归还要运行现有四个 skill 的测试、官方 validator 和完整仓库验证，确认新增触发描述没有改变现有职责合同。
- 使用临时 `CODEX_HOME` 做独立安装和五-skill plugin staging，确认不覆盖已有目标；不得安装到真实 skill home。
- 最终检查 `git diff --check`，并由未参与实现的 skill reviewer 与 workflow final reviewer 检查最新 diff、RED/GREEN 证据、触发冲突、打包、安装边界和文档当前事实。

### 文档同步

- README：工作流入口、skills 表、完整安装命令和五-skill 描述。
- `docs/install.md`：全量与单 skill 安装路径、五-skill 独立安装说明。
- `docs/workflow.md`：增加 AGENTS 规则治理独立入口以及与其它开发流程并行适用但不互相调用的边界。
- `docs/agent-development.md`、根 `AGENTS.md`：把四-skill 当前事实、验证命令和最终评审范围更新为五-skill。
- CHANGELOG：在未发布 `0.1.0` 下增加 `managing-agents-rules` 条目并更新 Repository 能力描述。
- `.codex-plugin/plugin.json`：更新 description、shortDescription、longDescription 和 defaultPrompt，使第五个 skill 可发现；版本保持 `0.1.0`。
- `.codex/agents/workflow-final-reviewer.toml`：将最终全量评审范围更新为完整五-skill plugin；`docs/agent-development.md` 同步角色说明。

## Acceptance Criteria

1. 仓库新增可独立安装的 `skills/managing-agents-rules`，frontmatter 和 UI 元数据能触发实质性开发前置检查与完成阶段规则候选检查，且不调用兄弟 skill。
2. Git 项目、非 Git 工作区、局部 `AGENTS.md`、根规则已存在、根规则缺失和根规则不可读场景均产生本 spec 规定的行为。
3. 同一会话内的缺失提示和 Git 建议按项目隔离，完成扫描按项目内逻辑任务隔离；拒绝后当前会话静默，新项目仍独立检查，并行或分别交付的任务不会覆盖彼此状态，且不写入持久化状态或 Codex task/thread 标识符。
4. 缺失项目规则只有在展示目标、证据、理由和创建 diff 并获得当次批准后才创建；目标状态变化会使批准失效。
5. 非 Git 项目的 `git init` 与项目规则创建分别批准；拒绝或失败不会形成未授权初始化，也不会错误阻塞另一动作。
6. 完成阶段只接受同时满足证据、复用性、非临时性和效率价值的候选，正确区分项目/全局范围；无候选时零提示。
7. 项目规则被拒绝后不再出现项目级提示，但独立合格的全局候选仍可集中提示一次。
8. 全局长期目标固定为当前 Codex home 的基础 `AGENTS.md`；非空 `AGENTS.override.md` 只产生遮蔽告警，除非用户显式指定否则不更新。校验只针对当次选定目标：默认基础文件或显式 override 必须已存在且可读，缺失、冲突或不可读时不猜测、不创建，也不操作 `agent-rules`。
9. 每次项目级或全局写入都绑定当前 diff；写入前基线变化、读取失败或目标变化会关闭原批准并重新请求，写后验证只认可已批准修改。
10. 项目级规则写入进入目标仓库最新完整 diff、受影响验证和适用的最终独立评审；全局规则保持仓库外独立批准。无需独立评审的任务不增加虚假门禁。
11. 新 skill 与 `implementing-bounded-changes` 同时适用的前向场景证明规则写入不会绕过最新 diff 评审，也不会接管或重复 bounded implementation 的职责。
12. 新 skill 的 registry 按 `baseline-only → implemented → review-approved` 推进，RED、GREEN、合同测试、官方 validator、仓库 validator、plugin validator、临时安装和独立评审证据完整，且现有四个 skill 回归通过。
13. plugin manifest、README、安装/工作流/Agent 开发文档、根规则、CHANGELOG、仓库契约测试和最终 reviewer 全部反映五-skill 当前事实，真实 skill home 和 `agent-rules` 保持未操作。
